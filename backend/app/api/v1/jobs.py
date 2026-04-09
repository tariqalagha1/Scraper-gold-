"""Jobs API endpoints.

Handles creation, listing, and management of scraping jobs.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.job import Job
from app.models.run import Run
from app.models.user import User
from app.schemas.job import JobCreate, JobListResponse, JobResponse
from app.schemas.run import RunListResponse, RunResponse
from app.services.saas import enforce_job_limit, enforce_run_limit


router = APIRouter()

FULL_COVERAGE_PROMPT_MARKERS = (
    "all pages",
    "all page",
    "entire pages",
    "entire page",
    "intire pages",
    "full pages",
    "every page",
    "all records",
    "all patients",
    "complete data",
)


def _should_boost_page_budget(prompt: str | None, follow_pagination: bool) -> bool:
    if not follow_pagination:
        return False
    text = str(prompt or "").strip().lower()
    if not text:
        return False
    return any(marker in text for marker in FULL_COVERAGE_PROMPT_MARKERS)


def _resolve_max_pages(
    *,
    requested_max_pages: int,
    prompt: str | None,
    follow_pagination: bool,
) -> int:
    if requested_max_pages > 10:
        return requested_max_pages
    if _should_boost_page_budget(prompt, follow_pagination):
        return 1000
    return requested_max_pages


def _get_run_scraping_job():
    try:
        from app.queue.tasks import run_scraping_job
    except ModuleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Background worker dependencies are missing. Install backend requirements and restart the API.",
        ) from exc

    return run_scraping_job


async def _enqueue_run_or_fail(
    db: AsyncSession,
    *,
    job: Job,
    current_user: User,
    run: Run,
) -> None:
    try:
        _get_run_scraping_job().delay(str(job.id), str(current_user.id), str(run.id))
    except Exception as exc:
        run.status = "failed"
        run.error_message = "Execution queue is unavailable. Start the worker and try again."
        await db.commit()
        await db.refresh(run)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=run.error_message,
        ) from exc


def _serialize_job(job: Job) -> JobResponse:
    config = job.config or {}
    return JobResponse(
        id=job.id,
        user_id=job.user_id,
        url=job.url,
        login_url=job.login_url,
        scrape_type=job.scrape_type,
        prompt=config.get("prompt"),
        status=job.status,
        max_pages=config.get("max_pages", 10),
        follow_pagination=bool(config.get("follow_pagination", True)),
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new scraping job",
)
async def create_job(
    job_data: JobCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobResponse:
    """Create a new scraping job.
    
    The execution flow is explicit: a job is created first, then a run is
    started separately through ``POST /jobs/{job_id}/runs``.
    
    Args:
        job_data: Job configuration data.
        db: Database session.
        current_user: The authenticated user.
        
    Returns:
        JobResponse: The created job data.
    """
    await enforce_job_limit(db, current_user)

    # Build config with max_pages and follow_pagination
    config = job_data.config.model_dump(exclude_none=True) if job_data.config else {}
    effective_max_pages = _resolve_max_pages(
        requested_max_pages=job_data.max_pages,
        prompt=job_data.prompt,
        follow_pagination=job_data.follow_pagination,
    )
    config["max_pages"] = effective_max_pages
    config["follow_pagination"] = job_data.follow_pagination
    if job_data.prompt is not None:
        config["prompt"] = job_data.prompt
    
    # Create job record
    new_job = Job(
        user_id=current_user.id,
        url=str(job_data.url),
        login_url=str(job_data.login_url) if job_data.login_url else None,
        login_username=job_data.login_username,
        login_password=job_data.login_password,
        scrape_type=job_data.scrape_type.value,
        config=config,
        status="pending",
    )
    
    db.add(new_job)
    await db.commit()
    await db.refresh(new_job)
    
    return _serialize_job(new_job)


@router.get(
    "",
    response_model=JobListResponse,
    summary="List user's jobs",
)
async def list_jobs(
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum records to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobListResponse:
    """List all jobs for the current user with pagination.
    
    Args:
        skip: Number of records to skip.
        limit: Maximum number of records to return.
        db: Database session.
        current_user: The authenticated user.
        
    Returns:
        JobListResponse: Paginated list of jobs.
    """
    # Get total count
    count_stmt = select(func.count(Job.id)).where(Job.user_id == current_user.id)
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0
    
    # Get jobs
    stmt = (
        select(Job)
        .where(Job.user_id == current_user.id)
        .order_by(Job.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    jobs = result.scalars().all()
    
    # Convert to response format
    job_responses = []
    for job in jobs:
        config = job.config or {}
        job_responses.append(_serialize_job(job))
    
    return JobListResponse(jobs=job_responses, total=total)


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get job details",
)
async def get_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobResponse:
    """Get details of a specific job.
    
    Args:
        job_id: The job's unique identifier.
        db: Database session.
        current_user: The authenticated user.
        
    Returns:
        JobResponse: The job data.
        
    Raises:
        HTTPException 404: If job not found or doesn't belong to user.
    """
    stmt = select(Job).where(Job.id == job_id, Job.user_id == current_user.id)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    
    return _serialize_job(job)


@router.post(
    "/{job_id}/runs",
    response_model=RunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new run for a job",
)
async def create_job_run(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RunResponse:
    await enforce_run_limit(db, current_user)

    stmt = select(Job).where(Job.id == job_id, Job.user_id == current_user.id).with_for_update()
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    # Backward-compatible safeguard: older jobs created with default max_pages=10
    # should still honor "all pages"/"entire pages" prompts at run time.
    config = dict(job.config or {})
    try:
        configured_max_pages = int(config.get("max_pages", 10) or 10)
    except (TypeError, ValueError):
        configured_max_pages = 10
    effective_max_pages = _resolve_max_pages(
        requested_max_pages=configured_max_pages,
        prompt=config.get("prompt"),
        follow_pagination=bool(config.get("follow_pagination", True)),
    )
    if effective_max_pages != configured_max_pages:
        config["max_pages"] = effective_max_pages
        job.config = config
        await db.commit()
        await db.refresh(job)

    active_run_stmt = select(Run).where(
        Run.job_id == job.id,
        Run.status.in_(("pending", "running")),
    )
    active_run_result = await db.execute(active_run_stmt)
    active_run = active_run_result.scalar_one_or_none()
    if active_run:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A run is already pending or running for this job",
        )

    run = Run(
        job_id=job.id,
        status="pending",
        progress=0,
        started_at=None,
        finished_at=None,
        error_message=None,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    await _enqueue_run_or_fail(db, job=job, current_user=current_user, run=run)

    return RunResponse.model_validate(run)


@router.get(
    "/{job_id}/runs",
    response_model=RunListResponse,
    summary="List runs for a job",
)
async def list_job_runs(
    job_id: UUID,
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum records to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RunListResponse:
    """List all runs for a specific job.
    
    Args:
        job_id: The job's unique identifier.
        skip: Number of records to skip.
        limit: Maximum number of records to return.
        db: Database session.
        current_user: The authenticated user.
        
    Returns:
        RunListResponse: Paginated list of runs.
        
    Raises:
        HTTPException 404: If job not found or doesn't belong to user.
    """
    # Verify job belongs to user
    job_stmt = select(Job).where(Job.id == job_id, Job.user_id == current_user.id)
    job_result = await db.execute(job_stmt)
    job = job_result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    
    # Get total count of runs
    count_stmt = select(func.count(Run.id)).where(Run.job_id == job_id)
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0
    
    # Get runs
    stmt = (
        select(Run)
        .where(Run.job_id == job_id)
        .order_by(Run.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    runs = result.scalars().all()
    
    run_responses = [RunResponse.model_validate(run) for run in runs]
    
    return RunListResponse(runs=run_responses, total=total)


@router.delete(
    "/{job_id}",
    response_model=JobResponse,
    summary="Cancel a job",
)
async def cancel_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobResponse:
    """Cancel a scraping job.
    
    Sets the job status to 'cancelled'. Jobs that are already completed
    or failed cannot be cancelled.
    
    Args:
        job_id: The job's unique identifier.
        db: Database session.
        current_user: The authenticated user.
        
    Returns:
        JobResponse: The updated job data.
        
    Raises:
        HTTPException 404: If job not found or doesn't belong to user.
        HTTPException 400: If job cannot be cancelled.
    """
    stmt = select(Job).where(Job.id == job_id, Job.user_id == current_user.id)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    
    # Check if job can be cancelled
    if job.status in ("completed", "failed", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job with status '{job.status}'",
        )
    
    # Update status to cancelled
    job.status = "cancelled"
    await db.commit()
    await db.refresh(job)
    
    return _serialize_job(job)
