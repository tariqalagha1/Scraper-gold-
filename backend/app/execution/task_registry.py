from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from threading import Lock
from typing import Any


RUNNING_TASKS: dict[str, dict[str, Any]] = {}
_LOCK = Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def register_task(
    *,
    run_id: str,
    job_id: str,
    trace_id: str,
) -> None:
    with _LOCK:
        RUNNING_TASKS[run_id] = {
            "run_id": run_id,
            "job_id": job_id,
            "trace_id": trace_id,
            "status": "queued",
            "started_at": None,
            "finished_at": None,
            "result": {},
            "error": None,
            "_task": None,
        }


def set_task_handle(run_id: str, task: asyncio.Task[Any]) -> None:
    with _LOCK:
        if run_id in RUNNING_TASKS:
            RUNNING_TASKS[run_id]["_task"] = task


def mark_running(run_id: str) -> None:
    with _LOCK:
        if run_id in RUNNING_TASKS:
            RUNNING_TASKS[run_id]["status"] = "running"
            RUNNING_TASKS[run_id]["started_at"] = _now_iso()


def mark_completed(run_id: str, result: dict[str, Any]) -> None:
    with _LOCK:
        if run_id in RUNNING_TASKS:
            RUNNING_TASKS[run_id]["status"] = "completed"
            RUNNING_TASKS[run_id]["finished_at"] = _now_iso()
            RUNNING_TASKS[run_id]["result"] = result
            RUNNING_TASKS[run_id]["error"] = None
            RUNNING_TASKS[run_id]["_task"] = None


def mark_failed(run_id: str, error: str, result: dict[str, Any] | None = None) -> None:
    with _LOCK:
        if run_id in RUNNING_TASKS:
            RUNNING_TASKS[run_id]["status"] = "failed"
            RUNNING_TASKS[run_id]["finished_at"] = _now_iso()
            RUNNING_TASKS[run_id]["result"] = result or {}
            RUNNING_TASKS[run_id]["error"] = error
            RUNNING_TASKS[run_id]["_task"] = None


def mark_cancelled(run_id: str, message: str = "Cancelled by user") -> None:
    with _LOCK:
        if run_id in RUNNING_TASKS:
            RUNNING_TASKS[run_id]["status"] = "cancelled"
            RUNNING_TASKS[run_id]["finished_at"] = _now_iso()
            RUNNING_TASKS[run_id]["error"] = message
            RUNNING_TASKS[run_id]["_task"] = None


def get_task(run_id: str) -> dict[str, Any] | None:
    with _LOCK:
        task = RUNNING_TASKS.get(run_id)
        if task is None:
            return None
        copied = dict(task)
        copied.pop("_task", None)
        return copied


def get_trace_id(run_id: str) -> str | None:
    with _LOCK:
        task = RUNNING_TASKS.get(run_id)
        if task is None:
            return None
        return str(task.get("trace_id") or "") or None


def cancel_task(run_id: str) -> bool:
    with _LOCK:
        task = RUNNING_TASKS.get(run_id)
        if task is None:
            return False
        handle = task.get("_task")
        if isinstance(handle, asyncio.Task):
            handle.cancel()
            return True
        return False


def cancel_all_tasks(message: str = "Cancelled due to service shutdown") -> list[asyncio.Task[Any]]:
    cancelled_handles: list[asyncio.Task[Any]] = []
    with _LOCK:
        for run_id, task in RUNNING_TASKS.items():
            handle = task.get("_task")
            if isinstance(handle, asyncio.Task) and not handle.done():
                handle.cancel()
                cancelled_handles.append(handle)
            if task.get("status") in {"queued", "running"}:
                task["status"] = "cancelled"
                task["finished_at"] = _now_iso()
                task["error"] = message
                task["_task"] = None
    return cancelled_handles
