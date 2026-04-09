import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.config import settings

T = TypeVar("T")


async def run_with_db_retry(operation: Callable[[], Awaitable[T]]) -> T:
    last_error: Exception | None = None
    for attempt in range(1, settings.DATABASE_CONNECT_MAX_RETRIES + 1):
        try:
            return await operation()
        except Exception as exc:
            last_error = exc
            if attempt == settings.DATABASE_CONNECT_MAX_RETRIES:
                break
            await asyncio.sleep(settings.DATABASE_CONNECT_RETRY_DELAY * attempt)
    raise last_error if last_error is not None else RuntimeError("Database operation failed.")


async def check_database_health(engine: AsyncEngine) -> dict[str, str]:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return {"status": "ok"}
    except SQLAlchemyError as exc:
        return {"status": "error", "detail": str(exc)}
