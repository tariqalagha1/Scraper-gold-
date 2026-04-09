from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class WorkflowState:
    job_id: str = ""
    url: str = ""
    scraping_type: str = "general"
    credentials: dict[str, Any] = field(default_factory=dict)
    raw_data: dict[str, Any] = field(default_factory=dict)
    processed_data: dict[str, Any] = field(default_factory=dict)
    vector_data: dict[str, Any] = field(default_factory=dict)
    analysis_data: dict[str, Any] = field(default_factory=dict)
    export_paths: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    errors: list[str] = field(default_factory=list)

    config: dict[str, Any] = field(default_factory=dict)
    strategy: dict[str, Any] = field(default_factory=dict)
    user_id: str = ""
    run_id: str = ""
    current_step: str = "pending"
    started_at: str = ""
    finished_at: str = ""
    node_timings: dict[str, float] = field(default_factory=dict)
    token_compression_ratio: float | None = None
    stealth_engaged: bool = False
    markdown_snapshot_path: str = ""

    def mark_started(self, step: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        if not self.started_at:
            self.started_at = now
        self.current_step = step
        if self.status == "pending":
            self.status = "running"

    def mark_finished(self) -> None:
        self.finished_at = datetime.now(timezone.utc).isoformat()

    def add_error(self, message: str) -> None:
        self.errors.append(message)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
