"""
Tracking service — MongoDB-backed CRUD for tracking IDs, encoded image
records, and decoding logs.

All methods are async (Motor). Each method documents the shape of the
documents it touches and returns plain dicts (with `_id` stripped) so the
caller can hand them straight to a Pydantic response model.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.database import (
    decoding_log_collection,
    encoded_collection,
    tracking_collection,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _strip_id(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if doc is None:
        return None
    doc.pop("_id", None)
    return doc


class TrackingService:
    """Static collection of async methods. No instance state required."""

    # ------------------------------------------------------------------
    # Tracking IDs
    # ------------------------------------------------------------------
    @staticmethod
    async def create_tracking_id(
        tracking_id: str,
        owner_name: str,
        owner_email: str,
        *,
        user_id: Optional[str] = None,
        location: Optional[str] = None,
        description: Optional[str] = None,
        original_filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        now = _utcnow()
        doc = {
            "tracking_id": tracking_id,
            "user_id": user_id,
            "owner_name": owner_name,
            "owner_email": owner_email,
            "location": location,
            "description": description,
            "original_filename": original_filename,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        await tracking_collection().insert_one(doc)
        return _strip_id(doc)

    @staticmethod
    async def get_tracking_id(tracking_id: str) -> Optional[Dict[str, Any]]:
        doc = await tracking_collection().find_one({"tracking_id": tracking_id})
        return _strip_id(doc)

    @staticmethod
    async def list_user_tracking_ids(
        user_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        cursor = (
            tracking_collection()
            .find({"user_id": user_id, "is_active": True})
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )
        return [_strip_id(d) async for d in cursor]

    @staticmethod
    async def update_tracking_id(
        tracking_id: str, **fields: Any
    ) -> Optional[Dict[str, Any]]:
        if not fields:
            return await TrackingService.get_tracking_id(tracking_id)

        fields["updated_at"] = _utcnow()
        result = await tracking_collection().find_one_and_update(
            {"tracking_id": tracking_id},
            {"$set": fields},
            return_document=True,
        )
        return _strip_id(result)

    @staticmethod
    async def deactivate_tracking_id(tracking_id: str) -> Optional[Dict[str, Any]]:
        return await TrackingService.update_tracking_id(
            tracking_id, is_active=False
        )

    # ------------------------------------------------------------------
    # Encoded image records
    # ------------------------------------------------------------------
    @staticmethod
    async def log_encoded_image(
        tracking_id: str,
        encoded_path: str,
        psnr: float,
        ssim: float,
        file_size: int,
        *,
        user_id: Optional[str] = None,
        original_filename: Optional[str] = None,
        image_hash: Optional[str] = None,
    ) -> Dict[str, Any]:
        doc = {
            "id": str(uuid.uuid4()),
            "tracking_id": tracking_id,
            "user_id": user_id,
            "encoded_path": encoded_path,
            "original_filename": original_filename,
            "image_hash": image_hash,
            "psnr": float(psnr),
            "ssim": float(ssim),
            "file_size": int(file_size),
            "created_at": _utcnow(),
        }
        await encoded_collection().insert_one(doc)
        return _strip_id(doc)

    @staticmethod
    async def get_encoded_record(tracking_id: str) -> Optional[Dict[str, Any]]:
        doc = await encoded_collection().find_one(
            {"tracking_id": tracking_id},
            sort=[("created_at", -1)],
        )
        return _strip_id(doc)

    # ------------------------------------------------------------------
    # Decoding logs
    # ------------------------------------------------------------------
    @staticmethod
    async def log_decoding_attempt(
        tracking_id: str,
        decoded_id: str,
        success: bool,
        confidence: float,
    ) -> Dict[str, Any]:
        doc = {
            "id": str(uuid.uuid4()),
            "tracking_id": tracking_id,
            "decoded_id": decoded_id,
            "success": bool(success),
            "confidence": float(confidence),
            "created_at": _utcnow(),
        }
        await decoding_log_collection().insert_one(doc)
        return _strip_id(doc)

    # ------------------------------------------------------------------
    # Aggregates
    # ------------------------------------------------------------------
    @staticmethod
    async def get_user_statistics(user_id: str) -> Dict[str, Any]:
        tcol = tracking_collection()
        ecol = encoded_collection()
        dcol = decoding_log_collection()

        active_ids = await tcol.count_documents(
            {"user_id": user_id, "is_active": True}
        )
        encoded_count = await ecol.count_documents({"user_id": user_id})

        # Count decode attempts whose tracking_id belongs to this user.
        user_tracking_ids = [
            d["tracking_id"]
            async for d in tcol.find(
                {"user_id": user_id}, projection={"tracking_id": 1}
            )
        ]
        attempts = (
            await dcol.count_documents({"tracking_id": {"$in": user_tracking_ids}})
            if user_tracking_ids
            else 0
        )
        successes = (
            await dcol.count_documents(
                {"tracking_id": {"$in": user_tracking_ids}, "success": True}
            )
            if user_tracking_ids
            else 0
        )

        return {
            "tracking_ids": active_ids,
            "encoded_images": encoded_count,
            "decoding_attempts": attempts,
            "successful_decodings": successes,
            "success_rate": (successes / attempts * 100.0) if attempts else 0.0,
        }
