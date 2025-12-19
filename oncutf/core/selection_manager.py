"""
Module: selection_manager.py

Author: Michael Economou
Date: 2025-05-31

selection_manager.py
Centralized selection management operations extracted from MainWindow.
Handles file table selection operations, preview updates, and metadata synchronization.
"""

import time

from oncutf.utils.cursor_helper import wait_cursor
from oncutf.utils.logger_factory import get_cached_logger
from oncutf.utils.metadata_cache_helper import MetadataCacheHelper
from oncutf.utils.timer_manager import schedule_metadata_load

logger = get_cached_logger(__name__)


class SelectionManager:
    """
    Centralized selection management operations.

    Handles:
    - Select all, clear all, invert selection operations
    - Preview update from selection changes
    - Metadata display synchronization
    - Efficient range-based selection updates
    """

    def __init__(self, parent_window=None):
        """Initialize the selection manager with the parent window."""
        self.parent_window = parent_window
        self._cache_helper = None
        # Cache for avoiding unnecessary preview updates
        self._last_selected_rows = None
        self._last_preview_update_time = 0

    def _get_cache_helper(self) -> MetadataCacheHelper:
        """Get or create the MetadataCacheHelper instance."""
        if self._cache_helper is None and self.parent_window:
            metadata_cache = getattr(self.parent_window, "metadata_cache", None)
            if metadata_cache:
                self._cache_helper = MetadataCacheHelper(metadata_cache)
        return self._cache_helper

    def select_all_rows(self) -> None:
        """
        Selects all rows in the file table efficiently with wait cursor.
        """
        if not self.parent_window:
            return

        file_model = getattr(self.parent_window, "file_model", None)
        file_table_view = getattr(self.parent_window, "file_table_view", None)

        if not file_model or not file_table_view or not file_model.files:
            if hasattr(self.parent_window, "status_manager"):
                self.parent_window.status_manager.set_selection_status(
                    "No files to select", selected_count=0, total_count=0, auto_reset=True
                )
            return

        with wait_cursor():
            # Clear cache to force update
            self.clear_preview_cache()

            # PROTECTION: Block signals during checked state updates to prevent infinite loops
            if file_table_view:
                file_table_view.blockSignals(True)

            try:
                for file in file_model.files:
                    file.checked = True

                file_table_view.select_rows_range(0, len(file_model.files) - 1)
                if hasattr(file_table_view, "anchor_row"):
                    file_table_view.anchor_row = 0

                if hasattr(self.parent_window, "update_files_label"):
                    self.parent_window.update_files_label()

                # Step 4: Request preview update (this can be async to avoid blocking)
                if hasattr(self.parent_window, "request_preview_update"):
                    self.parent_window.request_preview_update()

                # Step 5: Handle metadata display using centralized logic (async)
                def show_metadata_later():
                    metadata_tree_view = getattr(self.parent_window, "metadata_tree_view", None)
                    cache_helper = self._get_cache_helper()
                    if metadata_tree_view:
                        # Use centralized logic - select_all means multiple files, so show empty state
                        if hasattr(
                            metadata_tree_view, "should_display_metadata_for_selection"
                        ) and not metadata_tree_view.should_display_metadata_for_selection(
                            len(file_model.files)
                        ):
                            metadata_tree_view.show_empty_state("Multiple files selected")
                        else:
                            # Fallback for single file case (shouldn't happen with select_all)
                            last_file = file_model.files[-1]
                            if cache_helper:
                                metadata = cache_helper.get_metadata_for_file(last_file)
                                metadata_tree_view.display_metadata(metadata, context="select_all")

                schedule_metadata_load(show_metadata_later, 15)

            finally:
                # Restore signals
                if file_table_view:
                    file_table_view.blockSignals(False)

    def clear_all_selection(self) -> None:
        """
        Clears all selection in the file table.
        """
        if not self.parent_window:
            return

        file_model = getattr(self.parent_window, "file_model", None)
        file_table_view = getattr(self.parent_window, "file_table_view", None)

        if not file_model or not file_table_view:
            return

        # If everything is already deselected, do nothing
        if not file_model.files or all(not f.checked for f in file_model.files):
            logger.info("[ClearAll] All files already unselected. No action taken.")
            return

        with wait_cursor():
            # Clear cache to force update
            self.clear_preview_cache()

            # PROTECTION: Block signals during checked state updates to prevent infinite loops
            if file_table_view:
                file_table_view.blockSignals(True)

            try:
                selection_model = file_table_view.selectionModel()
                if selection_model:
                    selection_model.clearSelection()

                for file in file_model.files:
                    file.checked = False

                file_table_view.viewport().update()

                if hasattr(self.parent_window, "update_files_label"):
                    self.parent_window.update_files_label()
                if hasattr(self.parent_window, "request_preview_update"):
                    self.parent_window.request_preview_update()

                metadata_tree_view = getattr(self.parent_window, "metadata_tree_view", None)
                if metadata_tree_view and hasattr(metadata_tree_view, "clear_view"):
                    metadata_tree_view.clear_view()

            finally:
                # Restore signals
                if file_table_view:
                    file_table_view.blockSignals(False)

    def invert_selection(self) -> None:
        """
        Inverts the selection in the file table efficiently using select_rows_range helper.
        Shows wait cursor during the operation.
        """
        if not self.parent_window:
            return

        file_model = getattr(self.parent_window, "file_model", None)
        file_table_view = getattr(self.parent_window, "file_table_view", None)

        if not file_model or not file_table_view or not file_model.files:
            if hasattr(self.parent_window, "status_manager"):
                self.parent_window.status_manager.set_selection_status(
                    "No files to invert selection", selected_count=0, total_count=0, auto_reset=True
                )
            return

        with wait_cursor():
            # Clear cache to force update
            self.clear_preview_cache()

            # PROTECTION: Block signals during checked state updates to prevent infinite loops
            if file_table_view:
                file_table_view.blockSignals(True)

            try:
                selection_model = file_table_view.selectionModel()
                current_selected = set()
                if selection_model:
                    current_selected = {idx.row() for idx in selection_model.selectedRows()}

                # Uncheck all selected, check all unselected
                for row, file in enumerate(file_model.files):
                    file.checked = row not in current_selected

                # Find all checked rows (i.e. those that were previously unselected)
                checked_rows = [row for row, file in enumerate(file_model.files) if file.checked]
                checked_rows.sort()

                # Use parent's _find_consecutive_ranges if available
                ranges = []
                if hasattr(self.parent_window, "_find_consecutive_ranges"):
                    ranges = self.parent_window._find_consecutive_ranges(checked_rows)
                # Fallback: simple range creation
                elif checked_rows:
                    ranges = [(checked_rows[0], checked_rows[-1])]

                if selection_model:
                    selection_model.clearSelection()

                logger.info(
                    "[InvertSelection] Selecting %d rows in %d ranges.",
                    len(checked_rows),
                    len(ranges),
                )

                for start, end in ranges:
                    if hasattr(file_table_view, "select_rows_range"):
                        file_table_view.select_rows_range(start, end)

                if hasattr(file_table_view, "anchor_row") and checked_rows:
                    file_table_view.anchor_row = checked_rows[0]
                elif hasattr(file_table_view, "anchor_row"):
                    file_table_view.anchor_row = 0

                file_table_view.viewport().update()

                if hasattr(self.parent_window, "update_files_label"):
                    self.parent_window.update_files_label()
                if hasattr(self.parent_window, "request_preview_update"):
                    self.parent_window.request_preview_update()

                # Handle metadata display using centralized logic
                metadata_tree_view = getattr(self.parent_window, "metadata_tree_view", None)
                cache_helper = self._get_cache_helper()

                if metadata_tree_view:
                    # Use centralized logic to determine if metadata should be displayed
                    should_display = hasattr(
                        metadata_tree_view, "should_display_metadata_for_selection"
                    ) and metadata_tree_view.should_display_metadata_for_selection(
                        len(checked_rows)
                    )

                    if should_display and checked_rows and cache_helper:

                        def show_metadata_later():
                            last_row = checked_rows[-1]
                            file_item = file_model.files[last_row]
                            metadata = cache_helper.get_metadata_for_file(file_item)
                            if hasattr(metadata_tree_view, "handle_invert_selection"):
                                metadata_tree_view.handle_invert_selection(metadata)
                            elif hasattr(metadata_tree_view, "display_metadata"):
                                metadata_tree_view.display_metadata(
                                    metadata, context="invert_selection"
                                )

                        schedule_metadata_load(show_metadata_later, 20)
                    # Multiple files or no files - show empty state
                    elif hasattr(metadata_tree_view, "handle_invert_selection"):
                        metadata_tree_view.handle_invert_selection(None)
                    elif hasattr(metadata_tree_view, "show_empty_state"):
                        if checked_rows:
                            metadata_tree_view.show_empty_state("Multiple files selected")
                        else:
                            metadata_tree_view.show_empty_state("No file selected")

            finally:
                # Restore signals
                if file_table_view:
                    file_table_view.blockSignals(False)

    def update_preview_from_selection(self, selected_rows: list[int]) -> None:
        """
        Synchronizes the checked state of files and updates preview + metadata panel.
        Optimized for performance with minimal logging and simplified logic.
        """
        if not self.parent_window:
            return

        file_model = getattr(self.parent_window, "file_model", None)
        if not file_model:
            return

        # Check if selection actually changed
        selected_rows_set = set(selected_rows) if selected_rows else set()
        last_selected_set = set(self._last_selected_rows) if self._last_selected_rows else set()
        if selected_rows_set == last_selected_set:
            return

        # Update cache
        self._last_selected_rows = selected_rows[:]
        self._last_preview_update_time = time.time()

        # Performance optimization: Clear preview caches when selection changes
        if hasattr(self.parent_window, "utility_manager"):
            self.parent_window.utility_manager.clear_preview_caches()

        # Block signals to prevent loops
        file_table_view = getattr(self.parent_window, "file_table_view", None)
        if file_table_view:
            file_table_view.blockSignals(True)

        try:
            # Update checked states
            for row, file in enumerate(file_model.files):
                file.checked = row in selected_rows

            # Update UI components
            if hasattr(self.parent_window, "update_files_label"):
                self.parent_window.update_files_label()
            if hasattr(self.parent_window, "request_preview_update"):
                self.parent_window.request_preview_update()

            # Handle metadata display
            self._update_metadata_display(selected_rows)

        finally:
            if file_table_view:
                file_table_view.blockSignals(False)

    def _update_metadata_display(self, selected_rows: list[int]) -> None:
        """Simplified metadata display logic."""
        if not selected_rows:
            self._clear_metadata_display()
            return

        file_model = getattr(self.parent_window, "file_model", None)
        metadata_tree_view = getattr(self.parent_window, "metadata_tree_view", None)
        rename_modules_area = getattr(self.parent_window, "rename_modules_area", None)
        cache_helper = self._get_cache_helper()

        if not file_model or not metadata_tree_view:
            return

        last_row = selected_rows[-1]
        if 0 <= last_row < len(file_model.files):
            file_item = file_model.files[last_row]

            # Update current file for modules
            if rename_modules_area and hasattr(rename_modules_area, "set_current_file_for_modules"):
                rename_modules_area.set_current_file_for_modules(file_item)

            # Display metadata
            if len(selected_rows) == 1 and cache_helper:
                metadata = cache_helper.get_metadata_for_file(file_item)
                if hasattr(metadata_tree_view, "smart_display_metadata_or_empty_state"):
                    metadata_tree_view.smart_display_metadata_or_empty_state(
                        metadata, len(selected_rows), context="selection_update"
                    )
                elif hasattr(metadata_tree_view, "display_metadata"):
                    metadata_tree_view.display_metadata(metadata, context="selection_update")
            # Multiple files - show empty state
            elif hasattr(metadata_tree_view, "show_empty_state"):
                metadata_tree_view.show_empty_state("Multiple files selected")

    def _clear_metadata_display(self) -> None:
        """Clear metadata display and current file."""
        metadata_tree_view = getattr(self.parent_window, "metadata_tree_view", None)
        rename_modules_area = getattr(self.parent_window, "rename_modules_area", None)

        if metadata_tree_view and hasattr(metadata_tree_view, "clear_view"):
            metadata_tree_view.clear_view()
        if rename_modules_area and hasattr(rename_modules_area, "set_current_file_for_modules"):
            rename_modules_area.set_current_file_for_modules(None)

    def force_preview_update(self) -> None:
        """
        Force a preview update regardless of cache state.
        Useful when rename modules change or other external factors require an update.
        """
        logger.debug("[Sync] Force preview update requested", extra={"dev_only": True})
        # Clear cache to force update
        self._last_selected_rows = None
        self._last_preview_update_time = 0

        # Get current selection and trigger update
        if self.parent_window and hasattr(self.parent_window, "file_table_view"):
            selection_model = self.parent_window.file_table_view.selectionModel()
            if selection_model:
                selected_rows = [idx.row() for idx in selection_model.selectedRows()]
                self.update_preview_from_selection(selected_rows)

    def clear_preview_cache(self) -> None:
        """Clear the preview cache to force next update."""
        self._last_selected_rows = None
        self._last_preview_update_time = 0
