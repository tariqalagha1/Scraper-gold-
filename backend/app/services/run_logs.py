from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import settings


def _logs_dir() -> Path:
    path = Path(settings.STORAGE_ROOT) / "run_logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _run_log_path(run_id: str) -> Path:
    return _logs_dir() / f"{run_id}.jsonl"


def append_run_log(
    run_id: str,
    *,
    event: str,
    message: str,
    level: str = "info",
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "event": event,
        "message": message,
        "details": details or {},
    }
    with _run_log_path(run_id).open("a", encoding="utf-8") as file_handle:
        file_handle.write(json.dumps(entry, ensure_ascii=True) + "\n")
    return entry


def read_run_logs(run_id: str) -> list[dict[str, Any]]:
    log_path = _run_log_path(run_id)
    if not log_path.exists():
        return []

    entries: list[dict[str, Any]] = []
    with log_path.open("r", encoding="utf-8") as file_handle:
        for line in file_handle:
            text = line.strip()
            if not text:
                continue
            try:
                entries.append(json.loads(text))
            except json.JSONDecodeError:
                continue
    return entries
