from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select

from app.db.session import async_session_factory
from app.export.excel import ExcelExporter
from app.export.json import JSONExporter
from app.export.pdf import PDFExporter
from app.export.word import WordExporter
from app.models.export import Export
from app.models.result import Result
from app.observability.event_emitter import emit
from app.storage.manager import StorageManager

from app.execution.export_task_registry import (
    mark_export_completed,
    mark_export_failed,
    mark_export_running,
)

_STORAGE = StorageManager()


def _exporter_for_format(export_format: str) -> Any:
    exporter_cls = {
        "excel": ExcelExporter,
        "pdf": PDFExporter,
        "word": WordExporter,
        "json": JSONExporter,
    }.get(str(export_format).strip().lower())
    if exporter_cls is None:
        raise ValueError(f"Unsupported export format: {export_format}")
    return exporter_cls()


async def _load_export_and_result(export_id: str, run_id: str) -> tuple[Export | None, Result | None]:
    async with async_session_factory() as session:
        export = (
            await session.execute(
                select(Export).where(
                    Export.id == UUID(export_id),
                    Export.run_id == UUID(run_id),
                )
            )
        ).scalar_one_or_none()
        if export is None:
            return None, None
        result = (
            await session.execute(
                select(Result).where(Result.run_id == UUID(run_id)).order_by(Result.created_at.desc())
            )
        ).scalars().first()
        return export, result


async def execute_export(
    export_id: str,
    run_id: str,
    trace_id: str | None = None,
) -> dict[str, Any]:
    execution_trace_id = str(trace_id or uuid4())
    mark_export_running(export_id)
    emit("EXPORT_STARTED", {"export_id": export_id, "run_id": run_id}, execution_trace_id)

    export, result = await _load_export_and_result(export_id, run_id)
    if export is None:
        error = f"Export {export_id} was not found for run {run_id}."
        mark_export_failed(export_id, error=error)
        emit("EXPORT_FAILED", {"export_id": export_id, "run_id": run_id, "error": error}, execution_trace_id)
        return {"status": "failed", "export_id": export_id, "run_id": run_id, "trace_id": execution_trace_id, "error": error}
    if result is None:
        error = f"Run {run_id} has no persisted results to export."
        mark_export_failed(export_id, error=error)
        emit("EXPORT_FAILED", {"export_id": export_id, "run_id": run_id, "error": error}, execution_trace_id)
        return {"status": "failed", "export_id": export_id, "run_id": run_id, "trace_id": execution_trace_id, "error": error}

    try:
        exporter = _exporter_for_format(export.format)
        file_path = await exporter.export(
            result.data_json,
            export_id=export_id,
            source_url=result.url,
            title="Processed Web Data Export",
        )
    except Exception as exc:
        error = str(exc).strip() or "Export generation failed."
        mark_export_failed(export_id, error=error)
        emit("EXPORT_FAILED", {"export_id": export_id, "run_id": run_id, "error": error}, execution_trace_id)
        return {"status": "failed", "export_id": export_id, "run_id": run_id, "trace_id": execution_trace_id, "error": error}

    try:
        async with async_session_factory() as session:
            db_export = (await session.execute(select(Export).where(Export.id == UUID(export_id)))).scalar_one()
            db_export.file_path = file_path
            db_export.file_size = _STORAGE.get_file_size(file_path)
            await session.commit()
            await session.refresh(db_export)
    except Exception as exc:
        error = f"Failed to persist export metadata: {exc}"
        mark_export_failed(export_id, error=error)
        emit("EXPORT_FAILED", {"export_id": export_id, "run_id": run_id, "error": error}, execution_trace_id)
        return {"status": "failed", "export_id": export_id, "run_id": run_id, "trace_id": execution_trace_id, "error": error}

    mark_export_completed(export_id, file_path=file_path)
    emit(
        "EXPORT_COMPLETED",
        {"export_id": export_id, "run_id": run_id, "file_path": file_path},
        execution_trace_id,
    )
    return {
        "status": "completed",
        "export_id": export_id,
        "run_id": run_id,
        "trace_id": execution_trace_id,
        "file_path": file_path,
    }
