"""Compatibility helpers for job persistence.

These service functions mirror the current API contract so older imports do
not silently drift away from the live route behavior.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.schemas.job import JobCreate, JobUpdate


def _build_job_config(
    *,
    incoming: dict[str, Any] | Any | None,
    prompt: str | None,
    max_pages: int | None,
    follow_pagination: bool | None,
    existing: dict | None = None,
) -> dict:
    config = dict(existing or {})
    if incoming:
        if hasattr(incoming, "model_dump"):
            config.update(incoming.model_dump(exclude_none=True))
        elif isinstance(incoming, dict):
            config.update(incoming)
    if prompt is not None:
        config["prompt"] = prompt
    if max_pages is not None:
        config["max_pages"] = max_pages
    if follow_pagination is not None:
        config["follow_pagination"] = follow_pagination
    return config


async def create_job(db: AsyncSession, job_data: JobCreate, user_id: UUID) -> Job:
    job = Job(
        user_id=user_id,
        url=job_data.url,
        login_url=job_data.login_url,
        login_username=job_data.login_username,
        login_password=job_data.login_password,
        scrape_type=job_data.scrape_type.value,
        config=_build_job_config(
            incoming=job_data.config,
            prompt=job_data.prompt,
            max_pages=job_data.max_pages,
            follow_pagination=job_data.follow_pagination,
        ),
        status="pending",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def get_job_by_id(db: AsyncSession, job_id: UUID, user_id: UUID) -> Job | None:
    result = await db.execute(select(Job).where(Job.id == job_id, Job.user_id == user_id))
    return result.scalar_one_or_none()


async def get_jobs_by_user(
    db: AsyncSession,
    user_id: UUID,
    skip: int = 0,
    limit: int = 100,
) -> list[Job]:
    result = await db.execute(
        select(Job)
        .where(Job.user_id == user_id)
        .order_by(Job.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def update_job(
    db: AsyncSession,
    job_id: UUID,
    job_data: JobUpdate,
    user_id: UUID,
) -> Job | None:
    job = await get_job_by_id(db, job_id, user_id)
    if job is None:
        return None

    update_data = job_data.model_dump(exclude_unset=True)
    config_update = update_data.pop("config", None)
    prompt = update_data.pop("prompt", None)
    max_pages = update_data.pop("max_pages", None)
    follow_pagination = update_data.pop("follow_pagination", None)

    for field, value in update_data.items():
        if field == "scrape_type" and value is not None:
            value = value.value
        setattr(job, field, value)

    if config_update is not None or prompt is not None or max_pages is not None or follow_pagination is not None:
        job.config = _build_job_config(
            incoming=config_update,
            prompt=prompt,
            max_pages=max_pages,
            follow_pagination=follow_pagination,
            existing=job.config,
        )

    await db.commit()
    await db.refresh(job)
    return job


async def cancel_job(db: AsyncSession, job_id: UUID, user_id: UUID) -> Job | None:
    job = await get_job_by_id(db, job_id, user_id)
    if job is None:
        return None

    job.status = "cancelled"
    await db.commit()
    await db.refresh(job)
    return job
