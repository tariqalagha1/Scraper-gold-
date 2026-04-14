"""Diagnostics service for system diagnostics.

Provides business logic for diagnostics functionality.
"""
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.orchestrator.diagnostics_orchestrator import DiagnosticsOrchestrator

logger = get_logger("app.services.diagnostics_service")


class DiagnosticsService:
    """Service for diagnostics operations."""

    @staticmethod
    async def get_system_diagnostics(db: AsyncSession) -> Dict[str, Any]:
        """Get system diagnostics."""
        orchestrator = DiagnosticsOrchestrator(db)
        return await orchestrator.get_system_diagnostics()

    @staticmethod
    async def get_demo_overview(db: AsyncSession) -> Dict[str, Any]:
        """Get demo overview data."""
        orchestrator = DiagnosticsOrchestrator(db)
        return await orchestrator.get_demo_overview()
