"""Database package — MongoDB (Motor) helpers."""
from .database import (
    close_mongo_connection,
    connect_to_mongo,
    decoding_log_collection,
    encoded_collection,
    ensure_connected,
    ensure_indexes,
    get_client,
    get_db,
    tracking_collection,
    users_collection,
)

__all__ = [
    "connect_to_mongo",
    "close_mongo_connection",
    "ensure_connected",
    "ensure_indexes",
    "get_client",
    "get_db",
    "tracking_collection",
    "encoded_collection",
    "decoding_log_collection",
    "users_collection",
]
