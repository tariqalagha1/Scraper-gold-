"""Jobs API endpoints.

Handles creation, listing, and management of scraping jobs.
"""
import asyncio
import logging
import math
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, verify_api_key
from app.execution.brainit_execution_service import execute_scraping_run
from app.execution.task_registry import get_task, get_trace_id, register_task, set_task_handle
from app.models.job import Job
from app.models.run import Run
from app.models.user import User
from app.schemas.job import JobCreate, JobDeleteResponse, JobListResponse, JobResponse, JobUpdate
from app.schemas.execution_contract import ExecutionContract, build_execution_contract_from_job_config
from app.schemas.run import (
    RunExecutionStatusResponse,
    RunListResponse,
    RunQueuedResponse,
    RunResponse,
    RunStartRequest,
)
from app.services.saas import enforce_job_limit, enforce_run_limit


router = APIRouter()
logger = logging.getLogger(__name__)

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
DEFAULT_RECORDS_PER_PAGE_ESTIMATE = 20
RECORD_BUDGET_SAFETY_MULTIPLIER = 1.25
MAX_AUTO_PAGE_BUDGET = 1000
HIGH_RECORD_LIMIT_FORCE_PAGINATION = 100


def _has_full_coverage_intent(prompt: str | None) -> bool:
    text = str(prompt or "").strip().lower()
    if not text:
        return False
    return any(marker in text for marker in FULL_COVERAGE_PROMPT_MARKERS)


def _should_boost_page_budget(prompt: str | None, follow_pagination: bool) -> bool:
    if not follow_pagination:
        return False
    return _has_full_coverage_intent(prompt)


def _resolve_max_pages(
    *,
    requested_max_pages: int,
    prompt: str | None,
    follow_pagination: bool,
    requested_record_limit: int | None = None,
) -> int:
    if requested_max_pages > 10:
        return requested_max_pages
    if _should_boost_page_budget(prompt, follow_pagination):
        return MAX_AUTO_PAGE_BUDGET
    if follow_pagination:
        auto_budget = _resolve_page_budget_from_record_limit(requested_record_limit)
        if auto_budget and auto_budget > requested_max_pages:
            return auto_budget
    return requested_max_pages


def _resolve_page_budget_from_record_limit(requested_record_limit: int | None) -> int | None:
    try:
        normalized_limit = int(requested_record_limit or 0)
    except (TypeError, ValueError):
        return None
    if normalized_limit <= 0:
        return None

    baseline_pages = math.ceil(normalized_limit / DEFAULT_RECORDS_PER_PAGE_ESTIMATE)
    buffered_pages = math.ceil(baseline_pages * RECORD_BUDGET_SAFETY_MULTIPLIER)
    auto_budget = max(1, buffered_pages)
    return min(MAX_AUTO_PAGE_BUDGET, auto_budget)


def _normalize_record_limit(value: object) -> int | None:
    try:
        normalized_limit = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return normalized_limit if normalized_limit > 0 else None


def _should_force_pagination_from_record_limit(requested_record_limit: int | None) -> bool:
    return bool(
        requested_record_limit is not None
        and requested_record_limit >= HIGH_RECORD_LIMIT_FORCE_PAGINATION
    )


def _resolve_effective_follow_pagination(
    *,
    requested_follow_pagination: bool,
    prompt: str | None,
    requested_record_limit: int | None,
    context: str,
) -> tuple[bool, str | None]:
    if _has_full_coverage_intent(prompt) and not requested_follow_pagination:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "Pagination cannot be disabled when the request asks for full coverage "
                "(all/every/entire pages or records). Set follow_pagination=true."
            ),
        )

    if not requested_follow_pagination and _should_force_pagination_from_record_limit(requested_record_limit):
        logger.info(
            "User intent enforcement activated: forced pagination enabled for high record target.",
            enforcement_event="user_intent_enforced",
            reason="high_record_limit",
            context=context,
            requested_record_limit=requested_record_limit,
        )
        return True, "high_record_limit"

    return requested_follow_pagination, None


def _is_sqlite_lock_error(exc: Exception) -> bool:
    return "database is locked" in str(exc).lower()


async def _commit_with_retry_on_sqlite_lock(
    db: AsyncSession,
    *,
    context: str,
    max_attempts: int = 4,
) -> None:
    for attempt in range(1, max_attempts + 1):
        try:
            await db.commit()
            return
        except OperationalError as exc:
            await db.rollback()
            if not _is_sqlite_lock_error(exc) or attempt >= max_attempts:
                raise
            delay_seconds = 0.25 * attempt
            logger.warning(
                "SQLite lock detected; retrying transaction commit.",
                context=context,
                attempt=attempt,
                retry_in_seconds=delay_seconds,
            )
            await asyncio.sleep(delay_seconds)


