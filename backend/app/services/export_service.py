"""Compatibility helpers for export persistence."""
from __future__ import annotations

import asyncio
from uuid import UUID
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.execution.export_execution_service import execute_export
from app.execution.export_task_registry import register_export_task, set_export_task_handle
from app.models.export import Export
from app.models.job import Job
from app.models.run import Run
from app.schemas.export import ExportCreate


async def create_export(
    db: AsyncSession,
    export_data: ExportCreate,
    user_id: UUID,
) -> Export:
    run = await db.scalar(
        select(Run)
        .join(Job, Run.job_id == Job.id)
        .where(Run.id == export_data.run_id, Job.user_id == user_id)
    )
    if run is None:
        raise ValueError("Run not found or not accessible")

    export = Export(
        run_id=export_data.run_id,
        format=export_data.format,
        file_path="",
    )
    db.add(export)
    await db.commit()
    await db.refresh(export)

    export_id = str(export.id)
    trace_id = str(uuid4())
    register_export_task(export_id=export_id, run_id=str(run.id), trace_id=trace_id)
    task = asyncio.create_task(
        execute_export(export_id=export_id, run_id=str(run.id), trace_id=trace_id),
        name=f"brainit-export-{export_id}",
    )
    set_export_task_handle(export_id, task)
    return export


async def get_export_by_id(
    db: AsyncSession,
    export_id: UUID,
    user_id: UUID,
) -> Export | None:
    result = await db.execute(
        select(Export)
        .join(Run, Export.run_id == Run.id, isouter=True)
        .join(Job, Run.job_id == Job.id, isouter=True)
        .where(Export.id == export_id, Job.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_exports_by_user(
    db: AsyncSession,
    user_id: UUID,
    skip: int = 0,
    limit: int = 100,
) -> list[Export]:
    result = await db.execute(
        select(Export)
        .join(Run, Export.run_id == Run.id, isouter=True)
        .join(Job, Run.job_id == Job.id, isouter=True)
        .where(Job.user_id == user_id)
        .order_by(Export.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_export_file_path(
    db: AsyncSession,
    export_id: UUID,
    user_id: UUID,
) -> str | None:
    export = await get_export_by_id(db, export_id, user_id)
    if not export or not export.file_path:
        return None
    return export.file_path
