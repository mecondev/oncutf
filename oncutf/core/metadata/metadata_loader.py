"""Module: metadata_loader.py.

Author: Michael Economou
Date: 2025-12-21

Metadata loading orchestration module.
Extracted from unified_metadata_manager.py for better separation of concerns.

Responsibilities:
- Orchestrate metadata loading for single and multiple files
- Manage loading modes (wait_cursor vs progress dialog)
- Handle cache pre-checking and filtering
- Coordinate parallel loading operations
- Manage streaming metadata loading
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from oncutf.config import COMPANION_FILES_ENABLED, LOAD_COMPANION_METADATA
from oncutf.utils.filesystem.path_utils import paths_equal
from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from oncutf.core.metadata.companion_metadata_handler import CompanionMetadataHandler
    from oncutf.core.metadata.metadata_progress_handler import MetadataProgressHandler
    from oncutf.core.metadata.parallel_loader import ParallelMetadataLoader
    from oncutf.infra.external.exiftool_wrapper import ExifToolWrapper
    from oncutf.models.file_item import FileItem

logger = get_cached_logger(__name__)


class MetadataLoader:
    """Orchestrates metadata loading operations.

    This class encapsulates the core loading logic that was previously
    in UnifiedMetadataManager, including:
    - Single file loading with wait_cursor
    - Multiple file loading with progress dialog
    - Streaming metadata loading
    - Cache pre-checking
    - Parallel loading coordination
    """

    def __init__(
        self,
        parent_window: Any = None,
        exiftool_getter: Callable[[], ExifToolWrapper] | None = None,
        companion_handler: CompanionMetadataHandler | None = None,
        progress_handler: MetadataProgressHandler | None = None,
    ) -> None:
        """Initialize metadata loader.

        Args:
            parent_window: Reference to the main application window
            exiftool_getter: Callable that returns ExifToolWrapper instance
            companion_handler: Handler for companion file metadata
            progress_handler: Handler for progress dialogs

        """
        self._parent_window = parent_window
        self._exiftool_getter = exiftool_getter
        self._companion_handler = companion_handler
        self._progress_handler = progress_handler

        # State tracking
        self._metadata_cancelled = False

        # Parallel loader (lazy-initialized)
        self._parallel_loader: ParallelMetadataLoader | None = None

    @property
    def parent_window(self) -> Any:
        """Get parent window."""
        return self._parent_window

    @parent_window.setter
    def parent_window(self, value: Any) -> None:
        """Set parent window."""
        self._parent_window = value

    @property
    def exiftool_wrapper(self) -> ExifToolWrapper:
        """Get ExifTool wrapper via getter function."""
        if self._exiftool_getter:
            return self._exiftool_getter()
        # Fallback: create new instance
        from oncutf.infra.external.exiftool_wrapper import ExifToolWrapper

        return ExifToolWrapper()

    @property
    def parallel_loader(self) -> Any:
        """Lazy-initialized parallel metadata loader."""
        if self._parallel_loader is None:
            from oncutf.core.metadata.parallel_loader import ParallelMetadataLoader

            self._parallel_loader = ParallelMetadataLoader()
            logger.debug(
                "[MetadataLoader] ParallelMetadataLoader initialized",
                extra={"dev_only": True},
            )
        return self._parallel_loader

    # =========================================================================
    # Cancellation Management
    # =========================================================================

    def reset_cancellation_flag(self) -> None:
        """Reset the metadata cancellation flag."""
        self._metadata_cancelled = False

    def request_cancellation(self) -> None:
        """Request cancellation of current loading operation."""
        self._metadata_cancelled = True
        # Also cancel the parallel loader if it exists
        if self._parallel_loader is not None:
            self._parallel_loader.cancel()
        logger.info("[MetadataLoader] Cancellation requested")

    def is_cancelled(self) -> bool:
        """Check if loading has been cancelled."""
        return self._metadata_cancelled

    def cleanup(self) -> None:
        """Clean up resources including parallel loader.

        This should be called during application shutdown to ensure
        all threads and subprocesses are properly terminated.
        """
        self._metadata_cancelled = True

        # Clean up parallel loader if it was initialized
        if self._parallel_loader is not None:
            self._parallel_loader.cleanup()
            self._parallel_loader = None

        logger.info("[MetadataLoader] Cleanup completed")

    # =========================================================================
    # Mode Determination
    # =========================================================================

    def determine_loading_mode(self, file_count: int) -> str:
        """Determine the appropriate loading mode based on file count.

        Args:
            file_count: Number of files to process

        Returns:
            str: Loading mode ("single_file_wait_cursor" or "multiple_files_dialog")

        """
        if file_count == 1:
            return "single_file_wait_cursor"
        else:
            # Use progress dialog for 2+ files (parallel loading with progress)
            return "multiple_files_dialog"

    # =========================================================================
    # Main Loading Entry Point
    # =========================================================================

    def load_metadata_for_items(
        self,
        items: list[FileItem],
        use_extended: bool = False,
        source: str = "unknown",
        on_finished: Callable[[], None] | None = None,
    ) -> None:
        """Load metadata for the given FileItem objects.

        Loading modes (determined by file count AFTER cache check):
        - Single file: Immediate loading with wait_cursor (fast and responsive)
        - Multiple files (2+): ProgressDialog with ESC cancel support

        Cache behavior:
        - Files with extended metadata are never downgraded to fast
        - Files with fast metadata can be upgraded to extended
        - Files with matching metadata type are skipped

        Args:
            items: List of FileItem objects to load metadata for
            use_extended: Whether to use extended metadata loading (Shift modifier)
            source: Source of the request (for logging)
            on_finished: Optional callback when loading completes

        """
        if not items:
            logger.debug("[MetadataLoader] No items provided for metadata loading")
            return

        # Reset cancellation flag for new operation
        self.reset_cancellation_flag()

        # ===== PHASE 1: Cache Pre-Check (fast, no UI blocking) =====
        needs_loading, skipped_count = self._filter_cached_items(items, use_extended)

        # Get metadata tree view reference
        metadata_tree_view = self._get_metadata_tree_view()

        # ===== PHASE 2: Handle "all cached" case =====
        if not needs_loading:
            logger.info(
                "[%s] All %d files already cached (skipped %d)",
                source,
                len(items),
                skipped_count,
            )
            self._handle_all_cached(items, metadata_tree_view)
            if on_finished:
                on_finished()
            return

        # Log loading info
        mode_str = "extended" if use_extended else "fast"
        if skipped_count > 0:
            logger.info(
                "[%s] Loading %s metadata: %d files (skipped %d cached)",
                source,
                mode_str,
                len(needs_loading),
                skipped_count,
            )
        else:
            logger.info(
                "[%s] Loading %s metadata for %d files",
                source,
                mode_str,
                len(needs_loading),
            )

        # ===== PHASE 3: Single file - use wait_cursor (immediate) =====
        if len(needs_loading) == 1:
            self._load_single_file_metadata(needs_loading[0], use_extended, metadata_tree_view)
            if on_finished:
                on_finished()
            return

        # ===== PHASE 4: Multiple files - use ProgressDialog with parallel loading =====
        self._load_multiple_files_metadata(
            needs_loading, use_extended, metadata_tree_view, source, on_finished
        )

    # =========================================================================
    # Cache Pre-Checking
    # =========================================================================

    def _filter_cached_items(
        self, items: list[FileItem], use_extended: bool
    ) -> tuple[list[FileItem], int]:
        """Filter items that already have valid cached metadata.

        Args:
            items: List of items to check
            use_extended: Whether extended metadata is required

        Returns:
            Tuple of (items_needing_load, skipped_count)

        """
        needs_loading = []
        skipped_count = 0

        # Use batch cache retrieval for performance
        cache_entries = {}
        if self._parent_window and hasattr(self._parent_window, "metadata_cache"):
            paths = [item.full_path for item in items]
            cache_entries = self._parent_window.metadata_cache.get_entries_batch(paths)

        from oncutf.utils.filesystem.path_normalizer import normalize_path

        for item in items:
            norm_path = normalize_path(item.full_path)
            cache_entry = cache_entries.get(norm_path)

            # Check if we have valid metadata in cache
            has_valid_cache = (
                cache_entry is not None
                and hasattr(cache_entry, "is_extended")
                and hasattr(cache_entry, "data")
                and cache_entry.data
            )

            if has_valid_cache and cache_entry is not None:
                # Already has extended - never downgrade
                if (
                    cache_entry.is_extended and not use_extended
                ) or cache_entry.is_extended == use_extended:
                    skipped_count += 1
                    continue
                # else: Need upgrade from fast to extended - add to needs_loading

            needs_loading.append(item)

        return needs_loading, skipped_count

    def _handle_all_cached(self, items: list[FileItem], metadata_tree_view: Any) -> None:
        """Handle case where all items are already cached."""
        # Update file table icons to show metadata icons
        if self._parent_window and hasattr(self._parent_window, "file_model"):
            self._parent_window.file_model.refresh_icons()

        # Smart display: respect selection count
        if items:
            # Get metadata from the appropriate file
            display_file = items[0] if len(items) == 1 else items[-1]
            metadata = None
            if hasattr(display_file, "metadata") and display_file.metadata:
                metadata = display_file.metadata
            elif self._parent_window and hasattr(self._parent_window, "metadata_cache"):
                from oncutf.utils.filesystem.path_normalizer import normalize_path

                cache_entry = self._parent_window.metadata_cache.get_entry(
                    normalize_path(display_file.full_path)
                )
                if cache_entry and hasattr(cache_entry, "data"):
                    metadata = cache_entry.data

            self._smart_display_metadata(metadata, context="all_cached")

    def _get_metadata_tree_view(self) -> Any:
        """Get metadata tree view reference from parent window."""
        if self._parent_window and hasattr(self._parent_window, "metadata_tree_view"):
            return self._parent_window.metadata_tree_view
        return None

    def _get_current_selection_count(self) -> int:
        """Get current selection count from file table."""
        if not self._parent_window:
            return 0

        # Try SelectionStore first (most reliable)
        try:
            from oncutf.app.state.context import get_app_context

            context = get_app_context()
            if context and hasattr(context, "selection_store"):
                return len(context.selection_store.get_selected_rows())
        except Exception:
            pass

        # Fallback: check file_table_view selection
        if hasattr(self._parent_window, "file_table_view"):
            selection_model = self._parent_window.file_table_view.selectionModel()
            if selection_model:
                return len(selection_model.selectedRows())

        return 0

    def _smart_display_metadata(self, metadata: dict[str, Any] | None, context: str = "") -> None:
        """Smart display metadata respecting selection count rules.

        Args:
            metadata: Metadata to display (or None)
            context: Context string for logging

        """
        metadata_tree_view = self._get_metadata_tree_view()
        if not metadata_tree_view:
            return

        selection_count = self._get_current_selection_count()

        # Use smart display method if available
        if hasattr(metadata_tree_view, "smart_display_metadata_or_empty_state"):
            metadata_tree_view.smart_display_metadata_or_empty_state(
                metadata, selection_count, context
            )
        elif selection_count == 1 and metadata:
            # Fallback: only display if single selection
            if hasattr(metadata_tree_view, "display_metadata"):
                metadata_tree_view.display_metadata(metadata, context)
        elif hasattr(metadata_tree_view, "show_empty_state"):
            # Multiple selection or no metadata - show empty state
            if selection_count > 1:
                metadata_tree_view.show_empty_state(f"{selection_count} files selected")
            elif selection_count == 0:
                metadata_tree_view.show_empty_state("No file selected")
            else:
                metadata_tree_view.show_empty_state("No metadata available")

    # =========================================================================
    # Single File Loading
    # =========================================================================

    def _load_single_file_metadata(
        self, item: FileItem, use_extended: bool, metadata_tree_view: Any
    ) -> None:
        """Load metadata for a single file with wait_cursor (immediate, no dialog).

        Args:
            item: The FileItem to load metadata for
            use_extended: Whether to use extended metadata
            metadata_tree_view: Reference to metadata tree view for display

        """
        from oncutf.app.services import wait_cursor

        with wait_cursor():
            try:
                # Load metadata using ExifTool wrapper
                metadata = self.exiftool_wrapper.get_metadata(item.full_path, use_extended)

                if metadata:
                    # Mark metadata with loading mode
                    if use_extended:
                        metadata["__extended__"] = True
                    elif "__extended__" in metadata:
                        del metadata["__extended__"]

                    # Enhance with companion file data
                    enhanced_metadata = self._enhance_with_companions(item, metadata, [item])

                    # Save to cache
                    if self._parent_window and hasattr(self._parent_window, "metadata_cache"):
                        self._parent_window.metadata_cache.set(
                            item.full_path, enhanced_metadata, is_extended=use_extended
                        )

                    # Update file item
                    item.metadata = enhanced_metadata

                    # Update UI
                    if self._parent_window and hasattr(self._parent_window, "file_model"):
                        self._parent_window.file_model.refresh_icons()

                    # Smart display: respect selection count
                    self._smart_display_metadata(enhanced_metadata, context="single_file_load")

                    logger.debug(
                        "[MetadataLoader] Loaded %s metadata for %s",
                        "extended" if use_extended else "fast",
                        item.filename,
                    )
                else:
                    logger.warning(
                        "[MetadataLoader] No metadata returned for %s",
                        item.filename,
                    )

            except Exception:
                logger.exception(
                    "[MetadataLoader] Failed to load metadata for %s",
                    item.filename,
                )

    # =========================================================================
    # Multiple Files Loading
    # =========================================================================

    def _load_multiple_files_metadata(
        self,
        needs_loading: list[FileItem],
        use_extended: bool,
        metadata_tree_view: Any,
        source: str,
        on_finished: Callable[[], None] | None = None,
    ) -> None:
        """Load metadata for multiple files with ProgressDialog and parallel loading.

        Args:
            needs_loading: List of FileItem objects that need loading
            use_extended: Whether to use extended metadata
            metadata_tree_view: Reference to metadata tree view for display
            source: Source of the request (for logging)
            on_finished: Optional callback when loading completes

        """
        # Cancellation support
        self._metadata_cancelled = False

        def cancel_callback() -> None:
            self._metadata_cancelled = True
            logger.info("[MetadataLoader] Metadata loading cancelled by user")

        # Create progress dialog
        from oncutf.app.services import create_metadata_dialog
        from oncutf.utils.filesystem.file_size_calculator import (
            calculate_files_total_size,
        )

        loading_dialog = create_metadata_dialog(
            self._parent_window,
            is_extended=use_extended,
            cancel_callback=cancel_callback,
        )
        loading_dialog.set_status(
            "Loading extended metadata..." if use_extended else "Loading metadata..."
        )

        # Calculate total size for progress tracking
        total_size = calculate_files_total_size(needs_loading)
        loading_dialog.start_progress_tracking(total_size)

        # Set initial count (0/N files) and first filename BEFORE showing
        total_files = len(needs_loading)
        loading_dialog.set_count(0, total_files)
        loading_dialog.update_progress(
            file_count=0,
            total_files=total_files,
            processed_bytes=0,
            total_bytes=total_size,
        )
        if needs_loading:
            loading_dialog.set_filename(needs_loading[0].filename)

        # Show dialog NOW with initialized state
        loading_dialog.show()
        loading_dialog.activateWindow()
        loading_dialog.setFocus()
        loading_dialog.raise_()

        # Process events to ensure dialog is visible with initial state
        for _ in range(3):
            QApplication.processEvents()

        # Progress tracking
        processed_size = 0

        def on_progress(current: int, total: int, item: FileItem, metadata: dict[str, Any]) -> None:
            """Called for each completed file during parallel loading."""
            nonlocal processed_size

            # Update processed size
            try:
                if hasattr(item, "size") and item.size is not None:
                    current_file_size = item.size
                elif hasattr(item, "full_path") and Path(item.full_path).exists():
                    current_file_size = Path(item.full_path).stat().st_size
                    item.size = current_file_size
                else:
                    current_file_size = 0
                processed_size += current_file_size
            except (OSError, AttributeError):
                pass

            # Update progress dialog
            loading_dialog.update_progress(
                file_count=current,
                total_files=total,
                processed_bytes=processed_size,
                total_bytes=total_size,
            )
            loading_dialog.set_filename(item.filename)
            loading_dialog.set_count(current, total)

            # Process metadata
            if metadata:
                # Mark metadata with loading mode
                if use_extended:
                    metadata["__extended__"] = True
                elif "__extended__" in metadata:
                    del metadata["__extended__"]

                # Enhance with companion data
                enhanced_metadata = self._enhance_with_companions(item, metadata, needs_loading)

                # Save to cache
                if self._parent_window and hasattr(self._parent_window, "metadata_cache"):
                    self._parent_window.metadata_cache.set(
                        item.full_path, enhanced_metadata, is_extended=use_extended
                    )

                # Update file item
                item.metadata = enhanced_metadata

                # Emit dataChanged for progressive UI update
                self._emit_data_changed_for_item(item)

        def on_completion() -> None:
            """Called when parallel loading completes."""
            loading_dialog.close()

            # Smart display: respect selection count
            if needs_loading:
                display_file = needs_loading[-1]
                metadata = None
                if hasattr(display_file, "metadata") and display_file.metadata:
                    metadata = display_file.metadata

                self._smart_display_metadata(metadata, context="parallel_load_complete")

            logger.info(
                "[%s] Completed loading metadata for %d files",
                source,
                len(needs_loading),
            )

            if on_finished:
                on_finished()

        def check_cancellation() -> bool:
            """Check if loading should be cancelled."""
            return self._metadata_cancelled

        # Start parallel loading
        self.parallel_loader.load_metadata_parallel(
            items=needs_loading,
            use_extended=use_extended,
            progress_callback=on_progress,
            completion_callback=on_completion,
            cancellation_check=check_cancellation,
        )

    def _emit_data_changed_for_item(self, item: FileItem) -> None:
        """Emit dataChanged signal for a specific item in the file model."""
        if not self._parent_window or not hasattr(self._parent_window, "file_model"):
            return

        try:
            for j, file in enumerate(self._parent_window.file_model.files):
                if paths_equal(file.full_path, item.full_path):
                    top_left = self._parent_window.file_model.index(j, 0)
                    bottom_right = self._parent_window.file_model.index(
                        j, self._parent_window.file_model.columnCount() - 1
                    )
                    self._parent_window.file_model.dataChanged.emit(
                        top_left, bottom_right, [Qt.DecorationRole, Qt.ToolTipRole]
                    )
                    break
        except Exception:
            logger.warning(
                "[MetadataLoader] Failed to emit dataChanged for %s",
                item.filename,
                exc_info=True,
            )

    # =========================================================================
    # Streaming Loading
    # =========================================================================

    def load_metadata_streaming(
        self, items: list[FileItem], use_extended: bool = False
    ) -> Iterator[tuple[FileItem, dict[str, Any]]]:
        """Yield metadata as soon as available using parallel loading.

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
                self._parent_window.metadata_cache.get_entry(item.full_path)
                if self._parent_window and hasattr(self._parent_window, "metadata_cache")
                else None
            )

            has_valid_cache = (
                cache_entry is not None
                and hasattr(cache_entry, "is_extended")
                and hasattr(cache_entry, "data")
                and cache_entry.data
            )

            if (
                has_valid_cache
                and cache_entry is not None
                and (
                    (cache_entry.is_extended and not use_extended)
                    or cache_entry.is_extended == use_extended
                )
            ):
                yield item, cache_entry.data
                continue

            items_to_load.append(item)

        if not items_to_load:
            return

        # Use parallel loading for the rest
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
                    if self._parent_window and hasattr(self._parent_window, "metadata_cache"):
                        self._parent_window.metadata_cache.set(
                            item.full_path, metadata, is_extended=use_extended
                        )

                    # Update item metadata
                    item.metadata = metadata

                    yield item, metadata
                except Exception:
                    logger.exception("Failed to load metadata for %s", item.filename)
                    yield item, {}

    # =========================================================================
    # Companion File Enhancement
    # =========================================================================

    def _enhance_with_companions(
        self,
        file_item: FileItem,
        base_metadata: dict[str, Any],
        all_files: list[FileItem],
    ) -> dict[str, Any]:
        """Enhance metadata with companion file data.

        Args:
            file_item: The main file being processed
            base_metadata: Base metadata from ExifTool
            all_files: All files being processed (for folder context)

        Returns:
            Enhanced metadata including companion data

        """
        if not COMPANION_FILES_ENABLED or not LOAD_COMPANION_METADATA:
            return base_metadata

        # Use injected companion handler if available
        if self._companion_handler:
            return self._companion_handler.enhance_metadata_with_companions(
                file_item, base_metadata, all_files
            )

        # Fallback: inline implementation (for backward compatibility)
        return self._enhance_metadata_with_companions_inline(file_item, base_metadata, all_files)

    def _enhance_metadata_with_companions_inline(
        self,
        file_item: FileItem,
        base_metadata: dict[str, Any],
        all_files: list[FileItem],
    ) -> dict[str, Any]:
        """Inline implementation of companion metadata enhancement.

        This is a fallback when no companion handler is injected.
        """
        from oncutf.utils.filesystem.companion_files_helper import CompanionFilesHelper

        try:
            # Get folder files for companion detection
            folder_path = str(Path(file_item.full_path).parent)
            folder_files = []

            # First try to use the files being loaded (more efficient)
            if all_files:
                folder_files = [
                    f.full_path for f in all_files if str(Path(f.full_path).parent) == folder_path
                ]

            # If not enough context, scan the folder
            if len(folder_files) < 2:
                try:
                    folder_files = [
                        str(Path(folder_path) / f)
                        for f in Path(folder_path).iterdir()
                        if (Path(folder_path) / f.name).is_file()
                    ]
                except OSError:
                    return base_metadata

            # Find companion files
            companions = CompanionFilesHelper.find_companion_files(
                file_item.full_path, folder_files
            )

            if not companions:
                return base_metadata

            # Create enhanced metadata
            enhanced_metadata = base_metadata.copy()
            companion_metadata = {}

            # Extract metadata from companion files
            for companion_path in companions:
                try:
                    companion_data = CompanionFilesHelper.extract_companion_metadata(companion_path)
                    if companion_data:
                        companion_name = Path(companion_path).name
                        for key, value in companion_data.items():
                            if key != "source":
                                companion_key = f"Companion:{companion_name}:{key}"
                                companion_metadata[companion_key] = value

                        logger.debug(
                            "[MetadataLoader] Enhanced %s with companion %s",
                            file_item.filename,
                            companion_name,
                        )
                except Exception:
                    logger.warning(
                        "[MetadataLoader] Failed to extract companion metadata from %s",
                        companion_path,
                        exc_info=True,
                    )

            # Merge companion metadata
            if companion_metadata:
                enhanced_metadata.update(companion_metadata)
                enhanced_metadata["__companion_files__"] = companions
                logger.debug(
                    "[MetadataLoader] Added %d companion fields to %s",
                    len(companion_metadata),
                    file_item.filename,
                )

            return enhanced_metadata

        except Exception:
            logger.warning(
                "[MetadataLoader] Error enhancing metadata with companions for %s",
                file_item.filename,
                exc_info=True,
            )
            return base_metadata
