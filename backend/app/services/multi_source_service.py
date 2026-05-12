import asyncio
from uuid import uuid4
from typing import Any
from copy import deepcopy

from app.schemas.scrape import ScrapeRequest
from app.api.v1.scrape import run_pipeline

SOURCE_WEIGHTS = {
    "internal": 1.0,
    "google_maps": 0.9,
    "web": 0.7
}

async def _run_source(source_name: str, request: ScrapeRequest, trace_id: str) -> dict[str, Any]:
    from time import perf_counter
    from app.services.source_reliability_service import record_source_result
    from app.observability.event_emitter import emit
    
    emit("SOURCE_STARTED", {"source": source_name}, trace_id)
    
    payload = request.model_dump(exclude_none=True)
    if source_name == "web":
        # Force full pipeline mode
        payload.pop("task_type", None)
        payload["task_type"] = "general"
        payload["source_type"] = "web"
    elif source_name == "google_maps":
        payload["task_type"] = "google_maps"
        payload["source_type"] = "google_maps"
    else:
        # Default internal scraper contract
        payload["task_type"] = "scrape"
        payload["source_type"] = "internal"
    
    start_time = perf_counter()
    try:
        res = await run_pipeline(payload)
        latency_ms = (perf_counter() - start_time) * 1000
        
        data = res.get("final_data", [])
        status = str(res.get("status") or ("success" if data else "failed"))
        quality = res.get("quality_metrics", {})
        
        record_source_result(
            source=source_name,
            status=status,
            total=len(data),
            coverage=quality.get("coverage", 0.0),
            confidence=quality.get("confidence", 0.0),
            latency_ms=latency_ms,
            duplicates_removed=quality.get("duplicates_removed", 0)
        )
        
        if status == "failed" or len(data) == 0:
             emit("SOURCE_FAILED", {"source": source_name, "error": res.get("errors", ["No data"])[0] if res.get("errors") else "No data"}, trace_id)
        else:
             emit("SOURCE_COMPLETED", {"source": source_name, "records": len(data), "latency_ms": latency_ms}, trace_id)
        
        return {"source_name": source_name, "result": res}
    except Exception as e:
        latency_ms = (perf_counter() - start_time) * 1000
        record_source_result(
            source=source_name,
            status="failed",
            total=0,
            coverage=0.0,
            confidence=0.0,
            latency_ms=latency_ms,
            duplicates_removed=0
        )
        emit("SOURCE_FAILED", {"source": source_name, "error": str(e)}, trace_id)
        return {"source_name": source_name, "result": {"final_data": [], "errors": [str(e)]}}

def _normalize_cross_source_key(record: dict[str, Any]) -> str:
    email = str(record.get("email") or "").strip().lower()
    if email: return email
    phone = str(record.get("phone") or record.get("contact") or "").strip().lower()
    if phone: return phone
    name = str(record.get("name") or "").strip().lower()
    location = str(record.get("location") or record.get("address") or "").strip().lower()
    if name and location: return f"{name}_{location}"
    if name: return name
    return str(hash(str(record)))

def _merge_records(existing: dict[str, Any], new: dict[str, Any], existing_weight: float, new_weight: float) -> dict[str, Any]:
    merged = deepcopy(existing)
    for k, v in new.items():
        if k not in merged or not merged[k]:
            merged[k] = v
        elif v and isinstance(v, str) and isinstance(merged[k], str) and len(v) > len(merged[k]) and new_weight > existing_weight:
            merged[k] = v
    return merged

def _score_record(record: dict[str, Any], fields: list[str], source_weight: float) -> float:
    filled = sum(1 for f in fields if record.get(f))
    coverage = filled / max(1, len(fields))
    completeness = filled / max(1, len(record))
    return (coverage * 0.5) + (source_weight * 0.3) + (completeness * 0.2)

def _accumulate_and_merge(existing_records: list[dict[str, Any]], new_records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int, list[str]]:
    unique_records = {}
    record_sources = {}
    cross_source_duplicates = 0
    
    for r in existing_records:
        key = _normalize_cross_source_key(r)
        unique_records[key] = r
        record_sources[key] = r.get("_source", "unknown")
        
    for r in new_records:
        key = _normalize_cross_source_key(r)
        src = r.get("_source", "unknown")
        weight = SOURCE_WEIGHTS.get(src, 0.5)
        
        if key in unique_records:
            existing_src = record_sources[key]
            existing_weight = SOURCE_WEIGHTS.get(existing_src, 0.5)
            unique_records[key] = _merge_records(unique_records[key], r, existing_weight, weight)
            if existing_src != src:
                cross_source_duplicates += 1
        else:
            unique_records[key] = r
            record_sources[key] = src
            
    final_list = list(unique_records.values())
    return final_list, cross_source_duplicates, list(record_sources.values())

async def execute_multi_source(
    request: ScrapeRequest,
    trace_id: str | None = None,
    execution_controls: dict[str, bool] | None = None,
) -> dict[str, Any]:
    from app.services.adaptive_source_selector import build_source_execution_plan
    from app.services.strategic_execution_service import execute_strategically
    from app.services.scrape_contract import calculate_coverage
    from app.observability.event_emitter import emit
    from app.control.control_service import clear_control
    
    resolved_trace_id = str(trace_id or uuid4())
    emit("SCRAPE_STARTED", {"query": request.query}, resolved_trace_id)
    
    try:
        plan = build_source_execution_plan(
            requested_sources=request.sources,
            force_sources=request.force_sources
        )
        
        strat_res = await execute_strategically(
            request=request,
            execution_order=plan.execution_order,
            run_source_func=_run_source,
            merge_records_func=_accumulate_and_merge,
            calculate_coverage_func=calculate_coverage,
            trace_id=resolved_trace_id,
            controls=execution_controls,
        )
        
        final_list = strat_res["final_data"]
        
        for r in final_list:
            src = r.get("_source", "unknown")
            weight = SOURCE_WEIGHTS.get(src, 0.5)
            r["_score"] = _score_record(r, request.fields, weight)
            
        final_list.sort(key=lambda x: x.get("_score", 0), reverse=True)
        
        for r in final_list:
            r.pop("_score", None)
            r.pop("_source", None)
            
        final_list = final_list[:request.limit]
        
        return {
            "final_data": final_list,
            "errors": strat_res["errors"],
            "sources_used": strat_res["sources_used"],
            "sources_skipped": plan.sources_skipped,
            "execution_order": plan.execution_order,
            "cross_source_duplicates_removed": strat_res["cross_source_duplicates_removed"],
            "execution_tiers": strat_res["execution_tiers"],
            "tiers_executed": strat_res["tiers_executed"],
            "early_stopped": strat_res["early_stopped"],
            "fallback_used": strat_res["fallback_used"],
            "retries_triggered": strat_res["retries_triggered"]
        }
    finally:
        clear_control(resolved_trace_id)
