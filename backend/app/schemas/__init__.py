"""Pydantic request/response schemas package.

Provides data validation and serialization schemas for:
- Agent communication (AgentMessage)
- Scraping configuration (ScrapingType, ScrapingConfig)
- API request/response models

Exports:
    AgentMessage: Structured JSON communication format for agents
    AgentMetadata: Metadata included with agent messages
    ScrapingType: Enumeration of supported scraping data types
    ScrapingTypeInfo: Schema for scraping type information
    ScrapingConfig: User's scraping configuration for a job
    SCRAPING_TYPE_REGISTRY: Registry of all scraping types with descriptions
"""
from app.schemas.agent_message import AgentMessage, AgentMetadata
from app.schemas.scraping_types import (
    ScrapingType,
    ScrapingTypeInfo,
    ScrapingConfig,
    SCRAPING_TYPE_REGISTRY,
    get_scraping_type_info,
)

__all__ = [
    # Agent communication
    "AgentMessage",
    "AgentMetadata",
    # Scraping types
    "ScrapingType",
    "ScrapingTypeInfo",
    "ScrapingConfig",
    "SCRAPING_TYPE_REGISTRY",
    "get_scraping_type_info",
]
