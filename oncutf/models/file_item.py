"""
file_item.py

Author: Michael Economou
Date: 2025-05-01

This module defines the FileItem class, which represents a single file entry
with attributes such as filename, filetype, last modification date, and a checked
state indicating whether the file is selected for renaming. The class is used
within the FileTableModel to manage file entries in a table view.

Classes:
    FileItem: Represents a single file item in the table.
"""

import os
from datetime import datetime

# Initialize Logger
from oncutf.utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class FileItem:
    """
    Represents a file in the application.
    Stores file metadata and handles file operations.
    """

    def __init__(self, path: str, extension: str, modified: datetime):
        self.full_path = path  # Full absolute path
        self.path = path  # Keep for compatibility
        self.extension = extension
        self.modified = modified
        self.filename = os.path.basename(path)  # Just the filename
        self.name = self.filename  # Keep for compatibility
        self.size = 0  # Will be updated later if needed
        self.metadata = {}  # Will store file metadata
        self.metadata_status = "none"  # Track metadata loading status: "none", "loaded", "extended", "modified"
        self.checked = False  # Selection state for UI

        # Load saved color tag from database (hex color or "none")
        # Import here to avoid circular imports and initialization issues
        try:
            from oncutf.core.database.database_manager import get_database_manager
            db_manager = get_database_manager()
            self.color = db_manager.get_color_tag(path)
        except Exception as e:
            logger.warning("[FileItem] Could not load color tag: %s", e)
            self.color = "none"

    def __str__(self) -> str:
        return f"FileItem({self.filename})"

    def __repr__(self) -> str:
        return f"FileItem(full_path='{self.full_path}', extension='{self.extension}', modified='{self.modified}')"

    @classmethod
    def from_path(cls, file_path: str) -> "FileItem":
        """
        Create a FileItem from a file path by auto-detecting properties.

        Args:
            file_path: Full path to the file

        Returns:
            FileItem instance with auto-detected properties
        """

        filename = os.path.basename(file_path)
        _, ext = os.path.splitext(filename)
        extension = ext[1:].lower() if ext.startswith(".") else ""

        # Get modification time
        try:
            mtime = os.path.getmtime(file_path)
            modified = datetime.fromtimestamp(mtime)
        except (OSError, ValueError):
            modified = datetime.fromtimestamp(0)

        # Create the instance
        instance = cls(file_path, extension, modified)

        # Calculate and set the file size
        instance.size = instance._detect_size()

        return instance

    @property
    def has_metadata(self) -> bool:
        logger.debug(
            "[DEBUG] Checking has_metadata for %s | metadata: %s",
            self.filename,
            self.metadata,
            extra={"dev_only": True},
        )
        result = isinstance(self.metadata, dict) and bool(self.metadata)
        logger.debug(
            "[DEBUG] has_metadata result for %s: %s",
            self.filename,
            result,
            extra={"dev_only": True},
        )
        return result

    @property
    def metadata_extended(self) -> bool:
        return isinstance(self.metadata, dict) and self.metadata.get("__extended__") is True

    def _detect_size(self) -> int:
        """
        Attempts to determine the file size in bytes from full_path.
        Returns 0 if file is inaccessible or not found.
        """
        if self.full_path and os.path.exists(self.full_path):
            try:
                return os.path.getsize(self.full_path)
            except Exception:
                logger.warning(
                    "[FileItem] Failed to get size for %s",
                    self.full_path,
                    exc_info=True,
                )
        return 0

    def get_human_readable_size(self) -> str:
        """
        Returns a human-readable string for the file size, e.g. '1.2 GB', '540 MB', '999 KB'.
        Uses cross-platform formatting that respects system locale and conventions.
        """
        from oncutf.utils.file_size_formatter import format_file_size_system_compatible

        return format_file_size_system_compatible(self.size)
