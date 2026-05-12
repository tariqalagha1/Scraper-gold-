"""Canonical external scrape endpoint for service integrations."""
from __future__ import annotations

from time import perf_counter
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import verify_api_key
from app.core.logging import get_logger
from app.core.service_health import get_core_services_status
from app.db.session import engine
from app.schemas.scrape import ScrapeRequest, ScrapeResponse
from app.services.scrape_contract import (
    build_sources_breakdown,
    build_quality_metadata,
    deduplicate_records,
    normalize_errors,
    normalize_records,
    normalize_status,
    resolve_request_id,
)


router = APIRouter()
logger = get_logger("app.api.v1.scrape")


def _get_scrape_orchestrator():
    from app.orchestrator.smart_orchestrator import SmartOrchestrator

    return SmartOrchestrator()


async def verify_system_health():
    services = await get_core_services_status(engine)
    if any(status == "down" for status in services.values()):
        raise HTTPException(
            status_code=503,
            detail={"status": "down", "services": services}
        )


async def run_pipeline(input_data: dict[str, object]) -> dict[str, object]:
    """Contract-mode pipeline hook.

    Kept as a dedicated function so tests and integration environments can
    monkeypatch execution without altering endpoint behavior.
    """
    request = ScrapeRequest.model_validate(input_data)
    request_id = resolve_request_id(request)
    try:
        orchestrator = _get_scrape_orchestrator()
        if str(request.url or "").strip():
            credentials: dict[str, object] = {}
            if str(request.login_url or "").strip():
                credentials["login_url"] = str(request.login_url).strip()
            if str(request.login_username or "").strip():
                credentials["username"] = str(request.login_username).strip()
            if str(request.login_password or "").strip():
                credentials["password"] = str(request.login_password).strip()
            orchestration_result = await orchestrator.run(
                {
                    "url": str(request.url).strip(),
                    "scrape_type": "structured",
                    "credentials": credentials,
                    "config": {
                        "prompt": request.query,
                        "location": request.location,
                        "fields": list(request.fields),
                        "request_id": request_id,
                        "source_type": request.source_type,
                        "max_records": request.limit,
                    },
                    "strategy": {
                        "record_fields": list(request.fields),
                    },
                    "run_id": request_id,
                }
            )
        else:
            task_payload: dict[str, object] = {
                "task_type": "scrape",
                "task_id": request_id,
                "input_payload": request.model_dump(exclude_none=True),
            }
            if isinstance(task_payload["input_payload"], dict):
                task_payload["input_payload"]["request_id"] = request_id
            orchestration_result = await orchestrator.run(task_payload)
    except Exception as exc:
        logger.error(
            "Scrape orchestration failed before contract response generation.",
            request_id=request_id,
            error=str(exc),
            exc_info=True,
        )
        return {
            "request_id": request_id,
            "status": "failed",
            "final_data": [],
            "sources": [request.source_type] if request.source_type else [],
            "errors": [f"Scrape execution failed: {exc}"],
            "execution_time": 0.0,
            "quality_metrics": {},
        }

    if not isinstance(orchestration_result, dict):
        orchestration_result = {}

    output_payload = orchestration_result.get("output_payload", {})
    if "output_payload" in orchestration_result and isinstance(output_payload, dict):
        errors = normalize_errors(output_payload.get("errors"))
        if not errors:
            errors = normalize_errors(orchestration_result.get("errors", []))

        sources = output_payload.get("sources")
        if not isinstance(sources, list):
            sources = [request.source_type] if request.source_type else []

        return {
            "request_id": str(output_payload.get("request_id") or request_id),
            "status": str(orchestration_result.get("status") or "failed"),
            "final_data": output_payload.get("data", []),
            "sources": sources,
            "errors": normalize_errors(errors),
            "execution_time": output_payload.get("execution_time", 0.0),
            "quality_metrics": output_payload.get("quality", {}),
        }

    local_result = orchestration_result.get("result", {})
    if not isinstance(local_result, dict):
        local_result = {}
    execution = orchestration_result.get("execution", {})
    if not isinstance(execution, dict):
        execution = {}
    metadata = orchestration_result.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}

    raw_sources = []
    if request.source_type:
        raw_sources = [{"name": request.source_type, "count": len(local_result.get("data", []))}]

    return {
        "request_id": request_id,
        "status": str(orchestration_result.get("status") or "failed"),
        "final_data": local_result.get("data", []),
        "sources": raw_sources,
        "errors": normalize_errors(orchestration_result.get("errors", [])),
        "execution_time": max(0.0, float(metadata.get("duration_ms", 0) or 0) / 1000.0),
        "quality_metrics": execution.get("validation", {}).get("metrics", {}) if isinstance(execution.get("validation"), dict) else {},
    }


