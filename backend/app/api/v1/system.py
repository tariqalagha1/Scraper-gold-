"""System API endpoints.

Provides system diagnostics and health information.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.execution_contract import build_system_capabilities
from app.services.diagnostics_service import DiagnosticsService

router = APIRouter()


@router.get("/diagnostics")
async def get_system_diagnostics(
    db: AsyncSession = Depends(get_db),
):
    """Get system diagnostics information."""
    return await DiagnosticsService.get_system_diagnostics(db)


@router.get("/capabilities")
async def get_system_capabilities():
    """Return configurable execution capabilities for contract builders."""
    return build_system_capabilities()
