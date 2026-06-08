"""
Async MongoDB connection layer for PixelGuard.

Exposes:
    - get_client() / get_db()                    : access singletons in routes
    - connect_to_mongo() / close_mongo_connection(): wire from FastAPI lifespan
    - ensure_indexes()                            : idempotent index setup
    - collection helpers (tracking_collection, etc.)

Documents are stored as plain dicts; we rely on Pydantic schemas in
`app.database.schemas` for validation at the API boundary.
"""
from __future__ import annotations

import logging
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import PyMongoError

from app.config import settings

logger = logging.getLogger(__name__)


class _MongoState:
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None


_state = _MongoState()


# ---------------------------------------------------------------------------
# Connection lifecycle
# ---------------------------------------------------------------------------
async def connect_to_mongo() -> None:
    """Open a Motor client and verify the connection."""
    if _state.client is not None:
        return

    logger.info("Connecting to MongoDB at %s", settings.MONGODB_URL)
    _state.client = AsyncIOMotorClient(
        settings.MONGODB_URL,
        serverSelectionTimeoutMS=5000,
        uuidRepresentation="standard",
    )
    _state.db = _state.client[settings.MONGODB_DB]

    # Force a round-trip so we fail fast if Mongo is unreachable.
    try:
        await _state.client.admin.command("ping")
        logger.info("MongoDB connection OK (db=%s)", settings.MONGODB_DB)
    except PyMongoError as exc:
        logger.error("MongoDB ping failed: %s", exc)
        raise

    await ensure_indexes()


async def close_mongo_connection() -> None:
    """Close the Motor client at shutdown."""
    if _state.client is not None:
        _state.client.close()
        _state.client = None
        _state.db = None
        logger.info("MongoDB connection closed")


# ---------------------------------------------------------------------------
# Accessors
# ---------------------------------------------------------------------------
def get_client() -> AsyncIOMotorClient:
    if _state.client is None:
        raise RuntimeError("MongoDB client is not initialized; call connect_to_mongo() first.")
    return _state.client


def get_db() -> AsyncIOMotorDatabase:
    if _state.db is None:
        raise RuntimeError("MongoDB database is not initialized; call connect_to_mongo() first.")
    return _state.db


def tracking_collection():
    return get_db()[settings.MONGODB_TRACKING_COLLECTION]


def encoded_collection():
    return get_db()[settings.MONGODB_ENCODED_COLLECTION]


def decoding_log_collection():
    return get_db()[settings.MONGODB_DECODE_LOG_COLLECTION]


def users_collection():
    return get_db()[settings.MONGODB_USERS_COLLECTION]


# ---------------------------------------------------------------------------
# Index management
# ---------------------------------------------------------------------------
async def ensure_indexes() -> None:
    """
    Create the indexes our queries rely on. Safe to call repeatedly — Mongo
    skips already-existing indexes with the same spec.
    """
    db = get_db()

    await db[settings.MONGODB_TRACKING_COLLECTION].create_index(
        [("tracking_id", ASCENDING)], unique=True, name="uniq_tracking_id"
    )
    await db[settings.MONGODB_TRACKING_COLLECTION].create_index(
        [("user_id", ASCENDING), ("created_at", DESCENDING)],
        name="user_created_desc",
    )
    await db[settings.MONGODB_TRACKING_COLLECTION].create_index(
        [("owner_email", ASCENDING)], name="owner_email_idx"
    )

    await db[settings.MONGODB_ENCODED_COLLECTION].create_index(
        [("tracking_id", ASCENDING)], name="encoded_tracking_idx"
    )
    await db[settings.MONGODB_ENCODED_COLLECTION].create_index(
        [("image_hash", ASCENDING)], unique=True, sparse=True, name="uniq_image_hash"
    )

    await db[settings.MONGODB_DECODE_LOG_COLLECTION].create_index(
        [("tracking_id", ASCENDING), ("created_at", DESCENDING)],
        name="decode_tracking_created",
    )

    await db[settings.MONGODB_USERS_COLLECTION].create_index(
        [("email", ASCENDING)], unique=True, name="uniq_user_email"
    )

    logger.info("MongoDB indexes ensured")
