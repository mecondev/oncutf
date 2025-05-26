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
from typing import Optional
import os

# Initialize Logger
from utils.logger_helper import get_logger
logger = get_logger(__name__)


class FileItem:
    """
    Represents a single file item in the table.

    Attributes:
        filename (str): The name of the file without the path.
        extension (str): The extension/type of the file (e.g., jpg, png, mp4).
        modified (str): The file's last modification date as a string.
        full_path (Optional[str]): Full path to the file.
        checked (bool): Whether the file is selected for renaming.
        metadata (dict): Optional metadata dictionary for this file.
        size (int): File size in bytes (autodetected from full_path).
    """

    def __init__(self, filename: str, extension: str, modified: str, full_path: Optional[str] = None):
        self.filename = filename
        self.extension = extension
        self.modified = modified
        self.full_path = full_path
        self.checked = True
        self.date = None
        self.metadata = {}
        self.size = self._detect_size()

    @property
    def name(self) -> str:
        return self.filename

    def _detect_size(self) -> int:
        """
        Attempts to determine the file size in bytes from full_path.
        Returns 0 if file is inaccessible or not found.
        """
        if self.full_path and os.path.exists(self.full_path):
            try:
                return os.path.getsize(self.full_path)
            except Exception as e:
                logger.warning(f"[FileItem] Failed to get size for {self.full_path}: {e}")
        return 0

    def get_human_readable_size(self) -> str:
        """
        Returns a human-readable string for the file size, e.g. '1.2 GB', '540 MB', '999 KB'.
        """
        size = self.size
        units = ["B", "KB", "MB", "GB", "TB"]
        index = 0
        while size >= 1024 and index < len(units) - 1:
            size /= 1024.0
            index += 1
        return f"{size:.1f} {units[index]}"

    @property
    def has_metadata(self) -> bool:
        logger.debug(f"[DEBUG] Checking has_metadata for {self.filename}")
        return isinstance(self.metadata, dict) and bool(self.metadata)

    @property
    def metadata_extended(self) -> bool:
        return isinstance(self.metadata, dict) and self.metadata.get('__extended__') is True
