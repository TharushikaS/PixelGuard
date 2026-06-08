"""Tracking-ID lookup / listing endpoints."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, Query

from app.config import settings
from app.database.schemas import TrackingIDResponse
from app.services import TrackingService

router = APIRouter(prefix=f"{settings.API_V1_STR}/tracking", tags=["tracking"])


@router.get("/{tracking_id}", response_model=TrackingIDResponse)
async def get_tracking_info(tracking_id: str):
    """Look up metadata for a tracking ID."""
    record = await TrackingService.get_tracking_id(tracking_id)
    if not record or not record.get("is_active", False):
        raise HTTPException(status_code=404, detail="Tracking ID not found.")
    return TrackingIDResponse(**record)


@router.get("/user/{user_id}/statistics")
async def get_user_statistics(user_id: str):
    """Aggregate stats: how many IDs, encoded images, decode attempts, success rate."""
    return await TrackingService.get_user_statistics(user_id)


@router.get("/user/{user_id}/tracking-ids", response_model=List[TrackingIDResponse])
async def list_tracking_ids(
    user_id: str,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
):
    """List a user's tracking IDs, newest first."""
    rows = await TrackingService.list_user_tracking_ids(user_id, skip, limit)
    return [TrackingIDResponse(**row) for row in rows]


@router.delete("/{tracking_id}", response_model=TrackingIDResponse)
async def deactivate_tracking_id(tracking_id: str):
    """Soft-delete: mark tracking ID inactive (preserves history)."""
    record = await TrackingService.deactivate_tracking_id(tracking_id)
    if not record:
        raise HTTPException(status_code=404, detail="Tracking ID not found.")
    return TrackingIDResponse(**record)
