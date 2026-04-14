"""Runs API endpoints.

Handles viewing run status and history for scraping jobs.
"""
import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_storage
from app.config import settings
from app.models.job import Job
from app.models.result import Result
from app.models.run import Run
from app.models.user import User
from app.schemas.result import ResultListResponse, ResultResponse
from app.schemas.run import RunListResponse, RunResponse
from app.services.run_logs import append_run_log, read_run_logs
from app.services.saas import enforce_run_limit
from app.storage.manager import StorageManager


router = APIRouter()


def _get_run_scraping_job():
    try:
        from app.queue.tasks import run_scraping_job
    except ModuleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Background worker dependencies are missing. Install backend requirements and restart the API.",
        ) from exc

    return run_scraping_job


async def _enqueue_retry_or_fail(
    db: AsyncSession,
    *,
    run: Run,
    current_user: User,
) -> None:
    try:
        _get_run_scraping_job().delay(str(run.job_id), str(current_user.id), str(run.id))
    except Exception as exc:
        run.status = "failed"
        run.error_message = "Execution queue is unavailable. Start the worker and try again."
        await db.commit()
        await db.refresh(run)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=run.error_message,
        ) from exc


@router.get(
    "",
    response_model=RunListResponse,
    summary="List user's runs",
)
async def list_runs(
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum records to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RunListResponse:
    count_stmt = (
        select(func.count(Run.id))
        .select_from(Run)
        .join(Job, Run.job_id == Job.id)
        .where(Job.user_id == current_user.id)
    )
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    stmt = (
        select(Run)
        .join(Job, Run.job_id == Job.id)
        .where(Job.user_id == current_user.id)
        .order_by(Run.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    runs = result.scalars().all()

    return RunListResponse(runs=[RunResponse.model_validate(run) for run in runs], total=total)


@router.get(
    "/{run_id}/logs",
    summary="Get logs for a run",
)
async def get_run_logs(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    stmt = (
        select(Run)
        .join(Job, Run.job_id == Job.id)
        .where(Run.id == run_id, Job.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )

    return {
        "run_id": str(run.id),
        "logs": await asyncio.to_thread(read_run_logs, str(run.id)),
    }


@router.post(
    "/{run_id}/retry",
    response_model=RunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Retry a failed run",
)
async def retry_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RunResponse:
    await enforce_run_limit(db, current_user)

    stmt = (
        select(Run)
        .join(Job, Run.job_id == Job.id)
        .where(Run.id == run_id, Job.user_id == current_user.id)
        .with_for_update()
    )
    result = await db.execute(stmt)
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )
    if run.status not in {"failed", "completed"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only completed or failed runs can be retried",
        )

    active_run_stmt = select(Run).where(
        Run.job_id == run.job_id,
        Run.status.in_(("pending", "running")),
    )
    active_run_result = await db.execute(active_run_stmt)
    active_run = active_run_result.scalar_one_or_none()
    if active_run:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A run is already pending or running for this job",
        )

    retry = Run(
        job_id=run.job_id,
        status="pending",
        progress=0,
        started_at=None,
        finished_at=None,
        error_message=None,
    )
    db.add(retry)
    await db.commit()
    await db.refresh(retry)

    append_run_log(
        str(retry.id),
        event="retry_requested",
        message="Run retry requested.",
        details={"retry_of": str(run.id)},
    )
    await _enqueue_retry_or_fail(db, run=retry, current_user=current_user)

    return RunResponse.model_validate(retry)


@router.post(
    "/{run_id}/cancel",
    response_model=RunResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel a queued, pending, or running run",
)
async def cancel_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RunResponse:
    """Cancel a queued, pending, or running run."""
    stmt = (
        select(Run)
        .join(Job, Run.job_id == Job.id)
        .where(Run.id == run_id, Job.user_id == current_user.id)
        .with_for_update()
    )
    result = await db.execute(stmt)
    run = result.scalar_one_or_none()
    
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )
    
    if run.status not in {"queued", "pending", "running"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel a {run.status} run. Only queued, pending, or running runs can be cancelled.",
        )
    
    run.status = "cancelled"
    run.finished_at = func.now()
    run.error_message = "Run was cancelled by user"
    
    await db.commit()
    await db.refresh(run)
    
    append_run_log(str(run.id), event="run_cancelled", message="Run was cancelled by user.")
    
    return RunResponse.model_validate(run)


@router.get(
    "/{run_id}",
    response_model=RunResponse,
    summary="Get run details",
)
async def get_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RunResponse:
    """Get details of a specific run.
    
    Verifies that the run belongs to a job owned by the current user.
    
    Args:
        run_id: The run's unique identifier.
        db: Database session.
        current_user: The authenticated user.
        
    Returns:
        RunResponse: The run data.
        
    Raises:
        HTTPException 404: If run not found or doesn't belong to user.
    """
    # Join with Job to verify ownership
    stmt = (
        select(Run)
        .join(Job, Run.job_id == Job.id)
        .where(Run.id == run_id, Job.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    run = result.scalar_one_or_none()
    
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )
    
    return RunResponse.model_validate(run)


@router.get(
    "/{run_id}/markdown",
    summary="Get semantic markdown snapshot for a run",
)
async def get_run_markdown(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: StorageManager = Depends(get_storage),
) -> dict[str, str]:
    stmt = (
        select(Run)
        .join(Job, Run.job_id == Job.id)
        .where(Run.id == run_id, Job.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )

    snapshot_path = str(run.markdown_snapshot_path or "").strip()
    if not snapshot_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No semantic markdown snapshot found for this run",
        )

    resolved_snapshot_path = storage.resolve_path(snapshot_path)
    storage_root = settings.STORAGE_ROOT.resolve()
    resolved_snapshot_path_str = str(resolved_snapshot_path)
    storage_root_str = str(storage_root)
    storage_root_prefix = f"{storage_root_str}/"
    if not (
        resolved_snapshot_path_str == storage_root_str
        or resolved_snapshot_path_str.startswith(storage_root_prefix)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid markdown snapshot path",
        )
    if not resolved_snapshot_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Semantic markdown snapshot file is missing",
        )

    return {
        "run_id": str(run.id),
        "snapshot_path": snapshot_path,
        "markdown": storage.get_file_text(str(resolved_snapshot_path)),
    }


@router.get(
    "/{run_id}/results",
    response_model=ResultListResponse,
    summary="List results for a run",
)
async def list_run_results(
    run_id: UUID,
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum records to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResultListResponse:
    """List all results for a specific run.
    
    Verifies ownership through the run's parent job.
    
    Args:
        run_id: The run's unique identifier.
        skip: Number of records to skip.
        limit: Maximum number of records to return.
        db: Database session.
        current_user: The authenticated user.
        
    Returns:
        ResultListResponse: Paginated list of results.
        
    Raises:
        HTTPException 404: If run not found or doesn't belong to user.
    """
    # Verify run belongs to user via job ownership
    run_stmt = (
        select(Run)
        .join(Job, Run.job_id == Job.id)
        .where(Run.id == run_id, Job.user_id == current_user.id)
    )
    run_result = await db.execute(run_stmt)
    run = run_result.scalar_one_or_none()
    
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )
    
    # Get total count of results
    count_stmt = select(func.count(Result.id)).where(Result.run_id == run_id)
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0
    
    # Get results
    stmt = (
        select(Result)
        .where(Result.run_id == run_id)
        .order_by(Result.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    results = result.scalars().all()
    
    result_responses = [ResultResponse.model_validate(r) for r in results]
    
    return ResultListResponse(results=result_responses, total=total)
