"""Module: header_keyboard_behavior.py.

Author: Michael Economou
Date: 2026-01-08

Behavior for handling keyboard shortcuts for column reordering.
Provides Ctrl+Left/Right shortcuts to move columns based on hover position.
"""

from oncutf.core.pyqt_imports import QEvent, QKeyEvent, QObject, Qt
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class HeaderKeyboardBehavior(QObject):
    """Handles keyboard shortcuts for column reordering in header.

    Features:
    - Ctrl+Left: Move hovered column one position to the left
    - Ctrl+Right: Move hovered column one position to the right
    - Works when hovering anywhere in the table or header
    """

    def __init__(self, table_view, header):
        """Initialize the keyboard behavior.

        Args:
            table_view: The QTableView widget
            header: The QHeaderView widget (InteractiveHeader)

        """
        super().__init__(table_view)
        self._table_view = table_view
        self._header = header

        # Install event filter on table view to catch keyboard events
        self._table_view.installEventFilter(self)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Filter keyboard events from table view for column reordering shortcuts.

        Args:
            obj: The object that received the event
            event: The event to filter

        Returns:
            True if event was handled, False otherwise

        """
        if event.type() == QEvent.KeyPress and isinstance(event, QKeyEvent):
            # Check for Ctrl+Left or Ctrl+Right
            if event.modifiers() == Qt.ControlModifier:
                if event.key() in (Qt.Key_Left, Qt.Key_Right):
                    # Handle the shortcut
                    handled = self._handle_column_move_shortcut(event)
                    if handled:
                        event.accept()
                        return True

        # Pass event to parent's event filter
        return super().eventFilter(obj, event)

    def _handle_column_move_shortcut(self, event: QKeyEvent) -> bool:
        """Handle Ctrl+Left/Right shortcuts for column movement.

        Args:
            event: The keyboard event

        Returns:
            True if event was handled, False otherwise

        """
        # Only handle shortcuts if sections are movable (not locked)
        if not self._header.sectionsMovable():
            return False

        # Get the focused section (under mouse cursor)
        focused_visual = self._get_focused_section()
        if focused_visual < 0:
            return False

        logical_index = self._header.logicalIndex(focused_visual)

        # Skip status column (0) - it's not movable
        if logical_index == 0:
            return False

        if event.key() == Qt.Key_Left:
            # Move left (decrease visual index)
            if focused_visual > 1:  # Don't move before status column (visual 0)
                self._header.moveSection(focused_visual, focused_visual - 1)
                logger.info("[HEADER_KEYBOARD] Moved column left via Ctrl+Left")
                return True
        elif event.key() == Qt.Key_Right:
            # Move right (increase visual index)
            if focused_visual < self._header.count() - 1:
                self._header.moveSection(focused_visual, focused_visual + 1)
                logger.info("[HEADER_KEYBOARD] Moved column right via Ctrl+Right")
                return True

        return False

    def _get_focused_section(self) -> int:
        """Get the visual index of the column under mouse cursor.

        Returns:
            Visual index of focused section, or -1 if none found.

        """
        # Get mouse position relative to table view
        cursor_pos = self._table_view.mapFromGlobal(self._table_view.cursor().pos())

        # Check if cursor is within table viewport
        if (
            self._table_view.viewport()
            .rect()
            .contains(self._table_view.viewport().mapFromParent(cursor_pos))
        ):
            # Get column at cursor position in table view
            logical = self._table_view.columnAt(cursor_pos.x())
            if logical >= 0:
                return self._header.visualIndex(logical)

        # Also check if cursor is in header itself
        header_cursor_pos = self._header.mapFromGlobal(self._header.cursor().pos())
        if self._header.rect().contains(header_cursor_pos):
            logical = self._header.logicalIndexAt(header_cursor_pos)
            if logical >= 0:
                return self._header.visualIndex(logical)

        # Fallback: Return the first visible non-status column
        for visual_idx in range(1, self._header.count()):  # Start from 1 to skip status column
            if not self._header.isSectionHidden(self._header.logicalIndex(visual_idx)):
                return visual_idx

        return -1

    def cleanup(self):
        """Remove event filter and cleanup resources."""
        if self._table_view:
            self._table_view.removeEventFilter(self)
