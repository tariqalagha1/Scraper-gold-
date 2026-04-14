"""Exports API endpoints.

Handles triggering and downloading export files.
"""
import io
import logging
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_storage, verify_api_key
from app.config import settings
from app.models.export import Export
from app.storage.manager import StorageManager
from app.models.job import Job
from app.models.run import Run
from app.models.user import User
from app.schemas.export import ExportCreate, ExportListResponse, ExportResponse
from app.orchestrator.export_orchestrator import ExportOrchestrator
from app.services.export_management_service import ExportManagementService


router = APIRouter()
logger = logging.getLogger(__name__)


def _get_run_export():
    try:
        from app.queue.tasks import run_export
    except ModuleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Background worker dependencies are missing. Install backend requirements and restart the API.",
        ) from exc

    return run_export


@router.post(
    "",
    response_model=ExportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new export",
)
async def create_export(
    export_data: ExportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    api_key: str = Depends(verify_api_key),
) -> ExportResponse:
    """Create a new export from run results.
    
    Dispatches a Celery task to generate the export file asynchronously.
    
    Args:
        export_data: Export configuration (run_id, format).
        db: Database session.
        current_user: The authenticated user.
        
    Returns:
        ExportResponse: The created export record.
        
    Raises:
        HTTPException 404: If run not found or doesn't belong to user.
    """
    # Verify run belongs to user
    run_stmt = (
        select(Run)
        .join(Job, Run.job_id == Job.id)
        .where(Run.id == export_data.run_id, Job.user_id == current_user.id)
    )
    run_result = await db.execute(run_stmt)
    run = run_result.scalar_one_or_none()
    
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )
    
    # Create export record placeholder to be populated by the background worker.
    new_export = Export(
        run_id=export_data.run_id,
        format=export_data.format,
        file_path="",
    )
    
    db.add(new_export)
    await db.commit()
    await db.refresh(new_export)
    
    # Dispatch Celery task for async export generation
    try:
        _get_run_export().delay(str(new_export.id), str(current_user.id))
    except Exception as exc:
        await db.delete(new_export)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Export queue is currently unavailable. Please try again shortly.",
        ) from exc
    
    return ExportResponse.model_validate(new_export)


