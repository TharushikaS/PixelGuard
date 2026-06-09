"""
Classical LSB (Least Significant Bit) steganography.

Used as the working demo path until the neural encoder is trained on COCO.
With LSB:
  - encoded image is visually identical to the cover (PSNR ~ 60 dB)
  - decoder recovers the embedded ID with 100% accuracy on lossless formats
  - NOT robust to JPEG / cropping / resizing -- that's the neural path's job

Payload layout (all values stored little-endian-by-bit, LSB-first):
    [MAGIC: 16 bits = 'PG' ascii] [LEN: 16 bits = payload byte count]
    [PAYLOAD: LEN * 8 bits = utf-8 of the tracking ID]

Bits are written into the LSB of each colour channel, scanning pixels in
row-major order, channel-major within a pixel. PNG output preserves the
LSBs; JPEG would destroy them.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, Tuple

import numpy as np

from app.utils import MetricsCalculator


_MAGIC = b"PG"
_MAGIC_BITS = 16          # 2 bytes
_LEN_BITS = 16            # max 65535 byte payload (more than enough)
_HEADER_BITS = _MAGIC_BITS + _LEN_BITS


def _bytes_to_bits(data: bytes) -> np.ndarray:
    """Unpack bytes into a flat array of 0/1 ints, MSB-first within each byte."""
    arr = np.frombuffer(data, dtype=np.uint8)
    return np.unpackbits(arr).astype(np.uint8)


def _bits_to_bytes(bits: np.ndarray) -> bytes:
    """Pack 0/1 bits (MSB-first) back into bytes. `bits` length must be multiple of 8."""
    return np.packbits(bits.astype(np.uint8)).tobytes()


def _ensure_uint8(image: np.ndarray) -> np.ndarray:
    """Coerce [0,1] floats to [0,255] uint8."""
    if image.dtype == np.uint8:
        return image
    return np.clip(image * 255.0, 0, 255).astype(np.uint8)


class LSBSteganographyService:
    """Drop-in replacement for SteganographyService that uses LSB embedding."""

    # ------------------------------------------------------------------
    # Public API (matches SteganographyService)
    # ------------------------------------------------------------------
    def generate_tracking_id(self) -> str:
        # 16-char UUID slice. ASCII -> 16 bytes -> 128 bits payload.
        return str(uuid.uuid4()).replace("-", "")[:16]

    def encode(
        self,
        cover_image: np.ndarray,
        tracking_id: str,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Embed `tracking_id` into the LSBs of `cover_image`.
        cover_image: (H, W, 3) -- uint8 OR float in [0,1].
        Returns the stego image in the same float-or-uint8 representation
        as the input (we keep float [0,1] to match the existing pipeline).
        """
        was_float = (cover_image.dtype != np.uint8)
        img = _ensure_uint8(cover_image).copy()  # work on uint8 copy

        H, W, C = img.shape
        assert C >= 3, "Need at least 3 channels."

        payload = tracking_id.encode("utf-8")
        if len(payload) > 0xFFFF:
            raise ValueError("Tracking ID too long for 16-bit length header.")

        # Build the bit-stream: MAGIC + LEN + PAYLOAD
        header = (
            _MAGIC
            + len(payload).to_bytes(2, byteorder="big")
        )
        bitstream = _bytes_to_bits(header + payload)  # 1D uint8 array of 0/1

        capacity = H * W * C  # one bit per channel
        if bitstream.size > capacity:
            raise ValueError(
                f"Image too small to hold payload "
                f"({bitstream.size} bits needed, {capacity} available)."
            )

        # Flatten image, set LSBs of the first N channels to our bits.
        flat = img.reshape(-1)
        flat[: bitstream.size] = (flat[: bitstream.size] & 0b11111110) | bitstream
        encoded = flat.reshape(H, W, C)

        # Metrics (compare to the cover at the same uint8 quantization).
        cover_uint8 = _ensure_uint8(cover_image)
        psnr = MetricsCalculator.calculate_psnr(cover_uint8, encoded)
        ssim = MetricsCalculator.calculate_ssim(cover_uint8, encoded)

        metrics = {
            "tracking_id": tracking_id,
            "psnr": round(float(psnr), 2),
            "ssim": round(float(ssim), 4),
            "bits_embedded": int(bitstream.size),
            "method": "lsb",
        }

        # Match input dtype.
        if was_float:
            encoded = encoded.astype(np.float32) / 255.0
        return encoded, metrics

    def decode(
        self,
        encoded_image: np.ndarray,
        apply_noise: str | None = None,  # ignored -- LSB is not noise-robust
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Recover the embedded tracking ID. Returns (id, metrics).
        If no valid PixelGuard header is found, returns ("", {found=False}).
        """
        img = _ensure_uint8(encoded_image)
        H, W, C = img.shape

        flat = img.reshape(-1)
        lsbs = (flat & 1).astype(np.uint8)

        # Pull header.
        if lsbs.size < _HEADER_BITS:
            return "", {"confidence": 0.0, "method": "lsb", "found": False}

        magic_bits = lsbs[:_MAGIC_BITS]
        magic = _bits_to_bytes(magic_bits)
        if magic != _MAGIC:
            # No watermark found.
            return "", {"confidence": 0.0, "method": "lsb", "found": False}

        len_bits = lsbs[_MAGIC_BITS:_HEADER_BITS]
        payload_len = int.from_bytes(_bits_to_bytes(len_bits), byteorder="big")

        needed = _HEADER_BITS + payload_len * 8
        if needed > lsbs.size:
            return "", {"confidence": 0.0, "method": "lsb", "found": False}

        payload_bits = lsbs[_HEADER_BITS:needed]
        payload = _bits_to_bytes(payload_bits)
        try:
            tracking_id = payload.decode("utf-8")
        except UnicodeDecodeError:
            return "", {"confidence": 0.0, "method": "lsb", "found": False}

        return tracking_id, {
            "confidence": 100.0,         # LSB extraction is deterministic
            "method": "lsb",
            "found": True,
        }

    def test_robustness(
        self,
        cover_image: np.ndarray,
        tracking_id: str,
        distortions: list | None = None,
    ) -> Dict[str, Any]:
        """LSB is not robust to distortions -- documented for completeness."""
        encoded, encode_metrics = self.encode(cover_image, tracking_id)
        decoded, _ = self.decode(encoded)
        return {
            "tracking_id": tracking_id,
            "encode_metrics": encode_metrics,
            "robustness_tests": {
                "identity": {
                    "success": decoded == tracking_id,
                    "decoded_id": decoded,
                    "confidence": 100.0,
                },
                "note": (
                    "LSB is not robust to JPEG/blur/crop/resize. "
                    "Switch STEGO_METHOD=neural after training for robustness."
                ),
            },
        }
