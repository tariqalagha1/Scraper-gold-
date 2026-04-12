from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.logging import get_logger
from app.models.export import Export
from app.models.job import Job
from app.models.result import Result
from app.models.run import Run
from app.schemas.storage_cleanup import (
    CleanupResultResponse,
    HistoryCleanupEstimate,
    StorageCleanupEstimateResponse,
    TempFilesCleanupEstimate,
)
from app.storage.manager import StorageManager


logger = get_logger(__name__)


@dataclass
class _TempArtifacts:
    files: set[Path] = field(default_factory=set)
    directories: set[Path] = field(default_factory=set)
    cached_exports: int = 0
    temp_markdown: int = 0
    temp_pdfs: int = 0
    image_cache: int = 0
    processing_temp_files: int = 0
    orphaned_uploads: int = 0
    stale_session_artifacts: int = 0


def _storage_root() -> Path:
    return Path(settings.STORAGE_ROOT).resolve()


def _run_logs_dir() -> Path:
    return _storage_root() / "run_logs"


def _run_log_path(run_id: str) -> Path:
    return _run_logs_dir() / f"{run_id}.jsonl"


def _is_within_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root)
        return True
    except ValueError:
        return False


def _round_mb(value: int | float) -> float:
    return round(float(value) / (1024 * 1024), 2)


async def _load_user_jobs(db: AsyncSession, user_id: UUID) -> list[Job]:
    result = await db.execute(
        select(Job)
        .where(Job.user_id == user_id)
        .options(
            selectinload(Job.runs).selectinload(Run.results).selectinload(Result.exports),
            selectinload(Job.runs).selectinload(Run.exports),
        )
    )
    return list(result.scalars().unique().all())


def _iter_unique_exports(runs: Iterable[Run]) -> list[Export]:
    unique: dict[str, Export] = {}
    for run in runs:
        for export in run.exports:
            unique[str(export.id)] = export
        for result in run.results:
            for export in result.exports:
                unique[str(export.id)] = export
    return list(unique.values())


def _build_history_estimate(jobs: list[Job]) -> HistoryCleanupEstimate:
    runs = [run for job in jobs for run in job.runs]
    exports = _iter_unique_exports(runs)
    search_history = len(jobs)
    prompt_history = sum(1 for job in jobs if (job.config or {}).get("prompt"))
    previous_runs = len(runs)
    generated_reports_metadata = len(exports)
    recent_activity_log = len(jobs) + len(runs) + len(exports)
    total_records = len(jobs) + len(runs) + sum(len(run.results) for run in runs) + len(exports)
    return HistoryCleanupEstimate(
        search_history=search_history,
        prompt_history=prompt_history,
        previous_runs=previous_runs,
        generated_reports_metadata=generated_reports_metadata,
        recent_activity_log=recent_activity_log,
        total_records=total_records,
    )


def _register_file(artifacts: _TempArtifacts, file_path: Path, *, category: str) -> None:
    root = _storage_root()
    resolved = file_path.resolve()
    if not resolved.exists() or not resolved.is_file() or not _is_within_root(resolved, root):
        return

    if resolved in artifacts.files:
        return

    artifacts.files.add(resolved)

    if category == "cached_exports":
        artifacts.cached_exports += 1
        if resolved.suffix.lower() == ".pdf":
            artifacts.temp_pdfs += 1
    elif category == "temp_markdown":
        artifacts.temp_markdown += 1
    elif category == "image_cache":
        artifacts.image_cache += 1
    elif category == "processing_temp_files":
        artifacts.processing_temp_files += 1


def _register_directory_files(artifacts: _TempArtifacts, directory: Path, *, category: str) -> None:
    root = _storage_root()
    resolved_dir = directory.resolve()
    if not resolved_dir.exists() or not resolved_dir.is_dir() or not _is_within_root(resolved_dir, root):
        return

    artifacts.directories.add(resolved_dir)
    for child in resolved_dir.rglob("*"):
        if child.is_file():
            _register_file(artifacts, child, category=category)


