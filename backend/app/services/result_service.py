"""Result service.

Handles result querying and filtering.
"""
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.models.result import Result
from app.models.run import Run
from app.schemas.result import ResultCreate, ResultSearch
from app.vector.search import semantic_search


async def create_result(
    db: AsyncSession, result_data: ResultCreate
) -> Result:
    """Create a new result.
    
    Args:
        db: Database session
        result_data: Result creation data
        
    Returns:
        Created result
    """
    result = Result(
        run_id=result_data.run_id,
        data_json=result_data.data_json,
        data_type=result_data.data_type,
        url=result_data.url,
        raw_html_path=result_data.raw_html_path,
        screenshot_path=result_data.screenshot_path,
    )
    db.add(result)
    await db.commit()
    await db.refresh(result)
    return result


async def get_result_by_id(
    db: AsyncSession, result_id: UUID, user_id: UUID
) -> Optional[Result]:
    """Get a result by ID for a specific user.
    
    Args:
        db: Database session
        result_id: Result ID
        user_id: User ID for ownership check
        
    Returns:
        Result if found and owned by user, None otherwise
    """
    result = await db.execute(
        select(Result)
        .join(Run)
        .join(Job)
        .where(Result.id == result_id, Job.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_results_by_run(
    db: AsyncSession,
    run_id: UUID | None,
    user_id: UUID,
    skip: int = 0,
    limit: int = 100,
) -> list[Result]:
    """Get all results for a run or all results for a user.
    
    Args:
        db: Database session
        run_id: Run ID (optional)
        user_id: User ID for ownership check
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of results
    """
    query = (
        select(Result)
        .join(Run)
        .join(Job)
        .where(Job.user_id == user_id)
    )
    
    if run_id:
        query = query.where(Result.run_id == run_id)
    
    query = query.offset(skip).limit(limit).order_by(Result.created_at.desc())
    
    result = await db.execute(query)
    return list(result.scalars().all())


async def search_results(
    db: AsyncSession,
    search_params: ResultSearch,
    user_id: UUID,
    skip: int = 0,
    limit: int = 100,
) -> list[Result]:
    """Search results with optional semantic search.
    
    Args:
        db: Database session
        search_params: Search parameters
        user_id: User ID for ownership check
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of matching results
    """
    if search_params.use_semantic_search:
        # Use vector-based semantic search
        result_ids = await semantic_search(
            query=search_params.query,
            user_id=user_id,
            limit=limit,
        )
        
        if not result_ids:
            return []
        
        query = (
            select(Result)
            .join(Run)
            .join(Job)
            .where(Result.id.in_(result_ids), Job.user_id == user_id)
        )
    else:
        # Use basic text search
        query = (
            select(Result)
            .join(Run)
            .join(Job)
            .where(Job.user_id == user_id)
        )
    
    if search_params.data_type:
        query = query.where(Result.data_type == search_params.data_type)
    
    if search_params.run_id:
        query = query.where(Result.run_id == search_params.run_id)
    
    if search_params.job_id:
        query = query.where(Run.job_id == search_params.job_id)
    
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    return list(result.scalars().all())
