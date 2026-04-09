"""Run service.

Handles run lifecycle management.
"""
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.run import Run
from app.models.job import Job


async def create_run(db: AsyncSession, job_id: UUID) -> Run:
    """Create a new run for a job.
    
    Args:
        db: Database session
        job_id: Parent job ID
        
    Returns:
        Created run
    """
    run = Run(
        job_id=job_id,
        status="pending",
        progress=0,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run


async def start_run(db: AsyncSession, run_id: UUID) -> Optional[Run]:
    """Mark a run as started.
    
    Args:
        db: Database session
        run_id: Run ID
        
    Returns:
        Updated run
    """
    result = await db.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        return None
    
    run.status = "running"
    run.progress = max(run.progress, 5)
    run.started_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(run)
    return run


async def complete_run(db: AsyncSession, run_id: UUID, error: Optional[str] = None) -> Optional[Run]:
    """Mark a run as completed or failed.
    
    Args:
        db: Database session
        run_id: Run ID
        error: Optional error message if run failed
        
    Returns:
        Updated run
    """
    result = await db.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        return None
    
    run.status = "failed" if error else "completed"
    run.progress = 100 if not error else run.progress
    run.finished_at = datetime.now(timezone.utc)
    run.error = error
    run.error_message = error
    await db.commit()
    await db.refresh(run)
    return run


async def get_run_by_id(
    db: AsyncSession, run_id: UUID, user_id: UUID
) -> Optional[Run]:
    """Get a run by ID for a specific user.
    
    Args:
        db: Database session
        run_id: Run ID
        user_id: User ID for ownership check
        
    Returns:
        Run if found and owned by user, None otherwise
    """
    result = await db.execute(
        select(Run)
        .join(Job)
        .where(Run.id == run_id, Job.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_runs_by_job(
    db: AsyncSession, job_id: UUID, user_id: UUID, skip: int = 0, limit: int = 100
) -> List[Run]:
    """Get all runs for a job.
    
    Args:
        db: Database session
        job_id: Job ID
        user_id: User ID for ownership check
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of runs
    """
    result = await db.execute(
        select(Run)
        .join(Job)
        .where(Run.job_id == job_id, Job.user_id == user_id)
        .offset(skip)
        .limit(limit)
        .order_by(Run.started_at.desc())
    )
    return list(result.scalars().all())


async def get_runs_by_user(
    db: AsyncSession, user_id: UUID, skip: int = 0, limit: int = 100
) -> List[Run]:
    """Get all runs for a user across all jobs.
    
    Args:
        db: Database session
        user_id: User ID
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of runs
    """
    result = await db.execute(
        select(Run)
        .join(Job)
        .where(Job.user_id == user_id)
        .offset(skip)
        .limit(limit)
        .order_by(Run.started_at.desc())
    )
    return list(result.scalars().all())
