from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.api.deps import verify_api_key
from app.control.control_service import set_control
from app.observability.event_emitter import emit
from app.policy.policy_service import get_policy

router = APIRouter()

def _check_control_permission(tenant_id: str = "default"):
    policy = get_policy(tenant_id)
    if not policy["allow_control_actions"]:
        raise HTTPException(status_code=403, detail="Control actions are disabled by policy")

class SourcePayload(BaseModel):
    source: str

class TierPayload(BaseModel):
    tier: str

@router.post("/{trace_id}/cancel", summary="Cancel scrape")
async def cancel_execution(trace_id: str, api_key: str = Depends(verify_api_key)):
    _check_control_permission()
    set_control(trace_id, "cancel", True)
    emit("CONTROL_CANCELLED", {}, trace_id)
    return {"status": "cancelled", "trace_id": trace_id}

@router.post("/{trace_id}/pause", summary="Pause scrape")
async def pause_execution(trace_id: str, api_key: str = Depends(verify_api_key)):
    _check_control_permission()
    set_control(trace_id, "pause", True)
    emit("CONTROL_PAUSED", {}, trace_id)
    return {"status": "paused", "trace_id": trace_id}

@router.post("/{trace_id}/resume", summary="Resume scrape")
async def resume_execution(trace_id: str, api_key: str = Depends(verify_api_key)):
    _check_control_permission()
    set_control(trace_id, "pause", False)
    emit("CONTROL_RESUMED", {}, trace_id)
    return {"status": "resumed", "trace_id": trace_id}

@router.post("/{trace_id}/fallback", summary="Force fallback")
async def force_fallback(trace_id: str, api_key: str = Depends(verify_api_key)):
    _check_control_permission()
    set_control(trace_id, "force_fallback", True)
    emit("CONTROL_FALLBACK", {}, trace_id)
    return {"status": "fallback_forced", "trace_id": trace_id}

@router.post("/{trace_id}/disable_source", summary="Disable source")
async def disable_source(trace_id: str, payload: SourcePayload, api_key: str = Depends(verify_api_key)):
    _check_control_permission()
    set_control(trace_id, "disabled_sources", payload.source)
    emit("CONTROL_SOURCE_DISABLED", {"source": payload.source}, trace_id)
    return {"status": "source_disabled", "source": payload.source, "trace_id": trace_id}

@router.post("/{trace_id}/override_tier", summary="Override tier")
async def override_tier(trace_id: str, payload: TierPayload, api_key: str = Depends(verify_api_key)):
    _check_control_permission()
    set_control(trace_id, "override_tier", payload.tier)
    emit("CONTROL_TIER_OVERRIDE", {"tier": payload.tier}, trace_id)
    return {"status": "tier_overridden", "tier": payload.tier, "trace_id": trace_id}
