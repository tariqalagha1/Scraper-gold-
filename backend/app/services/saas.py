from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.export import Export
from app.models.job import Job
from app.models.run import Run
from app.models.user import User


PLAN_LIMITS: dict[str, dict[str, int]] = {
    "free": {"max_jobs": 5, "max_runs_per_day": 20},
    "pro": {"max_jobs": 100, "max_runs_per_day": 1000},
}


def normalize_plan(plan: str | None) -> str:
    normalized = (plan or "free").strip().lower()
    return normalized if normalized in PLAN_LIMITS else "free"


def get_plan_limits(plan: str | None) -> dict[str, int]:
    return PLAN_LIMITS[normalize_plan(plan)]


def generate_api_key_secret() -> str:
    return f"ss_{secrets.token_urlsafe(32)}"


def hash_api_key(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_key_preview(api_key: str) -> str:
    if len(api_key) <= 8:
        return "*" * len(api_key)
    return f"{api_key[:6]}...{api_key[-4:]}"


async def get_usage_summary(db: AsyncSession, user_id: UUID) -> dict[str, int]:
    total_jobs = (await db.execute(select(func.count(Job.id)).where(Job.user_id == user_id))).scalar() or 0
    total_runs = (
        await db.execute(
            select(func.count(Run.id))
            .select_from(Run)
            .join(Job, Run.job_id == Job.id)
            .where(Job.user_id == user_id)
        )
    ).scalar() or 0
    total_exports = (
        await db.execute(
            select(func.count(Export.id))
            .select_from(Export)
            .join(Run, Export.run_id == Run.id)
            .join(Job, Run.job_id == Job.id)
            .where(Job.user_id == user_id)
        )
    ).scalar() or 0
    today = datetime.now(timezone.utc).date()
    runs_today = (
        await db.execute(
            select(func.count(Run.id))
            .select_from(Run)
            .join(Job, Run.job_id == Job.id)
            .where(Job.user_id == user_id, func.date(Run.created_at) == today)
        )
    ).scalar() or 0
    return {
        "total_jobs": int(total_jobs),
        "total_runs": int(total_runs),
        "total_exports": int(total_exports),
        "runs_today": int(runs_today),
    }


async def enforce_job_limit(db: AsyncSession, user: User) -> None:
    limits = get_plan_limits(user.plan)
    total_jobs = (await db.execute(select(func.count(Job.id)).where(Job.user_id == user.id))).scalar() or 0
    if int(total_jobs) >= limits["max_jobs"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"{normalize_plan(user.plan).title()} plan job limit reached",
        )


async def enforce_run_limit(db: AsyncSession, user: User) -> None:
    limits = get_plan_limits(user.plan)
    usage = await get_usage_summary(db, user.id)
    if usage["runs_today"] >= limits["max_runs_per_day"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"{normalize_plan(user.plan).title()} plan daily run limit reached",
        )
