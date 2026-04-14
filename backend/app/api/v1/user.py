from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_storage
from app.models.user import User
from app.schemas.storage_cleanup import CleanupResultResponse, StorageCleanupEstimateResponse
from app.orchestrator.history_orchestrator import HistoryOrchestrator
from app.services.user_cleanup import (
    clear_user_all,
    clear_user_history,
    clear_user_temp_files,
    get_storage_cleanup_estimate,
)
from app.storage.manager import StorageManager


router = APIRouter()


@router.get("/storage-summary", response_model=StorageCleanupEstimateResponse)
async def get_storage_summary(
    db: AsyncSession = Depends(get_db),
    storage: StorageManager = Depends(get_storage),
    current_user: User = Depends(get_current_user),
) -> StorageCleanupEstimateResponse:
    return await get_storage_cleanup_estimate(db, current_user.id, storage)


@router.delete("/history", response_model=CleanupResultResponse)
async def delete_user_history(
    db: AsyncSession = Depends(get_db),
    storage: StorageManager = Depends(get_storage),
    current_user: User = Depends(get_current_user),
) -> CleanupResultResponse:
    return await clear_user_history(db, current_user.id, storage)


@router.delete("/temp-files", response_model=CleanupResultResponse)
async def delete_user_temp_files(
    db: AsyncSession = Depends(get_db),
    storage: StorageManager = Depends(get_storage),
    current_user: User = Depends(get_current_user),
) -> CleanupResultResponse:
    return await clear_user_temp_files(db, current_user.id, storage)


@router.delete("/clear-all", response_model=CleanupResultResponse)
async def delete_user_all(
    db: AsyncSession = Depends(get_db),
    storage: StorageManager = Depends(get_storage),
    current_user: User = Depends(get_current_user),
) -> CleanupResultResponse:
    return await clear_user_all(db, current_user.id, storage)


@router.get("/activity", response_model=Dict[str, Any])
async def get_user_activity(
    limit: int = Query(default=50, ge=1, le=100, description="Number of activities to return"),
    offset: int = Query(default=0, ge=0, description="Number of activities to skip"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get user activity timeline."""
    orchestrator = HistoryOrchestrator(db)
    return await orchestrator.get_user_activity(current_user.id, limit, offset)


@router.get("/history", response_model=Dict[str, Any])
async def get_user_history(
    start_date: Optional[str] = Query(None, description="Start date filter (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date filter (ISO format)"),
    item_type: Optional[str] = Query(None, description="Filter by type: jobs, runs, exports"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(default=50, ge=1, le=200, description="Number of history items to return"),
    offset: int = Query(default=0, ge=0, description="Number of history items to skip"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get user history with optional filtering."""
    from datetime import datetime
    parsed_start_date = None
    parsed_end_date = None
    if start_date:
        parsed_start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
    if end_date:
        parsed_end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

    orchestrator = HistoryOrchestrator(db)
    return await orchestrator.get_user_history(
        current_user.id,
        limit=limit,
        offset=offset,
        start_date=parsed_start_date,
        end_date=parsed_end_date,
        item_type=item_type,
        status=status,
    )


@router.delete("/history/{item_id}", response_model=Dict[str, bool])
async def delete_history_item(
    item_id: UUID,
    item_type: str = Query(..., description="Type of item to delete: job, run, export"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, bool]:
    """Delete a specific history item."""
    orchestrator = HistoryOrchestrator(db)
    success = await orchestrator.delete_history_item(current_user.id, item_id, item_type)
    return {"success": success}
