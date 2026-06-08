"""
Pydantic schemas — request/response validation and MongoDB document shapes.

All times are UTC. We do NOT store Mongo's `_id` here; instead each domain
object carries a stable string `tracking_id` (for tracking) or UUID `id`
(for everything else) we control ourselves.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------------------------------------------------------------------------
# User (auth — minimal scaffolding, not yet wired into routes)
# ---------------------------------------------------------------------------
class UserBase(BaseModel):
    username: str
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(min_length=8)


class UserResponse(UserBase):
    id: str
    is_active: bool
    created_at: datetime


class UserInDB(UserBase):
    """Internal document shape."""
    id: str
    hashed_password: str
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Tracking ID — the core domain object
# ---------------------------------------------------------------------------
class TrackingIDBase(BaseModel):
    owner_name: str = Field(min_length=1, max_length=200)
    owner_email: EmailStr
    location: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)


class TrackingIDCreate(TrackingIDBase):
    pass


class TrackingIDInDB(TrackingIDBase):
    """Mongo document for the `tracking_ids` collection."""
    tracking_id: str
    user_id: Optional[str] = None
    original_filename: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class TrackingIDResponse(TrackingIDBase):
    tracking_id: str
    created_at: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Encoded image record
# ---------------------------------------------------------------------------
class EncodedImageInDB(BaseModel):
    id: str
    tracking_id: str
    user_id: Optional[str] = None
    encoded_path: str
    original_filename: Optional[str] = None
    image_hash: Optional[str] = None
    psnr: float
    ssim: float
    file_size: int
    created_at: datetime


# ---------------------------------------------------------------------------
# API: Encode
# ---------------------------------------------------------------------------
class EncodeResponse(BaseModel):
    tracking_id: str
    psnr: float
    ssim: float
    encoded_image_url: str
    download_url: str
    created_at: datetime
    owner_name: str
    owner_email: EmailStr


# ---------------------------------------------------------------------------
# API: Decode
# ---------------------------------------------------------------------------
class DecodeResponse(BaseModel):
    tracking_id: str
    confidence: float
    found: bool
    owner_name: Optional[str] = None
    owner_email: Optional[EmailStr] = None
    location: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# API: Decoding log
# ---------------------------------------------------------------------------
class DecodingLogInDB(BaseModel):
    id: str
    tracking_id: str
    decoded_id: str
    success: bool
    confidence: float
    created_at: datetime


# ---------------------------------------------------------------------------
# Auth tokens
# ---------------------------------------------------------------------------
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None
