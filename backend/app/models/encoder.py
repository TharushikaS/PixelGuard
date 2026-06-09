"""
HiDDeN Encoder — implementation faithful to:

  Zhu, Kaplan, Johnson, Fei-Fei. "HiDDeN: Hiding Data with Deep Networks."
  ECCV 2018.

…with the extensions called out in our project proposal:

  * Fully-Convolutional Network (resolution-agnostic — no dense layers in
    the message-handling path; works on any H×W at inference time).
  * Residual blocks for high-frequency preservation (PSNR > 40 dB target).
  * Residual-output formulation: the encoder predicts a small additive
    perturbation `delta`, and  I_en = clip(I_co + α · delta, 0, 1).
    This trains far more stably than learning the full stego image from
    scratch, and matches what most HiDDeN reimplementations do.

The message is treated as a "global statistical bias dispersed throughout
the image" — every spatial location sees the full message via spatial
replication, then convolutions decide how to thread it into the textures.
"""
from __future__ import annotations

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers


# ---------------------------------------------------------------------------
# Conv block + Residual block
# ---------------------------------------------------------------------------
class ConvBNReLU(layers.Layer):
    """3×3 conv → BN → ReLU. The building block used throughout."""

    def __init__(self, channels: int, kernel: int = 3, **kw):
        super().__init__(**kw)
        self.conv = layers.Conv2D(channels, kernel, padding="same", use_bias=False)
        self.bn = layers.BatchNormalization()
        self.act = layers.ReLU()

    def call(self, x, training=False):
        return self.act(self.bn(self.conv(x), training=training))


class ResidualBlock(layers.Layer):
    """Standard residual block: x + Conv(BN(Conv(BN(x))))."""

    def __init__(self, channels: int, **kw):
        super().__init__(**kw)
        self.conv1 = ConvBNReLU(channels)
        self.conv2 = layers.Conv2D(channels, 3, padding="same", use_bias=False)
        self.bn2 = layers.BatchNormalization()

    def call(self, x, training=False):
        h = self.conv1(x, training=training)
        h = self.bn2(self.conv2(h), training=training)
        return tf.nn.relu(x + h)


# ---------------------------------------------------------------------------
# Encoder
# ---------------------------------------------------------------------------
class Encoder(keras.Model):
    """
    Inputs:
        cover   — (B, H, W, 3) image in [0, 1]
        message — (B, L) binary bits (float32, 0.0 or 1.0)

    Output:
        stego   — (B, H, W, 3) image in [0, 1], visually close to `cover`

    Architecture (paper-faithful with proposal's residual extension):

        cover  ──► ConvBNReLU(C)
                         │ image feats (B, H, W, C)
        message ──► tile to (B, H, W, L)
                         │
                concat (cover + image_feats + msg_volume)
                         │
                1×1 fuse conv  ──►  (B, H, W, C)
                         │
                ResidualBlock × N
                         │
                1×1 conv → 3 channels, tanh
                         │
                delta ∈ [-1, 1]
                         │
                stego = clip(cover + α · delta, 0, 1)
    """

    def __init__(
        self,
        message_length: int = 32,
        conv_channels: int = 64,
        num_residual_blocks: int = 4,
        perturbation_scale: float = 0.1,
    ):
        super().__init__()
        self.L = message_length
        self.perturbation_scale = perturbation_scale

        # Image feature extraction (kept at full resolution — FCN style)
        self.image_conv = ConvBNReLU(conv_channels)

        # 1×1 projection after concat (cover + img_feats + msg_volume → conv_channels)
        self.fuse = layers.Conv2D(
            conv_channels, 1, padding="same", activation="relu"
        )

        # Residual stack — learns the embedding
        self.residual_blocks = [
            ResidualBlock(conv_channels) for _ in range(num_residual_blocks)
        ]

        # Predict the residual / perturbation. tanh keeps it in [-1, 1].
        self.delta_conv = layers.Conv2D(3, 1, padding="same", activation="tanh")

    def call(self, inputs, training=False):
        cover, message = inputs

        B = tf.shape(cover)[0]
        H = tf.shape(cover)[1]
        W = tf.shape(cover)[2]

        # ---- image features ----
        img_feats = self.image_conv(cover, training=training)

        # ---- message volume: replicate the L bits at every (h, w) ----
        # message: (B, L) → (B, 1, 1, L) → tile to (B, H, W, L)
        msg = tf.reshape(message, (B, 1, 1, self.L))
        msg_vol = tf.tile(msg, (1, H, W, 1))

        # ---- fuse cover + image features + message volume ----
        x = tf.concat([cover, img_feats, msg_vol], axis=-1)
        x = self.fuse(x)

        # ---- residual stack ----
        for block in self.residual_blocks:
            x = block(x, training=training)

        # ---- predict the small additive perturbation ----
        delta = self.delta_conv(x)              # (B, H, W, 3), values in [-1, 1]

        # ---- compose stego image ----
        stego = tf.clip_by_value(
            cover + self.perturbation_scale * delta, 0.0, 1.0
        )
        return stego
