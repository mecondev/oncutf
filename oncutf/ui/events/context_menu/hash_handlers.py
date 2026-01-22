"""Module: hash_handlers.py

Author: Michael Economou
Date: 2026-01-01

Hash-related context menu handlers.
Analyzes hash state and provides smart enable/disable logic for hash operations.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.models.file_item import FileItem

logger = get_cached_logger(__name__)


class HashHandlers:
    """Handles hash-related context menu operations."""

    def __init__(self, parent_window: Any) -> None:
        """Initialize hash handlers with parent window reference."""
        self.parent_window = parent_window

    def _analyze_hash_state(self, files: list[FileItem]) -> dict[str, Any]:
        """Analyze the hash state of files to determine smart hash menu options.

        Args:
            files: List of FileItem objects to analyze

        Returns:
            dict: Analysis results with enable/disable logic for hash menu items

        """
        if not files:
            return {
                "enable_selected": False,
                "enable_all": False,
                "selected_label": "Calculate checksums for selection",
                "all_label": "Calculate checksums for all files",
                "selected_tooltip": "No files selected",
                "all_tooltip": "No files available",
            }

        start_time = time.time()

        files_with_hash: list[FileItem] = []
        files_without_hash: list[FileItem] = []

        try:
            file_paths = [file_item.full_path for file_item in files]

            if hasattr(self.parent_window, "hash_cache") and hasattr(
                self.parent_window.hash_cache, "get_files_with_hash_batch"
            ):
                files_with_hash_paths = self.parent_window.hash_cache.get_files_with_hash_batch(
                    file_paths, "CRC32"
                )
                files_with_hash_set = set(files_with_hash_paths)

                for file_item in files:
                    if file_item.full_path in files_with_hash_set:
                        files_with_hash.append(file_item)
                    else:
                        files_without_hash.append(file_item)

                elapsed_time = time.time() - start_time
                logger.debug(
                    "[EventHandler] Batch hash check completed in %.3fs: %d/%d files have hashes",
                    elapsed_time,
                    len(files_with_hash),
                    len(files),
                )
            else:
                for file_item in files:
                    if self._file_has_hash(file_item):
                        files_with_hash.append(file_item)
                    else:
                        files_without_hash.append(file_item)

                elapsed_time = time.time() - start_time
                logger.debug(
                    "[EventHandler] Individual hash check completed in %.3fs: "
                    "%d/%d files have hashes",
                    elapsed_time,
                    len(files_with_hash),
                    len(files),
                )

        except Exception as e:
            logger.warning(
                "[EventHandler] Batch hash check failed, falling back to individual checks: %s",
                e,
            )
            for file_item in files:
                if self._file_has_hash(file_item):
                    files_with_hash.append(file_item)
                else:
                    files_without_hash.append(file_item)

        total = len(files)
        with_hash_count = len(files_with_hash)
        without_hash_count = len(files_without_hash)

        enable_selected = without_hash_count > 0
        selected_label = "Calculate checksums for selection"

        if without_hash_count == 0:
            selected_tooltip = f"All {total} file(s) already have checksums calculated"
        elif without_hash_count == total:
            selected_tooltip = f"Calculate checksums for {total} file(s)"
        else:
            selected_tooltip = (
                f"Calculate checksums for {without_hash_count} of {total} file(s) that need them"
            )

        return {
            "enable_selected": enable_selected,
            "selected_label": selected_label,
            "selected_tooltip": selected_tooltip,
            "stats": {
                "total": total,
                "with_hash": with_hash_count,
                "without_hash": without_hash_count,
            },
        }

    def _file_has_hash(self, file_item: FileItem) -> bool:
        """Check if a file has hash in cache."""
        from oncutf.utils.filesystem.file_status_helpers import has_hash

        return has_hash(file_item.full_path)
