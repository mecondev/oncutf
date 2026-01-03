"""Module: tooltip_handler.py - Custom tooltip logic for FileTableView.

Author: Michael Economou
Date: 2026-01-04

Handles custom tooltips for table cells:
- Manage tooltip timer and delay
- Show context-aware tooltips (info, warning, error)
- Clear tooltips on mouse events
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from oncutf.core.pyqt_imports import QEvent, QModelIndex, Qt, QTimer
from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.ui.tooltip_helper import TooltipHelper, TooltipType

if TYPE_CHECKING:
    from oncutf.ui.widgets.file_table.view import FileTableView

logger = get_cached_logger(__name__)

# Tooltip hover delay in milliseconds
TOOLTIP_HOVER_DELAY = 600


class TooltipHandler:
    """Manages custom tooltips for FileTableView cells.

    This handler provides context-aware tooltips that:
    - Show after a hover delay
    - Display different styles for info/warning/error
    - Hide on mouse events or leaving the viewport

    Attributes:
        _view: Reference to the parent FileTableView
        _timer: Timer for tooltip hover delay
        _current_index: Currently tracked cell index
    """

    def __init__(self, view: FileTableView) -> None:
        """Initialize tooltip handler.

        Args:
            view: The parent FileTableView widget
        """
        self._view = view
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._show_tooltip)
        self._current_index = QModelIndex()

    def handle_event(self, event_type: int, index: QModelIndex | None = None) -> bool:
        """Handle viewport events for tooltip management.

        Args:
            event_type: The QEvent type
            index: The cell index under the mouse (for MouseMove)

        Returns:
            True if the event was handled and should be suppressed
        """
        if event_type == QEvent.ToolTip:
            # Suppress default Qt tooltips
            return True

        elif event_type == QEvent.MouseMove:
            if index is None:
                return False
            if index != self._current_index:
                # Index changed - hide current and start timer for new
                self.clear()
                self._current_index = index
                if index.isValid():
                    self._timer.start(TOOLTIP_HOVER_DELAY)
            if not index.isValid():
                self.clear()
            return False

        elif event_type in (QEvent.MouseButtonPress, QEvent.MouseButtonRelease):
            # Mouse clicked - hide tooltip immediately
            self.clear()
            return False

        elif event_type in (QEvent.Leave, QEvent.HoverLeave):
            # Mouse left viewport
            self.clear()
            return False

        return False

    def clear(self) -> None:
        """Clear active tooltip and stop timer."""
        TooltipHelper.clear_tooltips_for_widget(self._view.viewport())
        self._timer.stop()
        self._current_index = QModelIndex()

    def clear_for_widget(self) -> None:
        """Clear tooltips for the view widget (not viewport)."""
        TooltipHelper.clear_tooltips_for_widget(self._view)

    def _show_tooltip(self) -> None:
        """Show custom tooltip for current cell."""
        if not self._current_index.isValid():
            return

        model = self._view.model()
        if not model:
            return

        # Get tooltip text from model
        tooltip_text = model.data(self._current_index, Qt.ToolTipRole)
        if not tooltip_text:
            return

        # Convert to string if necessary
        tooltip_text = str(tooltip_text) if tooltip_text else ""
        if not tooltip_text:
            return

        # Determine tooltip type based on content
        tooltip_type = self._detect_tooltip_type(tooltip_text)

        # Show custom tooltip
        from oncutf.config import TOOLTIP_DURATION

        TooltipHelper.show_tooltip(
            self._view.viewport(),
            tooltip_text,
            tooltip_type,
            duration=TOOLTIP_DURATION,
            persistent=False,
        )

    def _detect_tooltip_type(self, text: str) -> str:
        """Detect appropriate tooltip type from content.

        Args:
            text: The tooltip text content

        Returns:
            The appropriate TooltipType string constant
        """
        text_lower = text.lower()
        if "no metadata" in text_lower or "no hash" in text_lower:
            return TooltipType.WARNING
        elif "error" in text_lower or "invalid" in text_lower:
            return TooltipType.ERROR
        return TooltipType.INFO

    def get_current_index(self) -> QModelIndex:
        """Get the currently tracked tooltip index.

        Returns:
            The QModelIndex being tracked for tooltip
        """
        return self._current_index