def _collect_temp_artifacts(jobs: list[Job], storage: StorageManager) -> _TempArtifacts:
    artifacts = _TempArtifacts()

    for job in jobs:
        for run in job.runs:
            if run.markdown_snapshot_path:
                _register_file(
                    artifacts,
                    storage.resolve_path(run.markdown_snapshot_path),
                    category="temp_markdown",
                )

            _register_directory_files(
                artifacts,
                _storage_root() / "raw_html" / str(run.id),
                category="processing_temp_files",
            )
            _register_directory_files(
                artifacts,
                _storage_root() / "processed" / str(run.id),
                category="processing_temp_files",
            )
            _register_directory_files(
                artifacts,
                _storage_root() / "screenshots" / str(run.id),
                category="image_cache",
            )
            _register_file(artifacts, _run_log_path(str(run.id)), category="processing_temp_files")

            for result in run.results:
                if result.raw_html_path:
                    _register_file(
                        artifacts,
                        storage.resolve_path(result.raw_html_path),
                        category="processing_temp_files",
                    )
                if result.screenshot_path:
                    _register_file(
                        artifacts,
                        storage.resolve_path(result.screenshot_path),
                        category="image_cache",
                    )

            for export in _iter_unique_exports([run]):
                if export.file_path:
                    _register_file(
                        artifacts,
                        storage.resolve_path(export.file_path),
                        category="cached_exports",
                    )

    return artifacts


def _build_temp_estimate(artifacts: _TempArtifacts) -> TempFilesCleanupEstimate:
    freed_space_bytes = sum(path.stat().st_size for path in artifacts.files if path.exists())
    return TempFilesCleanupEstimate(
        cached_exports=artifacts.cached_exports,
        temp_markdown=artifacts.temp_markdown,
        temp_pdfs=artifacts.temp_pdfs,
        image_cache=artifacts.image_cache,
        processing_temp_files=artifacts.processing_temp_files,
        orphaned_uploads=artifacts.orphaned_uploads,
        stale_session_artifacts=artifacts.stale_session_artifacts,
        total_files=len(artifacts.files),
        estimated_freed_space_mb=_round_mb(freed_space_bytes),
    )


async def get_storage_cleanup_estimate(
    db: AsyncSession,
    user_id: UUID,
    storage: StorageManager,
) -> StorageCleanupEstimateResponse:
    jobs = await _load_user_jobs(db, user_id)
    history = _build_history_estimate(jobs)
    temp = _build_temp_estimate(_collect_temp_artifacts(jobs, storage))
    return StorageCleanupEstimateResponse(history=history, temp_files=temp)


def _cleanup_files(artifacts: _TempArtifacts) -> tuple[int, int, list[str]]:
    deleted_count = 0
    freed_bytes = 0
    warnings: list[str] = []

    for path in sorted(artifacts.files):
        try:
            if path.exists() and path.is_file():
                freed_bytes += path.stat().st_size
                path.unlink()
                deleted_count += 1
        except OSError as exc:
            warnings.append(f"Could not delete {path.name}: {exc}")

    for directory in sorted(artifacts.directories, key=lambda item: len(item.parts), reverse=True):
        try:
            if directory.exists() and directory.is_dir() and _is_within_root(directory, _storage_root()):
                shutil.rmtree(directory, ignore_errors=True)
        except OSError as exc:
            warnings.append(f"Could not remove {directory.name}: {exc}")

    return deleted_count, freed_bytes, warnings


def _build_cleanup_result(
    *,
    status: str,
    deleted_history_records: int,
    deleted_temp_files: int,
    freed_bytes: int,
    cleared_scopes: list[str],
    warnings: list[str],
) -> CleanupResultResponse:
    return CleanupResultResponse(
        status=status,
        deleted_history_records=deleted_history_records,
        deleted_temp_files=deleted_temp_files,
        freed_space_mb=_round_mb(freed_bytes),
        deleted_items_count=deleted_history_records + deleted_temp_files,
        cleared_scopes=cleared_scopes,
        warnings=warnings,
    )


