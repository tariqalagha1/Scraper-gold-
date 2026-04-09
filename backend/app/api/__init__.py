"""API layer package for FastAPI routes.

Exports the main API router for inclusion in the FastAPI application.
"""
from app.api.v1 import v1_router

__all__ = ["v1_router"]
