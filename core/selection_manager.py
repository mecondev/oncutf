"""
selection_manager.py

Author: Michael Economou
Date: 2025-05-01

Centralized selection management operations extracted from MainWindow.
Handles file table selection operations, preview updates, and metadata synchronization.
"""

from typing import List

from core.qt_imports import QTimer, QElapsedTimer
from utils.cursor_helper import wait_cursor
from utils.logger_factory import get_cached_logger
from utils.timer_manager import schedule_selection_update, schedule_metadata_load

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
        """Initialize SelectionManager with parent window reference."""
        self.parent_window = parent_window

    def select_all_rows(self) -> None:
        """
        Selects all rows in the file table efficiently using select_rows_range helper.
        Shows wait cursor during the operation for consistent UX.
        """
        if not self.parent_window:
            return

        file_model = getattr(self.parent_window, 'file_model', None)
        file_table_view = getattr(self.parent_window, 'file_table_view', None)

        if not file_model or not file_table_view or not file_model.files:
            return

        total = len(file_model.files)
        if total == 0:
            return

        selection_model = file_table_view.selectionModel()
        all_checked = all(f.checked for f in file_model.files)
        all_selected = False

        selected_rows = getattr(file_table_view, 'selected_rows', set())
        if selection_model is not None:
            selected_rows = set(idx.row() for idx in selection_model.selectedRows())
            all_selected = (len(selected_rows) == total)

        if all_checked and all_selected:
            logger.debug("[SelectAll] All files already selected in both checked and selection model. No action taken.", extra={"dev_only": True})
            return

        with wait_cursor():
            logger.info(f"[SelectAll] Selecting all {total} rows.")

            # Step 1: Pre-generate preview data (without updating UI yet)
            list(file_model.files)  # Create a list of what will be selected

            # Step 2: Update internal state first
            for file in file_model.files:
                file.checked = True

            # Step 3: Start preview generation (this triggers the heavy work)
            if hasattr(self.parent_window, 'request_preview_update'):
                self.parent_window.request_preview_update()

            # Step 4: Add small delay to let preview start, then do visual selection
            def apply_visual_selection():
                file_table_view.select_rows_range(0, total - 1)
                if hasattr(file_table_view, 'anchor_row'):
                    file_table_view.anchor_row = 0
                file_table_view.viewport().update()
                if hasattr(self.parent_window, 'update_files_label'):
                    self.parent_window.update_files_label()

                # Handle metadata display for the last file
                def show_metadata_later():
                    last_file = file_model.files[-1]
                    metadata_cache = getattr(self.parent_window, 'metadata_cache', None)
                    metadata_tree_view = getattr(self.parent_window, 'metadata_tree_view', None)

                    if metadata_cache and metadata_tree_view:
                        metadata = last_file.metadata or metadata_cache.get(last_file.full_path)
                        metadata_tree_view.display_metadata(metadata, context="select_all")

                schedule_metadata_load(show_metadata_later, 15)

            schedule_selection_update(apply_visual_selection, 5)

    def clear_all_selection(self) -> None:
        """
        Clears all selection in the file table.
        """
        if not self.parent_window:
            return

        file_model = getattr(self.parent_window, 'file_model', None)
        file_table_view = getattr(self.parent_window, 'file_table_view', None)

        if not file_model or not file_table_view:
            return

        # If everything is already deselected, do nothing
        if not file_model.files or all(not f.checked for f in file_model.files):
            logger.info("[ClearAll] All files already unselected. No action taken.")
            return

        with wait_cursor():
            selection_model = file_table_view.selectionModel()
            if selection_model:
                selection_model.clearSelection()

            for file in file_model.files:
                file.checked = False

            file_table_view.viewport().update()

            if hasattr(self.parent_window, 'update_files_label'):
                self.parent_window.update_files_label()
            if hasattr(self.parent_window, 'request_preview_update'):
                self.parent_window.request_preview_update()

            metadata_tree_view = getattr(self.parent_window, 'metadata_tree_view', None)
            if metadata_tree_view and hasattr(metadata_tree_view, 'clear_view'):
                metadata_tree_view.clear_view()

    def invert_selection(self) -> None:
        """
        Inverts the selection in the file table efficiently using select_rows_range helper.
        Shows wait cursor during the operation.
        """
        if not self.parent_window:
            return

        file_model = getattr(self.parent_window, 'file_model', None)
        file_table_view = getattr(self.parent_window, 'file_table_view', None)

        if not file_model or not file_table_view or not file_model.files:
            if hasattr(self.parent_window, 'set_status'):
                self.parent_window.set_status("No files to invert selection.", color="gray", auto_reset=True)
            return

        with wait_cursor():
            selection_model = file_table_view.selectionModel()
            current_selected = set()
            if selection_model:
                current_selected = set(idx.row() for idx in selection_model.selectedRows())

            # Uncheck all selected, check all unselected
            for row, file in enumerate(file_model.files):
                file.checked = row not in current_selected

            # Find all checked rows (i.e. those that were previously unselected)
            checked_rows = [row for row, file in enumerate(file_model.files) if file.checked]
            checked_rows.sort()

            # Use parent's _find_consecutive_ranges if available
            ranges = []
            if hasattr(self.parent_window, '_find_consecutive_ranges'):
                ranges = self.parent_window._find_consecutive_ranges(checked_rows)
            else:
                # Fallback: simple range creation
                if checked_rows:
                    ranges = [(checked_rows[0], checked_rows[-1])]

            if selection_model:
                selection_model.clearSelection()

            logger.info(f"[InvertSelection] Selecting {len(checked_rows)} rows in {len(ranges)} ranges.")

            for start, end in ranges:
                if hasattr(file_table_view, 'select_rows_range'):
                    file_table_view.select_rows_range(start, end)

            if hasattr(file_table_view, 'anchor_row') and checked_rows:
                file_table_view.anchor_row = checked_rows[0]
            elif hasattr(file_table_view, 'anchor_row'):
                file_table_view.anchor_row = 0

            file_table_view.viewport().update()

            if hasattr(self.parent_window, 'update_files_label'):
                self.parent_window.update_files_label()
            if hasattr(self.parent_window, 'request_preview_update'):
                self.parent_window.request_preview_update()

            # Handle metadata display
            metadata_tree_view = getattr(self.parent_window, 'metadata_tree_view', None)
            metadata_cache = getattr(self.parent_window, 'metadata_cache', None)

            if checked_rows and metadata_tree_view and metadata_cache:
                def show_metadata_later():
                    last_row = checked_rows[-1]
                    file_item = file_model.files[last_row]
                    metadata = file_item.metadata or metadata_cache.get(file_item.full_path)
                    if hasattr(metadata_tree_view, 'handle_invert_selection'):
                        metadata_tree_view.handle_invert_selection(metadata)
                    elif hasattr(metadata_tree_view, 'display_metadata'):
                        metadata_tree_view.display_metadata(metadata, context="invert_selection")
                schedule_metadata_load(show_metadata_later, 20)
            elif metadata_tree_view and hasattr(metadata_tree_view, 'handle_invert_selection'):
                metadata_tree_view.handle_invert_selection(None)

    def update_preview_from_selection(self, selected_rows: List[int]) -> None:
        """
        Synchronizes the checked state of files and updates preview + metadata panel,
        based on selected rows emitted from the custom table view.

        Args:
            selected_rows (List[int]): The indices of selected rows (from custom selection).
        """
        if not self.parent_window:
            return

        file_model = getattr(self.parent_window, 'file_model', None)
        metadata_cache = getattr(self.parent_window, 'metadata_cache', None)
        metadata_tree_view = getattr(self.parent_window, 'metadata_tree_view', None)
        rename_modules_area = getattr(self.parent_window, 'rename_modules_area', None)

        if not file_model:
            return

        if not selected_rows:
            logger.debug("[Sync] No selection - clearing preview", extra={"dev_only": True})
            # Clear all checked states
            for file in file_model.files:
                file.checked = False

            if hasattr(self.parent_window, 'update_files_label'):
                self.parent_window.update_files_label()
            if hasattr(self.parent_window, 'update_preview_tables_from_pairs'):
                self.parent_window.update_preview_tables_from_pairs([])

            if metadata_tree_view and hasattr(metadata_tree_view, 'clear_view'):
                metadata_tree_view.clear_view()
            return

        logger.debug(f"[Sync] update_preview_from_selection: {selected_rows}", extra={"dev_only": True})
        timer = QElapsedTimer()
        timer.start()

        for row, file in enumerate(file_model.files):
            file.checked = row in selected_rows

        if hasattr(self.parent_window, 'update_files_label'):
            self.parent_window.update_files_label()
        if hasattr(self.parent_window, 'request_preview_update'):
            self.parent_window.request_preview_update()

        # Show metadata for last selected file and update current file for context menus
        if selected_rows:
            last_row = selected_rows[-1]
            if 0 <= last_row < len(file_model.files):
                file_item = file_model.files[last_row]

                # Update current file for SpecifiedText modules context menu
                if rename_modules_area and hasattr(rename_modules_area, 'set_current_file_for_modules'):
                    rename_modules_area.set_current_file_for_modules(file_item)

                if metadata_cache and metadata_tree_view:
                    metadata = file_item.metadata or metadata_cache.get(file_item.full_path)
                    if isinstance(metadata, dict) and hasattr(metadata_tree_view, 'display_metadata'):
                        metadata_tree_view.display_metadata(metadata, context="update_preview_from_selection")
                    elif metadata_tree_view and hasattr(metadata_tree_view, 'clear_view'):
                        metadata_tree_view.clear_view()
        else:
            # Clear current file when no selection
            if rename_modules_area and hasattr(rename_modules_area, 'set_current_file_for_modules'):
                rename_modules_area.set_current_file_for_modules(None)
            if metadata_tree_view and hasattr(metadata_tree_view, 'clear_view'):
                metadata_tree_view.clear_view()

        elapsed = timer.elapsed()
        logger.debug(f"[Performance] Full preview update took {elapsed} ms")
