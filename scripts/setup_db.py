#!/usr/bin/env python3
"""
Bootstrap MongoDB for PixelGuard.

Usage:
    python scripts/setup_db.py                  # ensure indexes
    python scripts/setup_db.py --drop           # drop the whole DB first (DANGEROUS)
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

# Add backend to import path so `app.*` resolves.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.config import settings  # noqa: E402
from app.database import close_mongo_connection, connect_to_mongo, get_db  # noqa: E402


async def _run(drop: bool) -> None:
    await connect_to_mongo()
    if drop:
        print(f"[setup_db] dropping database '{settings.MONGODB_DB}'…")
        await get_db().client.drop_database(settings.MONGODB_DB)
        # Re-create indexes after drop.
        await connect_to_mongo()
    print(f"[setup_db] db={settings.MONGODB_DB} ready at {settings.MONGODB_URL}")
    await close_mongo_connection()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--drop", action="store_true", help="Drop DB before re-creating indexes")
    args = parser.parse_args()
    asyncio.run(_run(args.drop))


if __name__ == "__main__":
    main()
