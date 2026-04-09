"""Results API endpoints.

Handles viewing scraped results.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.job import Job
from app.models.result import Result
from app.models.run import Run
from app.models.user import User
from app.schemas.result import ResultResponse


router = APIRouter()


@router.get(
    "/{result_id}",
    response_model=ResultResponse,
    summary="Get result details",
)
async def get_result(
    result_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResultResponse:
    """Get details of a specific result with extracted data.
    
    Verifies ownership through the result's parent run and job.
    
    Args:
        result_id: The result's unique identifier.
        db: Database session.
        current_user: The authenticated user.
        
    Returns:
        ResultResponse: The result data including extracted JSON.
        
    Raises:
        HTTPException 404: If result not found or doesn't belong to user.
    """
    # Join through Run and Job to verify ownership
    stmt = (
        select(Result)
        .join(Run, Result.run_id == Run.id)
        .join(Job, Run.job_id == Job.id)
        .where(Result.id == result_id, Job.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    db_result = result.scalar_one_or_none()
    
    if not db_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result not found",
        )
    
    return ResultResponse.model_validate(db_result)
