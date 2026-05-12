from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select

from app.db.session import async_session_factory
from app.execution.task_registry import mark_cancelled, mark_completed, mark_failed, mark_running
from app.export.contract_helpers import build_persisted_result_payload
from app.models.job import Job
from app.models.result import Result
from app.models.run import Run
from app.observability.event_emitter import emit
from app.policy.policy_service import enforce_quality_policy, enforce_request_policy
from app.schemas.execution_contract import (
    ExecutionContract,
    build_execution_contract_from_job_config,
)
from app.schemas.scrape import ScrapeRequest
from app.services.run_logs import append_run_log
from app.services.scrape_contract import (
    build_quality_metadata,
    deduplicate_records,
    normalize_errors,
    normalize_records,
    normalize_status,
    resolve_request_id,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_payload(value: dict[str, Any] | None) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


async def _execute_multi_source(
    request: ScrapeRequest,
    trace_id: str,
    execution_controls: dict[str, bool] | None,
) -> dict[str, Any]:
    from app.services.multi_source_service import execute_multi_source

    return await execute_multi_source(
        request,
        trace_id,
        execution_controls=execution_controls,
    )


def _emit_stage_log(
    *,
    run_id: str,
    trace_id: str,
    stage: str,
    status: str,
    message: str,
    extra: dict[str, Any] | None = None,
) -> None:
    ui_node_map = {
        "policy_service": "intake",
        "strategic_execution_service": "scraper",
        "multi_source_service": "processing",
        "quality_layer": "vector",
        "event_emitter": "analysis",
    }
    details = {"stage": stage, "status": status}
    ui_node = ui_node_map.get(stage)
    if ui_node:
        details["node"] = ui_node
    if extra:
        details.update(extra)

    log_event = "node_started" if status == "started" else "node_completed" if status == "completed" else "node_failed"
    append_run_log(run_id, event=log_event, message=message, details=details)

    event_type = "STAGE_STARTED" if status == "started" else "STAGE_COMPLETED" if status == "completed" else "STAGE_FAILED"
    emit(event_type, {"stage": stage, **details}, trace_id)


def _build_request_from_job_and_contract(job: Job, contract: ExecutionContract) -> ScrapeRequest:
    config = dict(job.config or {})
    prompt = str(config.get("prompt") or "").strip()
    query = str(config.get("query") or prompt or job.url).strip()
    location = str(config.get("location") or "global").strip()

    raw_fields = config.get("fields") or ["name", "phone", "address"]
    if not isinstance(raw_fields, list) or not raw_fields:
        raw_fields = ["name", "phone", "address"]
    fields = [str(field).strip() for field in raw_fields if str(field).strip()]
    if not fields:
        fields = ["name", "phone", "address"]

    request_id = str(config.get("request_id") or "").strip() or None
    source_type = str(config.get("source_type") or "").strip() or None

    return ScrapeRequest(
        url=job.url,
        login_url=job.login_url,
        login_username=job.login_username,
        login_password=job.login_password,
        query=query,
        location=location,
        limit=contract.limit,
        fields=fields,
        source_type=source_type,
        request_id=request_id,
        sources=list(contract.sources),
        force_sources=False,
    )


def _resolve_execution_contract(runtime_payload: dict[str, Any], run: Run, job: Job) -> ExecutionContract:
    payload_contract = runtime_payload.get("execution_contract")
    if isinstance(payload_contract, dict):
        return ExecutionContract.model_validate(payload_contract)

    persisted_contract = run.execution_contract
    if isinstance(persisted_contract, dict):
        return ExecutionContract.model_validate(persisted_contract)

    return build_execution_contract_from_job_config(
        job.config,
        job_url=job.url,
    )


async def _load_job_and_run(
    *,
    job_id: str,
    user_id: str | None,
    run_id: str,
) -> tuple[Job | None, Run | None]:
    async with async_session_factory() as session:
        job_stmt = select(Job).where(Job.id == UUID(job_id))
        if user_id:
            job_stmt = job_stmt.where(Job.user_id == UUID(user_id))
        job = (await session.execute(job_stmt)).scalar_one_or_none()
        if job is None:
            return None, None
        run = (
            await session.execute(select(Run).where(Run.id == UUID(run_id), Run.job_id == job.id))
        ).scalar_one_or_none()
        return job, run


async def execute_scraping_run(
    job_id: str,
    user_id: str | None = None,
    payload: dict | None = None,
    trace_id: str | None = None,
) -> dict:
    runtime_payload = _normalize_payload(payload)
    run_id = str(runtime_payload.get("run_id") or "").strip()
    execution_trace_id = str(trace_id or runtime_payload.get("trace_id") or uuid4())

    if not run_id:
        error = "Missing run_id for execution payload."
        return {"status": "failed", "errors": [error], "trace_id": execution_trace_id}

    mark_running(run_id)
    started_at = _now()
    emit("SCRAPE_STARTED", {"job_id": job_id, "run_id": run_id}, execution_trace_id)
    append_run_log(run_id, event="run_started", message="Brain it execution started.")

    job, run = await _load_job_and_run(job_id=job_id, user_id=user_id, run_id=run_id)
    if job is None or run is None:
        error = "Job or run was not found for execution."
        mark_failed(run_id, error)
        emit("SCRAPE_FAILED", {"error": error}, execution_trace_id)
        return {"status": "failed", "errors": [error], "trace_id": execution_trace_id}

    try:
        execution_contract = _resolve_execution_contract(runtime_payload, run, job)
    except Exception as exc:
        message = str(exc).strip() or "Invalid execution contract"
        mark_failed(run_id, message)
        emit("SCRAPE_FAILED", {"error": message}, execution_trace_id)
        return {
            "run_id": run_id,
            "job_id": job_id,
            "trace_id": execution_trace_id,
            "status": "failed",
            "errors": [message],
        }

    async with async_session_factory() as session:
        db_run = (await session.execute(select(Run).where(Run.id == run.id))).scalar_one()
        db_job = (await session.execute(select(Job).where(Job.id == job.id))).scalar_one()
        db_run.status = "running"
        db_run.progress = max(5, int(db_run.progress or 0))
        db_run.started_at = started_at
        db_run.execution_contract = execution_contract.model_dump()
        db_job.status = "running"
        await session.commit()

    request = _build_request_from_job_and_contract(job, execution_contract)
    decision = {}

    for optional_agent in execution_contract.optional_agents:
        emit(
            "OPTIONAL_AGENT_REGISTERED",
            {"agent": optional_agent, "run_id": run_id},
            execution_trace_id,
        )
        append_run_log(
            run_id,
            event="optional_agent_registered",
            message=f"Optional agent declared: {optional_agent}",
            details={"agent": optional_agent},
        )

    try:
        _emit_stage_log(
            run_id=run_id,
            trace_id=execution_trace_id,
            stage="policy_service",
            status="started",
            message="Applying execution policy.",
        )
        decision, filtered_sources, final_limit, final_force = enforce_request_policy(
            tenant_id="default",
            requested_sources=request.sources,
            requested_limit=request.limit,
            force_sources=request.force_sources,
            trace_id=execution_trace_id,
        )
        request.sources = filtered_sources
        request.limit = final_limit
        request.force_sources = final_force
        _emit_stage_log(
            run_id=run_id,
            trace_id=execution_trace_id,
            stage="policy_service",
            status="completed",
            message="Execution policy applied.",
            extra={"sources": filtered_sources, "limit": final_limit},
        )

        _emit_stage_log(
            run_id=run_id,
            trace_id=execution_trace_id,
            stage="strategic_execution_service",
            status="started",
            message="Starting strategic execution planning.",
        )
        _emit_stage_log(
            run_id=run_id,
            trace_id=execution_trace_id,
            stage="multi_source_service",
            status="started",
            message="Starting multi-source collection.",
        )
        multi_res = await _execute_multi_source(
            request,
            execution_trace_id,
            execution_contract.controls.model_dump(),
        )
        _emit_stage_log(
            run_id=run_id,
            trace_id=execution_trace_id,
            stage="multi_source_service",
            status="completed",
            message="Multi-source collection completed.",
        )
        _emit_stage_log(
            run_id=run_id,
            trace_id=execution_trace_id,
            stage="strategic_execution_service",
            status="completed",
            message="Strategic execution completed.",
        )
    except Exception as exc:
        message = str(exc).strip() or "Execution failed."
        _emit_stage_log(
            run_id=run_id,
            trace_id=execution_trace_id,
            stage="strategic_execution_service",
            status="failed",
            message=message,
        )
        async with async_session_factory() as session:
            db_run = (await session.execute(select(Run).where(Run.id == run.id))).scalar_one()
            db_job = (await session.execute(select(Job).where(Job.id == job.id))).scalar_one()
            db_run.status = "failed"
            db_run.progress = min(100, max(1, int(db_run.progress or 0)))
            db_run.finished_at = _now()
            db_run.error = message
            db_run.error_message = message
            db_run.execution_result = {
                "status": "failed",
                "errors": [message],
                "trace_id": execution_trace_id,
            }
            db_job.status = "failed"
            await session.commit()
        append_run_log(run_id, event="run_failed", message=message, level="error")
        mark_failed(run_id, message)
        emit("SCRAPE_FAILED", {"error": message}, execution_trace_id)
        return {
            "run_id": run_id,
            "job_id": job_id,
            "trace_id": execution_trace_id,
            "status": "failed",
            "errors": [message],
            "execution_contract": execution_contract.model_dump(),
        }

    _emit_stage_log(
        run_id=run_id,
        trace_id=execution_trace_id,
        stage="quality_layer",
        status="started",
        message="Computing quality metrics.",
    )

    records = multi_res.get("final_data", [])
    pipeline_records = [item for item in records if isinstance(item, dict)]
    normalized_records, normalized_fields_count = normalize_records(pipeline_records)
    deduped_records, duplicates_removed = deduplicate_records(normalized_records, request.fields)
    selected_records = deduped_records[: request.limit]
    errors = normalize_errors(multi_res.get("errors", []))
    result_status = normalize_status(
        "completed" if selected_records else "failed",
        has_errors=bool(errors),
        total_records=len(selected_records),
    )
    if result_status in {"success", "completed", "partial"} and not selected_records:
        errors.append("No data returned")
        result_status = "failed"

    quality = build_quality_metadata(
        records=selected_records,
        fields=request.fields,
        duplicates_removed=duplicates_removed,
        errors_count=len(errors),
        normalized_fields_count=normalized_fields_count,
    )
    quality.sources_used = list(multi_res.get("sources_used", []))
    quality.sources_skipped = list(multi_res.get("sources_skipped", []))
    quality.execution_order = list(multi_res.get("execution_order", []))
    quality.cross_source_duplicates_removed = int(multi_res.get("cross_source_duplicates_removed", 0))
    quality.execution_tiers = dict(multi_res.get("execution_tiers", {}))
    quality.tiers_executed = list(multi_res.get("tiers_executed", []))
    quality.early_stopped = bool(multi_res.get("early_stopped", False))
    quality.fallback_used = bool(multi_res.get("fallback_used", False))
    quality.retries_triggered = list(multi_res.get("retries_triggered", []))
    quality.policy = decision

    if result_status == "completed":
        if not enforce_quality_policy("default", quality.confidence, quality.coverage, execution_trace_id):
            result_status = "partial"
            errors.append("Result below tenant quality policy threshold")

    cancelled = bool(runtime_payload.get("cancelled", False))
    if cancelled:
        result_status = "failed"
        errors.append("Run was cancelled by user")

    if result_status == "failed" and not errors:
        errors.append("Run failed before any usable data could be returned.")

    _emit_stage_log(
        run_id=run_id,
        trace_id=execution_trace_id,
        stage="quality_layer",
        status="completed",
        message="Quality metrics computed.",
    )

    finished_at = _now()
    workflow_result = {
        "status": "completed" if result_status in {"completed", "partial"} else "failed",
        "processed_data": {"items": selected_records},
        "raw_data": {"final_url": job.url},
        "validation": {
            "status": result_status,
            "confidence": quality.confidence,
            "issues": errors,
            "metrics": {
                "fill_ratio": quality.coverage,
                "duplicates_removed": quality.duplicates_removed,
                "normalized_fields": quality.normalized_fields,
                "errors_count": len(errors),
                "sources_used": len(quality.sources_used),
            },
            "should_retry": bool(errors),
        },
        "errors": errors,
        "job_id": str(job.id),
        "run_id": str(run.id),
        "user_id": str(job.user_id),
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
    }
    persisted_payload = build_persisted_result_payload(workflow_result)
    request_id = str(request.request_id or resolve_request_id(request))

    response = {
        "run_id": run_id,
        "job_id": job_id,
        "trace_id": execution_trace_id,
        "request_id": request_id,
        "status": result_status,
        "result": {
            "total": len(selected_records),
            "data": selected_records,
            "quality": quality.model_dump(),
            "sources_used": quality.sources_used,
        },
        "errors": errors,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "execution_contract": execution_contract.model_dump(),
    }

    async with async_session_factory() as session:
        db_run = (await session.execute(select(Run).where(Run.id == run.id))).scalar_one()
        db_job = (await session.execute(select(Job).where(Job.id == job.id))).scalar_one()

        if result_status == "failed":
            db_run.status = "failed"
            db_job.status = "failed"
        else:
            db_run.status = "completed"
            db_job.status = "completed"
        db_run.progress = 100
        db_run.finished_at = finished_at
        db_run.error = " | ".join(errors) if errors else None
        db_run.error_message = db_run.error
        db_run.pages_scraped = len(selected_records)
        db_run.execution_contract = execution_contract.model_dump()
        db_run.execution_result = response

        session.add(
            Result(
                run_id=db_run.id,
                data_json=persisted_payload,
                data_type=db_job.scrape_type,
                raw_html_path=None,
                screenshot_path=None,
                url=db_job.url,
            )
        )
        await session.commit()

    if result_status == "failed":
        failure_message = errors[0] if errors else "Run failed"
        _emit_stage_log(
            run_id=run_id,
            trace_id=execution_trace_id,
            stage="event_emitter",
            status="failed",
            message=failure_message,
        )
        append_run_log(run_id, event="run_failed", message=failure_message, level="error")
        mark_failed(run_id, failure_message, response)
        if cancelled:
            mark_cancelled(run_id, "Run was cancelled by user")
        emit("SCRAPE_FAILED", {"error": failure_message}, execution_trace_id)
    else:
        _emit_stage_log(
            run_id=run_id,
            trace_id=execution_trace_id,
            stage="event_emitter",
            status="started",
            message="Publishing final execution events.",
        )
        append_run_log(run_id, event="run_completed", message="Brain it execution completed.")
        mark_completed(run_id, response)
        emit(
            "SCRAPE_COMPLETED",
            {"total": len(selected_records), "confidence": quality.confidence},
            execution_trace_id,
        )

        _emit_stage_log(
            run_id=run_id,
            trace_id=execution_trace_id,
            stage="event_emitter",
            status="completed",
            message="Execution events published.",
        )
        _emit_stage_log(
            run_id=run_id,
            trace_id=execution_trace_id,
            stage="control_service",
            status="completed",
            message="Control state synchronized for run completion.",
        )

    return response
