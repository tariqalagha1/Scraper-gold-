from typing import Dict, Any, List
import asyncio
from threading import Lock

_LOCK = Lock()

CONTROL_STATE: Dict[str, Dict[str, Any]] = {}

def _init_state(trace_id: str) -> None:
    if trace_id not in CONTROL_STATE:
        with _LOCK:
            if trace_id not in CONTROL_STATE:
                CONTROL_STATE[trace_id] = {
                    "cancel": False,
                    "pause": False,
                    "force_fallback": False,
                    "disabled_sources": [],
                    "override_tier": None
                }

def set_control(trace_id: str, key: str, value: Any) -> None:
    _init_state(trace_id)
    with _LOCK:
        if key == "disabled_sources":
            if value not in CONTROL_STATE[trace_id]["disabled_sources"]:
                CONTROL_STATE[trace_id]["disabled_sources"].append(value)
        else:
            CONTROL_STATE[trace_id][key] = value

def get_control(trace_id: str) -> Dict[str, Any]:
    _init_state(trace_id)
    return CONTROL_STATE[trace_id]

def clear_control(trace_id: str) -> None:
    with _LOCK:
        CONTROL_STATE.pop(trace_id, None)

async def wait_until_resumed(trace_id: str) -> None:
    while get_control(trace_id)["pause"] and not get_control(trace_id)["cancel"]:
        await asyncio.sleep(0.2)
