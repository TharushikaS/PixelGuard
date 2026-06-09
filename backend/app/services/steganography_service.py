"""
Neural-network steganography service — uses the trained HiDDeN-style
encoder/decoder to embed and recover a 32-bit tracking ID inside an image.

The encoder operates on float images in [0, 1] of shape (H, W, 3) at the
training resolution (default 128×128). The tracking ID is converted to a
32-bit bitstring; the decoder predicts those bits back.

This service is selected when STEGO_METHOD=neural in the .env. Until you
train the model (and place weights under MODEL_PATH), the network runs
with random weights and will not produce useful results — the LSB service
is the safe demo default.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Tuple

import numpy as np
import tensorflow as tf

from app.config import settings
from app.models import Decoder, Encoder
from app.utils import MetricsCalculator


# ---------------------------------------------------------------------------
# Helpers: tracking-ID  ↔  32-bit array
# ---------------------------------------------------------------------------
def _tracking_id_to_bits(tracking_id: str, n_bits: int) -> np.ndarray:
    """
    Map an 8-hex-char tracking ID (or any hex string) into an n_bits bit array.
    Right-pads with zeros if shorter; truncates if longer.
    """
    # Treat the hex string as an integer.
    try:
        value = int(tracking_id, 16)
    except ValueError:
        # Fall back: use the int hash of the string.
        value = abs(hash(tracking_id)) & ((1 << n_bits) - 1)
    bits = np.zeros(n_bits, dtype=np.float32)
    for i in range(n_bits):
        bits[n_bits - 1 - i] = (value >> i) & 1
    return bits


def _bits_to_tracking_id(bits: np.ndarray) -> str:
    """Inverse of _tracking_id_to_bits — produce a hex string."""
    value = 0
    for b in bits:
        value = (value << 1) | int(b > 0.5)
    n_hex = (bits.size + 3) // 4
    return f"{value:0{n_hex}x}"


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------
class SteganographyService:
    """Trained neural encoder/decoder. Same interface as LSBSteganographyService."""

    def __init__(self):
        self.message_length = settings.MESSAGE_LENGTH
        self.image_size = settings.IMAGE_SIZE

        self.encoder = Encoder(message_length=self.message_length)
        self.decoder = Decoder(message_length=self.message_length)

        # Force a build so weight files can be loaded against a known shape.
        dummy_cover = tf.zeros((1, self.image_size, self.image_size, 3))
        dummy_msg = tf.zeros((1, self.message_length))
        _ = self.encoder([dummy_cover, dummy_msg], training=False)
        _ = self.decoder(dummy_cover, training=False)

        self._loaded = self._load_weights()

    # ------------------------------------------------------------------
    # Weight management
    # ------------------------------------------------------------------
    def _load_weights(self) -> bool:
        # Keras 3 .weights.h5 format (newer). Also try the old TF-checkpoint
        # prefix format for back-compat with weights saved on TF 2.15.
        candidates = {
            "encoder": [
                os.path.join(settings.MODEL_PATH, "encoder.weights.h5"),
                os.path.join(settings.MODEL_PATH, "encoder"),  # TF<=2.15 checkpoint
            ],
            "decoder": [
                os.path.join(settings.MODEL_PATH, "decoder.weights.h5"),
                os.path.join(settings.MODEL_PATH, "decoder"),
            ],
        }

        def _load(net, paths, label):
            for p in paths:
                # h5: file must exist directly. checkpoint: a .index sibling.
                exists = os.path.exists(p) or os.path.exists(p + ".index")
                if exists:
                    try:
                        net.load_weights(p)
                        print(f"[stego/neural] loaded {label} from {p}")
                        return True
                    except Exception as exc:  # noqa: BLE001
                        print(f"[stego/neural] {label} load failed at {p}: {exc}")
            print(f"[stego/neural] no {label} weights found (random init)")
            return False

        ok_e = _load(self.encoder, candidates["encoder"], "encoder")
        ok_d = _load(self.decoder, candidates["decoder"], "decoder")
        return ok_e and ok_d

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def generate_tracking_id(self) -> str:
        """
        Generate an N/4-hex-char tracking ID where N = MESSAGE_LENGTH bits.
        E.g. 32 bits → 8 hex chars.
        """
        n_hex = self.message_length // 4
        # Random N-bit integer rendered as hex.
        value = int.from_bytes(os.urandom((self.message_length + 7) // 8), "big")
        value &= (1 << self.message_length) - 1
        return f"{value:0{n_hex}x}"

    def encode(
        self,
        cover_image: np.ndarray,
        tracking_id: str,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        cover_image: (H, W, 3), float in [0, 1] OR uint8.
        Returns the stego image (same dtype family as input — float [0,1] preferred).
        """
        # Coerce to float32 [0, 1]
        was_uint8 = (cover_image.dtype == np.uint8)
        x = cover_image.astype(np.float32)
        if was_uint8 or x.max() > 1.5:
            x = x / 255.0

        # Resize to the training resolution. The network is technically FCN,
        # but it's been trained at one resolution, so we honor that.
        if x.shape[0] != self.image_size or x.shape[1] != self.image_size:
            x = tf.image.resize(x, (self.image_size, self.image_size)).numpy()

        bits = _tracking_id_to_bits(tracking_id, self.message_length)
        cover_b = x[np.newaxis, ...]                          # (1, H, W, 3)
        bits_b = bits[np.newaxis, ...]                        # (1, L)

        stego = self.encoder([cover_b, bits_b], training=False).numpy()[0]
        stego = np.clip(stego, 0.0, 1.0)

        psnr = MetricsCalculator.calculate_psnr(x, stego)
        ssim = MetricsCalculator.calculate_ssim(x, stego)
        metrics = {
            "tracking_id": tracking_id,
            "psnr": round(float(psnr), 2),
            "ssim": round(float(ssim), 4),
            "method": "neural",
            "weights_loaded": self._loaded,
        }
        return stego, metrics

    def decode(
        self,
        encoded_image: np.ndarray,
        apply_noise: str | None = None,   # unused; kept for interface parity
    ) -> Tuple[str, Dict[str, Any]]:
        x = encoded_image.astype(np.float32)
        if x.max() > 1.5:
            x = x / 255.0
        if x.shape[0] != self.image_size or x.shape[1] != self.image_size:
            x = tf.image.resize(x, (self.image_size, self.image_size)).numpy()

        logits = self.decoder(x[np.newaxis, ...], training=False).numpy()[0]
        probs = 1.0 / (1.0 + np.exp(-logits))
        bits = (probs > 0.5).astype(np.float32)
        tracking_id = _bits_to_tracking_id(bits)

        # Confidence: how far each bit is from 0.5.
        confidence = float(np.mean(np.abs(probs - 0.5)) * 2 * 100)
        return tracking_id, {
            "tracking_id": tracking_id,
            "confidence": round(confidence, 2),
            "method": "neural",
            "found": False,  # caller will check DB; service can't know
        }

    def test_robustness(
        self,
        cover_image: np.ndarray,
        tracking_id: str,
        distortions: list | None = None,
    ) -> Dict[str, Any]:
        from app.utils import NoiseProcessor

        encoded, enc_metrics = self.encode(cover_image, tracking_id)
        results: Dict[str, Any] = {
            "tracking_id": tracking_id,
            "encode_metrics": enc_metrics,
            "robustness_tests": {},
        }

        processor = NoiseProcessor()
        for d in (distortions or ["identity", "jpeg", "blur", "crop", "resize"]):
            test_img = encoded.copy()
            if d == "jpeg":
                test_img = processor.apply_jpeg_compression(test_img, quality=50)
            elif d == "blur":
                test_img = processor.apply_gaussian_blur(test_img)
            elif d == "crop":
                test_img = processor.apply_crop(test_img, 0.5)
            elif d == "resize":
                test_img = processor.apply_resize(test_img)
            decoded_id, dec_metrics = self.decode(test_img)
            results["robustness_tests"][d] = {
                "success": decoded_id == tracking_id,
                "decoded_id": decoded_id,
                "confidence": dec_metrics["confidence"],
            }
        return results
