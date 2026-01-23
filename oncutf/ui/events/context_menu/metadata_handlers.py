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
    from oncutf.models.file_item import FileItem

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
            dict: Analysis results with enable/disable logic for metadata menu items

        """
        if not files:
            return {
                "enable_fast_selected": False,
                "enable_extended_selected": False,
                "fast_tooltip": "No files selected",
                "extended_tooltip": "No files selected",
            }

        start_time = time.time()

        files_no_metadata: list[FileItem] = []
        files_fast_metadata: list[FileItem] = []
        files_extended_metadata: list[FileItem] = []

        try:
            metadata_cache = getattr(self.parent_window, "metadata_cache", None)

            if metadata_cache and hasattr(metadata_cache, "get_entries_batch"):
                file_paths = [file_item.full_path for file_item in files]
                batch_entries = metadata_cache.get_entries_batch(file_paths)

                for file_item in files:
                    cache_entry = batch_entries.get(file_item.full_path)

                    if cache_entry and hasattr(cache_entry, "data") and cache_entry.data:
                        if hasattr(cache_entry, "is_extended") and cache_entry.is_extended:
                            files_extended_metadata.append(file_item)
                        else:
                            files_fast_metadata.append(file_item)
                    else:
                        files_no_metadata.append(file_item)
            elif metadata_cache:
                for file_item in files:
                    cache_entry = metadata_cache.get_entry(file_item.full_path)

                    if cache_entry and hasattr(cache_entry, "data") and cache_entry.data:
                        if hasattr(cache_entry, "is_extended") and cache_entry.is_extended:
                            files_extended_metadata.append(file_item)
                        else:
                            files_fast_metadata.append(file_item)
                    else:
                        files_no_metadata.append(file_item)
            else:
                files_no_metadata.extend(files)

            elapsed_time = time.time() - start_time
            logger.debug(
                "[EventHandler] Batch metadata check completed in %.3fs: "
                "%d no metadata, %d fast, %d extended",
                elapsed_time,
                len(files_no_metadata),
                len(files_fast_metadata),
                len(files_extended_metadata),
            )

        except Exception as e:
            logger.warning("[EventHandler] Metadata state analysis failed: %s", e)
            files_no_metadata = list(files)
            files_fast_metadata = []
            files_extended_metadata = []

        total = len(files)
        no_metadata_count = len(files_no_metadata)
        fast_metadata_count = len(files_fast_metadata)
        extended_metadata_count = len(files_extended_metadata)

        enable_fast_selected = (
            no_metadata_count > 0 or fast_metadata_count > 0
        ) and extended_metadata_count == 0

        enable_extended_selected = (
            no_metadata_count > 0 or fast_metadata_count > 0 or extended_metadata_count > 0
        )

        # Fast metadata tooltip
        if extended_metadata_count > 0:
            fast_tooltip = (
                f"Cannot load fast metadata: {extended_metadata_count} file(s) "
                "already have extended metadata"
            )
            enable_fast_selected = False
        elif no_metadata_count == total:
            fast_tooltip = f"Load fast metadata for {total} file(s)"
        elif no_metadata_count == 0 and fast_metadata_count == total:
            fast_tooltip = f"All {total} file(s) already have fast metadata"
            enable_fast_selected = False
        else:
            need_fast = no_metadata_count
            fast_tooltip = f"Load fast metadata for {need_fast} of {total} file(s) that need it"

        # Extended metadata tooltip
        if extended_metadata_count == total:
            extended_tooltip = f"All {total} file(s) already have extended metadata"
            enable_extended_selected = False
        elif extended_metadata_count == 0:
            if fast_metadata_count > 0:
                extended_tooltip = (
                    f"Upgrade {fast_metadata_count} file(s) to extended metadata "
                    f"and load for {no_metadata_count} file(s)"
                )
            else:
                extended_tooltip = f"Load extended metadata for {total} file(s)"
        else:
            need_extended = total - extended_metadata_count
            extended_tooltip = (
                f"Load/upgrade extended metadata for {need_extended} of {total} file(s)"
            )

        return {
            "enable_fast_selected": enable_fast_selected,
            "enable_extended_selected": enable_extended_selected,
            "fast_label": "Load Fast Metadata",
            "extended_label": "Load Extended Metadata",
            "fast_tooltip": fast_tooltip,
            "extended_tooltip": extended_tooltip,
            "stats": {
                "total": total,
                "no_metadata": no_metadata_count,
                "fast_metadata": fast_metadata_count,
                "extended_metadata": extended_metadata_count,
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
