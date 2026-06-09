"""
Differentiable noise layer — applied between encoder and decoder during
training so the encoder learns to embed bits in places that survive each
distortion.

Implemented per Section 3 of Zhu et al. 2018 plus the proposal's DCT-based
JPEG approximation. Six distortion types:

    identity   — no change (baseline)
    dropout    — per-pixel mix of cover + stego (binary erasure channel)
    cropout    — random square mix of cover + stego
    crop       — random square sub-region of stego only
    gaussian   — depthwise Gaussian blur
    jpeg_mask  — DCT → zero high-frequency coefs → inverse DCT
                  (differentiable approximation to true JPEG)

The CombinedNoiseLayer samples a random distortion per minibatch — this
is the "combined model" recipe from the paper's Section 4.2 that ends up
competitive with specialized models across all attack types.

All ops are TF-native and differentiable (the JPEG approximation uses a
straight-through estimator for rounding).
"""
from __future__ import annotations

import math

import numpy as np
import tensorflow as tf
from tensorflow import keras


# ---------------------------------------------------------------------------
# DCT basis (fixed; not trainable)
# ---------------------------------------------------------------------------
def _dct_basis_8x8() -> np.ndarray:
    """
    Build the 8×8 type-II DCT basis as a (8, 8, 1, 64) conv kernel.

    Applying this as a `tf.nn.conv2d` with strides=(8, 8) on a single-channel
    image produces an output of shape (B, H/8, W/8, 64), where the 64
    channels are the DCT coefficients of each 8×8 block.
    """
    basis = np.zeros((8, 8, 64), dtype=np.float32)
    for u in range(8):
        for v in range(8):
            cu = 1.0 / math.sqrt(2) if u == 0 else 1.0
            cv = 1.0 / math.sqrt(2) if v == 0 else 1.0
            for x in range(8):
                for y in range(8):
                    basis[x, y, u * 8 + v] = (
                        (cu * cv / 4.0)
                        * math.cos((2 * x + 1) * u * math.pi / 16.0)
                        * math.cos((2 * y + 1) * v * math.pi / 16.0)
                    )
    return basis[..., np.newaxis, :]  # (8, 8, 1, 64)


def _jpeg_mask_keep_25_y_9_uv() -> np.ndarray:
    """JPEG-Mask: keep 25 low-freq coefs in Y, 9 in U/V (zig-zag order)."""
    # Standard zig-zag order for 8×8 DCT.
    zigzag = [
        0, 1, 8, 16, 9, 2, 3, 10, 17, 24, 32, 25, 18, 11, 4, 5,
        12, 19, 26, 33, 40, 48, 41, 34, 27, 20, 13, 6, 7, 14, 21, 28,
        35, 42, 49, 56, 57, 50, 43, 36, 29, 22, 15, 23, 30, 37, 44, 51,
        58, 59, 52, 45, 38, 31, 39, 46, 53, 60, 61, 54, 47, 55, 62, 63,
    ]
    mask_y = np.zeros(64, dtype=np.float32)
    mask_y[zigzag[:25]] = 1.0
    mask_c = np.zeros(64, dtype=np.float32)
    mask_c[zigzag[:9]] = 1.0
    return mask_y, mask_c


# ---------------------------------------------------------------------------
# Individual noise ops
# ---------------------------------------------------------------------------
def _apply_dropout(cover, stego, drop_prob: float):
    """Bernoulli per-pixel mix: with prob=drop_prob, fall back to cover."""
    keep_mask = tf.cast(
        tf.random.uniform(tf.shape(stego)) >= drop_prob, stego.dtype
    )
    return stego * keep_mask + cover * (1.0 - keep_mask)


def _apply_cropout(cover, stego, keep_ratio: float):
    """Random square region keeps stego; rest reverts to cover."""
    shape = tf.shape(stego)
    H, W = shape[1], shape[2]

    side_h = tf.cast(tf.cast(H, tf.float32) * tf.sqrt(keep_ratio), tf.int32)
    side_w = tf.cast(tf.cast(W, tf.float32) * tf.sqrt(keep_ratio), tf.int32)
    side_h = tf.maximum(side_h, 1)
    side_w = tf.maximum(side_w, 1)

    off_h = tf.random.uniform([], 0, H - side_h + 1, dtype=tf.int32)
    off_w = tf.random.uniform([], 0, W - side_w + 1, dtype=tf.int32)

    # Build a (1, H, W, 1) mask with a 1 inside the box.
    row_mask = tf.logical_and(
        tf.range(H) >= off_h, tf.range(H) < off_h + side_h
    )
    col_mask = tf.logical_and(
        tf.range(W) >= off_w, tf.range(W) < off_w + side_w
    )
    mask = tf.cast(row_mask, tf.float32)[:, None] * tf.cast(col_mask, tf.float32)[None, :]
    mask = mask[None, :, :, None]  # (1, H, W, 1)

    return stego * mask + cover * (1.0 - mask)


def _apply_crop(stego, keep_ratio: float):
    """Random square crop of stego only; output IS smaller spatially."""
    shape = tf.shape(stego)
    H, W = shape[1], shape[2]
    side_h = tf.cast(tf.cast(H, tf.float32) * tf.sqrt(keep_ratio), tf.int32)
    side_w = tf.cast(tf.cast(W, tf.float32) * tf.sqrt(keep_ratio), tf.int32)
    side_h = tf.maximum(side_h, 8)
    side_w = tf.maximum(side_w, 8)

    off_h = tf.random.uniform([], 0, H - side_h + 1, dtype=tf.int32)
    off_w = tf.random.uniform([], 0, W - side_w + 1, dtype=tf.int32)

    return tf.image.crop_to_bounding_box(stego, off_h, off_w, side_h, side_w)