@router.get(
    "",
    response_model=ExportListResponse,
    summary="List user's exports",
)
async def list_exports(
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum records to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExportListResponse:
    """List all exports for the current user.
    
    Args:
        skip: Number of records to skip.
        limit: Maximum number of records to return.
        db: Database session.
        current_user: The authenticated user.
        
    Returns:
        ExportListResponse: Paginated list of exports.
    """
    # Get total count - exports belong to user via run -> job -> user
    count_stmt = (
        select(func.count(Export.id))
        .select_from(Export)
        .join(Run, Export.run_id == Run.id, isouter=True)
        .join(Job, Run.job_id == Job.id, isouter=True)
        .where(Job.user_id == current_user.id)
    )
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0
    
    # Get exports
    stmt = (
        select(Export)
        .join(Run, Export.run_id == Run.id, isouter=True)
        .join(Job, Run.job_id == Job.id, isouter=True)
        .where(Job.user_id == current_user.id)
        .order_by(Export.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    exports = result.scalars().all()
    
    export_responses = [ExportResponse.model_validate(e) for e in exports]
    
    return ExportListResponse(exports=export_responses, total=total)


@router.get(
    "/{export_id}",
    response_model=ExportResponse,
    summary="Get export details",
)
async def get_export(
    export_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExportResponse:
    """Get details of a specific export.
    
    Args:
        export_id: The export's unique identifier.
        db: Database session.
        current_user: The authenticated user.
        
    Returns:
        ExportResponse: The export data.
        
    Raises:
        HTTPException 404: If export not found or doesn't belong to user.
    """
    stmt = (
        select(Export)
        .join(Run, Export.run_id == Run.id, isouter=True)
        .join(Job, Run.job_id == Job.id, isouter=True)
        .where(Export.id == export_id, Job.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    export = result.scalar_one_or_none()
    
    if not export:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export not found",
        )
    
    return ExportResponse.model_validate(export)


@router.get(
    "/{export_id}/download",
    summary="Download export file",
)
async def download_export(
    export_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: StorageManager = Depends(get_storage),
) -> FileResponse:
    """Download an export file.
    
    Args:
        export_id: The export's unique identifier.
        db: Database session.
        current_user: The authenticated user.
        storage: Storage manager for file operations.
        
    Returns:
        FileResponse: The export file for download.
        
    Raises:
        HTTPException 404: If export or file not found.
    """
    stmt = (
        select(Export)
        .join(Run, Export.run_id == Run.id, isouter=True)
        .join(Job, Run.job_id == Job.id, isouter=True)
        .where(Export.id == export_id, Job.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    export = result.scalar_one_or_none()
    
    if not export:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export not found",
        )
    
    # Check if file exists
    if not storage.file_exists(export.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export file not found",
        )
    resolved_file_path = storage.resolve_path(export.file_path)
    storage_root = settings.STORAGE_ROOT.resolve()
    resolved_file_path_str = str(resolved_file_path)
    storage_root_str = str(storage_root)
    storage_root_prefix = f"{storage_root_str}/"
    if not (
        resolved_file_path_str == storage_root_str
        or resolved_file_path_str.startswith(storage_root_prefix)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid export file path",
        )
    
    # Determine media type and filename
    media_types = {
        "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "pdf": "application/pdf",
        "word": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "json": "application/json",
    }
    extensions = {
        "excel": ".xlsx",
        "pdf": ".pdf",
        "word": ".docx",
        "json": ".json",
    }
    
    media_type = media_types.get(export.format, "application/octet-stream")
    extension = extensions.get(export.format, "")
    filename = f"export_{export_id}{extension}"
    
    return FileResponse(
        path=resolved_file_path,
        filename=filename,
        media_type=media_type,
    )


@router.post(
    "/download",
    summary="Download multiple exports",
)
async def download_multiple_exports(
    export_ids: List[UUID],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: StorageManager = Depends(get_storage),
):
    """Download multiple exports as a ZIP file.
    
    Args:
        export_ids: List of export IDs to download.
        db: Database session.
        current_user: The authenticated user.
        storage: Storage manager for file operations.
        
    Returns:
        FileResponse: ZIP file containing all requested exports.
        
    Raises:
        HTTPException 404: If any export not found or doesn't belong to user.
    """
    if not export_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one export ID must be provided",
        )

    # De-duplicate while preserving input order.
    unique_export_ids = list(dict.fromkeys(export_ids))

    # Fetch all requested exports in a single query and verify ownership.
    stmt = (
        select(Export)
        .join(Run, Export.run_id == Run.id, isouter=True)
        .join(Job, Run.job_id == Job.id, isouter=True)
        .where(Export.id.in_(unique_export_ids), Job.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    exports = result.scalars().all()
    exports_by_id = {export.id: export for export in exports}

    if len(exports_by_id) != len(unique_export_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more exports were not found",
        )

    storage_root = settings.STORAGE_ROOT.resolve()
    storage_root_str = str(storage_root)
    storage_root_prefix = f"{storage_root_str}/"

    # Create ZIP file with all exports
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for export_id in unique_export_ids:
            export = exports_by_id[export_id]
            if not export.file_path or not storage.file_exists(export.file_path):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Export file for {export_id} not found",
                )

            resolved_file_path = storage.resolve_path(export.file_path)
            resolved_file_path_str = str(resolved_file_path)
            if not (
                resolved_file_path_str == storage_root_str
                or resolved_file_path_str.startswith(storage_root_prefix)
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid export file path for {export_id}",
                )
            if not resolved_file_path.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Export file for {export_id} not found",
                )

            try:
                file_content = storage.read_file(export.file_path)
                suffix = Path(export.file_path).suffix
                arcname = f"{export.format}_{export_id}{suffix}"
                zip_file.writestr(arcname, file_content)
            except Exception as e:
                logger.warning(f"Failed to add export {export_id} to ZIP: {e}")
    
    zip_buffer.seek(0)
    
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"exports_{len(export_ids)}_files_{timestamp}.zip"
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )




@router.delete(
    "/{export_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an export",
)
async def delete_export(
    export_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: StorageManager = Depends(get_storage),
) -> None:
    """Delete an export and its associated file."""

    stmt = (
        select(Export)
        .join(Run, Export.run_id == Run.id)
        .join(Job, Run.job_id == Job.id)
        .where(Export.id == export_id, Job.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    export = result.scalar_one_or_none()
    
    if not export:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export not found",
        )
    
    # Delete the export file from storage
    if export.file_path and storage.file_exists(export.file_path):
        try:
            storage.delete_file(export.file_path)
        except Exception:
            pass
    
    # Delete the export record from database
    await db.delete(export)
    await db.commit()

@router.get(
    "/stats",
    summary="Get export statistics",
)
async def get_export_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: StorageManager = Depends(get_storage),
):
    """Get export statistics for the current user."""
    return await ExportManagementService.get_export_stats(db, storage, current_user.id)
