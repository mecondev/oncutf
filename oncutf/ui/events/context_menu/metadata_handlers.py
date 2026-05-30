"""Module: metadata_handlers.py.

Author: Michael Economou
Date: 2026-01-01

Metadata-related context menu handlers.
Analyzes metadata state and provides smart enable/disable logic for metadata operations.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.domain.models.file_item import FileItem

logger = get_cached_logger(__name__)


class MetadataHandlers:
    """Handles metadata-related context menu operations."""

    def __init__(self, parent_window: Any) -> None:
        """Initialize metadata handlers with parent window reference."""
        self.parent_window = parent_window

    def _analyze_metadata_state(self, files: list[FileItem]) -> dict[str, Any]:
        """Analyze the metadata state of files to determine smart metadata menu options.

        Args:
            files: List of FileItem objects to analyze

        Returns:
            dict: Analysis results with enable/disable logic for the metadata menu item

        """
        if not files:
            return {
                "enable_load": False,
                "load_tooltip": "No files selected",
            }

        start_time = time.time()

        files_with_metadata: list[FileItem] = []
        files_without_metadata: list[FileItem] = []

        try:
            metadata_cache = getattr(self.parent_window, "metadata_cache", None)

            if metadata_cache and hasattr(metadata_cache, "get_entries_batch"):
                file_paths = [file_item.full_path for file_item in files]
                batch_entries = metadata_cache.get_entries_batch(file_paths)

                for file_item in files:
                    cache_entry = batch_entries.get(file_item.full_path)
                    if cache_entry and hasattr(cache_entry, "data") and cache_entry.data:
                        files_with_metadata.append(file_item)
                    else:
                        files_without_metadata.append(file_item)

            elif metadata_cache:
                for file_item in files:
                    cache_entry = metadata_cache.get_entry(file_item.full_path)
                    if cache_entry and hasattr(cache_entry, "data") and cache_entry.data:
                        files_with_metadata.append(file_item)
                    else:
                        files_without_metadata.append(file_item)
            else:
                files_without_metadata.extend(files)

            elapsed_time = time.time() - start_time
            logger.debug(
                "[EventHandler] Batch metadata check completed in %.3fs: "
                "%d with metadata, %d without",
                elapsed_time,
                len(files_with_metadata),
                len(files_without_metadata),
            )

        except Exception as e:
            logger.warning("[EventHandler] Metadata state analysis failed: %s", e)
            files_without_metadata = list(files)
            files_with_metadata = []

        total = len(files)
        with_count = len(files_with_metadata)
        without_count = len(files_without_metadata)

        enable_load = without_count > 0

        if without_count == 0:
            load_tooltip = f"All {total} file(s) already have metadata"
        elif with_count == 0:
            load_tooltip = f"Load metadata for {total} file(s)"
        else:
            load_tooltip = f"Load metadata for {without_count} of {total} file(s) that need it"

        return {
            "enable_load": enable_load,
            "load_tooltip": load_tooltip,
            "stats": {
                "total": total,
                "with_metadata": with_count,
                "without_metadata": without_count,
            },
        }

    def _has_metadata_loaded(self, file_item: FileItem) -> bool:
        """Check if a file has metadata loaded in cache."""
        if not self.parent_window or not hasattr(self.parent_window, "metadata_cache"):
            return False

        metadata_entry = self.parent_window.metadata_cache.get_entry(file_item.full_path)
        if metadata_entry and hasattr(metadata_entry, "data") and metadata_entry.data:
            return True

        return hasattr(file_item, "metadata") and bool(file_item.metadata)