async def _schedule_brainit_run_or_fail(
    *,
    job: Job,
    current_user: User,
    run: Run,
    execution_contract: ExecutionContract,
) -> str:
    trace_id = str(uuid4())
    run_id = str(run.id)
    register_task(run_id=run_id, job_id=str(job.id), trace_id=trace_id)

    task = asyncio.create_task(
        execute_scraping_run(
            str(job.id),
            user_id=str(current_user.id),
            payload={
                "run_id": run_id,
                "execution_contract": execution_contract.model_dump(),
            },
            trace_id=trace_id,
        ),
        name=f"brainit-run-{run_id}",
    )
    set_task_handle(run_id, task)
    return trace_id


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


def _serialize_run(run: Run) -> RunResponse:
    data = RunResponse.model_validate(run)
    trace_id = get_trace_id(str(run.id))
    if trace_id:
        return data.model_copy(update={"trace_id": trace_id})
    return data


@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new scraping job",
    dependencies=[Depends(verify_api_key)],
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
    requested_record_limit = _normalize_record_limit(config.get("max_records"))
    effective_follow_pagination, enforcement_reason = _resolve_effective_follow_pagination(
        requested_follow_pagination=bool(job_data.follow_pagination),
        prompt=job_data.prompt,
        requested_record_limit=requested_record_limit,
        context="create_job",
    )
    effective_max_pages = _resolve_max_pages(
        requested_max_pages=job_data.max_pages,
        prompt=job_data.prompt,
        follow_pagination=effective_follow_pagination,
        requested_record_limit=requested_record_limit,
    )
    config["max_pages"] = effective_max_pages
    config["follow_pagination"] = effective_follow_pagination
    if job_data.prompt is not None:
        config["prompt"] = job_data.prompt
    if enforcement_reason:
        logger.info(
            "Job configuration normalized to enforce user intent coverage policy.",
            enforcement_event="user_intent_enforced",
            reason=enforcement_reason,
            user_id=str(current_user.id),
            url=str(job_data.url),
            follow_pagination=effective_follow_pagination,
            max_pages=effective_max_pages,
            max_records=requested_record_limit,
        )
    
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
    await _commit_with_retry_on_sqlite_lock(db, context="create_job")
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


