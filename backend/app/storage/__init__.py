"""Storage package for the Smart Scraper Platform.

This module exports storage utilities including path constants
and the StorageManager for file operations.
"""
from app.storage.manager import StorageManager, storage_manager
from app.storage.paths import (
    ALL_STORAGE_DIRS,
    EXPORTS_DIR,
    PROCESSED_DIR,
    RAW_HTML_DIR,
    SCREENSHOTS_DIR,
    STORAGE_ROOT,
    ensure_storage_dirs_exist,
    get_run_processed_dir,
    get_run_raw_html_dir,
    get_run_screenshots_dir,
)

__all__ = [
    # Path constants
    "STORAGE_ROOT",
    "RAW_HTML_DIR",
    "SCREENSHOTS_DIR",
    "PROCESSED_DIR",
    "EXPORTS_DIR",
    "ALL_STORAGE_DIRS",
    # Path functions
    "ensure_storage_dirs_exist",
    "get_run_raw_html_dir",
    "get_run_screenshots_dir",
    "get_run_processed_dir",
    # Storage manager
    "StorageManager",
    "storage_manager",
]
