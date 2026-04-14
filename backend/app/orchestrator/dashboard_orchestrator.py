"""Dashboard orchestrator for workflow dashboard enhancements.

Handles dashboard data aggregation and processing.
"""
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.export import Export
from app.models.job import Job
from app.models.run import Run
from app.models.user import User

logger = get_logger("app.orchestrator.dashboard_orchestrator")


class DashboardOrchestrator:
    """Orchestrator for dashboard operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard_overview(self, user_id: UUID) -> Dict[str, Any]:
        """Get dashboard overview data."""
        # Get job counts
        job_query = select(
            func.count(Job.id).label("total_jobs"),
            func.count(func.nullif(Job.status, "completed")).label("active_jobs"),
        ).where(Job.user_id == user_id)

        job_result = await self.db.execute(job_query)
        job_stats = job_result.first()

        # Get run counts
        run_query = select(
            func.count(Run.id).label("total_runs"),
            func.sum(case((Run.status == "completed", 1), else_=0)).label("completed_runs"),
            func.sum(case((Run.status == "running", 1), else_=0)).label("running_runs"),
            func.sum(case((Run.status == "failed", 1), else_=0)).label("failed_runs"),
        ).join(Job).where(Job.user_id == user_id)

        run_result = await self.db.execute(run_query)
        run_stats = run_result.first()

        # Get export counts
        export_query = select(
            func.count(Export.id).label("total_exports"),
        ).join(Run).join(Job).where(Job.user_id == user_id)

        export_result = await self.db.execute(export_query)
        export_stats = export_result.first()

        return {
            "jobs": {
                "total": job_stats.total_jobs or 0,
                "active": job_stats.active_jobs or 0,
            },
            "runs": {
                "total": run_stats.total_runs or 0,
                "completed": run_stats.completed_runs or 0,
                "running": run_stats.running_runs or 0,
                "failed": run_stats.failed_runs or 0,
            },
            "exports": {
                "total": export_stats.total_exports or 0,
            },
        }

    async def get_recent_activity(self, user_id: UUID, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent user activity."""
        # Combine runs, jobs, exports into activity timeline
        activities = []

        # Recent runs
        run_query = select(Run, Job.name.label("job_name")).join(Job).where(
            Job.user_id == user_id
        ).order_by(Run.created_at.desc()).limit(limit)

        run_results = await self.db.execute(run_query)
        for run, job_name in run_results:
            activities.append({
                "id": str(run.id),
                "type": "run",
                "action": f"Run started for job '{job_name}'",
                "status": run.status,
                "timestamp": run.created_at.isoformat(),
            })

        # Recent exports
        export_query = select(Export, Job.name.label("job_name")).join(Run).join(Job).where(
            Job.user_id == user_id
        ).order_by(Export.created_at.desc()).limit(limit)

        export_results = await self.db.execute(export_query)
        for export, job_name in export_results:
            activities.append({
                "id": str(export.id),
                "type": "export",
                "action": f"Export created for job '{job_name}' in {export.format} format",
                "status": "completed",
                "timestamp": export.created_at.isoformat(),
            })

        # Sort by timestamp and limit
        activities.sort(key=lambda x: x["timestamp"], reverse=True)
        return activities[:limit]