def _normalize_records(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


@router.post(
    "",
    response_model=ScrapeResponse,
    response_model_exclude={
        "quality": {
            "sources_used",
            "sources_skipped",
            "execution_order",
            "cross_source_duplicates_removed",
            "source_reliability",
            "execution_tiers",
            "tiers_executed",
            "early_stopped",
            "fallback_used",
            "retries_triggered",
            "policy",
        }
    },
    summary="Canonical scraper entrypoint",
    dependencies=[Depends(verify_api_key), Depends(verify_system_health)],
)
async def scrape(payload: ScrapeRequest) -> ScrapeResponse:
    logger.info(
        "Scrape contract request received.",
        request_id=payload.request_id,
        source_type=payload.source_type,
        location=payload.location,
        limit=payload.limit,
    )
    started = perf_counter()
    pipeline_result = await run_pipeline(payload.model_dump())
    elapsed_seconds = round(max(0.0, perf_counter() - started), 4)

    records = pipeline_result.get("final_data", pipeline_result.get("data", []))
    pipeline_records = _normalize_records(records)
    normalized_records, normalized_fields_count = normalize_records(pipeline_records)
    deduped_records, duplicates_removed = deduplicate_records(normalized_records, payload.fields)
    selected_records = deduped_records[: payload.limit]

    errors = normalize_errors(pipeline_result.get("errors", []))
    status = normalize_status(
        pipeline_result.get("status"),
        has_errors=bool(errors),
        total_records=len(selected_records),
    )
    
    if str(pipeline_result.get("status") or "").strip().lower() in ("success", "completed", "partial") and len(selected_records) == 0:
        if "No data returned" not in errors:
            errors.append("No data returned")
            status = "failed"
    request_id = str(pipeline_result.get("request_id") or resolve_request_id(payload))
    execution_time = pipeline_result.get("execution_time")
    try:
        execution_seconds = max(0.0, float(execution_time))
    except (TypeError, ValueError):
        execution_seconds = 0.0
    if execution_seconds <= 0.0:
        execution_seconds = elapsed_seconds

    quality = build_quality_metadata(
        records=selected_records,
        fields=payload.fields,
        duplicates_removed=duplicates_removed,
        errors_count=len(errors),
        normalized_fields_count=normalized_fields_count,
    )

    response = ScrapeResponse(
        request_id=request_id,
        status=status,
        execution_time=execution_seconds,
        total=len(selected_records),
        data=selected_records,
        sources=build_sources_breakdown(selected_records, pipeline_result.get("sources", [])),
        errors=errors,
        quality=quality,
    )
    logger.info(
        "Scrape contract request completed.",
        request_id=payload.request_id,
        total=response.total,
        duplicates_removed=response.quality.duplicates_removed,
        coverage=response.quality.coverage,
    )
    return response

@router.post(
    "/multi",
    response_model=ScrapeResponse,
    summary="Multi-source scraper entrypoint",
    dependencies=[Depends(verify_api_key), Depends(verify_system_health)],
)
async def scrape_multi(payload: ScrapeRequest) -> ScrapeResponse:
    from app.services.multi_source_service import execute_multi_source
    from app.observability.event_emitter import emit
    from app.policy.policy_service import enforce_request_policy, enforce_quality_policy, get_policy
    from uuid import uuid4
    
    trace_id = str(uuid4())
    
    logger.info(
        "Multi-source request received.",
        request_id=payload.request_id,
        sources=payload.sources,
    )
    
    decision, filtered_sources, final_limit, final_force = enforce_request_policy(
        tenant_id="default",
        requested_sources=payload.sources,
        requested_limit=payload.limit,
        force_sources=payload.force_sources,
        trace_id=trace_id
    )
    
    payload.sources = filtered_sources
    payload.limit = final_limit
    payload.force_sources = final_force
    
    started = perf_counter()
    multi_res = await execute_multi_source(payload, trace_id)
    elapsed_seconds = round(max(0.0, perf_counter() - started), 4)
    
    records = multi_res.get("final_data", [])
    pipeline_records = _normalize_records(records)
    normalized_records, normalized_fields_count = normalize_records(pipeline_records)
    
    deduped_records, duplicates_removed = deduplicate_records(normalized_records, payload.fields)
    selected_records = deduped_records[: payload.limit]

    errors = normalize_errors(multi_res.get("errors", []))
    status = normalize_status(
        "completed" if selected_records else "failed",
        has_errors=bool(errors),
        total_records=len(selected_records),
    )
    
    if status in ("success", "completed", "partial") and len(selected_records) == 0:
        if "No data returned" not in errors:
            errors.append("No data returned")
            status = "failed"
            
    request_id = str(payload.request_id or resolve_request_id(payload))

    quality = build_quality_metadata(
        records=selected_records,
        fields=payload.fields,
        duplicates_removed=duplicates_removed,
        errors_count=len(errors),
        normalized_fields_count=normalized_fields_count,
    )
    quality.sources_used = multi_res.get("sources_used", [])
    quality.sources_skipped = multi_res.get("sources_skipped", [])
    quality.execution_order = multi_res.get("execution_order", [])
    quality.cross_source_duplicates_removed = multi_res.get("cross_source_duplicates_removed", 0)
    quality.execution_tiers = multi_res.get("execution_tiers", {})
    quality.tiers_executed = multi_res.get("tiers_executed", [])
    quality.early_stopped = multi_res.get("early_stopped", False)
    quality.fallback_used = multi_res.get("fallback_used", False)
    quality.retries_triggered = multi_res.get("retries_triggered", [])
    quality.policy = decision
    
    if status == "completed":
        passes_quality = enforce_quality_policy("default", quality.confidence, quality.coverage, trace_id)
        if not passes_quality:
            status = "partial"
            errors.append("Result below tenant quality policy threshold")
    
    from app.services.source_reliability_service import get_reliability_score
    quality.source_reliability = {
        s: get_reliability_score(s) for s in quality.sources_used
    }

    response = ScrapeResponse(
        request_id=request_id,
        status=status,
        execution_time=elapsed_seconds,
        total=len(selected_records),
        data=selected_records,
        sources=build_sources_breakdown(selected_records, [{"name": s} for s in multi_res.get("sources_used", [])]),
        errors=errors,
        quality=quality,
    )
    
    if status == "failed":
        emit("SCRAPE_FAILED", {"error": errors[0] if errors else "unknown"}, trace_id)
    else:
        emit("SCRAPE_COMPLETED", {"total": response.total, "confidence": quality.confidence}, trace_id)
        
    return response

@router.get(
    "/sources/reliability",
    summary="Get source reliability profiles",
    dependencies=[Depends(verify_api_key)],
)
async def get_sources_reliability():
    from app.services.source_reliability_service import get_all_reliability_profiles
    return {"sources": get_all_reliability_profiles()}
