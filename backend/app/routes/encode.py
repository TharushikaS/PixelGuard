"""Encode API — embed a tracking ID into a cover image."""
from __future__ import annotations

import os
from datetime import datetime, timezone

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.config import settings
from app.database import ensure_connected
from app.database.schemas import EncodeResponse
from app.services import TrackingService, get_stego_service
from app.utils import ImageProcessor

router = APIRouter(prefix=f"{settings.API_V1_STR}/encode", tags=["encode"])

# Lazily-initialized; first request triggers model construction.
_stego = None


def _get_stego():
    global _stego
    if _stego is None:
        _stego = get_stego_service()
    return _stego


def _input_size() -> int | None:
    """Neural path needs fixed-size input; LSB keeps native resolution."""
    return None if settings.STEGO_METHOD.lower() == "lsb" else settings.IMAGE_SIZE


@router.post("/", response_model=EncodeResponse)
async def encode_image(
    file: UploadFile = File(..., description="Cover image to watermark"),
    owner_name: str = Form(..., min_length=1, max_length=200),
    owner_email: str = Form(..., max_length=200),
    location: str | None = Form(default=None, max_length=200),
    description: str | None = Form(default=None, max_length=2000),
):
    """
    Pipeline:
        1. Read upload (size-limited)
        2. Decode + resize cover image
        3. Generate tracking ID
        4. Persist metadata to MongoDB
        5. Run encoder → stego image
        6. Save to disk under uploads/, log encoded record
        7. Return tracking ID, metrics, and a download URL
    """
    # ---- 1. read & validate upload ----
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty upload.")
    if len(contents) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (max {settings.MAX_UPLOAD_SIZE} bytes).",
        )

    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext and ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail=f"Unsupported file type: .{ext}")

    # ---- 2. decode cover (LSB keeps native resolution, neural resizes) ----
    try:
        cover_image = ImageProcessor.load_image_from_bytes(contents, _input_size())
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Image decode failed: {exc}")

    stego = _get_stego()

    # ---- 3. tracking ID ----
    tracking_id = stego.generate_tracking_id()

    # ---- 4. persist metadata FIRST so a partial failure later leaves a
    # record we can debug.
    try:
        await ensure_connected()
        await TrackingService.create_tracking_id(
            tracking_id=tracking_id,
            owner_name=owner_name,
            owner_email=owner_email,
            location=location,
            description=description,
            original_filename=file.filename,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"DB write failed: {exc}")

    # ---- 5. encode ----
    try:
        encoded_image, metrics = stego.encode(cover_image, tracking_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Encoding failed: {exc}")

    # ---- 6. persist file + record ----
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    encoded_path = os.path.join(settings.UPLOAD_DIR, f"{tracking_id}.png")
    ImageProcessor.save_image(encoded_image, encoded_path)

    try:
        file_size = os.path.getsize(encoded_path)
        await TrackingService.log_encoded_image(
            tracking_id=tracking_id,
            encoded_path=encoded_path,
            psnr=metrics["psnr"],
            ssim=metrics["ssim"],
            file_size=file_size,
            original_filename=file.filename,
            image_hash=ImageProcessor.get_image_hash(encoded_image),
        )
    except Exception as exc:  # noqa: BLE001
        # File still exists; the metadata write is non-fatal.
        print(f"[encode] log_encoded_image failed: {exc}")

    return EncodeResponse(
        tracking_id=tracking_id,
        psnr=metrics["psnr"],
        ssim=metrics["ssim"],
        encoded_image_url=f"{settings.API_V1_STR}/encode/download/{tracking_id}",
        download_url=f"{settings.API_V1_STR}/encode/download/{tracking_id}",
        created_at=datetime.now(timezone.utc),
        owner_name=owner_name,
        owner_email=owner_email,
    )


@router.get("/download/{tracking_id}")
async def download_encoded_image(tracking_id: str):
    """Stream back a previously-encoded image by its tracking ID."""
    record = await TrackingService.get_encoded_record(tracking_id)
    if not record:
        # fall back to file on disk in case DB write failed
        candidate = os.path.join(settings.UPLOAD_DIR, f"{tracking_id}.png")
        if os.path.exists(candidate):
            return FileResponse(candidate, media_type="image/png")
        raise HTTPException(status_code=404, detail="Encoded image not found.")

    path = record["encoded_path"]
    if not os.path.exists(path):
        raise HTTPException(status_code=410, detail="Encoded file no longer on disk.")
    return FileResponse(path, media_type="image/png", filename=f"{tracking_id}.png")


@router.post("/test-robustness")
async def test_robustness(
    file: UploadFile = File(...),
    tracking_id: str | None = Form(default=None),
):
    """Encode, then decode under several distortions; report per-distortion bit accuracy."""
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty upload.")

    cover_image = ImageProcessor.load_image_from_bytes(contents, _input_size())
    stego = _get_stego()
    if not tracking_id:
        tracking_id = stego.generate_tracking_id()

    results = stego.test_robustness(
        cover_image,
        tracking_id,
        distortions=["identity", "jpeg", "blur", "crop", "resize"],
    )
    return results
