from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from threading import Lock
from typing import Any


EXPORT_TASKS: dict[str, dict[str, Any]] = {}
_LOCK = Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def register_export_task(*, export_id: str, run_id: str, trace_id: str) -> None:
    with _LOCK:
        EXPORT_TASKS[export_id] = {
            "export_id": export_id,
            "run_id": run_id,
            "trace_id": trace_id,
            "status": "queued",
            "file_path": "",
            "error": None,
            "created_at": _now_iso(),
            "finished_at": None,
            "_task": None,
        }


def set_export_task_handle(export_id: str, task: asyncio.Task[Any]) -> None:
    with _LOCK:
        if export_id in EXPORT_TASKS:
            EXPORT_TASKS[export_id]["_task"] = task


def mark_export_running(export_id: str) -> None:
    with _LOCK:
        if export_id in EXPORT_TASKS:
            EXPORT_TASKS[export_id]["status"] = "running"


def mark_export_completed(export_id: str, *, file_path: str) -> None:
    with _LOCK:
        if export_id in EXPORT_TASKS:
            EXPORT_TASKS[export_id]["status"] = "completed"
            EXPORT_TASKS[export_id]["file_path"] = file_path
            EXPORT_TASKS[export_id]["error"] = None
            EXPORT_TASKS[export_id]["finished_at"] = _now_iso()
            EXPORT_TASKS[export_id]["_task"] = None


def mark_export_failed(export_id: str, *, error: str) -> None:
    with _LOCK:
        if export_id in EXPORT_TASKS:
            EXPORT_TASKS[export_id]["status"] = "failed"
            EXPORT_TASKS[export_id]["error"] = error
            EXPORT_TASKS[export_id]["finished_at"] = _now_iso()
            EXPORT_TASKS[export_id]["_task"] = None


def get_export_task(export_id: str) -> dict[str, Any] | None:
    with _LOCK:
        task = EXPORT_TASKS.get(export_id)
        if task is None:
            return None
        copied = dict(task)
        copied.pop("_task", None)
        return copied


def get_export_trace_id(export_id: str) -> str | None:
    with _LOCK:
        task = EXPORT_TASKS.get(export_id)
        if task is None:
            return None
        return str(task.get("trace_id") or "") or None


def cancel_export_task(export_id: str) -> bool:
    with _LOCK:
        task = EXPORT_TASKS.get(export_id)
        if task is None:
            return False
        handle = task.get("_task")
        if isinstance(handle, asyncio.Task):
            handle.cancel()
            return True
        return False


def cancel_all_export_tasks(message: str = "Cancelled due to service shutdown") -> list[asyncio.Task[Any]]:
    cancelled_handles: list[asyncio.Task[Any]] = []
    with _LOCK:
        for export_id, task in EXPORT_TASKS.items():
            handle = task.get("_task")
            if isinstance(handle, asyncio.Task) and not handle.done():
                handle.cancel()
                cancelled_handles.append(handle)
            if task.get("status") in {"queued", "running"}:
                task["status"] = "failed"
                task["error"] = message
                task["finished_at"] = _now_iso()
                task["_task"] = None
    return cancelled_handles
