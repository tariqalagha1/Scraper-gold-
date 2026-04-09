import hashlib
from collections.abc import Awaitable, Callable
from time import time

from fastapi import Request
from jose import JWTError, jwt
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.config import settings
from app.core.logging import get_logger


logger = get_logger("app.middleware.rate_limit")
_redis_client: Redis | None = None


def _resolve_route_limit(request: Request) -> tuple[int, int, str]:
    if request.method == "POST" and (request.url.path.endswith("/runs") or request.url.path.endswith("/retry")):
        return settings.RUN_CREATE_RATE_LIMIT, settings.RUN_CREATE_RATE_WINDOW_SECONDS, "run-write"
    if request.method == "POST" and request.url.path.endswith("/jobs"):
        return settings.JOB_CREATE_RATE_LIMIT, settings.JOB_CREATE_RATE_WINDOW_SECONDS, "job-write"
    if request.method == "GET":
        # UI pages poll status endpoints (runs/logs/results). Keep this high enough
        # to avoid blocking normal execution visibility in browser sessions.
        return max(120, _get_rate_limit()), _get_rate_window(), "read"
    return _get_rate_limit(), _get_rate_window(), "default"


def _get_rate_limit() -> int:
    try:
        return max(1, int(settings.RATE_LIMIT_REQUESTS))
    except Exception:
        return 10


def _get_rate_window() -> int:
    try:
        return max(1, int(settings.RATE_LIMIT_WINDOW_SECONDS))
    except Exception:
        return 60


async def get_redis() -> Redis | None:
    global _redis_client
    try:
        if _redis_client is None:
            redis_url = settings.REDIS_URL
            _redis_client = Redis.from_url(
                redis_url,
                decode_responses=True,
                socket_timeout=settings.REDIS_CONNECT_TIMEOUT,
                socket_connect_timeout=settings.REDIS_CONNECT_TIMEOUT,
            )
        return _redis_client
    except Exception:
        return None


def _resolve_identifier(request: Request) -> str:
    api_key = request.headers.get("X-API-Key") or request.headers.get(settings.API_KEY_HEADER_NAME)
    authorization = request.headers.get("Authorization", "")
    if authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = payload.get("sub")
            if user_id:
                return f"user:{user_id}"
        except JWTError:
            pass
    client_ip = request.client.host if request.client else "unknown"
    raw_identifier = api_key or client_ip
    return hashlib.sha256(raw_identifier.encode("utf-8")).hexdigest()


class RedisRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        if request.method in {"OPTIONS", "HEAD"}:
            return await call_next(request)
        if request.url.path in {"/health", "/health/full"}:
            return await call_next(request)

        try:
            client = await get_redis()
            if client is None:
                return await call_next(request)

            rate_limit, rate_window, route_scope = _resolve_route_limit(request)
            bucket = int(time() // rate_window)
            identifier = _resolve_identifier(request)
            # Keep separate buckets per route scope so frequent polling GET calls
            # do not consume POST budgets used to create jobs/runs.
            key = f"rate-limit:{identifier}:{route_scope}:{bucket}"

            current = await client.incr(key)
            if current == 1:
                await client.expire(key, rate_window)
            request.state.rate_limit = {
                "limit": rate_limit,
                "remaining": max(0, rate_limit - current),
                "window": rate_window,
            }
            if current > rate_limit:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "code": "rate_limit_exceeded",
                            "message": "Request rate limit exceeded.",
                            "details": {"limit": rate_limit, "window": rate_window},
                        }
                    },
                )
        except Exception:
            pass

        return await call_next(request)
