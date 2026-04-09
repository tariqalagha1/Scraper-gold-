from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime
from typing import Any


def _ensure_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _ensure_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _compute_duration_ms(started_at: Any, finished_at: Any) -> int:
    started = _coerce_datetime(started_at)
    finished = _coerce_datetime(finished_at)
    if not started or not finished:
        return 0
    return max(0, int((finished - started).total_seconds() * 1000))


def _extract_structured_records(processed_payload: Any) -> list[dict[str, Any]]:
    if isinstance(processed_payload, list):
        return [item for item in processed_payload if isinstance(item, dict)]

    if not isinstance(processed_payload, dict) or not processed_payload:
        return []

    if isinstance(processed_payload.get("items"), list):
        return [item for item in processed_payload["items"] if isinstance(item, dict)]

    candidates = [
        value
        for value in processed_payload.values()
        if isinstance(value, list) and value and all(isinstance(item, dict) for item in value)
    ]
    if candidates:
        return list(max(candidates, key=len))

    if processed_payload and not any(
        key in processed_payload for key in {"summary", "page_type", "cleaned_text", "tables", "links", "files", "images"}
    ):
        return [processed_payload]

    return []


def normalize_export_contract(
    payload: dict[str, Any] | None,
    *,
    analysis_data: dict[str, Any] | None = None,
    source_url: str = "",
) -> dict[str, Any]:
    """Return a predictable normalized contract for exporters."""
    payload = _ensure_dict(payload)
    if {"request", "result", "execution", "metadata"}.issubset(payload.keys()):
        contract = deepcopy(payload)
        contract["request"] = _ensure_dict(contract.get("request"))
        contract["result"] = _ensure_dict(contract.get("result"))
        contract["execution"] = _ensure_dict(contract.get("execution"))
        contract["metadata"] = _ensure_dict(contract.get("metadata"))
        contract["errors"] = [str(item) for item in _ensure_list(contract.get("errors"))]
        contract["result"]["data"] = [
            item for item in _ensure_list(contract["result"].get("data")) if isinstance(item, dict)
        ]
        contract["result"]["raw"] = _ensure_dict(contract["result"].get("raw"))
        processed = contract["result"].get("processed")
        contract["result"]["processed"] = processed if isinstance(processed, (dict, list)) else {}
        if not contract["result"]["data"]:
            contract["result"]["data"] = _extract_structured_records(contract["result"]["processed"])
        contract["result"]["analysis"] = _ensure_dict(contract["result"].get("analysis"))
        contract["result"]["vector"] = _ensure_dict(contract["result"].get("vector"))
        contract["result"]["exports"] = _ensure_dict(contract["result"].get("exports"))
        contract["execution"]["decision"] = _ensure_dict(contract["execution"].get("decision"))
        contract["execution"]["validation"] = _ensure_dict(contract["execution"].get("validation"))
        contract["execution"]["retry"] = _ensure_dict(contract["execution"].get("retry"))
        contract["execution"]["memory"] = _ensure_dict(contract["execution"].get("memory"))
        contract["execution"]["timing"] = _ensure_dict(contract["execution"].get("timing"))
        contract["execution"]["steps"] = _ensure_dict(contract["execution"].get("steps"))
        contract["execution"]["trace"] = _ensure_dict(contract["execution"].get("trace"))
        return contract

    processed_payload_raw = payload.get("processed_data", payload)
    processed_payload = (
        processed_payload_raw
        if isinstance(processed_payload_raw, (dict, list))
        else _ensure_dict(processed_payload_raw)
    )
    records = _extract_structured_records(processed_payload)
    status = str(payload.get("status") or ("completed" if records else "failed"))
    trace = _ensure_dict(payload.get("trace"))
    classification = _ensure_dict(trace.get("classification"))
    validation = _ensure_dict(payload.get("validation"))
    return {
        "status": status,
        "request": {
            "url": str(source_url or payload.get("url") or ""),
            "scrape_type": str(payload.get("scraping_type") or payload.get("scrape_type") or payload.get("data_type") or ""),
            "config": _ensure_dict(payload.get("config")),
            "strategy": _ensure_dict(payload.get("strategy")),
        },
        "result": {
            "data": records,
            "raw": _ensure_dict(payload.get("raw_data")),
            "processed": processed_payload,
            "analysis": _ensure_dict(analysis_data or payload.get("analysis_data")),
            "vector": _ensure_dict(payload.get("vector_data")),
            "exports": _ensure_dict(payload.get("export_paths")),
        },
        "execution": {
            "decision": {
                "page_type": str(
                    classification.get("page_type")
                    or payload.get("page_type")
                    or (processed_payload.get("page_type") if isinstance(processed_payload, dict) else "")
                    or "unknown"
                ),
                "confidence": _coerce_float(classification.get("confidence")),
                "reason": str(classification.get("reason") or ""),
            },
            "validation": {
                "status": str(validation.get("status") or "unknown"),
                "confidence": _coerce_float(validation.get("confidence")),
                "issues": [str(item) for item in _ensure_list(validation.get("issues"))],
                "metrics": _ensure_dict(validation.get("metrics")),
                "should_retry": bool(validation.get("should_retry", False)),
            },
            "retry": {
                "attempted": bool(trace.get("retry_attempted", payload.get("retry", False))),
                "result": bool(payload.get("retry_result", False)),
            },
            "memory": {
                "used": bool(trace.get("memory_used", False)),
                "selector_source": str(trace.get("selector_source") or "generated"),
                "success_rate": trace.get("memory_success_rate"),
            },
            "timing": _ensure_dict(payload.get("node_timings")),
            "steps": {
                "current": str(payload.get("current_step") or ""),
            },
            "trace": trace,
        },
        "errors": [str(item) for item in _ensure_list(payload.get("errors"))],
        "metadata": {
            "job_id": str(payload.get("job_id") or ""),
            "run_id": str(payload.get("run_id") or ""),
            "user_id": str(payload.get("user_id") or ""),
            "started_at": str(payload.get("started_at") or ""),
            "finished_at": str(payload.get("finished_at") or ""),
            "duration_ms": int(
                payload.get("duration_ms")
                or _compute_duration_ms(payload.get("started_at"), payload.get("finished_at"))
            ),
        },
    }


