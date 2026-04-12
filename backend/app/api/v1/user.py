from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_storage
from app.models.user import User
from app.schemas.storage_cleanup import CleanupResultResponse, StorageCleanupEstimateResponse
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
