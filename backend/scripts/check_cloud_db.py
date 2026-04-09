"""Quick cloud database connectivity check for Smart Scraper backend.

Usage:
  cd backend
  venv/bin/python scripts/check_cloud_db.py
"""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys

from sqlalchemy import text

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.config import settings
from app.db.session import engine


async def main() -> int:
    database_url = str(settings.DATABASE_URL or "").strip()
    if not database_url:
        print("FAIL: DATABASE_URL is empty.")
        return 1

    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        print("OK: Cloud database connection is healthy.")
        print(f"DATABASE_URL driver: {database_url.split('://', 1)[0]}")
        return 0
    except Exception as exc:  # pragma: no cover - operational script
        print("FAIL: Unable to connect to cloud database.")
        print(f"Reason: {exc}")
        print(
            "Tip: For Supabase/Neon use postgresql+asyncpg://... and include SSL if required "
            "(for example '?ssl=require')."
        )
        return 1
    finally:
        await engine.dispose()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
