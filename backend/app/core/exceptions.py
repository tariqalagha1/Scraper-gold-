from typing import Any, Optional

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError


class ScraperBaseException(Exception):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    code = "application_error"

    def __init__(self, message: str, *, details: Optional[dict[str, Any]] = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }


class ConfigurationError(ScraperBaseException):
    code = "configuration_error"


class DatabaseError(ScraperBaseException):
    code = "database_error"


class AuthenticationError(ScraperBaseException):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "authentication_error"


class AuthorizationError(ScraperBaseException):
    status_code = status.HTTP_403_FORBIDDEN
    code = "authorization_error"


class ScrapingError(ScraperBaseException):
    code = "scraping_error"


class ExtractionError(ScrapingError):
    code = "extraction_error"


class LoginError(ScrapingError):
    code = "login_error"


class RateLimitError(ScrapingError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = "rate_limit_error"

    def __init__(
        self,
        message: str,
        *,
        retry_after: Optional[float] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        merged = details or {}
        if retry_after is not None:
            merged = {**merged, "retry_after": retry_after}
        super().__init__(message, details=merged)
        self.retry_after = retry_after


class RobotsBlockedError(ScrapingError):
    code = "robots_blocked"


class ProcessingError(ScraperBaseException):
    code = "processing_error"


class ExportError(ScraperBaseException):
    code = "export_error"


class VectorError(ScraperBaseException):
    code = "vector_error"


class QueueError(ScraperBaseException):
    code = "queue_error"


class AgentError(ScraperBaseException):
    code = "agent_error"

    def __init__(
        self,
        message: str,
        *,
        agent_name: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.agent_name = agent_name
        super().__init__(message, details={**(details or {}), "agent_name": agent_name})


class AgentExecutionError(AgentError):
    code = "agent_execution_error"

    def __init__(
        self,
        message: str,
        *,
        agent_name: str = "unknown",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, agent_name=agent_name, details=details)


class ValidationError(ScraperBaseException):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "validation_error"

    def __init__(
        self,
        message: str,
        *,
        field: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        merged = details or {}
        if field is not None:
            merged = {**merged, "field": field}
        self.field = field
        super().__init__(message, details=merged)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Exception):
        return str(value)
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_json_safe(item) for item in value)
    return value


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ScraperBaseException)
    async def handle_scraper_exception(
        request: Request,
        exc: ScraperBaseException,
    ) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if isinstance(exc, AuthenticationError) else None
        return JSONResponse(status_code=exc.status_code, content=exc.to_dict(), headers=headers)

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        errors = _json_safe(exc.errors())
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "error": {
                    "code": "request_validation_error",
                    "message": "Request validation failed.",
                    "details": {"errors": errors},
                }
            },
        )

    @app.exception_handler(SQLAlchemyError)
    async def handle_sqlalchemy_error(
        request: Request,
        exc: SQLAlchemyError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=DatabaseError("A database error occurred.").to_dict(),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "internal_server_error",
                    "message": "An unexpected error occurred.",
                    "details": {},
                }
            },
        )
