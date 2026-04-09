import json
import logging
import sys
import time
import asyncio
from contextvars import ContextVar
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Iterator, Optional, TypeVar

from app.config import settings

F = TypeVar("F", bound=Callable[..., Any])

_RESERVED_LOG_RECORD_ATTRS = set(logging.makeLogRecord({}).__dict__.keys())
_REQUEST_ID: ContextVar[str] = ContextVar("request_id", default="")
_PIPELINE_ID: ContextVar[str] = ContextVar("pipeline_id", default="")


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    if hasattr(value, "__dict__"):
        return value.__dict__
    return str(value)


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key.startswith("_") or key in _RESERVED_LOG_RECORD_ATTRS:
                continue
            payload[key] = value
        if _REQUEST_ID.get():
            payload["request_id"] = _REQUEST_ID.get()
        if _PIPELINE_ID.get():
            payload["pipeline_id"] = _PIPELINE_ID.get()
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=_json_default, ensure_ascii=True)


def set_request_id(request_id: str) -> None:
    _REQUEST_ID.set(request_id)


def clear_request_id() -> None:
    _REQUEST_ID.set("")


def set_pipeline_id(pipeline_id: str) -> None:
    _PIPELINE_ID.set(pipeline_id)


def clear_pipeline_id() -> None:
    _PIPELINE_ID.set("")


class StructuredLogger:
    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    @property
    def name(self) -> str:
        return self._logger.name

    def bind(self, **context: Any) -> "BoundLogger":
        return BoundLogger(self, context)

    def log(self, level: int, message: str, **fields: Any) -> None:
        self._logger.log(level, message, extra=fields or None)

    def debug(self, message: str, **fields: Any) -> None:
        self.log(logging.DEBUG, message, **fields)

    def info(self, message: str, **fields: Any) -> None:
        self.log(logging.INFO, message, **fields)

    def warning(self, message: str, **fields: Any) -> None:
        self.log(logging.WARNING, message, **fields)

    def error(self, message: str, exc_info: bool = False, **fields: Any) -> None:
        self._logger.error(message, extra=fields or None, exc_info=exc_info)

    def exception(self, message: str, **fields: Any) -> None:
        self._logger.exception(message, extra=fields or None)

    def log_agent_action(
        self,
        *,
        agent_name: str,
        action: str,
        input_data: Any = None,
        output_data: Any = None,
        error: Any = None,
        execution_time: Optional[float] = None,
        status: Optional[str] = None,
    ) -> None:
        resolved_status = status or ("failed" if error else "success")
        level = logging.ERROR if error else logging.INFO
        self.log(
            level,
            f"{agent_name}:{action}",
            agent=agent_name,
            action=action,
            input=input_data,
            output=output_data,
            error=error,
            execution_time=execution_time,
            status=resolved_status,
        )


class BoundLogger:
    def __init__(self, logger: StructuredLogger, context: dict[str, Any]) -> None:
        self._logger = logger
        self._context = context

    def _merge(self, fields: dict[str, Any]) -> dict[str, Any]:
        return {**self._context, **fields}

    def debug(self, message: str, **fields: Any) -> None:
        self._logger.debug(message, **self._merge(fields))

    def info(self, message: str, **fields: Any) -> None:
        self._logger.info(message, **self._merge(fields))

    def warning(self, message: str, **fields: Any) -> None:
        self._logger.warning(message, **self._merge(fields))

    def error(self, message: str, exc_info: bool = False, **fields: Any) -> None:
        self._logger.error(message, exc_info=exc_info, **self._merge(fields))

    def exception(self, message: str, **fields: Any) -> None:
        self._logger.exception(message, **self._merge(fields))


class AgentLogHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        return None


def _build_handler() -> logging.Handler:
    handler = logging.StreamHandler(sys.stdout)
    if settings.LOG_FORMAT == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s [%(name)s] %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S%z",
            )
        )
    return handler


def get_logger(name: str) -> StructuredLogger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.addHandler(_build_handler())
        logger.setLevel(getattr(logging, settings.LOG_LEVEL, logging.INFO))
        logger.propagate = False
    return StructuredLogger(logger)


def get_agent_logger(name: str) -> StructuredLogger:
    return get_logger(f"agent.{name}" if not name.startswith("agent.") else name)


@contextmanager
def timed_operation(
    logger: StructuredLogger,
    operation_name: str,
    *,
    agent: Optional[str] = None,
    input_data: Any = None,
) -> Iterator[dict[str, Any]]:
    state: dict[str, Any] = {"output_data": None, "error": None}
    started_at = time.perf_counter()
    try:
        yield state
    except Exception as exc:
        state["error"] = str(exc)
        raise
    finally:
        logger.log_agent_action(
            agent_name=agent or logger.name,
            action=operation_name,
            input_data=input_data,
            output_data=state.get("output_data"),
            error=state.get("error"),
            execution_time=round(time.perf_counter() - started_at, 6),
        )


@asynccontextmanager
async def async_timed_operation(
    logger: StructuredLogger,
    operation_name: str,
    *,
    agent: Optional[str] = None,
    input_data: Any = None,
) -> Any:
    state: dict[str, Any] = {"output_data": None, "error": None}
    started_at = time.perf_counter()
    try:
        yield state
    except Exception as exc:
        state["error"] = str(exc)
        raise
    finally:
        logger.log_agent_action(
            agent_name=agent or logger.name,
            action=operation_name,
            input_data=input_data,
            output_data=state.get("output_data"),
            error=state.get("error"),
            execution_time=round(time.perf_counter() - started_at, 6),
        )


def log_execution_time(
    logger: Optional[StructuredLogger] = None,
    *,
    action: Optional[str] = None,
    agent: Optional[str] = None,
) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        resolved_logger = logger or get_logger(func.__module__)
        resolved_action = action or func.__name__
        resolved_agent = agent or resolved_logger.name

        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                started_at = time.perf_counter()
                try:
                    result = await func(*args, **kwargs)
                    resolved_logger.log_agent_action(
                        agent_name=resolved_agent,
                        action=resolved_action,
                        input_data={"args": args, "kwargs": kwargs},
                        output_data=result,
                        execution_time=round(time.perf_counter() - started_at, 6),
                    )
                    return result
                except Exception as exc:
                    resolved_logger.log_agent_action(
                        agent_name=resolved_agent,
                        action=resolved_action,
                        input_data={"args": args, "kwargs": kwargs},
                        error=str(exc),
                        execution_time=round(time.perf_counter() - started_at, 6),
                        status="failed",
                    )
                    raise

            return async_wrapper  # type: ignore[return-value]

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            started_at = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                resolved_logger.log_agent_action(
                    agent_name=resolved_agent,
                    action=resolved_action,
                    input_data={"args": args, "kwargs": kwargs},
                    output_data=result,
                    execution_time=round(time.perf_counter() - started_at, 6),
                )
                return result
            except Exception as exc:
                resolved_logger.log_agent_action(
                    agent_name=resolved_agent,
                    action=resolved_action,
                    input_data={"args": args, "kwargs": kwargs},
                    error=str(exc),
                    execution_time=round(time.perf_counter() - started_at, 6),
                    status="failed",
                )
                raise

        return sync_wrapper  # type: ignore[return-value]

    return decorator
