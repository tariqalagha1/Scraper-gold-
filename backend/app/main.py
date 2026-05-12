import asyncio
import signal
from contextlib import asynccontextmanager
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import v1_router
from app.api.routes import router as root_router
from app.config import settings
from app.core.config import validate_required_settings
from app.core.exceptions import register_exception_handlers
from app.core.logger import clear_request_id, set_request_id
from app.core.logging import get_logger
from app.core.service_health import (
    assert_startup_dependencies,
    assert_redis_broker_available,
    build_health_payload,
    check_scraper_integration_service,
    get_core_services_status,
)
from app.db.session import close_db, engine, init_db
from app.execution.export_task_registry import cancel_all_export_tasks
from app.execution.task_registry import cancel_all_tasks
from app.middleware.rate_limit import RedisRateLimitMiddleware
from app.orchestrator.memory_service import log_memory_backend_startup_status

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
shutdown_event = asyncio.Event()


def handle_shutdown(*_: object) -> None:
    shutdown_event.set()


def configure_signal_handlers() -> None:
    try:
        signal.signal(signal.SIGTERM, handle_shutdown)
        signal.signal(signal.SIGINT, handle_shutdown)
    except ValueError:
        # Signal handlers can only be set in the main thread.
        return


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        validate_required_settings()
    except Exception as exc:
        logger.error(
            "Startup configuration invalid. Missing or invalid required environment settings.",
            error=str(exc),
        )
        raise

    logger.info(
        "Application startup initiated.",
        environment=settings.ENVIRONMENT,
        broker_url=settings.REDIS_URL,
        scraper_base_url=settings.SCRAPER_BASE_URL,
        scraper_api_key_configured=bool(str(settings.SCRAPER_API_KEY).strip()),
    )
    await assert_redis_broker_available()
    await init_db()
    await assert_startup_dependencies(engine)
    log_memory_backend_startup_status()
    logger.info("Application startup completed.")
    try:
        yield
    finally:
        logger.info("Application shutdown initiated.")
        if shutdown_event.is_set():
            handles: list[asyncio.Task[object]] = []
            handles.extend(cancel_all_tasks())
            handles.extend(cancel_all_export_tasks())
            if handles:
                logger.info("Cancelling active in-process tasks.", task_count=len(handles))
                await asyncio.gather(*handles, return_exceptions=True)
        await close_db()
        logger.info("Application shutdown completed.")


def create_app() -> FastAPI:
    configure_signal_handlers()
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

    @app.get("/health")
    async def health() -> dict[str, object]:
        services = await get_core_services_status(engine)
        services["scraper"] = await check_scraper_integration_service()
        return build_health_payload(services)

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
                response.headers["X-DNS-Prefetch-Control"] = "off"
                response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
                response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
                response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
                response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
                response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
                response.headers["Cache-Control"] = "no-store"
                response.headers["Pragma"] = "no-cache"
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

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.RELOAD,
    )
