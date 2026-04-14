"""Export orchestrator for export management.

Handles export operations including listing, downloading, and status tracking.
"""
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.export import Export
from app.models.job import Job
from app.models.run import Run
from app.models.user import User
from app.storage.manager import StorageManager

logger = get_logger("app.orchestrator.export_orchestrator")


class ExportOrchestrator:
    """Orchestrator for export operations."""

    def __init__(self, db: AsyncSession, storage: StorageManager):
        self.db = db
        self.storage = storage

    async def get_user_exports(
        self,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0,
        format_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get user's exports with filtering."""
        query = select(
            Export,
            Job.name.label("job_name"),
            Run.status.label("run_status")
        ).join(Run).join(Job).where(Job.user_id == user_id)

        if format_filter:
            query = query.where(Export.format == format_filter)

        query = query.order_by(Export.created_at.desc()).offset(offset).limit(limit)

        results = await self.db.execute(query)
        exports = []
        for export, job_name, run_status in results:
            exports.append({
                "id": str(export.id),
                "job_name": job_name,
                "format": export.format,
                "file_size": export.file_size,
                "status": "completed",  # Exports are always completed when created
                "run_status": run_status,
                "created_at": export.created_at.isoformat(),
                "file_path": export.file_path,
            })

        # Get total count
        count_query = select(func.count(Export.id)).join(Run).join(Job).where(Job.user_id == user_id)
        if format_filter:
            count_query = count_query.where(Export.format == format_filter)

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return {
            "exports": exports,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def get_export_download_url(self, user_id: UUID, export_id: UUID) -> Optional[str]:
        """Get download URL for an export."""
        query = select(Export).join(Run).join(Job).where(
            Export.id == export_id,
            Job.user_id == user_id
        )

        result = await self.db.execute(query)
        export = result.first()
        if export:
            export = export[0]
            # Generate download URL
            return f"/api/v1/exports/{export_id}/download"
        return None

    async def get_export_stats(self, user_id: UUID) -> Dict[str, Any]:
        """Get export statistics for user."""
        query = select(
            func.count(Export.id).label("total_exports"),
            func.sum(Export.file_size).label("total_size"),
            Export.format,
            func.count(Export.format).label("count")
        ).join(Run).join(Job).where(Job.user_id == user_id).group_by(Export.format)

        results = await self.db.execute(query)
        format_stats = {}
        total_exports = 0
        total_size = 0

        for result in results:
            format_stats[result.format] = result.count
            total_exports += result.count
            total_size += result.total_size or 0

        return {
            "formats": format_stats,
            "total_exports": total_exports,
            "total_size": total_size,
        }
