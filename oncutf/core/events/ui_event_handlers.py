"""
Module: ui_event_handlers.py

Author: Michael Economou
Date: 2025-12-20

UI-related event handlers - table interactions, header toggles, row clicks.
Extracted from event_handler_manager.py for better separation of concerns.
"""
from __future__ import annotations

from typing import Any

from oncutf.core.pyqt_imports import QModelIndex
from oncutf.utils.cursor_helper import wait_cursor
from oncutf.utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class UIEventHandlers:
    """
    Handles UI-related events.

    Responsibilities:
    - Table header toggle (select all)
    - Row click handling
    - Double click handling
    - Splitter movement (if needed)
    """

    def __init__(self, parent_window: Any) -> None:
        """Initialize UI event handlers with parent window reference."""
        self.parent_window = parent_window
        logger.debug("UIEventHandlers initialized", extra={"dev_only": True})

    def handle_header_toggle(self, _: Any) -> None:
        """
        Triggered when column 0 header is clicked.
        Toggles selection and checked state of all files (efficient, like Ctrl+A).
        """
        if not self.parent_window.file_model.files:
            return

        total = len(self.parent_window.file_model.files)
        all_selected = all(file.checked for file in self.parent_window.file_model.files)
        selection_model = self.parent_window.file_table_view.selectionModel()

        with wait_cursor():
            if all_selected:
                # Unselect all
                selection_model.clearSelection()
                for file in self.parent_window.file_model.files:
                    file.checked = False
            else:
                # Select all efficiently
                self.parent_window.file_table_view.select_rows_range(0, total - 1)
                for file in self.parent_window.file_model.files:
                    file.checked = True
                self.parent_window.file_table_view.anchor_row = 0

            self.parent_window.file_table_view.viewport().update()
            self.parent_window.update_files_label()
            self.parent_window.request_preview_update()
            self.parent_window.metadata_tree_view.refresh_metadata_from_selection()

    def on_table_row_clicked(self, index: QModelIndex) -> None:
        """
        Handles single clicks on table rows.
        Metadata updates are handled by the selection system, not here.
        """
        if not index.isValid():
            return

        row = index.row()
        if 0 <= row < len(self.parent_window.file_model.files):
            file = self.parent_window.file_model.files[row]
            logger.debug("[RowClick] Clicked on: %s", file.filename, extra={"dev_only": True})

            # NOTE: Metadata updates are handled by the selection system automatically
            # Removed redundant refresh_metadata_from_selection() call that was causing conflicts

    def handle_file_double_click(
        self, index: QModelIndex, modifiers: Any = None
    ) -> None:
        """
        Placeholder for future double-click functionality.

        NOTE: Metadata loading on double-click was removed (2025-12-21).
        This method is kept as a placeholder for future functionality.
        Use keyboard shortcuts (Ctrl+M, Ctrl+Shift+M, etc.) for metadata loading.
        """
        # Reserved for future functionality
        _ = index, modifiers  # Silence unused warnings
