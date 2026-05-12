from typing import Any, Dict, List, Tuple
from fastapi import HTTPException
from app.observability.event_emitter import emit

TENANT_POLICIES = {
    "default": {
        "allowed_sources": ["internal", "google_maps", "web"],
        "blocked_sources": [],
        "max_limit": 100,
        "max_execution_ms": 60000,
        "min_confidence": 0.4,
        "min_coverage": 0.5,
        "allow_fallback": True,
        "allow_force_sources": False,
        "allow_control_actions": True,
    }
}

def get_policy(tenant_id: str) -> Dict[str, Any]:
    return TENANT_POLICIES.get(tenant_id, TENANT_POLICIES["default"])

def enforce_request_policy(tenant_id: str, requested_sources: List[str], requested_limit: int, force_sources: bool, trace_id: str) -> Tuple[Dict[str, Any], List[str], int, bool]:
    policy = get_policy(tenant_id)
    
    emit("POLICY_APPLIED", {"tenant_id": tenant_id, "policy": policy}, trace_id)
    
    # Check force mode
    if force_sources and not policy["allow_force_sources"]:
        emit("POLICY_FORCE_REJECTED", {}, trace_id)
        raise HTTPException(status_code=403, detail="force_sources is not allowed by tenant policy")
        
    # Check sources
    filtered_sources = []
    sources_filtered = []
    for s in requested_sources:
        if s not in policy["allowed_sources"] or s in policy["blocked_sources"]:
            sources_filtered.append(s)
        else:
            filtered_sources.append(s)
            
    if sources_filtered:
        emit("POLICY_SOURCE_FILTERED", {"sources": sources_filtered}, trace_id)
        
    if not filtered_sources:
        raise HTTPException(status_code=403, detail="No allowed sources available for this tenant policy")
        
    # Cap limit
    limit_capped = False
    final_limit = requested_limit
    if requested_limit > policy["max_limit"]:
        final_limit = policy["max_limit"]
        limit_capped = True
        emit("POLICY_LIMIT_CAPPED", {"requested": requested_limit, "capped": final_limit}, trace_id)
        
    decision = {
        "tenant_id": tenant_id,
        "limit_capped": limit_capped,
        "sources_filtered": sources_filtered,
        "force_sources_allowed": policy["allow_force_sources"]
    }
    
    return decision, filtered_sources, final_limit, force_sources if policy["allow_force_sources"] else False

def enforce_quality_policy(tenant_id: str, confidence: float, coverage: float, trace_id: str) -> bool:
    policy = get_policy(tenant_id)
    if confidence < policy["min_confidence"] or coverage < policy["min_coverage"]:
        emit("POLICY_QUALITY_FAILED", {"confidence": confidence, "coverage": coverage}, trace_id)
        return False
    return True