async def clear_user_temp_files(
    db: AsyncSession,
    user_id: UUID,
    storage: StorageManager,
) -> CleanupResultResponse:
    jobs = await _load_user_jobs(db, user_id)
    artifacts = _collect_temp_artifacts(jobs, storage)
    deleted_temp_files, freed_bytes, warnings = _cleanup_files(artifacts)

    if warnings:
        await db.rollback()
        logger.warning(
            "User temp file cleanup completed with warnings; DB metadata changes were rolled back.",
            action="user_cleanup_temp_files_partial",
            extra={
                "user_id": str(user_id),
                "deleted_temp_files": deleted_temp_files,
                "freed_space_mb": _round_mb(freed_bytes),
                "warnings": warnings,
            },
        )
        return _build_cleanup_result(
            status="partial_success",
            deleted_history_records=0,
            deleted_temp_files=deleted_temp_files,
            freed_bytes=freed_bytes,
            cleared_scopes=["temp_files"],
            warnings=warnings,
        )

    for job in jobs:
        for run in job.runs:
            run.markdown_snapshot_path = None
            for result in run.results:
                result.raw_html_path = None
                result.screenshot_path = None
            for export in _iter_unique_exports([run]):
                export.file_path = ""
                export.file_size = 0

    await db.commit()

    logger.info(
        "User temp files cleared.",
        action="user_cleanup_temp_files",
        extra={
            "user_id": str(user_id),
            "deleted_temp_files": deleted_temp_files,
            "freed_space_mb": _round_mb(freed_bytes),
        },
    )

    return _build_cleanup_result(
        status="success",
        deleted_history_records=0,
        deleted_temp_files=deleted_temp_files,
        freed_bytes=freed_bytes,
        cleared_scopes=["temp_files"],
        warnings=warnings,
    )


async def clear_user_history(
    db: AsyncSession,
    user_id: UUID,
    storage: StorageManager,
) -> CleanupResultResponse:
    jobs = await _load_user_jobs(db, user_id)
    history = _build_history_estimate(jobs)
    artifacts = _collect_temp_artifacts(jobs, storage)

    for job in jobs:
        await db.delete(job)

    await db.flush()
    deleted_temp_files, freed_bytes, warnings = _cleanup_files(artifacts)

    if warnings:
        await db.rollback()
        logger.warning(
            "User history cleanup completed with warnings; DB deletions were rolled back.",
            action="user_cleanup_history_partial",
            extra={
                "user_id": str(user_id),
                "attempted_deleted_history_records": history.total_records,
                "deleted_temp_files": deleted_temp_files,
                "freed_space_mb": _round_mb(freed_bytes),
                "warnings": warnings,
            },
        )
        return _build_cleanup_result(
            status="partial_success",
            deleted_history_records=0,
            deleted_temp_files=deleted_temp_files,
            freed_bytes=freed_bytes,
            cleared_scopes=["history"],
            warnings=warnings,
        )

    await db.commit()

    logger.info(
        "User history cleared.",
        action="user_cleanup_history",
        extra={
            "user_id": str(user_id),
            "deleted_history_records": history.total_records,
            "deleted_temp_files": deleted_temp_files,
            "freed_space_mb": _round_mb(freed_bytes),
        },
    )

    return _build_cleanup_result(
        status="success",
        deleted_history_records=history.total_records,
        deleted_temp_files=deleted_temp_files,
        freed_bytes=freed_bytes,
        cleared_scopes=["history"],
        warnings=warnings,
    )


async def clear_user_all(
    db: AsyncSession,
    user_id: UUID,
    storage: StorageManager,
) -> CleanupResultResponse:
    result = await clear_user_history(db, user_id, storage)

    logger.info(
        "User full cleanup executed.",
        action="user_cleanup_all",
        extra={
            "user_id": str(user_id),
            "deleted_history_records": result.deleted_history_records,
            "deleted_temp_files": result.deleted_temp_files,
            "freed_space_mb": result.freed_space_mb,
        },
    )

    return CleanupResultResponse(
        status=result.status,
        deleted_history_records=result.deleted_history_records,
        deleted_temp_files=result.deleted_temp_files,
        freed_space_mb=result.freed_space_mb,
        deleted_items_count=result.deleted_items_count,
        cleared_scopes=["history", "temp_files", "local_cache_keys", "stale_session_artifacts"],
        warnings=result.warnings,
    )
