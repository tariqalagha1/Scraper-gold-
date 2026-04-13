"""Dashboard service for dashboard operations.

Provides business logic for dashboard functionality.
"""
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.orchestrator.dashboard_orchestrator import DashboardOrchestrator

logger = get_logger("app.services.dashboard_service")


class DashboardService:
    """Service for dashboard operations."""

    @staticmethod
    async def get_dashboard_overview(db: AsyncSession, user_id: UUID) -> Dict[str, Any]:
        """Get dashboard overview for user."""
        orchestrator = DashboardOrchestrator(db)
        return await orchestrator.get_dashboard_overview(user_id)

    @staticmethod
    async def get_recent_activity(db: AsyncSession, user_id: UUID, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent activity for user."""
        orchestrator = DashboardOrchestrator(db)
        return await orchestrator.get_recent_activity(user_id, limit)
