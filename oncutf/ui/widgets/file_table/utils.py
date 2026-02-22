"""Module: utils.py - Utility functions for FileListView.

Author: Michael Economou
Date: 2026-01-04

Provides utility functions and helpers:
- Cursor cleanup for drag operations
- Emergency cursor reset
- Other helper functions
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.ui.widgets.file_table.view import FileListView

logger = get_cached_logger(__name__)


def force_cursor_cleanup(view: FileListView) -> None:
    """Force cleanup of any stuck cursor states.

    This clears all override cursors and resets the view's cursor
    to the default arrow cursor.

    Args:
        view: The FileListView to clean up

    """
    try:
        # Remove any override cursors that might be stuck
        while QApplication.overrideCursor() is not None:
            QApplication.restoreOverrideCursor()

        # Reset view cursor to default
        view.setCursor(Qt.ArrowCursor)
        view.viewport().setCursor(Qt.ArrowCursor)

    except Exception as e:
        logger.warning("Error during cursor cleanup: %s", e)


def emergency_cursor_cleanup(view: FileListView) -> None:
    """Emergency cursor cleanup with aggressive reset.

    This is a more aggressive cleanup that removes up to 10
    override cursors and forcefully resets all widget cursors.

    Args:
        view: The FileListView to clean up

    """
    try:
        # More aggressive cleanup - remove up to 10 override cursors
        for _ in range(10):
            if QApplication.overrideCursor() is not None:
                QApplication.restoreOverrideCursor()
            else:
                break

        # Forcefully reset cursor
        view.unsetCursor()
        view.viewport().unsetCursor()
        view.setCursor(Qt.ArrowCursor)
        view.viewport().setCursor(Qt.ArrowCursor)

        # Process events to ensure cursor is updated
        QApplication.processEvents()

    except Exception as e:
        logger.warning("Error during emergency cursor cleanup: %s", e)


def get_metadata_tree(view: FileListView):
    """Get the metadata tree widget from the parent hierarchy.

    Args:
        view: The FileListView to search from

    Returns:
        The metadata tree widget or None if not found

    """
    parent = view.parent()
    while parent:
        if hasattr(parent, "metadata_tree"):
            return parent.metadata_tree
        if hasattr(parent, "metadata_tree_view"):
            return parent.metadata_tree_view
        parent = parent.parent()
    return None


def get_main_window(view: FileListView):
    """Get the main window from the parent hierarchy.

    Args:
        view: The FileListView to search from

    Returns:
        The main window or None if not found

    """
    parent = view.parent()
    while parent:
        if hasattr(parent, "window_config_manager"):
            return parent
        parent = parent.parent()
    return None


def clear_preview_and_metadata(view: FileListView) -> None:
    """Clear preview and metadata displays when no selection exists.

    Args:
        view: The FileListView to use for finding parent window

    """
    try:
        parent_window = view.parent()
        while parent_window and not hasattr(parent_window, "metadata_tree_view"):
            parent_window = parent_window.parent()

        if parent_window:
            if hasattr(parent_window, "metadata_tree_view"):
                metadata_tree = parent_window.metadata_tree_view
                if hasattr(metadata_tree, "show_empty_state"):
                    metadata_tree.show_empty_state("No file selected")

            if hasattr(parent_window, "preview_tables_view"):
                preview_view = parent_window.preview_tables_view
                if hasattr(preview_view, "clear_view"):
                    preview_view.clear_view()

    except Exception as e:
        logger.warning("Error clearing preview/metadata displays: %s", e)
