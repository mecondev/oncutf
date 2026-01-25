"""Module: viewport_handler.py - Scrollbar and viewport management for FileTableView.

Author: Michael Economou
Date: 2026-01-04

Handles scrollbar visibility and viewport operations:
- Update scrollbar visibility based on content
- Force scrollbar updates
- Refresh text display
- Coordinate with column manager for horizontal scrollbar
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt5.QtCore import Qt

from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.shared.timer_manager import schedule_ui_update

if TYPE_CHECKING:
    from oncutf.ui.widgets.file_table.view import FileTableView

logger = get_cached_logger(__name__)


class ViewportHandler:
    """Manages scrollbar and viewport state for FileTableView.

    This handler coordinates:
    - Horizontal scrollbar visibility based on column widths
    - Vertical scrollbar visibility based on row count
    - Viewport refresh and geometry updates
    - Text display refresh for visible cells

    Attributes:
        _view: Reference to the parent FileTableView

    """

    def __init__(self, view: FileTableView) -> None:
        """Initialize viewport handler.

        Args:
            view: The parent FileTableView widget

        """
        self._view = view

    def update_scrollbar_visibility(self) -> None:
        """Update scrollbar visibility based on table content and column widths."""
        model = self._view.model()
        if not model:
            return

        # For empty table, always hide horizontal scrollbar
        if model.rowCount() == 0:
            self._view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            return

        # Calculate total column width
        total_width = 0
        for i in range(model.columnCount()):
            total_width += self._view.columnWidth(i)

        # Get viewport width
        viewport_width = self._view.viewport().width()

        # Show scrollbar if content is wider than viewport
        if total_width > viewport_width:
            self._view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        else:
            self._view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def force_scrollbar_update(self) -> None:
        """Force immediate scrollbar and viewport update."""
        # Update scrollbar visibility
        self.update_scrollbar_visibility()

        # Use column manager's improved horizontal scrollbar handling
        self._use_column_manager_scrollbar()

        # Force immediate viewport refresh
        self._view.viewport().update()

        # Force geometry update
        self._view.updateGeometry()

        # Force model data refresh
        if self._view.model():
            self._view.model().layoutChanged.emit()

        # Schedule a delayed update
        schedule_ui_update(self._delayed_refresh, delay=100)

        # Update both scrollbar and header visibility
        self._view.refresh_view_state()

    def _use_column_manager_scrollbar(self) -> None:
        """Use column manager for scrollbar handling with fallback."""
        try:
            from oncutf.core.application_context import get_app_context

            context = get_app_context()
            if context and hasattr(context, "column_manager"):
                context.column_manager.ensure_horizontal_scrollbar_state(self._view)
        except (RuntimeError, AttributeError):
            # Fallback to basic scrollbar handling
            self._basic_scrollbar_fallback()

    def _basic_scrollbar_fallback(self) -> None:
        """Basic scrollbar handling when column manager unavailable."""
        hbar = self._view.horizontalScrollBar()
        current_position = hbar.value() if hbar else 0

        self._view.updateGeometries()

        # Restore scroll position if still valid
        if hbar and hbar.maximum() > 0:
            if current_position <= hbar.maximum():
                hbar.setValue(current_position)
            else:
                hbar.setValue(hbar.maximum())

    def _delayed_refresh(self) -> None:
        """Delayed refresh for proper scrollbar and content updates."""
        # Update scrollbar visibility
        self.update_scrollbar_visibility()

        # Use column manager
        self._use_column_manager_scrollbar()

        self._view.viewport().update()

        # Refresh text in visible cells
        self.refresh_text_display()

        # Update header visibility
        if hasattr(self._view, "_update_header_visibility"):
            self._view._update_header_visibility()

    def refresh_text_display(self) -> None:
        """Refresh text display in all visible cells."""
        model = self._view.model()
        if not model:
            return

        # Get visible area
        visible_rect = self._view.viewport().rect()
        top_left = self._view.indexAt(visible_rect.topLeft())
        bottom_right = self._view.indexAt(visible_rect.bottomRight())

        if top_left.isValid() and bottom_right.isValid():
            # Emit dataChanged for visible area
            self._view.dataChanged(top_left, bottom_right)
        else:
            # Fallback: refresh all data
            top_left = model.index(0, 0)
            bottom_right = model.index(model.rowCount() - 1, model.columnCount() - 1)
            self._view.dataChanged(top_left, bottom_right)

    def ensure_scrollbar_visibility(self) -> None:
        """Public method to ensure scrollbar visibility is correct."""
        self.update_scrollbar_visibility()
