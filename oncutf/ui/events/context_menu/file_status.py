"""Module: file_status.py

Author: Michael Economou
Date: 2026-01-01

File status checking utilities for context menu operations.
Helper methods for checking metadata, hash, and other file status information.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from oncutf.utils.filesystem.file_status_helpers import (
    get_metadata_cache_entry,
    has_hash,
    has_metadata,
)
from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.models.file_item import FileItem

logger = get_cached_logger(__name__)


class FileStatusHelpers:
    """Helper methods for checking file status (metadata, hash, etc.)."""

    def __init__(self, parent_window: Any) -> None:
        """Initialize file status helpers with parent window reference."""
        self.parent_window = parent_window

    def _file_has_metadata(self, file_item: FileItem) -> bool:
        """Check if a file has metadata in cache."""
        return has_metadata(file_item.full_path)

    def _file_has_hash(self, file_item: FileItem) -> bool:
        """Check if a file has hash in cache."""
        return has_hash(file_item.full_path)

    def _file_has_metadata_type(self, file_item: FileItem, extended: bool) -> bool:
        """Check if a file has the specified type of metadata (basic or extended)."""
        if not has_metadata(file_item.full_path):
            return False

        entry = get_metadata_cache_entry(file_item.full_path)
        if entry and hasattr(entry, "is_extended"):
            return bool(entry.is_extended) == extended
        return not extended  # If no is_extended flag, assume basic metadata

    def check_files_status(
        self,
        files: list[FileItem] | None = None,
        check_type: str = "metadata",
        extended: bool = False,
        scope: str = "selected",
    ) -> dict[str, Any]:
        """Unified file status checking for metadata and hash operations.

        Args:
            files: List of files to check (None for all files)
            check_type: 'metadata' or 'hash'
            extended: For metadata checks, whether to check for extended metadata
            scope: 'selected' or 'all' (used when files is None)

        Returns:
            dict with status information

        """
        if files is None:
            if scope == "all" and hasattr(self.parent_window, "file_model"):
                files = self.parent_window.file_model.files or []
            else:
                files = []

        if not files:
            return {
                "has_status": False,
                "count": 0,
                "total": 0,
                "files_with_status": [],
                "files_without_status": [],
            }

        files_with_status: list[FileItem] = []
        files_without_status: list[FileItem] = []

        for file_item in files:
            if check_type == "metadata":
                if extended:
                    has_status = self._file_has_metadata_type(file_item, extended=True)
                else:
                    has_status = self._file_has_metadata_type(
                        file_item, extended=False
                    ) or self._file_has_metadata_type(file_item, extended=True)
            elif check_type == "hash":
                has_status = self._file_has_hash(file_item)
            else:
                has_status = False

            if has_status:
                files_with_status.append(file_item)
            else:
                files_without_status.append(file_item)

        return {
            "has_status": len(files_with_status) == len(files),
            "count": len(files_with_status),
            "total": len(files),
            "files_with_status": files_with_status,
            "files_without_status": files_without_status,
        }

    def get_files_without_metadata(
        self,
        files: list[FileItem] | None = None,
        extended: bool = False,
        scope: str = "selected",
    ) -> list[FileItem]:
        """Get list of files that don't have metadata."""
        status = self.check_files_status(
            files=files, check_type="metadata", extended=extended, scope=scope
        )
        result: list[FileItem] = status["files_without_status"]
        return result

    def get_files_without_hashes(
        self, files: list[FileItem] | None = None, scope: str = "selected"
    ) -> list[FileItem]:
        """Get list of files that don't have hash values."""
        status = self.check_files_status(files=files, check_type="hash", scope=scope)
        result: list[FileItem] = status["files_without_status"]
        return result

    def _get_simple_metadata_analysis(self) -> dict[str, Any]:
        """Get simple metadata analysis for all files without detailed scanning."""
        return {
            "enable_fast_selected": True,
            "enable_extended_selected": True,
            "fast_label": "Load Fast Metadata",
            "extended_label": "Load Extended Metadata",
            "fast_tooltip": "Load fast metadata for all files",
            "extended_tooltip": "Load extended metadata for all files",
        }

    def _get_simple_hash_analysis(self) -> dict[str, Any]:
        """Get simple hash analysis for all files without detailed scanning."""
        return {
            "enable_selected": True,
            "selected_label": "Calculate checksums for all files",
            "selected_tooltip": "Calculate checksums for all files",
        }