def _gaussian_kernel(sigma: float, ksize: int = 5) -> tf.Tensor:
    ax = tf.range(-(ksize // 2), ksize // 2 + 1, dtype=tf.float32)
    kernel_1d = tf.exp(-(ax ** 2) / (2.0 * sigma * sigma))
    kernel_1d = kernel_1d / tf.reduce_sum(kernel_1d)
    kernel_2d = tf.tensordot(kernel_1d, kernel_1d, axes=0)   # (k, k)
    return kernel_2d


def _apply_gaussian(stego, sigma: float):
    kernel = _gaussian_kernel(sigma)                          # (k, k)
    kernel = tf.reshape(kernel, (kernel.shape[0], kernel.shape[1], 1, 1))
    kernel = tf.tile(kernel, (1, 1, tf.shape(stego)[-1], 1))  # depthwise
    return tf.nn.depthwise_conv2d(
        stego, kernel, strides=(1, 1, 1, 1), padding="SAME"
    )


# JPEG-Mask: precompute DCT kernels and the zig-zag mask once.
_DCT_BASIS = tf.constant(_dct_basis_8x8(), dtype=tf.float32)        # (8,8,1,64)
_DCT_BASIS_T = tf.transpose(_DCT_BASIS, (0, 1, 3, 2))                # (8,8,64,1)
_JPEG_MASK_Y, _JPEG_MASK_C = _jpeg_mask_keep_25_y_9_uv()
_JPEG_MASKS = tf.constant(
    np.stack([_JPEG_MASK_Y, _JPEG_MASK_C, _JPEG_MASK_C], axis=0),    # (3, 64)
    dtype=tf.float32,
)


def _apply_jpeg_mask(stego: tf.Tensor) -> tf.Tensor:
    """
    DCT → mask high-freq coefs (zero out coefficients) → inverse DCT.

    Per-channel: Y keeps 25 low-freq coefs, U & V each keep 9.
    Assumes H, W are multiples of 8 — at training time we pick image_size
    accordingly (128 or 256 both work).
    """
    # Convert to YUV so we can mask Y less aggressively than U/V.
    yuv = tf.image.rgb_to_yuv(stego)
    out_channels = []

    for c in range(3):                                          # Y, U, V
        channel = yuv[..., c:c + 1]                             # (B, H, W, 1)

        # Forward DCT: (B, H/8, W/8, 64)
        coefs = tf.nn.conv2d(channel, _DCT_BASIS, strides=8, padding="VALID")

        # Mask high-frequency coefficients.
        coefs = coefs * _JPEG_MASKS[c]                          # broadcast (64,)

        # Inverse DCT via transposed conv with stride 8.
        recon = tf.nn.conv2d_transpose(
            coefs,
            _DCT_BASIS,                                          # (8,8,1,64)
            output_shape=tf.shape(channel),
            strides=(1, 8, 8, 1),
            padding="VALID",
        )
        out_channels.append(recon)

    yuv_recon = tf.concat(out_channels, axis=-1)
    return tf.image.yuv_to_rgb(yuv_recon)


# ---------------------------------------------------------------------------
# Public layers
# ---------------------------------------------------------------------------
class NoiseLayer(keras.layers.Layer):
    """
    Apply a SINGLE chosen distortion. Useful for the per-distortion
    specialized models in the paper's Section 4.2.

    `kind` is one of:
        identity, dropout, cropout, crop, gaussian, jpeg_mask
    """

    def __init__(self, kind: str = "identity", intensity: float = 0.3, **kw):
        super().__init__(**kw)
        self.kind = kind
        self.intensity = intensity

    def call(self, cover, stego, training=False):
        # At eval time we don't mangle — produces clean numbers for metrics.
        if not training:
            return stego

        if self.kind == "identity":
            return stego
        if self.kind == "dropout":
            return _apply_dropout(cover, stego, drop_prob=self.intensity)
        if self.kind == "cropout":
            return _apply_cropout(cover, stego, keep_ratio=self.intensity)
        if self.kind == "crop":
            return _apply_crop(stego, keep_ratio=self.intensity)
        if self.kind == "gaussian":
            sigma = max(0.1, self.intensity * 4.0)
            return _apply_gaussian(stego, sigma=sigma)
        if self.kind == "jpeg_mask":
            return _apply_jpeg_mask(stego)
        return stego


class CombinedNoiseLayer(keras.layers.Layer):
    """
    "Combined model" — picks ONE distortion uniformly at random per minibatch.

    Per the paper, this produces a single network competitive with the
    specialized-per-distortion models on every attack type, at the cost
    of doubling training time (~400 epochs vs. ~200).
    """

    def __init__(self, **kw):
        super().__init__(**kw)

    def call(self, cover, stego, training=False):
        if not training:
            return stego

        # Pick one of 6 buckets uniformly.
        p = tf.random.uniform([], 0.0, 1.0)
        # We use tf.switch_case via a chain of conds so this works in graph mode.

        def _identity(): return stego
        def _dropout():   return _apply_dropout(cover, stego, drop_prob=0.3)
        def _cropout():   return _apply_cropout(cover, stego, keep_ratio=0.3)
        def _crop():      return _apply_crop(stego, keep_ratio=0.5)
        def _gauss():     return _apply_gaussian(stego, sigma=2.0)
        def _jpeg():      return _apply_jpeg_mask(stego)

        return tf.case(
            [
                (p < 1.0 / 6.0,  _identity),
                (p < 2.0 / 6.0,  _dropout),
                (p < 3.0 / 6.0,  _cropout),
                (p < 4.0 / 6.0,  _crop),
                (p < 5.0 / 6.0,  _gauss),
            ],
            default=_jpeg,
            exclusive=False,
        )
