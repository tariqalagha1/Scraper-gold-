import asyncio
from typing import Any, Dict, List, Callable, Awaitable
from copy import deepcopy

from app.schemas.scrape import ScrapeRequest
from app.services.source_reliability_service import SOURCE_RELIABILITY, get_reliability_score


DEFAULT_SOURCE_TIERS = {
    "internal": "high",
    "google_maps": "medium",
    "web": "low",
}
TIER_RANK = {"low": 0, "medium": 1, "high": 2}

async def execute_strategically(
    request: ScrapeRequest,
    execution_order: List[str],
    run_source_func: Callable[[str, ScrapeRequest, str], Awaitable[Dict[str, Any]]],
    merge_records_func: Callable[[List[Dict[str, Any]], Dict[str, Any]], tuple[List[Dict[str, Any]], int, List[str]]],
    calculate_coverage_func: Callable[[List[Dict[str, Any]], List[str]], float],
    trace_id: str,
    controls: Dict[str, bool] | None = None,
) -> Dict[str, Any]:
    from app.observability.event_emitter import emit
    from app.control.control_service import get_control, wait_until_resumed
    from app.policy.policy_service import get_policy
    import time
    
    tiers = {"high": [], "medium": [], "low": []}
    for source in execution_order:
        source_key = str(source).strip().lower()
        score = get_reliability_score(source)
        if score >= 0.75:
            reliability_tier = "high"
        elif score >= 0.4:
            reliability_tier = "medium"
        else:
            reliability_tier = "low"

        default_tier = DEFAULT_SOURCE_TIERS.get(source_key)
        if default_tier and TIER_RANK[default_tier] > TIER_RANK[reliability_tier]:
            resolved_tier = default_tier
        else:
            resolved_tier = reliability_tier
        tiers[resolved_tier].append(source)
            
    tiers_executed = []
    retries_triggered = []
    early_stopped = False
    fallback_used = False
    
    all_results = []
    accumulated_records = []
    cross_source_duplicates = 0
    all_errors = []
    sources_used = []
    
    current_limit = request.limit
    
    policy = get_policy("default")
    controls = dict(controls or {})
    contract_allows_fallback = bool(controls.get("fallback", True))
    contract_allows_early_stop = bool(controls.get("early_stop", True))
    contract_allows_retry = bool(controls.get("retry", True))
    max_execution_ms = policy["max_execution_ms"]
    allow_fallback = policy["allow_fallback"]
    start_time = time.perf_counter()
    
    for tier_name in ["high", "medium", "low"]:
        if (time.perf_counter() - start_time) * 1000 > max_execution_ms:
            emit("POLICY_TIME_LIMIT_REACHED", {"max_ms": max_execution_ms}, trace_id)
            all_errors.append(f"Execution stopped: exceeded {max_execution_ms}ms limit")
            break
            
        control = get_control(trace_id)
        if control["cancel"]:
            emit("CONTROL_CANCELLED", {}, trace_id)
            break
            
        if control["pause"]:
            await wait_until_resumed(trace_id)
            if get_control(trace_id)["cancel"]:
                emit("CONTROL_CANCELLED", {}, trace_id)
                break
                
        if control["override_tier"] and control["override_tier"] != tier_name:
            continue
            
        if control["force_fallback"] and tier_name != "low":
            continue
            
        if tier_name == "low" and (
            not allow_fallback or not contract_allows_fallback
        ) and not control["force_fallback"]:
            continue

        sources_in_tier = [s for s in tiers[tier_name] if s not in get_control(trace_id)["disabled_sources"]]
        if not sources_in_tier:
            continue
            
        tiers_executed.append(tier_name)
        if tier_name == "low":
            fallback_used = True
            emit("FALLBACK_TRIGGERED", {"tier": "low"}, trace_id)
            
        emit("TIER_STARTED", {"tier": tier_name}, trace_id)
            
        # Run tier
        tier_req = request.model_copy()
        tier_req.limit = current_limit
        
        tasks = [run_source_func(src, tier_req, trace_id) for src in sources_in_tier]
        tier_results = await asyncio.gather(*tasks)
        
        # Check for retries
        retry_tasks = []
        for i, res in enumerate(tier_results):
            src = res["source_name"]
            data = res["result"].get("final_data", [])
            status = res["result"].get("status", "failed")
            
            if status == "failed" or len(data) == 0:
                retries_triggered.append(src)
                emit("RETRY_TRIGGERED", {"source": src}, trace_id)
                retry_tasks.append((i, run_source_func(src, tier_req, trace_id)))
                
        if retry_tasks and contract_allows_retry:
            retry_indices = [idx for idx, _ in retry_tasks]
            retry_awaits = [task for _, task in retry_tasks]
            retry_results = await asyncio.gather(*retry_awaits)
            
            for idx, retry_res in zip(retry_indices, retry_results):
                tier_results[idx] = retry_res
                
        all_results.extend(tier_results)
        
        # Merge and evaluate sufficiency
        tier_records = []
        for res in tier_results:
            src = res["source_name"]
            data = res["result"].get("final_data", [])
            if data:
                sources_used.append(src)
            all_errors.extend(res["result"].get("errors", []))
            for r in data:
                r["_source"] = src
            tier_records.extend(data)
            
        accumulated_records, new_dups, _ = merge_records_func(accumulated_records, tier_records)
        cross_source_duplicates += new_dups
        
        coverage = calculate_coverage_func(accumulated_records, request.fields)
        total_records = len(accumulated_records)
        
        is_sufficient = (total_records >= request.limit * 0.8) and (coverage >= 0.7)
        if is_sufficient and contract_allows_early_stop:
            early_stopped = True
            emit("EARLY_STOP", {"reason": "sufficient_data"}, trace_id)
            break
            
        current_limit = max(1, request.limit - total_records)
        
        # Fallback condition explicitly
        if tier_name == "medium" and total_records < request.limit * 0.5:
            pass # proceed to low, fallback_used will be true next iteration
            
    return {
        "final_data": accumulated_records,
        "errors": all_errors,
        "sources_used": sources_used,
        "cross_source_duplicates_removed": cross_source_duplicates,
        "execution_tiers": tiers,
        "tiers_executed": tiers_executed,
        "early_stopped": early_stopped,
        "fallback_used": fallback_used,
        "retries_triggered": retries_triggered
    }
