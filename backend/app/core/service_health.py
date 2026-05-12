import asyncio
from typing import Any

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.config import settings
from app.core.logging import get_logger
from app.services.scraper_client import ScraperClient


logger = get_logger("app.core.service_health")


async def check_database_service(engine: AsyncEngine) -> str:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "unavailable"


async def check_redis_service() -> str:
    redis = Redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_timeout=settings.REDIS_CONNECT_TIMEOUT,
        socket_connect_timeout=settings.REDIS_CONNECT_TIMEOUT,
    )
    try:
        await redis.ping()
        return "ok"
    except Exception:
        return "unavailable"
    finally:
        close_method = getattr(redis, "aclose", None)
        try:
            if callable(close_method):
                await close_method()
            else:
                await redis.close()
        except Exception:
            pass


async def assert_redis_broker_available() -> None:
    redis_status = await check_redis_service()
    logger.info(
        "Redis broker preflight check.",
        broker_url=settings.REDIS_URL,
        redis_status=redis_status,
    )
    if redis_status != "ok":
        if settings.ENVIRONMENT == "development":
            logger.warning(
                "Redis broker unreachable during startup; continuing in development mode.",
                broker_url=settings.REDIS_URL,
                redis_status=redis_status,
            )
            return
        logger.error(
            "Redis broker unreachable during startup.",
            broker_url=settings.REDIS_URL,
            redis_status=redis_status,
        )
        raise RuntimeError(f"Redis broker unreachable at {settings.REDIS_URL}")


async def get_core_services_status(engine: AsyncEngine) -> dict[str, str]:
    database, redis = await asyncio.gather(
        check_database_service(engine),
        check_redis_service(),
    )
    return {
        "database": database,
        "redis": redis,
    }


async def assert_startup_dependencies(engine: AsyncEngine) -> None:
    services = await get_core_services_status(engine)
    unavailable = [service for service, state in services.items() if state != "ok"]
    if settings.ENVIRONMENT == "development":
        unavailable = [
            service
            for service in unavailable
            if service not in {"redis"}
        ]
    if not unavailable:
        return

    logger.error(
        "Startup validation failed. Required services are unavailable.",
        unavailable_services=unavailable,
        services=services,
    )
    raise RuntimeError(f"Startup validation failed for services: {', '.join(unavailable)}")


async def check_scraper_integration_service() -> str:
    client = ScraperClient.from_settings()
    state = await client.check_health()
    if state == "reachable":
        return "ok"
    if state == "unconfigured":
        return "unconfigured"
    return "unavailable"


def build_health_payload(services: dict[str, str], **metadata: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": "ok" if all(value == "ok" for value in services.values()) else "degraded",
        "services": services,
    }
    payload.update(metadata)
    return payload