@router.patch(
    "/{job_id}",
    response_model=JobResponse,
    summary="Update job details",
    dependencies=[Depends(verify_api_key)],
)
async def update_job(
    job_id: UUID,
    job_update: JobUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobResponse:
    """Partially update a scraping job.
    
    Only provided fields will be updated. Jobs that are running or completed
    cannot be updated.
    
    Args:
        job_id: The job's unique identifier.
        job_update: Fields to update.
        db: Database session.
        current_user: The authenticated user.
        
    Returns:
        JobResponse: The updated job data.
        
    Raises:
        HTTPException 404: If job not found or doesn't belong to user.
        HTTPException 400: If job cannot be updated.
    """
    stmt = select(Job).where(Job.id == job_id, Job.user_id == current_user.id)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    
    # Check if job can be updated
    if job.status in ("running", "completed", "failed", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot update job with status '{job.status}'",
        )
    
    # Apply updates
    update_data = job_update.model_dump(exclude_unset=True)
    if update_data:
        current_config = dict(job.config or {})
        # Handle URL fields
        if "url" in update_data:
            update_data["url"] = str(update_data["url"])
        if "login_url" in update_data:
            update_data["login_url"] = str(update_data["login_url"]) if update_data["login_url"] else None
        
        # Handle scrape_type enum
        if "scrape_type" in update_data:
            update_data["scrape_type"] = update_data["scrape_type"].value

        # Merge explicit config first.
        if "config" in update_data:
            proposed_config = update_data.pop("config")
            if isinstance(proposed_config, dict):
                current_config.update(proposed_config)

        # Keep prompt/pagination/max_pages as canonical config keys.
        if "prompt" in update_data:
            current_config["prompt"] = update_data.pop("prompt")
        if "follow_pagination" in update_data:
            current_config["follow_pagination"] = bool(update_data.pop("follow_pagination"))
        if "max_pages" in update_data:
            current_config["max_pages"] = int(update_data.pop("max_pages"))

        requested_follow = bool(current_config.get("follow_pagination", True))
        requested_record_limit = _normalize_record_limit(current_config.get("max_records"))
        effective_follow_pagination, enforcement_reason = _resolve_effective_follow_pagination(
            requested_follow_pagination=requested_follow,
            prompt=str(current_config.get("prompt") or ""),
            requested_record_limit=requested_record_limit,
            context="update_job",
        )
        current_config["follow_pagination"] = effective_follow_pagination

        try:
            configured_max_pages = int(current_config.get("max_pages", 10) or 10)
        except (TypeError, ValueError):
            configured_max_pages = 10
        current_config["max_pages"] = _resolve_max_pages(
            requested_max_pages=configured_max_pages,
            prompt=str(current_config.get("prompt") or ""),
            follow_pagination=effective_follow_pagination,
            requested_record_limit=requested_record_limit,
        )
        update_data["config"] = current_config

        if enforcement_reason:
            logger.info(
                "Job update normalized to enforce user intent coverage policy.",
                enforcement_event="user_intent_enforced",
                reason=enforcement_reason,
                user_id=str(current_user.id),
                job_id=str(job.id),
                follow_pagination=effective_follow_pagination,
                max_pages=current_config["max_pages"],
                max_records=requested_record_limit,
            )
        
        # Update other fields
        for field, value in update_data.items():
            setattr(job, field, value)
        
        job.updated_at = None  # Will be set by database trigger
        await db.commit()
        await db.refresh(job)
    
    return _serialize_job(job)


@router.post(
    "/{job_id}/runs",
    response_model=RunQueuedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new run for a job",
    dependencies=[Depends(verify_api_key)],
)
async def create_job_run(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    run_request: RunStartRequest | None = None,
) -> RunQueuedResponse:
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
    requested_record_limit = _normalize_record_limit(config.get("max_records"))
    effective_follow_pagination, enforcement_reason = _resolve_effective_follow_pagination(
        requested_follow_pagination=bool(config.get("follow_pagination", True)),
        prompt=str(config.get("prompt") or ""),
        requested_record_limit=requested_record_limit,
        context="create_job_run",
    )
    config["follow_pagination"] = effective_follow_pagination
    try:
        configured_max_pages = int(config.get("max_pages", 10) or 10)
    except (TypeError, ValueError):
        configured_max_pages = 10
    effective_max_pages = _resolve_max_pages(
        requested_max_pages=configured_max_pages,
        prompt=config.get("prompt"),
        follow_pagination=effective_follow_pagination,
        requested_record_limit=requested_record_limit,
    )
    if effective_max_pages != configured_max_pages or enforcement_reason:
        config["max_pages"] = effective_max_pages
        job.config = config
        await db.commit()
        await db.refresh(job)
        if enforcement_reason:
            logger.info(
                "Run creation normalized job config to enforce user intent coverage policy.",
                enforcement_event="user_intent_enforced",
                reason=enforcement_reason,
                user_id=str(current_user.id),
                job_id=str(job.id),
                follow_pagination=effective_follow_pagination,
                max_pages=effective_max_pages,
                max_records=requested_record_limit,
            )

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
    if run_request and run_request.execution_contract:
        execution_contract = run_request.execution_contract
    else:
        execution_contract = build_execution_contract_from_job_config(
            job.config,
            job_url=job.url,
        )
    run.execution_contract = execution_contract.model_dump()
    db.add(run)
    await db.commit()
    await db.refresh(run)

    trace_id = await _schedule_brainit_run_or_fail(
        job=job,
        current_user=current_user,
        run=run,
        execution_contract=execution_contract,
    )
    return RunQueuedResponse(
        id=run.id,
        run_id=run.id,
        job_id=run.job_id,
        trace_id=trace_id,
        status="queued",
        progress=run.progress,
        started_at=run.started_at,
        finished_at=run.finished_at,
        error_message=run.error_message,
    )


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
    
    run_responses = [_serialize_run(run) for run in runs]
    
    return RunListResponse(runs=run_responses, total=total)


@router.get(
    "/{job_id}/runs/{run_id}",
    response_model=RunExecutionStatusResponse,
    summary="Get run execution status for a job",
)
async def get_job_run_status(
    job_id: UUID,
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RunExecutionStatusResponse:
    stmt = (
        select(Run)
        .join(Job, Run.job_id == Job.id)
        .where(Run.id == run_id, Run.job_id == job_id, Job.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )

    task_state = get_task(str(run.id))
    errors: list[str] = []
    if run.error_message:
        errors.append(run.error_message)
    elif run.error:
        errors.append(run.error)
    if task_state and task_state.get("error"):
        errors.append(str(task_state["error"]))

    return RunExecutionStatusResponse(
        run_id=run.id,
        job_id=run.job_id,
        trace_id=(task_state or {}).get("trace_id"),
        status=str((task_state or {}).get("status") or run.status),
        result=dict((task_state or {}).get("result") or run.execution_result or {}),
        errors=errors,
        started_at=(task_state or {}).get("started_at"),
        finished_at=(task_state or {}).get("finished_at"),
        execution_contract=dict(run.execution_contract or {}),
    )


@router.delete(
    "/{job_id}",
    response_model=JobResponse,
    summary="Cancel a job",
    dependencies=[Depends(verify_api_key)],
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


@router.delete(
    "/{job_id}/permanent",
    response_model=JobDeleteResponse,
    summary="Permanently delete a job",
    dependencies=[Depends(verify_api_key)],
)
async def delete_job_permanently(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobDeleteResponse:
    """Permanently delete a job and its related runs/results.

    Running jobs must be cancelled before permanent deletion.
    """
    stmt = select(Job).where(Job.id == job_id, Job.user_id == current_user.id)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    if job.status == "running":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot permanently delete a running job. Cancel it first.",
        )

    await db.delete(job)
    await db.commit()
    return JobDeleteResponse(id=job_id, deleted=True)
