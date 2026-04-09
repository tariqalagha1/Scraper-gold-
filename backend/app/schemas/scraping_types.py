"""Scraping type definitions for user-selected data extraction modes.

Defines the available scraping data types that users can select when
configuring a scraping job. Each type determines what content will be
extracted from target websites.
"""
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ScrapingType(str, Enum):
    """Enumeration of supported scraping data types.
    
    Each type represents a specific extraction strategy:
    - GENERAL: Extract all visible text and links
    - PDF: Find and download PDF files
    - WORD: Find and download Word documents
    - EXCEL: Find and download Excel spreadsheets
    - IMAGES: Extract and download images
    - VIDEOS: Detect and extract video content
    - STRUCTURED: Extract tables, lists, and structured data
    """
    GENERAL = "general"
    PDF = "pdf"
    WORD = "word"
    EXCEL = "excel"
    IMAGES = "images"
    VIDEOS = "videos"
    STRUCTURED = "structured"


class ScrapingTypeInfo(BaseModel):
    """Schema for scraping type information with user-friendly descriptions.
    
    Attributes:
        type: The scraping type enum value
        label: User-friendly display label
        description: Detailed description of what this type extracts
    """
    type: ScrapingType
    label: str
    description: str


# Registry of all scraping types with user-friendly descriptions
# Used by the frontend to display options and by the backend for validation
SCRAPING_TYPE_REGISTRY: list[ScrapingTypeInfo] = [
    ScrapingTypeInfo(
        type=ScrapingType.GENERAL,
        label="General Data",
        description="Extract all visible text and links from web pages"
    ),
    ScrapingTypeInfo(
        type=ScrapingType.PDF,
        label="PDF Documents",
        description="Find and download PDF files from the target site"
    ),
    ScrapingTypeInfo(
        type=ScrapingType.WORD,
        label="Word Documents",
        description="Find and download Word (.docx) files from the target site"
    ),
    ScrapingTypeInfo(
        type=ScrapingType.EXCEL,
        label="Excel Spreadsheets",
        description="Find and download Excel (.xlsx) files from the target site"
    ),
    ScrapingTypeInfo(
        type=ScrapingType.IMAGES,
        label="Images",
        description="Extract and download images from web pages"
    ),
    ScrapingTypeInfo(
        type=ScrapingType.VIDEOS,
        label="Videos",
        description="Detect and extract video URLs and embedded videos"
    ),
    ScrapingTypeInfo(
        type=ScrapingType.STRUCTURED,
        label="Structured Data",
        description="Extract tables, lists, and structured content into organized formats"
    ),
]


def get_scraping_type_info(scrape_type: ScrapingType) -> ScrapingTypeInfo | None:
    """Get the info for a specific scraping type.
    
    Args:
        scrape_type: The scraping type to look up
        
    Returns:
        ScrapingTypeInfo if found, None otherwise
    """
    for info in SCRAPING_TYPE_REGISTRY:
        if info.type == scrape_type:
            return info
    return None


class ScrapingConfig(BaseModel):
    """User's scraping configuration for a job.
    
    This model captures all user-configurable options for a scraping job,
    including what type of content to extract and how to navigate the target site.
    
    Attributes:
        scrape_type: Type of content to extract (default: GENERAL)
        max_pages: Maximum number of pages to scrape (1-1000)
        follow_pagination: Whether to follow pagination links
        include_screenshots: Whether to capture screenshots of pages
        custom_selectors: Optional CSS selectors for custom extraction
        respect_robots_txt: Whether to respect robots.txt directives
        max_depth: Maximum depth for link following (0 = only start URL)
        request_delay: Delay between requests in seconds
    """
    scrape_type: ScrapingType = Field(
        default=ScrapingType.GENERAL,
        description="Type of content to extract"
    )
    max_pages: int = Field(
        default=10,
        ge=1,
        le=1000,
        description="Maximum number of pages to scrape"
    )
    follow_pagination: bool = Field(
        default=True,
        description="Whether to follow pagination links"
    )
    include_screenshots: bool = Field(
        default=False,
        description="Whether to capture page screenshots"
    )
    custom_selectors: Optional[dict[str, str]] = Field(
        default=None,
        description="Custom CSS selectors for extraction"
    )
    respect_robots_txt: bool = Field(
        default=True,
        description="Whether to respect robots.txt directives"
    )
    max_depth: int = Field(
        default=2,
        ge=0,
        le=10,
        description="Maximum link following depth"
    )
    request_delay: float = Field(
        default=1.0,
        ge=0.0,
        le=30.0,
        description="Delay between requests in seconds"
    )
    
    def to_dict(self) -> dict:
        """Convert config to dictionary format.
        
        Returns:
            Dictionary representation of the config
        """
        return self.model_dump()
