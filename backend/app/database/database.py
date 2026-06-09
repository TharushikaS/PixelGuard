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
    last_error: Optional[str] = None  # remembered if connect() failed at startup


_state = _MongoState()


# ---------------------------------------------------------------------------
# Connection lifecycle
# ---------------------------------------------------------------------------
async def connect_to_mongo() -> None:
    """Open a Motor client and verify the connection."""
    if _state.client is not None:
        return

    # Log the URL with the password masked so we never leak secrets.
    masked = settings.MONGODB_URL
    if "@" in masked and "://" in masked:
        scheme, rest = masked.split("://", 1)
        creds, host = rest.split("@", 1)
        if ":" in creds:
            user, _ = creds.split(":", 1)
            masked = f"{scheme}://{user}:***@{host}"
    logger.info("Connecting to MongoDB at %s", masked)

    # AsyncIOMotorClient construction can throw on a malformed URL --
    # capture that too, not just the ping failure.
    try:
        _state.client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=5000,
            uuidRepresentation="standard",
        )
        _state.db = _state.client[settings.MONGODB_DB]
    except Exception as exc:  # noqa: BLE001
        logger.error("MongoDB client construction failed: %s", exc)
        _state.last_error = f"client construction: {exc}"
        _state.client = None
        _state.db = None
        raise

    # Force a round-trip so we fail fast if Mongo is unreachable.
    try:
        await _state.client.admin.command("ping")
        logger.info("MongoDB connection OK (db=%s)", settings.MONGODB_DB)
        _state.last_error = None
    except Exception as exc:  # noqa: BLE001
        logger.error("MongoDB ping failed: %s", exc)
        _state.last_error = f"ping: {exc}"
        _state.client = None
        _state.db = None
        raise

    await ensure_indexes()


async def close_mongo_connection() -> None:
    """Close the Motor client at shutdown."""
    if _state.client is not None:
        _state.client.close()
        _state.client = None
        _state.db = None
        logger.info("MongoDB connection closed")


async def ensure_connected() -> None:
    """
    If startup connection failed (transient DNS, network blip), retry now.
    Routes/services call this before touching the DB so a single bad
    moment at startup doesn't poison the whole server lifetime.
    """
    if _state.db is not None:
        return
    logger.info("Mongo not connected — retrying connection on demand")
    await connect_to_mongo()


# ---------------------------------------------------------------------------
# Accessors
# ---------------------------------------------------------------------------
def _conn_error_hint() -> str:
    if _state.last_error:
        return (
            f"MongoDB connection failed at startup. Last error: {_state.last_error}. "
            "Check MONGODB_URL in backend/.env — make sure it's your real Atlas URL "
            "(not the example placeholder) and the password is URL-safe."
        )
    return (
        "MongoDB is not connected. Either the server lifespan hasn't run yet, or "
        "MONGODB_URL is misconfigured. Check backend/.env and restart uvicorn."
    )


def get_client() -> AsyncIOMotorClient:
    if _state.client is None:
        raise RuntimeError(_conn_error_hint())
    return _state.client


def get_db() -> AsyncIOMotorDatabase:
    if _state.db is None:
        raise RuntimeError(_conn_error_hint())
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
