"""Module: selection_manager.py.

Author: Michael Economou
Date: 2025-05-31

selection_manager.py
Centralized selection management operations extracted from MainWindow.
Handles file table selection operations, preview updates, and metadata synchronization.
"""

import time
from typing import Any

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class SelectionManager:
    """Centralized selection management operations.

    Handles:
    - Select all, clear all, invert selection operations
    - Preview update from selection changes
    - Metadata display synchronization
    - Efficient range-based selection updates
    """

    def __init__(self, parent_window: Any = None) -> None:
        """Initialize the selection manager with the parent window."""
        self.parent_window = parent_window
        # Cache for avoiding unnecessary preview updates
        self._last_selected_rows = None
        self._last_preview_update_time = 0

    def select_all_rows(self) -> None:
        """Selects all rows in the file table efficiently with wait cursor."""
        if not self.parent_window:
            return

        file_model = getattr(self.parent_window, "file_model", None)
        file_list_view = getattr(self.parent_window, "file_list_view", None)

        if not file_model or not file_list_view or not file_model.files:
            if hasattr(self.parent_window, "status_manager"):
                self.parent_window.status_manager.set_selection_status(
                    "No files to select",
                    selected_count=0,
                    total_count=0,
                    auto_reset=True,
                )
            return

        from oncutf.ui.services.cursor_service import wait_cursor

        with wait_cursor():
            # Clear cache to force update
            self.clear_preview_cache()

            # PROTECTION: Block signals during checked state updates to prevent infinite loops
            if file_list_view:
                file_list_view.blockSignals(True)

            try:
                for file in file_model.files:
                    file.checked = True

                file_list_view._selection_behavior.select_rows_range(0, len(file_model.files) - 1)
                if hasattr(file_list_view, "anchor_row"):
                    file_list_view.anchor_row = 0

                if hasattr(self.parent_window, "update_files_label"):
                    self.parent_window.update_files_label()

                # Step 4: Request preview update (this can be async to avoid blocking)
                if hasattr(self.parent_window, "request_preview_update"):
                    self.parent_window.request_preview_update()

            finally:
                # Restore signals
                if file_list_view:
                    file_list_view.blockSignals(False)

        metadata_tree_view = getattr(self.parent_window, "metadata_tree_view", None)
        if metadata_tree_view:
            metadata_tree_view.refresh_metadata_from_selection()

    def clear_all_selection(self) -> None:
        """Clears all selection in the file table.

        Uses FileTableStateHelper for consistent state clearing.
        """
        if not self.parent_window:
            return

        file_model = getattr(self.parent_window, "file_model", None)
        file_list_view = getattr(self.parent_window, "file_list_view", None)

        if not file_model or not file_list_view:
            return

        # If everything is already deselected, do nothing
        if not file_model.files or all(not f.checked for f in file_model.files):
            logger.info("[ClearAll] All files already unselected. No action taken.")
            return

        from oncutf.app.state.context import get_app_context
        from oncutf.ui.helpers.file_table_state_helper import FileTableStateHelper
        from oncutf.ui.services.cursor_service import wait_cursor

        with wait_cursor():
            # Clear cache to force update
            self.clear_preview_cache()

            # Clear UI state (selection, checked, scroll, metadata tree)
            context = get_app_context()
            metadata_tree_view = getattr(self.parent_window, "metadata_tree_view", None)

            if context:
                FileTableStateHelper.clear_all_state(file_list_view, context, metadata_tree_view)

            # Sync thumbnail viewport explicitly: clear_all_state uses emit_signal=False
            # so SelectionStore.selection_changed does not fire automatically.
            thumbnail_viewport = getattr(self.parent_window, "thumbnail_viewport", None)
            if thumbnail_viewport and hasattr(thumbnail_viewport, "sync_selection_from_rows"):
                thumbnail_viewport.sync_selection_from_rows(set())

            # Update labels
            if hasattr(self.parent_window, "update_files_label"):
                self.parent_window.update_files_label()
            if hasattr(self.parent_window, "request_preview_update"):
                self.parent_window.request_preview_update()

    def invert_selection(self) -> None:
        """Inverts the selection using SelectionStore as source of truth.

        Reads current selection from SelectionStore (app layer) so the operation
        is view-agnostic and works correctly whether triggered from the file table
        or the thumbnail viewport.
        """
        if not self.parent_window:
            return

        file_model = getattr(self.parent_window, "file_model", None)
        file_list_view = getattr(self.parent_window, "file_list_view", None)

        if not file_model or not file_list_view or not file_model.files:
            if hasattr(self.parent_window, "status_manager"):
                self.parent_window.status_manager.set_selection_status(
                    "No files to invert selection",
                    selected_count=0,
                    total_count=0,
                    auto_reset=True,
                )
            return

        from oncutf.app.state.context import get_app_context
        from oncutf.ui.services.cursor_service import wait_cursor

        with wait_cursor():
            # Clear cache to force update
            self.clear_preview_cache()

            # PROTECTION: Block signals during checked state updates to prevent infinite loops
            if file_list_view:
                file_list_view.blockSignals(True)

            try:
                # Read current selection from SelectionStore (source of truth),
                # not from file_list_view.selectionModel() which is view-specific
                # and may not reflect selections made in the thumbnail viewport.
                context = get_app_context()
                current_selected: set[int] = set()
                if context and context.selection_store:
                    current_selected = context.selection_store.get_selected_rows()
                else:
                    # Fallback: read from file_list_view Qt model
                    selection_model = file_list_view.selectionModel()
                    if selection_model:
                        current_selected = {index.row() for index in selection_model.selectedRows()}

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

                selection_model = file_list_view.selectionModel()
                if selection_model:
                    selection_model.clearSelection()

                logger.info(
                    "[InvertSelection] Selecting %d rows in %d ranges.",
                    len(checked_rows),
                    len(ranges),
                )

                for start, end in ranges:
                    if hasattr(file_list_view, "_selection_behavior"):
                        file_list_view._selection_behavior.select_rows_range(start, end)

                if hasattr(file_list_view, "anchor_row") and checked_rows:
                    file_list_view.anchor_row = checked_rows[0]
                elif hasattr(file_list_view, "anchor_row"):
                    file_list_view.anchor_row = 0

                file_list_view.viewport().update()

                if hasattr(self.parent_window, "update_files_label"):
                    self.parent_window.update_files_label()
                if hasattr(self.parent_window, "request_preview_update"):
                    self.parent_window.request_preview_update()

            finally:
                # Restore signals
                if file_list_view:
                    file_list_view.blockSignals(False)

        metadata_tree_view = getattr(self.parent_window, "metadata_tree_view", None)
        if metadata_tree_view:
            metadata_tree_view.refresh_metadata_from_selection()

    def update_preview_from_selection(self, selected_rows: list[int]) -> None:
        """Synchronizes the checked state of files and updates preview + metadata panel.
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
        file_list_view = getattr(self.parent_window, "file_list_view", None)
        if file_list_view:
            file_list_view.blockSignals(True)

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
            if file_list_view:
                file_list_view.blockSignals(False)

    def _update_metadata_display(self, selected_rows: list[int]) -> None:
        """Update rename modules area with current file, then delegate metadata display."""
        file_model = getattr(self.parent_window, "file_model", None)
        metadata_tree_view = getattr(self.parent_window, "metadata_tree_view", None)
        rename_modules_area = getattr(self.parent_window, "rename_modules_area", None)

        # Update current file for rename modules area
        if rename_modules_area and hasattr(rename_modules_area, "set_current_file_for_modules"):
            if selected_rows and file_model and 0 <= selected_rows[-1] < len(file_model.files):
                rename_modules_area.set_current_file_for_modules(
                    file_model.files[selected_rows[-1]]
                )
            else:
                rename_modules_area.set_current_file_for_modules(None)

        # Delegate display to the single canonical path
        if metadata_tree_view:
            metadata_tree_view.refresh_metadata_from_selection()

    def force_preview_update(self) -> None:
        """Force a preview update regardless of cache state.
        Useful when rename modules change or other external factors require an update.
        """
        logger.debug("[Sync] Force preview update requested", extra={"dev_only": True})
        # Clear cache to force update
        self._last_selected_rows = None
        self._last_preview_update_time = 0

        # Get current selection and trigger update
        if self.parent_window and hasattr(self.parent_window, "file_list_view"):
            selection_model = self.parent_window.file_list_view.selectionModel()
            if selection_model:
                selected_rows = [idx.row() for idx in selection_model.selectedRows()]
                self.update_preview_from_selection(selected_rows)

    def clear_preview_cache(self) -> None:
        """Clear the preview cache to force next update."""
        self._last_selected_rows = None
        self._last_preview_update_time = 0