def get_export_data(contract: dict[str, Any]) -> list[dict[str, Any]]:
    normalized = normalize_export_contract(contract)
    return [item for item in _ensure_list(normalized["result"].get("data")) if isinstance(item, dict)]


def get_export_execution_summary(contract: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_export_contract(contract)
    execution = _ensure_dict(normalized.get("execution"))
    decision = _ensure_dict(execution.get("decision"))
    validation = _ensure_dict(execution.get("validation"))
    retry = _ensure_dict(execution.get("retry"))
    memory = _ensure_dict(execution.get("memory"))
    metadata = _ensure_dict(normalized.get("metadata"))
    return {
        "Page Type": str(decision.get("page_type") or "unknown"),
        "Decision Confidence": _coerce_float(decision.get("confidence")),
        "Decision Reason": str(decision.get("reason") or ""),
        "Validation Status": str(validation.get("status") or "unknown"),
        "Validation Confidence": _coerce_float(validation.get("confidence")),
        "Retry Attempted": bool(retry.get("attempted", False)),
        "Retry Result": bool(retry.get("result", False)),
        "Memory Used": bool(memory.get("used", False)),
        "Selector Source": str(memory.get("selector_source") or "generated"),
        "Run ID": str(metadata.get("run_id") or ""),
        "Duration (ms)": int(metadata.get("duration_ms") or 0),
        "Started At": str(metadata.get("started_at") or ""),
        "Finished At": str(metadata.get("finished_at") or ""),
    }


def get_export_metadata(contract: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_export_contract(contract)
    request = _ensure_dict(normalized.get("request"))
    metadata = _ensure_dict(normalized.get("metadata"))
    return {
        "URL": str(request.get("url") or ""),
        "Status": str(normalized.get("status") or ""),
        "Run ID": str(metadata.get("run_id") or ""),
        "Job ID": str(metadata.get("job_id") or ""),
        "User ID": str(metadata.get("user_id") or ""),
        "Started At": str(metadata.get("started_at") or ""),
        "Finished At": str(metadata.get("finished_at") or ""),
        "Duration (ms)": int(metadata.get("duration_ms") or 0),
    }


def get_export_errors(contract: dict[str, Any]) -> list[str]:
    normalized = normalize_export_contract(contract)
    errors = [str(item).strip() for item in _ensure_list(normalized.get("errors")) if str(item).strip()]
    return errors or ["None"]


def build_persisted_result_payload(workflow_result: dict[str, Any]) -> dict[str, Any]:
    """Persist the normalized contract while keeping processed aliases at the top level."""
    contract = normalize_export_contract(workflow_result)
    processed_aliases = _ensure_dict(contract["result"].get("processed"))
    return {
        **processed_aliases,
        "status": contract.get("status", ""),
        "request": contract.get("request", {}),
        "result": contract.get("result", {}),
        "execution": contract.get("execution", {}),
        "metadata": contract.get("metadata", {}),
        "errors": contract.get("errors", []),
    }


def get_export_json(contract: dict[str, Any]) -> bytes:
    normalized = normalize_export_contract(contract)
    return json.dumps(normalized, indent=2, ensure_ascii=True).encode("utf-8")
