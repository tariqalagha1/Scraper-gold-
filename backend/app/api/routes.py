from fastapi import APIRouter
from redis.asyncio import Redis
from sqlalchemy import text

from app.config import settings
from app.db.session import engine


router = APIRouter()


@router.get("/health/full", tags=["Health"])
async def health_full() -> dict[str, object]:
    services: dict[str, str] = {"api": "ok"}

    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        services["database"] = "ok"
    except Exception:
        services["database"] = "unavailable"

    try:
        redis = Redis.from_url(settings.REDIS_URL, decode_responses=True, socket_timeout=settings.REDIS_CONNECT_TIMEOUT)
        await redis.ping()
        await redis.close()
        services["redis"] = "ok"
    except Exception:
        services["redis"] = "unavailable"

    try:
        from app.scraper.browser import BrowserManager

        browser_manager = BrowserManager()
        try:
            await browser_manager._ensure_browser()
            services["playwright"] = "ok"
        except Exception:
            services["playwright"] = "unavailable"
        finally:
            try:
                await browser_manager.close()
            except Exception:
                pass
    except Exception:
        services["playwright"] = "unavailable"

    if settings.OPENAI_API_KEY:
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            await client.models.list()
            services["openai"] = "ok"
        except Exception:
            services["openai"] = "unavailable"
    else:
        services["openai"] = "skipped"

    overall_status = "ok" if all(
        service_status in {"ok", "skipped"} for service_status in services.values()
    ) else "degraded"

    return {
        "status": overall_status,
        "services": services,
    }
