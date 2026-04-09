import asyncio
import json
import time
from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable, Optional, TypeVar

from app.core.logger import get_pipeline_id, get_request_id
from app.core.exceptions import AgentExecutionError
from app.core.logging import get_agent_logger
from app.schemas.agent_message import AgentMessage

T = TypeVar("T")
REDACTED_VALUE = "***REDACTED***"
SENSITIVE_KEYS = {
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "credentials",
    "username_password",
    "login",
}


class BaseAgent(ABC):
    def __init__(self, agent_name: str) -> None:
        self.agent_name = agent_name
        self.logger = get_agent_logger(agent_name)

    @abstractmethod
    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        pass

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        started_at = time.perf_counter()
        try:
            self._validate_input(input_data)
            self._safe_log(
                "info",
                "Agent execution started.",
                agent=self.agent_name,
                status="started",
                input=self._prepare_log_payload(input_data),
            )
            result = await self.execute(input_data)
            elapsed = round(time.perf_counter() - started_at, 6)
            normalized = self._normalize_output(result, input_data, elapsed)
            resolved_status = self._resolve_log_status(normalized)
            self._safe_log(
                "info" if resolved_status != "failed" else "error",
                "Agent execution completed.",
                agent=self.agent_name,
                status=resolved_status,
                execution_time=elapsed,
                output=self._prepare_log_payload(normalized),
            )
            self.logger.log_agent_action(
                agent_name=self.agent_name,
                action="run",
                input_data=self._prepare_log_payload(input_data),
                output_data=self._prepare_log_payload(normalized),
                execution_time=elapsed,
                status=normalized["status"],
                error=normalized.get("error"),
            )
            asyncio.create_task(
                self._persist_log(
                    action="run",
                    input_data=self._prepare_log_payload(input_data),
                    output_data=self._prepare_log_payload(normalized.get("data")),
                    error=normalized.get("error"),
                    status=normalized["status"],
                    execution_time=elapsed,
                )
            )
            return normalized
        except Exception as exc:
            elapsed = round(time.perf_counter() - started_at, 6)
            error_message = str(exc)
            failure_response = self._normalize_output(self._build_failure(error_message), input_data, elapsed)
            self._safe_log(
                "error",
                "Agent execution failed.",
                agent=self.agent_name,
                status="failed",
                error=error_message,
                execution_time=elapsed,
                exc_info=True,
            )
            asyncio.create_task(
                self._persist_log(
                    action="run",
                    input_data=self._prepare_log_payload(input_data),
                    output_data=None,
                    error=error_message,
                    status="fail",
                    execution_time=elapsed,
                )
            )
            return failure_response

    async def safe_execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        return await self.run(input_data)

    def _validate_input(self, input_data: dict[str, Any]) -> None:
        if not isinstance(input_data, dict):
            raise AgentExecutionError(
                "Agent input must be a dictionary.",
                agent_name=self.agent_name,
            )

    def validate_required_fields(
        self,
        input_data: dict[str, Any],
        required_fields: list[str],
    ) -> Optional[str]:
        missing_fields = [field for field in required_fields if field not in input_data]
        if missing_fields:
            return f"Missing required fields: {', '.join(missing_fields)}"
        return None

    def validate_input(
        self,
        input_data: dict[str, Any],
        required_fields: Optional[list[str]] = None,
    ) -> Optional[str]:
        self._validate_input(input_data)
        if required_fields:
            return self.validate_required_fields(input_data, required_fields)
        return None

    async def retry_operation(
        self,
        operation: Callable[..., Awaitable[T]],
        *operation_args: Any,
        max_retries: int = 3,
        delay: float = 1.0,
        backoff_factor: float = 2.0,
        exceptions: tuple[type[Exception], ...] = (Exception,),
        **operation_kwargs: Any,
    ) -> T:
        last_error: Optional[Exception] = None
        for attempt in range(1, max_retries + 1):
            try:
                return await operation(*operation_args, **operation_kwargs)
            except exceptions as exc:
                last_error = exc
                if attempt == max_retries:
                    break
                wait_seconds = delay * (backoff_factor ** (attempt - 1))
                self.logger.warning(
                    "Retrying agent operation.",
                    agent=self.agent_name,
                    attempt=attempt,
                    max_retries=max_retries,
                    error=str(exc),
                    wait_seconds=wait_seconds,
                )
                await asyncio.sleep(wait_seconds)
        raise AgentExecutionError(
            str(last_error) if last_error else "Agent operation failed.",
            agent_name=self.agent_name,
        )

    def _build_success(self, data: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        return AgentMessage.success(self.agent_name, data or {}).model_dump()

    def _build_failure(
        self,
        error: str,
        data: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        return AgentMessage.fail(self.agent_name, error, data or {}).model_dump()

    def _attach_execution_time(self, payload: dict[str, Any], execution_time: float) -> dict[str, Any]:
        metadata = payload.setdefault("metadata", {})
        metadata["execution_time"] = f"{execution_time:.6f}"
        return payload

    def _resolve_log_status(self, payload: dict[str, Any]) -> str:
        if payload.get("status") == "fail":
            return "failed"
        data = payload.get("data", {})
        if isinstance(data, dict):
            inner_status = data.get("status")
            if inner_status in {"skipped", "failed", "success"}:
                return inner_status
        return "success"

    def _safe_log(self, level: str, message: str, **fields: Any) -> None:
        try:
            trace_fields = {
                "request_id": get_request_id(),
                "pipeline_id": str(
                    fields.pop("pipeline_id", "")
                    or (fields.get("input") or {}).get("pipeline_id", "")
                    or get_pipeline_id()
                ),
            }
            log_method = getattr(self.logger, level, self.logger.info)
            log_method(message, **trace_fields, **fields)
        except Exception:
            return

    def _normalize_output(
        self,
        result: Any,
        input_data: Optional[dict[str, Any]] = None,
        execution_time: Optional[float] = None,
    ) -> dict[str, Any]:
        if not isinstance(result, dict):
            raise AgentExecutionError(
                "Agent execute() must return a dictionary.",
                agent_name=self.agent_name,
            )
        if {"status", "data", "error", "metadata"}.issubset(result.keys()):
            payload = result
        else:
            payload = self._build_success(result)

        metadata = payload.setdefault("metadata", {})
        metadata["agent"] = metadata.get("agent") or self.agent_name
        metadata["timestamp"] = metadata.get("timestamp") or AgentMessage.success(self.agent_name).metadata.timestamp
        inferred_source = self._infer_source(input_data or {}, payload.get("data"))
        if not metadata.get("source"):
            metadata["source"] = inferred_source
        inferred_type = self._infer_type(input_data or {}, payload.get("data"))
        if not metadata.get("type") or metadata.get("type") == "generic":
            metadata["type"] = inferred_type
        if execution_time is not None:
            metadata["execution_time"] = f"{execution_time:.6f}"
        else:
            metadata["execution_time"] = metadata.get("execution_time") or "0.000000"

        AgentMessage.model_validate(payload)
        return payload

    def _infer_source(self, input_data: dict[str, Any], output_data: Any) -> str:
        for container in (
            input_data,
            output_data if isinstance(output_data, dict) else {},
            input_data.get("metadata") if isinstance(input_data.get("metadata"), dict) else {},
        ):
            for key in ("source", "source_url", "url", "final_url", "login_url"):
                value = container.get(key)
                if value:
                    return str(value)
        return ""

    def _infer_type(self, input_data: dict[str, Any], output_data: Any) -> str:
        for container in (
            output_data if isinstance(output_data, dict) else {},
            input_data,
        ):
            for key in ("type", "operation", "scrape_type", "scraping_type", "analysis_mode"):
                value = container.get(key)
                if value:
                    return str(value)
        return self.agent_name

    async def _persist_log(
        self,
        *,
        action: str,
        input_data: Any,
        output_data: Any,
        error: Optional[str],
        status: str,
        execution_time: float,
    ) -> None:
        try:
            from app.db.session import async_session_factory
            from app.models.log import Log

            async with async_session_factory() as session:
                session.add(
                    Log(
                        agent_name=self.agent_name,
                        action=action,
                        input_data=self._safe_json(input_data),
                        output_data=self._safe_json(output_data),
                        error=error,
                        status=status,
                        execution_time=execution_time,
                    )
                )
                await session.commit()
        except Exception as exc:
            self.logger.warning(
                "Failed to persist agent log.",
                agent=self.agent_name,
                error=str(exc),
            )

    @staticmethod
    def _safe_json(data: Any) -> Any:
        try:
            json.dumps(data)
            return data
        except TypeError:
            if isinstance(data, dict):
                return {str(key): BaseAgent._safe_json(value) for key, value in data.items()}
            if isinstance(data, (list, tuple, set)):
                return [BaseAgent._safe_json(item) for item in data]
            return str(data)

    @classmethod
    def _redact_sensitive_data(cls, data: Any) -> Any:
        if isinstance(data, dict):
            redacted: dict[str, Any] = {}
            for key, value in data.items():
                key_text = str(key).strip().lower()
                if key_text in SENSITIVE_KEYS:
                    redacted[str(key)] = REDACTED_VALUE
                else:
                    redacted[str(key)] = cls._redact_sensitive_data(value)
            return redacted
        if isinstance(data, list):
            return [cls._redact_sensitive_data(item) for item in data]
        if isinstance(data, tuple):
            return [cls._redact_sensitive_data(item) for item in data]
        if isinstance(data, set):
            return [cls._redact_sensitive_data(item) for item in data]
        return data

    @classmethod
    def _prepare_log_payload(cls, data: Any) -> Any:
        return cls._safe_json(cls._redact_sensitive_data(data))

    def build_response(self, status: str, data: Any = None, error: Optional[str] = None) -> dict[str, Any]:
        if status == "success":
            return self._build_success(data if isinstance(data, dict) else {"result": data})
        return self._build_failure(error or "Unknown error", data if isinstance(data, dict) else {"result": data})

    def success_response(self, data: Any = None) -> dict[str, Any]:
        return self.build_response("success", data=data)

    def fail_response(self, error: str, data: Any = None) -> dict[str, Any]:
        return self.build_response("fail", data=data, error=error)
