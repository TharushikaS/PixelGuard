"""Decode API — recover a tracking ID from a possibly-distorted image."""
from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.config import settings
from app.database import ensure_connected
from app.database.schemas import DecodeResponse
from app.services import TrackingService, get_stego_service
from app.utils import ImageProcessor

router = APIRouter(prefix=f"{settings.API_V1_STR}/decode", tags=["decode"])

_stego = None


def _get_stego():
    global _stego
    if _stego is None:
        _stego = get_stego_service()
    return _stego


def _input_size() -> int | None:
    return None if settings.STEGO_METHOD.lower() == "lsb" else settings.IMAGE_SIZE


@router.post("/", response_model=DecodeResponse)
async def decode_image(file: UploadFile = File(...)):
    """
    Pipeline:
        1. Read upload, decode + resize
        2. Run decoder → recovered tracking ID + confidence
        3. Look up metadata in MongoDB
        4. Log the decoding attempt
        5. Return metadata (or `found=false` if the ID is not in our DB)
    """
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty upload.")
    if len(contents) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File too large.")

    try:
        encoded_image = ImageProcessor.load_image_from_bytes(contents, _input_size())
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Image decode failed: {exc}")

    stego = _get_stego()
    decoded_id, metrics = stego.decode(encoded_image)
    confidence = float(metrics.get("confidence", 0.0))

    await ensure_connected()
    record = await TrackingService.get_tracking_id(decoded_id)
    found = record is not None and record.get("is_active", False)

    # Log the attempt for audit/analytics.
    try:
        await TrackingService.log_decoding_attempt(
            tracking_id=decoded_id,
            decoded_id=decoded_id,
            success=found,
            confidence=confidence,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[decode] log_decoding_attempt failed: {exc}")

    if not found:
        return DecodeResponse(
            tracking_id=decoded_id,
            confidence=confidence,
            found=False,
        )

    return DecodeResponse(
        tracking_id=decoded_id,
        confidence=confidence,
        found=True,
        owner_name=record.get("owner_name"),
        owner_email=record.get("owner_email"),
        location=record.get("location"),
        description=record.get("description"),
        created_at=record.get("created_at"),
    )


@router.post("/with-distortion")
async def decode_with_distortion(
    file: UploadFile = File(...),
    distortion_type: str = Form(default="jpeg"),
):
    """Apply a chosen distortion, then decode. Useful for robustness demos."""
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty upload.")

    encoded_image = ImageProcessor.load_image_from_bytes(contents, _input_size())
    stego = _get_stego()
    tracking_id, metrics = stego.decode(encoded_image, apply_noise=distortion_type)

    return {
        "tracking_id": tracking_id,
        "distortion_type": distortion_type,
        "confidence": metrics["confidence"],
    }
