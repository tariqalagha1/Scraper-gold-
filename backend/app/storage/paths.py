"""Storage path constants for the Smart Scraper Platform.

Defines directory paths for storing various types of files
including raw HTML, screenshots, processed data, and exports.
"""
from pathlib import Path

from app.config import settings

# Base storage root
STORAGE_ROOT: Path = Path(settings.STORAGE_ROOT)

# Directory for raw HTML snapshots
RAW_HTML_DIR: Path = STORAGE_ROOT / "raw_html"

# Directory for page screenshots
SCREENSHOTS_DIR: Path = STORAGE_ROOT / "screenshots"

# Directory for processed data files
PROCESSED_DIR: Path = STORAGE_ROOT / "processed"

# Directory for export files (Excel, PDF, Word)
EXPORTS_DIR: Path = STORAGE_ROOT / "exports"

# All storage directories for initialization
ALL_STORAGE_DIRS: list[Path] = [
    RAW_HTML_DIR,
    SCREENSHOTS_DIR,
    PROCESSED_DIR,
    EXPORTS_DIR,
]


def ensure_storage_dirs_exist() -> None:
    """Create all storage directories if they don't exist.
    
    This function should be called during application startup
    to ensure all required storage directories are available.
    """
    for directory in ALL_STORAGE_DIRS:
        directory.mkdir(parents=True, exist_ok=True)


def get_run_raw_html_dir(run_id: str) -> Path:
    """Get the raw HTML directory for a specific run.
    
    Args:
        run_id: The run's UUID as a string.
        
    Returns:
        Path to the run's raw HTML directory.
    """
    return RAW_HTML_DIR / str(run_id)


def get_run_screenshots_dir(run_id: str) -> Path:
    """Get the screenshots directory for a specific run.
    
    Args:
        run_id: The run's UUID as a string.
        
    Returns:
        Path to the run's screenshots directory.
    """
    return SCREENSHOTS_DIR / str(run_id)


def get_run_processed_dir(run_id: str) -> Path:
    """Get the processed data directory for a specific run.
    
    Args:
        run_id: The run's UUID as a string.
        
    Returns:
        Path to the run's processed data directory.
    """
    return PROCESSED_DIR / str(run_id)
