"""
Module: metadata_reader.py

Author: Michael Economou (refactored)
Date: 2025-12-20

Metadata reader - handles all metadata loading operations.
Extracted from unified_metadata_manager.py for better separation of concerns.

This is a simplified extraction focusing on core loading methods.
Full implementation to be completed in subsequent commits.
"""
from __future__ import annotations

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING, Any

from PyQt5.QtCore import QObject

from oncutf.core.pyqt_imports import QApplication, Qt
from oncutf.models.file_item import FileItem
from oncutf.utils.cursor_helper import wait_cursor
from oncutf.utils.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.core.parallel_metadata_loader import ParallelMetadataLoader
    from oncutf.utils.exiftool_wrapper import ExifToolWrapper

logger = get_cached_logger(__name__)


class MetadataReader(QObject):
    """
    Reader service for metadata loading operations.

    Responsibilities:
    - Load metadata for single/multiple files
    - Streaming metadata loading
    - Keyboard shortcut handlers for metadata loading
    - Mode determination (fast vs extended)
    - Progress tracking and UI updates
    """

    def __init__(self, parent_window: Any = None) -> None:
        """Initialize metadata reader with parent window reference."""
        super().__init__(parent_window)
        self.parent_window = parent_window
        self._exiftool_wrapper: ExifToolWrapper | None = None
        self._parallel_loader: ParallelMetadataLoader | None = None
        self._currently_loading: set[str] = set()
        self._metadata_cancelled = False

    @property
    def exiftool_wrapper(self) -> ExifToolWrapper:
        """Lazy-initialized ExifTool wrapper."""
        if self._exiftool_wrapper is None:
            from oncutf.utils.exiftool_wrapper import ExifToolWrapper

            self._exiftool_wrapper = ExifToolWrapper()
        return self._exiftool_wrapper

    @property
    def parallel_loader(self) -> ParallelMetadataLoader:
        """Lazy-initialized parallel metadata loader."""
        if self._parallel_loader is None:
            from oncutf.core.parallel_metadata_loader import ParallelMetadataLoader

            self._parallel_loader = ParallelMetadataLoader()
        return self._parallel_loader

    def is_loading(self) -> bool:
        """Check if any files are currently being loaded."""
        return len(self._currently_loading) > 0

    def reset_cancellation_flag(self) -> None:
        """Reset the metadata cancellation flag."""
        self._metadata_cancelled = False

    def determine_loading_mode(self, file_count: int, _use_extended: bool = False) -> str:
        """
        Determine the appropriate loading mode based on file count.

        Args:
            file_count: Number of files to process
            _use_extended: Whether to use extended metadata (unused parameter kept for compatibility)

        Returns:
            str: Loading mode ("single_file_wait_cursor" or "multiple_files_dialog")
        """
        if file_count == 1:
            return "single_file_wait_cursor"
        else:
            return "multiple_files_dialog"

    def determine_metadata_mode(
        self, modifier_state: Any = None
    ) -> tuple[bool, bool]:
        """
        Determines whether to use extended mode based on modifier keys.

        Args:
            modifier_state: Qt.KeyboardModifiers to use, or None for current state

        Returns:
            tuple: (skip_metadata, use_extended)
        """
        modifiers = modifier_state
        if modifiers is None:
            if self.parent_window and hasattr(self.parent_window, "modifier_state"):
                modifiers = self.parent_window.modifier_state
            else:
                modifiers = QApplication.keyboardModifiers()

        if modifiers == Qt.NoModifier:  # type: ignore[attr-defined]
            modifiers = QApplication.keyboardModifiers()

        ctrl = bool(modifiers & Qt.ControlModifier)  # type: ignore[attr-defined]
        shift = bool(modifiers & Qt.ShiftModifier)  # type: ignore[attr-defined]

        skip_metadata = not ctrl
        use_extended = ctrl and shift

        return skip_metadata, use_extended

    def should_use_extended_metadata(
        self, modifier_state: Any = None
    ) -> bool:
        """
        Returns True if Ctrl+Shift are both held.

        Args:
            modifier_state: Qt.KeyboardModifiers to use, or None for current state
        """
        modifiers = modifier_state
        if modifiers is None:
            if self.parent_window and hasattr(self.parent_window, "modifier_state"):
                modifiers = self.parent_window.modifier_state
            else:
                modifiers = QApplication.keyboardModifiers()

        ctrl = bool(modifiers & Qt.ControlModifier)  # type: ignore[attr-defined]
        shift = bool(modifiers & Qt.ShiftModifier)  # type: ignore[attr-defined]
        return ctrl and shift

    def load_metadata_streaming(
        self, items: list[FileItem], use_extended: bool = False
    ) -> Iterator[tuple[FileItem, dict[str, Any]]]:
        """
        Yield metadata as soon as available using parallel loading.

        Args:
            items: List of FileItem objects to load metadata for
            use_extended: Whether to use extended metadata loading

        Yields:
            Tuple[FileItem, dict]: (item, metadata)
        """
        if not items:
            return

        # Separate cached vs non-cached
        items_to_load = []

        for item in items:
            # Check cache
            cache_entry = (
                self.parent_window.metadata_cache.get_entry(item.full_path)
                if self.parent_window and hasattr(self.parent_window, "metadata_cache")
                else None
            )

            if cache_entry is None:
                items_to_load.append(item)
                continue

            has_valid_cache = (
                hasattr(cache_entry, "is_extended")
                and hasattr(cache_entry, "data")
                and cache_entry.data
            )

            if has_valid_cache:
                if (
                    cache_entry.is_extended
                    and not use_extended
                    or cache_entry.is_extended == use_extended
                ):
                    yield item, cache_entry.data
                    continue

            items_to_load.append(item)

        if not items_to_load:
            return

        # Use parallel loading for the rest
        max_workers = 4
        if self._parallel_loader:
            max_workers = self._parallel_loader.max_workers
        else:
            import multiprocessing

            max_workers = min(multiprocessing.cpu_count() * 2, 16)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_item = {
                executor.submit(
                    self.exiftool_wrapper.get_metadata, item.full_path, use_extended
                ): item
                for item in items_to_load
            }

            for future in as_completed(future_to_item):
                item = future_to_item[future]
                try:
                    metadata = future.result()

                    # Update cache
                    if self.parent_window and hasattr(self.parent_window, "metadata_cache"):
                        self.parent_window.metadata_cache.set(
                            item.full_path, metadata, is_extended=use_extended
                        )

                    # Update item metadata
                    item.metadata = metadata

                    yield item, metadata
                except Exception:
                    logger.exception("Failed to load metadata for %s", item.filename)
                    yield item, {}

    def load_metadata_for_items(
        self, items: list[FileItem], use_extended: bool = False, source: str = "unknown"
    ) -> None:
        """
        Load metadata for the given FileItem objects.

        NOTE: This is a simplified stub. Full implementation delegated to
        UnifiedMetadataManager for now to maintain backward compatibility.

        Args:
            items: List of FileItem objects to load metadata for
            use_extended: Whether to use extended metadata loading
            source: Source of the request (for logging)
        """
        logger.debug(
            "[MetadataReader] Stub called: %d items, extended=%s, source=%s",
            len(items) if items else 0,
            use_extended,
            source,
        )
        # Full implementation to be added in next phase

    def _load_single_file_metadata(
        self, item: FileItem, use_extended: bool, metadata_tree_view: Any
    ) -> None:
        """
        Load metadata for a single file with wait_cursor.

        Args:
            item: The FileItem to load metadata for
            use_extended: Whether to use extended metadata
            metadata_tree_view: Reference to metadata tree view for display
        """
        with wait_cursor():
            try:
                metadata = self.exiftool_wrapper.get_metadata(item.full_path, use_extended)

                # Update cache
                if self.parent_window and hasattr(self.parent_window, "metadata_cache"):
                    self.parent_window.metadata_cache.set(
                        item.full_path, metadata, is_extended=use_extended
                    )

                # Update item
                item.metadata = metadata

                # Update UI
                if metadata_tree_view:
                    metadata_tree_view.display_file_metadata(item)

                # Refresh icons
                if self.parent_window and hasattr(self.parent_window, "file_model"):
                    self.parent_window.file_model.refresh_icons()

                logger.debug("[MetadataReader] Loaded metadata for %s", item.filename)
            except Exception:
                logger.exception("[MetadataReader] Failed to load metadata for %s", item.filename)
