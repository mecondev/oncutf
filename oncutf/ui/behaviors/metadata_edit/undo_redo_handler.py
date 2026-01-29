"""Undo/Redo operations for metadata editing.

This module provides undo/redo functionality for metadata operations,
including history dialog support.

Author: Michael Economou
Date: 2026-01-01
"""

from typing import Any

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class UndoRedoHandler:
    """Handles undo/redo operations for metadata editing.

    Provides methods for:
    - Undo metadata operation
    - Redo metadata operation
    - Show history dialog
    """

    def __init__(self, widget: Any) -> None:
        """Initialize undo/redo handler.

        Args:
            widget: The host widget

        """
        self._widget = widget

    def undo_metadata_operation(self) -> None:
        """Undo the last metadata operation from context menu."""
        try:
            from oncutf.core.metadata import get_metadata_command_manager

            command_manager = get_metadata_command_manager()

            if command_manager.undo():
                logger.info("Undo operation successful")

                # Get parent window for status message
                parent_window = self._widget._get_parent_with_file_table()
                if parent_window and hasattr(parent_window, "status_manager"):
                    parent_window.status_manager.set_file_operation_status(
                        "Operation undone", success=True, auto_reset=True
                    )
            else:
                logger.info("No operations to undo")

                # Show status message
                parent_window = self._widget._get_parent_with_file_table()
                if parent_window and hasattr(parent_window, "status_manager"):
                    parent_window.status_manager.set_file_operation_status(
                        "No operations to undo", success=False, auto_reset=True
                    )

        except Exception as e:
            logger.exception("Error during undo operation: %s", e)

    def redo_metadata_operation(self) -> None:
        """Redo the last undone metadata operation from context menu."""
        try:
            from oncutf.core.metadata import get_metadata_command_manager

            command_manager = get_metadata_command_manager()

            if command_manager.redo():
                logger.info("Redo operation successful")

                # Get parent window for status message
                parent_window = self._widget._get_parent_with_file_table()
                if parent_window and hasattr(parent_window, "status_manager"):
                    parent_window.status_manager.set_file_operation_status(
                        "Operation redone", success=True, auto_reset=True
                    )
            else:
                logger.info("No operations to redo")

                # Show status message
                parent_window = self._widget._get_parent_with_file_table()
                if parent_window and hasattr(parent_window, "status_manager"):
                    parent_window.status_manager.set_file_operation_status(
                        "No operations to redo", success=False, auto_reset=True
                    )

        except Exception as e:
            logger.exception("Error during redo operation: %s", e)

    def show_history_dialog(self) -> None:
        """Show metadata history dialog."""
        try:
            from oncutf.ui.dialogs.metadata_history_dialog import MetadataHistoryDialog

            dialog = MetadataHistoryDialog(self._widget)
            dialog.exec_()
        except ImportError:
            logger.warning("MetadataHistoryDialog not available")
