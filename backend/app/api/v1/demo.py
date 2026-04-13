"""Demo API endpoints.

Provides demo overview data for stakeholder dashboard.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.services.diagnostics_service import DiagnosticsService

router = APIRouter()


@router.get("/overview")
async def get_demo_overview(
    db: AsyncSession = Depends(get_db),
):
    """Get demo overview data."""
    return await DiagnosticsService.get_demo_overview(db)