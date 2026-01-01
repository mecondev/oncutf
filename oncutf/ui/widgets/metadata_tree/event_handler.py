"""Event handler for MetadataTreeView Qt events.

This module extracts event-related methods from MetadataTreeView into a dedicated
EventHandler class following the delegation pattern. The view delegates Qt event
handling to this class for better separation of concerns.

Handles:
- Keyboard shortcuts (F5 refresh)
- Wheel events (hover state updates)
- Resize events (placeholder positioning)
- Focus events
- Mouse press events
- Scroll events

Author: Michael Economou
Date: 2026-01-01
"""

from typing import TYPE_CHECKING

from oncutf.core.pyqt_imports import QCursor, Qt
from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.ui.widgets.metadata_tree.view import MetadataTreeView

logger = get_cached_logger(__name__)


class MetadataTreeEventHandler:
    """Handles Qt events for MetadataTreeView using delegation pattern."""

    def __init__(self, view: "MetadataTreeView") -> None:
        """Initialize event handler with view reference.

        Args:
            view: The MetadataTreeView instance to handle events for
        """
        self._view = view

    def setup_shortcuts(self) -> None:
        """Setup local keyboard shortcuts for metadata tree."""
        # F5 refresh is now handled via keyPressEvent to avoid QShortcut priority issues
        # Note: Global undo/redo (Ctrl+Z, Ctrl+Shift+Z, Ctrl+Y) are registered in MainWindow
        # Context menu still provides Undo/Redo actions for mouse-based access.

    def handle_key_press(self, event) -> bool:
        """Handle keyboard events for F5 refresh.

        Args:
            event: The QKeyEvent to handle

        Returns:
            True if event was handled, False otherwise
        """
        # Handle F5 refresh
        if event.key() == Qt.Key_F5:
            self._view._on_refresh_shortcut()
            event.accept()
            return True

        return False

    def handle_wheel_event(self, event) -> None:
        """Update hover state after scroll to track cursor position smoothly.

        Args:
            event: The QWheelEvent to handle
        """
        # Update hover after scroll to reflect current cursor position
        delegate = self._view.itemDelegate()
        if delegate and hasattr(delegate, "hovered_index"):
            pos = self._view.viewport().mapFromGlobal(QCursor.pos())
            new_index = self._view.indexAt(pos)
            old_index = delegate.hovered_index

            # Only update if hover changed
            if new_index != old_index:
                delegate.hovered_index = new_index if new_index.isValid() else None
                # Repaint both old and new hover areas
                if old_index and old_index.isValid():
                    self._view.viewport().update(self._view.visualRect(old_index))
                if new_index.isValid():
                    self._view.viewport().update(self._view.visualRect(new_index))

    def handle_resize(self, event) -> None:
        """Handle resize events to adjust placeholder label size.

        Args:
            event: The QResizeEvent to handle
        """
        if hasattr(self._view, "placeholder_helper"):
            self._view.placeholder_helper.update_position()

    def handle_focus_out(self, event) -> None:
        """Handle focus loss events.

        Args:
            event: The QFocusEvent to handle
        """
        # Currently no special handling needed
        # This method exists for symmetry and future extensibility

    def handle_mouse_press(self, event) -> bool:
        """Handle mouse press events.

        Args:
            event: The QMouseEvent to handle

        Returns:
            True if event was handled, False to allow default processing
        """
        # Close any open context menu on left click
        if event.button() == Qt.LeftButton and self._view._current_menu:
            self._view._current_menu.close()
            self._view._current_menu = None

        return False  # Allow default processing

    def handle_scroll_contents(self, dx: int, dy: int) -> None:
        """Handle scroll contents by delta.

        This is called when the tree content is scrolled programmatically or by user.

        Args:
            dx: Horizontal scroll delta
            dy: Vertical scroll delta
        """
        # Currently no special handling needed
        # This method exists for symmetry and future extensibility
