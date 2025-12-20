"""
Module: ui_event_handlers.py

Author: Michael Economou
Date: 2025-12-20

UI-related event handlers - table interactions, header toggles, row clicks.
Extracted from event_handler_manager.py for better separation of concerns.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from oncutf.core.pyqt_imports import QModelIndex, Qt
from oncutf.utils.cursor_helper import wait_cursor
from oncutf.utils.logger_factory import get_cached_logger

if TYPE_CHECKING:
    pass

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
        Loads metadata for the file (even if already loaded), on double-click.
        Uses unified dialog-based loading for consistency.
        """
        if modifiers is None:
            modifiers = Qt.KeyboardModifiers()

        row = index.row()
        if 0 <= row < len(self.parent_window.file_model.files):
            file = self.parent_window.file_model.files[row]
            logger.info("[DoubleClick] Requested metadata reload for: %s", file.filename)

            # Check for Ctrl modifier for extended metadata
            ctrl_pressed = bool(modifiers & Qt.ControlModifier)  # type: ignore[attr-defined]
            use_extended = ctrl_pressed

            # Get selected files for context
            selected_files = [f for f in self.parent_window.file_model.files if f.checked]
            target_files = selected_files if len(selected_files) > 1 else [file]

            # Analyze metadata state to show appropriate dialog
            # Import here to avoid circular imports
            from oncutf.core.events.context_menu_handlers import ContextMenuHandlers

            # Create temporary handler instance for analysis
            temp_handler = ContextMenuHandlers(self.parent_window)
            metadata_analysis = temp_handler._analyze_metadata_state(target_files)

            # Check if we should show a dialog instead of loading
            if use_extended and not metadata_analysis["enable_extended_selected"]:
                # Extended metadata requested but all files already have it
                from oncutf.utils.dialog_utils import show_info_message

                message = f"All {len(target_files)} file(s) already have extended metadata."
                if metadata_analysis.get("extended_tooltip"):
                    message += f"\n\n{metadata_analysis['extended_tooltip']}"

                show_info_message(
                    self.parent_window,
                    "Extended Metadata",
                    message,
                )
                return
            elif not use_extended and not metadata_analysis["enable_fast_selected"]:
                # Fast metadata requested but files have extended or already have fast
                from oncutf.utils.dialog_utils import show_info_message

                message = f"Cannot load fast metadata for {len(target_files)} file(s)."
                if metadata_analysis.get("fast_tooltip"):
                    message += f"\n\n{metadata_analysis['fast_tooltip']}"

                show_info_message(
                    self.parent_window,
                    "Fast Metadata",
                    message,
                )
                return

            # Proceed with loading
            source = "double_click_extended" if use_extended else "double_click"
            if len(selected_files) > 1:
                source += "_multi"

            self.parent_window.load_metadata_for_items(
                target_files, use_extended=use_extended, source=source
            )
