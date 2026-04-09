from __future__ import annotations

import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.config import settings


class BaseExporter(ABC):
    def __init__(self) -> None:
        self.ensure_export_dir()
        self.cleanup_expired_exports()

    @abstractmethod
    async def export(
        self,
        processed_data: dict[str, Any],
        *,
        analysis_data: dict[str, Any] | None = None,
        export_id: str | None = None,
        source_url: str = "",
        generated_at: str | None = None,
        title: str = "",
    ) -> str:
        pass

    def resolve_export_id(self, export_id: str | None) -> str:
        return export_id or f"export_{uuid4()}"

    def resolve_generated_at(self, generated_at: str | None) -> str:
        return generated_at or datetime.now(timezone.utc).isoformat()

    def ensure_export_dir(self) -> Path:
        export_storage_path = os.getenv("EXPORT_STORAGE_PATH", "").strip()
        export_dir = Path(export_storage_path) if export_storage_path else Path(settings.STORAGE_ROOT) / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        return export_dir.resolve()

    def build_export_path(self, extension: str, export_id: str | None = None) -> Path:
        export_dir = self.ensure_export_dir()
        filename = f"{self.resolve_export_id(export_id)}.{extension.lstrip('.')}"
        file_path = (export_dir / filename).resolve()
        if export_dir not in file_path.parents:
            raise ValueError("Resolved export path escaped export directory.")
        return file_path

    def atomic_write(self, file_path: Path, file_bytes: bytes) -> str:
        temp_path = file_path.with_suffix(f"{file_path.suffix}.tmp")
        temp_path.write_bytes(file_bytes)
        temp_path.replace(file_path)
        try:
            return str(file_path.relative_to(file_path.parent.parent))
        except Exception:
            return str(file_path)

    def write_export_file(self, extension: str, file_bytes: bytes, export_id: str | None = None) -> str:
        file_path = self.build_export_path(extension, export_id=export_id)
        return self.atomic_write(file_path, file_bytes)

    def cleanup_expired_exports(self) -> None:
        ttl_value = os.getenv("EXPORT_TTL_SECONDS", "").strip()
        if not ttl_value:
            return
        try:
            ttl_seconds = max(1, int(ttl_value))
            export_dir = self.ensure_export_dir()
            cutoff = datetime.now(timezone.utc).timestamp() - ttl_seconds
            for file_path in export_dir.glob("*"):
                if file_path.is_file() and file_path.stat().st_mtime < cutoff:
                    file_path.unlink(missing_ok=True)
        except Exception:
            return
