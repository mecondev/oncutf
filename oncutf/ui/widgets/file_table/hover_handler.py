"""Module: hover_handler.py - Hover state management for FileListView.

Author: Michael Economou
Date: 2026-01-04

Handles hover highlighting state for table rows:
- Track currently hovered row
- Update hover visual feedback
- Clear hover state on leave events
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.ui.widgets.file_table.view import FileListView

logger = get_cached_logger(__name__)


class HoverHandler:
    """Manages hover state for FileListView rows.

    This handler tracks which row the mouse is currently hovering over
    and updates the visual feedback via the hover delegate.

    Attributes:
        _view: Reference to the parent FileListView

    """

    def __init__(self, view: FileListView) -> None:
        """Initialize hover handler.

        Args:
            view: The parent FileListView widget

        """
        self._view = view

    def update_hover_row(self, row: int) -> None:
        """Update the hover state to a new row.

        Args:
            row: The row index to hover, or -1 to clear hover

        """
        if not hasattr(self._view, "hover_delegate"):
            return

        old_row = self._view.hover_delegate.hovered_row
        if old_row == row:
            return

        self._view.hover_delegate.update_hover_row(row)
        self._invalidate_row(old_row)
        self._invalidate_row(row)

    def clear_hover(self) -> None:
        """Clear the current hover state."""
        self.update_hover_row(-1)

    def get_hovered_row(self) -> int:
        """Get the currently hovered row.

        Returns:
            The hovered row index, or -1 if no row is hovered

        """
        if hasattr(self._view, "hover_delegate"):
            return self._view.hover_delegate.hovered_row
        return -1

    def _invalidate_row(self, row: int) -> None:
        """Invalidate (repaint) a specific row.

        Args:
            row: The row index to invalidate

        """
        if row < 0:
            return

        model = self._view.model()
        if not model:
            return

        left = model.index(row, 0)
        right = model.index(row, model.columnCount() - 1)
        row_rect = self._view.visualRect(left).united(self._view.visualRect(right))
        self._view.viewport().update(row_rect)

    def handle_mouse_move(self, index_row: int) -> None:
        """Handle mouse move to update hover.

        Args:
            index_row: The row under the mouse, or -1 if outside

        """
        self.update_hover_row(index_row)

    def handle_leave(self) -> None:
        """Handle mouse leaving the view - clear hover."""
        self.clear_hover()
        self._view.viewport().update()
