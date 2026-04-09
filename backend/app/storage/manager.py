"""Storage manager for file operations.

Provides a centralized interface for saving, retrieving, and deleting
files in the storage system including raw HTML, screenshots, processed
data, and exports.
"""
import hashlib
import json
import uuid
from pathlib import Path
from typing import Any, Optional, Union
from urllib.parse import urlparse

from app.core.logging import get_logger
from app.storage.paths import (
    EXPORTS_DIR,
    PROCESSED_DIR,
    RAW_HTML_DIR,
    SCREENSHOTS_DIR,
    ensure_storage_dirs_exist,
)

logger = get_logger(__name__)


class StorageManager:
    """Manager for file storage operations.
    
    Provides methods for saving and retrieving various types of files
    used in the scraping process.
    
    Example:
        storage = StorageManager()
        path = storage.save_raw_html(run_id, url, html_content)
        content = storage.get_file(path)
    """

    def __init__(self) -> None:
        """Initialize storage manager and ensure directories exist."""
        ensure_storage_dirs_exist()

    @staticmethod
    def _url_to_filename(url: str) -> str:
        """Convert URL to a safe filename.
        
        Args:
            url: The URL to convert.
            
        Returns:
            A safe filename derived from the URL.
        """
        parsed = urlparse(url)
        # Create a hash of the full URL for uniqueness
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        # Get domain and path for readability
        domain = parsed.netloc.replace(".", "_").replace(":", "_")
        path = parsed.path.replace("/", "_").strip("_")[:30] or "index"
        return f"{domain}_{path}_{url_hash}"

    @staticmethod
    def _ensure_dir(path: Path) -> None:
        """Ensure directory exists, creating it if necessary.
        
        Args:
            path: Path to the directory.
        """
        path.mkdir(parents=True, exist_ok=True)

    def save_raw_html(
        self,
        run_id: Union[str, uuid.UUID],
        url: str,
        html_content: str,
        filename_suffix: str = "",
    ) -> str:
        """Save raw HTML content to storage.
        
        Args:
            run_id: The run's UUID.
            url: Source URL of the HTML.
            html_content: The HTML content to save.
            
        Returns:
            Relative path to the saved file.
        """
        run_dir = RAW_HTML_DIR / str(run_id)
        self._ensure_dir(run_dir)
        
        suffix = f"_{filename_suffix}" if filename_suffix else ""
        filename = f"{self._url_to_filename(url)}{suffix}.html"
        file_path = run_dir / filename
        
        file_path.write_text(html_content, encoding="utf-8")
        
        logger.info(
            f"Saved raw HTML for {url}",
            action="save_raw_html",
            extra={"run_id": str(run_id), "path": str(file_path)},
        )
        
        return str(file_path.relative_to(RAW_HTML_DIR.parent))

    def save_screenshot(
        self,
        run_id: Union[str, uuid.UUID],
        url: str,
        image_bytes: bytes,
        filename_suffix: str = "",
    ) -> str:
        """Save screenshot image to storage.
        
        Args:
            run_id: The run's UUID.
            url: Source URL of the screenshot.
            image_bytes: The screenshot image as bytes.
            
        Returns:
            Relative path to the saved file.
        """
        run_dir = SCREENSHOTS_DIR / str(run_id)
        self._ensure_dir(run_dir)
        
        suffix = f"_{filename_suffix}" if filename_suffix else ""
        filename = f"{self._url_to_filename(url)}{suffix}.png"
        file_path = run_dir / filename
        
        file_path.write_bytes(image_bytes)
        
        logger.info(
            f"Saved screenshot for {url}",
            action="save_screenshot",
            extra={"run_id": str(run_id), "path": str(file_path)},
        )
        
        return str(file_path.relative_to(SCREENSHOTS_DIR.parent))

    def save_processed(
        self,
        run_id: Union[str, uuid.UUID],
        data: Any,
        filename: str,
    ) -> str:
        """Save processed data as JSON to storage.
        
        Args:
            run_id: The run's UUID.
            data: The data to save (will be JSON serialized).
            filename: Name for the output file (without extension).
            
        Returns:
            Relative path to the saved file.
        """
        run_dir = PROCESSED_DIR / str(run_id)
        self._ensure_dir(run_dir)
        
        # Ensure filename has .json extension
        if not filename.endswith(".json"):
            filename = f"{filename}.json"
        
        file_path = run_dir / filename
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(
            f"Saved processed data to {filename}",
            action="save_processed",
            extra={"run_id": str(run_id), "path": str(file_path)},
        )
        
        return str(file_path.relative_to(PROCESSED_DIR.parent))

    def save_markdown_snapshot(
        self,
        run_id: Union[str, uuid.UUID],
        markdown_content: str,
        filename: str = "semantic_markdown",
    ) -> str:
        """Save semantic markdown content to the processed directory."""
        run_dir = PROCESSED_DIR / str(run_id)
        self._ensure_dir(run_dir)

        safe_name = str(filename or "semantic_markdown").strip() or "semantic_markdown"
        if not safe_name.endswith(".md"):
            safe_name = f"{safe_name}.md"

        file_path = run_dir / safe_name
        file_path.write_text(str(markdown_content or ""), encoding="utf-8")

        logger.info(
            f"Saved markdown snapshot to {safe_name}",
            action="save_markdown_snapshot",
            extra={"run_id": str(run_id), "path": str(file_path)},
        )

        return str(file_path.relative_to(PROCESSED_DIR.parent))

    def save_export(
        self,
        export_id: Union[str, uuid.UUID],
        format: str,
        file_bytes: bytes,
    ) -> str:
        """Save export file to storage.
        
        Args:
            export_id: The export's UUID.
            format: Export format (excel, pdf, word).
            file_bytes: The file content as bytes.
            
        Returns:
            Relative path to the saved file.
        """
        self._ensure_dir(EXPORTS_DIR)
        
        # Map format to extension
        extensions = {
            "excel": ".xlsx",
            "pdf": ".pdf",
            "word": ".docx",
        }
        ext = extensions.get(format.lower(), f".{format}")
        
        filename = f"{export_id}{ext}"
        file_path = EXPORTS_DIR / filename
        
        file_path.write_bytes(file_bytes)
        
        logger.info(
            f"Saved export file {filename}",
            action="save_export",
            extra={"export_id": str(export_id), "format": format, "path": str(file_path)},
        )
        
        return str(file_path.relative_to(EXPORTS_DIR.parent))

    def get_file(self, path: str) -> bytes:
        """Read file content from storage.
        
        Args:
            path: Path to the file (relative or absolute).
            
        Returns:
            File content as bytes.
            
        Raises:
            FileNotFoundError: If the file doesn't exist.
        """
        file_path = Path(path)
        
        # If relative path, try to resolve from storage root
        if not file_path.is_absolute():
            file_path = RAW_HTML_DIR.parent / path
        
        if not file_path.exists():
            logger.error(
                f"File not found: {path}",
                action="get_file",
                error_data={"path": str(path)},
            )
            raise FileNotFoundError(f"File not found: {path}")

        return file_path.read_bytes()

    def resolve_path(self, path: str) -> Path:
        """Resolve a storage path to an absolute filesystem path."""
        file_path = Path(path)
        if not file_path.is_absolute():
            file_path = RAW_HTML_DIR.parent / path
        return file_path.resolve()

    def get_file_text(self, path: str, encoding: str = "utf-8") -> str:
        """Read file content as text from storage.
        
        Args:
            path: Path to the file (relative or absolute).
            encoding: Text encoding to use.
            
        Returns:
            File content as string.
            
        Raises:
            FileNotFoundError: If the file doesn't exist.
        """
        return self.get_file(path).decode(encoding)

    def delete_file(self, path: str) -> bool:
        """Delete a file from storage.
        
        Args:
            path: Path to the file (relative or absolute).
            
        Returns:
            True if file was deleted, False if it didn't exist.
        """
        file_path = Path(path)
        
        # If relative path, try to resolve from storage root
        if not file_path.is_absolute():
            file_path = RAW_HTML_DIR.parent / path
        
        if file_path.exists():
            file_path.unlink()
            logger.info(
                f"Deleted file: {path}",
                action="delete_file",
                extra={"path": str(path)},
            )
            return True
        
        logger.warning(
            f"File not found for deletion: {path}",
            action="delete_file",
            extra={"path": str(path)},
        )
        return False

    def file_exists(self, path: str) -> bool:
        """Check if a file exists in storage.
        
        Args:
            path: Path to the file (relative or absolute).
            
        Returns:
            True if file exists, False otherwise.
        """
        file_path = Path(path)
        
        if not file_path.is_absolute():
            file_path = RAW_HTML_DIR.parent / path
        
        return file_path.exists()

    def get_file_size(self, path: str) -> Optional[int]:
        """Get the size of a file in bytes.
        
        Args:
            path: Path to the file.
            
        Returns:
            File size in bytes, or None if file doesn't exist.
        """
        file_path = Path(path)
        
        if not file_path.is_absolute():
            file_path = RAW_HTML_DIR.parent / path
        
        if file_path.exists():
            return file_path.stat().st_size
        return None


# Global storage manager instance
storage_manager = StorageManager()
