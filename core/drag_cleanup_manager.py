"""
DragCleanupManager - Handles drag and drop cleanup operations

Author: Michael Economou
Date: 2025-01-27

This manager centralizes drag cleanup operations including:
- Force drag cleanup on Escape key
- Emergency drag cleanup for stuck cursors
- Widget drag state cleanup
- Cursor management
"""

from typing import TYPE_CHECKING

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from core.drag_manager import DragManager
from utils.logger_helper import get_logger

if TYPE_CHECKING:
    from main_window import MainWindow

logger = get_logger(__name__)


class DragCleanupManager:
    """
    Manages drag and drop cleanup operations for the main window.

    This manager handles:
    - Force drag cleanup triggered by Escape key
    - Emergency cleanup for stuck cursors
    - Widget drag state cleanup
    - Cursor state management
    """

    def __init__(self, main_window: 'MainWindow'):
        """
        Initialize the DragCleanupManager.

        Args:
            main_window: Reference to the main window instance
        """
        self.main_window = main_window
        logger.debug("[DragCleanupManager] Initialized")

    def force_drag_cleanup(self) -> None:
        """
        Force cleanup of any active drag operations.
        Triggered by Escape key globally.
        """
        logger.info("[MainWindow] FORCE CLEANUP: Escape key pressed")

        drag_manager = DragManager.get_instance()

        # Check if there's any stuck cursor or drag state
        has_override_cursor = QApplication.overrideCursor() is not None
        has_active_drag = drag_manager.is_drag_active()

        if not has_override_cursor and not has_active_drag:
            logger.info("[MainWindow] FORCE CLEANUP: No cursors or drags to clean")
            return

        # Clean any stuck cursors first
        cursor_count = self._clean_stuck_cursors()

        # Clean drag manager state if needed
        if has_active_drag:
            drag_manager.force_cleanup()

        # Clean widget states
        self._cleanup_widget_drag_states()

        # Report what was cleaned
        if cursor_count > 0 or has_active_drag:
            self.main_window.set_status("Drag cancelled", color="blue", auto_reset=True, reset_delay=1000)
            logger.info(f"[MainWindow] FORCE CLEANUP: Cleaned {cursor_count} cursors, drag_active={has_active_drag}")
        else:
            logger.info("[MainWindow] FORCE CLEANUP: Nothing to clean")

    def _clean_stuck_cursors(self) -> int:
        """
        Clean any stuck override cursors.

        Returns:
            Number of cursors that were cleaned
        """
        cursor_count = 0
        while QApplication.overrideCursor() and cursor_count < 5:
            QApplication.restoreOverrideCursor()
            cursor_count += 1
        return cursor_count

    def _cleanup_widget_drag_states(self) -> None:
        """Clean up internal drag states in all widgets (lightweight version)."""
        # Only clean essential drag state, let widgets handle their own cleanup
        if hasattr(self.main_window, 'folder_tree'):
            if hasattr(self.main_window.folder_tree, '_dragging'):
                self.main_window.folder_tree._dragging = False

        if hasattr(self.main_window, 'file_table_view'):
            if hasattr(self.main_window.file_table_view, '_drag_start_pos'):
                self.main_window.file_table_view._drag_start_pos = None

        logger.debug("[MainWindow] Widget drag states cleaned")

    def emergency_drag_cleanup(self) -> None:
        """
        Emergency cleanup that runs every 5 seconds to catch stuck cursors.
        Only acts if cursor has been stuck for multiple checks.
        """
        app = QApplication.instance()
        if not app:
            return

        # Check if cursor looks stuck in drag mode
        current_cursor = app.overrideCursor()
        if current_cursor:
            cursor_shape = current_cursor.shape()
            # Common drag cursor shapes that might be stuck
            drag_cursors = [Qt.DragMoveCursor, Qt.DragCopyCursor, Qt.DragLinkCursor, Qt.ClosedHandCursor]

            if cursor_shape in drag_cursors:
                self._handle_stuck_cursor()
            else:
                # Reset count if cursor is not drag-related
                self._reset_stuck_cursor_count()
        else:
            # Reset count if no override cursor
            self._reset_stuck_cursor_count()

    def _handle_stuck_cursor(self) -> None:
        """Handle detection of a potentially stuck cursor."""
        drag_manager = DragManager.get_instance()
        if not drag_manager.is_drag_active():
            # Initialize stuck count if not exists
            if not hasattr(self.main_window, '_stuck_cursor_count'):
                self.main_window._stuck_cursor_count = 0

            self.main_window._stuck_cursor_count += 1

            # Only cleanup after 2 consecutive detections (10 seconds total)
            if self.main_window._stuck_cursor_count >= 2:
                logger.warning(f"[Emergency] Stuck drag cursor detected for {self.main_window._stuck_cursor_count * 5}s, forcing cleanup")
                drag_manager.force_cleanup()
                self.main_window.set_status("Stuck cursor fixed", color="green", auto_reset=True, reset_delay=1000)
                self.main_window._stuck_cursor_count = 0
            else:
                logger.debug(f"[Emergency] Suspicious cursor detected ({self.main_window._stuck_cursor_count}/2)")
        else:
            # Reset count if drag is actually active
            self._reset_stuck_cursor_count()

    def _reset_stuck_cursor_count(self) -> None:
        """Reset the stuck cursor count."""
        if hasattr(self.main_window, '_stuck_cursor_count'):
            self.main_window._stuck_cursor_count = 0

    def is_drag_active(self) -> bool:
        """
        Check if there's currently an active drag operation.

        Returns:
            True if drag is active, False otherwise
        """
        drag_manager = DragManager.get_instance()
        return drag_manager.is_drag_active()

    def has_override_cursor(self) -> bool:
        """
        Check if there's currently an override cursor.

        Returns:
            True if override cursor exists, False otherwise
        """
        return QApplication.overrideCursor() is not None

    def get_drag_cleanup_status(self) -> dict:
        """
        Get current drag cleanup status.

        Returns:
            Dictionary with drag and cursor status information
        """
        return {
            "has_active_drag": self.is_drag_active(),
            "has_override_cursor": self.has_override_cursor(),
            "stuck_cursor_count": getattr(self.main_window, '_stuck_cursor_count', 0)
        }
