import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy import text

from app.api import v1_router
from app.api.routes import router as root_router
from app.config import settings
from app.core.config import validate_required_settings
from app.core.exceptions import register_exception_handlers
from app.core.logger import clear_request_id, set_request_id
from app.core.logging import get_logger
from app.db.session import close_db, engine, init_db
from app.middleware.rate_limit import RedisRateLimitMiddleware
from app.orchestrator.memory_service import log_memory_backend_startup_status
from app.queue.celery_app import celery_app

# Initialize Sentry
if settings.SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.redis import RedisIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[
            FastApiIntegration(),
            RedisIntegration(),
            SqlalchemyIntegration(),
        ],
        traces_sample_rate=1.0,
        environment=settings.ENVIRONMENT,
    )


logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_required_settings()
    logger.info("Application startup initiated.", environment=settings.ENVIRONMENT)
    await init_db()
    log_memory_backend_startup_status()
    logger.info("Application startup completed.")
    try:
        yield
    finally:
        logger.info("Application shutdown initiated.")
        await close_db()
        logger.info("Application shutdown completed.")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=settings.APP_DESCRIPTION,
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.CORS_ORIGINS],
        allow_origin_regex=settings.CORS_ORIGIN_REGEX,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", settings.API_KEY_HEADER_NAME],
    )
    app.add_middleware(RedisRateLimitMiddleware)

    @app.middleware("http")
    async def enforce_request_limits(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        set_request_id(request_id)

        def _attach_rate_limit_headers(response):
            rate_limit = getattr(request.state, "rate_limit", None)
            if rate_limit:
                response.headers["X-RateLimit-Limit"] = str(rate_limit["limit"])
                response.headers["X-RateLimit-Remaining"] = str(rate_limit["remaining"])
                response.headers["X-RateLimit-Window"] = str(rate_limit["window"])
            response.headers["X-Request-ID"] = request_id
            if settings.ENABLE_SECURITY_HEADERS:
                response.headers["X-Content-Type-Options"] = "nosniff"
                response.headers["X-Frame-Options"] = "DENY"
                response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
                response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
                response.headers["Cache-Control"] = "no-store"
                response.headers["Content-Security-Policy"] = (
                    "default-src 'self'; frame-ancestors 'none'; base-uri 'self'; "
                    "form-action 'self'; object-src 'none'"
                )
                if settings.is_production:
                    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
            return response

        try:
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > settings.MAX_REQUEST_SIZE_BYTES:
                response = JSONResponse(
                    status_code=413,
                    content={"error": {"code": "payload_too_large", "message": "Request payload too large.", "details": {}}},
                )
                return _attach_rate_limit_headers(response)
            response = await asyncio.wait_for(call_next(request), timeout=settings.REQUEST_TIMEOUT_SECONDS)
            return _attach_rate_limit_headers(response)
        except TimeoutError:
            response = JSONResponse(
                status_code=504,
                content={"error": {"code": "request_timeout", "message": "Request timed out.", "details": {}}},
            )
            return _attach_rate_limit_headers(response)
        except Exception as exc:
            logger.error(
                "Unhandled exception while processing request.",
                method=request.method,
                path=str(request.url.path),
                request_id=request_id,
                error=str(exc),
                exc_info=True,
            )
            response = JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "internal_server_error",
                        "message": "An unexpected error occurred.",
                        "details": {},
                    }
                },
            )
            return _attach_rate_limit_headers(response)
        finally:
            clear_request_id()

    register_exception_handlers(app)
    app.include_router(root_router)
    app.include_router(v1_router)

    @app.get("/health", tags=["Health"])
    async def health_check() -> dict[str, Any]:
        services = {"database": "unavailable", "redis": "unavailable", "queue": "unavailable"}

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
            await asyncio.to_thread(
                lambda: celery_app.connection_for_read().ensure_connection(max_retries=0)
            )
            services["queue"] = "ok"
        except Exception:
            services["queue"] = "unavailable"

        return {
            "status": "ok" if all(value == "ok" for value in services.values()) else "degraded",
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": services,
        }

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.RELOAD,
    )
