"""Scraping Types API endpoints.

Handles listing available scraping types with their descriptions.
"""
from typing import List

from fastapi import APIRouter

from app.schemas.scraping_types import SCRAPING_TYPE_REGISTRY, ScrapingTypeInfo


router = APIRouter()


@router.get(
    "",
    response_model=List[ScrapingTypeInfo],
    summary="List all available scraping types",
)
async def list_scraping_types() -> List[ScrapingTypeInfo]:
    """List all available scraping types with labels and descriptions.
    
    This endpoint is publicly accessible without authentication.
    Returns all supported scraping types that can be selected when
    creating a new scraping job.
    
    Returns:
        List[ScrapingTypeInfo]: All available scraping types with descriptions.
    """
    return SCRAPING_TYPE_REGISTRY
