"""Thumbnail Viewport Tooltip Behavior.

Author: Michael Economou
Date: 2026-02-06

Provides hover tooltip functionality for thumbnail viewport items.
"""

from typing import TYPE_CHECKING

from PyQt5.QtCore import QEvent, Qt

from oncutf.ui.helpers.tooltip_helper import TooltipHelper, TooltipType
from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.shared.timer_manager import cancel_timer, schedule_dialog_close

if TYPE_CHECKING:
    from PyQt5.QtCore import QModelIndex
    from PyQt5.QtGui import QMouseEvent
    from PyQt5.QtWidgets import QListView

logger = get_cached_logger(__name__)


class ThumbnailViewportTooltipBehavior:
    """Handles hover tooltips for thumbnail viewport items."""

    def __init__(self, list_view: "QListView"):
        """Initialize tooltip behavior.

        Args:
            list_view: QListView widget to show tooltips for

        """
        self._list_view = list_view
        self._tooltip_timer_id: int | None = None
        self._tooltip_index: QModelIndex | None = None

    def schedule_tooltip(self, index: "QModelIndex") -> None:
        """Schedule tooltip display after hover delay.

        Args:
            index: Model index of item to show tooltip for

        """
        # Cancel any pending tooltip
        self.cancel_tooltip()

        self._tooltip_index = index

        # Use schedule_dialog_close for consistent tooltip delay (default 500ms)
        self._tooltip_timer_id = schedule_dialog_close(self._show_tooltip)

    def cancel_tooltip(self) -> None:
        """Cancel pending tooltip and clear active tooltip."""
        if self._tooltip_timer_id:
            cancel_timer(self._tooltip_timer_id)
            self._tooltip_timer_id = None

        TooltipHelper.clear_tooltips_for_widget(self._list_view.viewport())
        self._tooltip_index = None

    def _show_tooltip(self) -> None:
        """Show tooltip for currently hovered item."""
        if not self._tooltip_index or not self._tooltip_index.isValid():
            return

        file_item = self._tooltip_index.data(Qt.UserRole)
        if not file_item:
            return

        # Build tooltip text
        tooltip_lines = [
            f"<b>{file_item.filename}</b>",
            f"Type: {file_item.extension.upper() if file_item.extension else 'Unknown'}",
        ]

        # Add metadata if available
        if hasattr(file_item, "duration") and file_item.duration:
            tooltip_lines.append(f"Duration: {file_item.duration}")
        if hasattr(file_item, "image_size") and file_item.image_size:
            tooltip_lines.append(f"Size: {file_item.image_size}")
        if file_item.color and file_item.color.lower() != "none":
            tooltip_lines.append(f"Color: {file_item.color}")

        tooltip_text = "<br>".join(tooltip_lines)

        from oncutf.config import TOOLTIP_DURATION

        TooltipHelper.show_tooltip(
            self._list_view.viewport(),
            tooltip_text,
            TooltipType.INFO,
            duration=TOOLTIP_DURATION,
            persistent=False,
        )

    def handle_event_filter(self, obj: "QListView", event: QEvent, is_panning: bool) -> bool:
        """Handle events from event filter.

        Args:
            obj: Watched object
            event: Event
            is_panning: Whether pan is currently active (don't show tooltips while panning)

        Returns:
            True if event handled, False otherwise

        """
        event_type = event.type()

        # Handle hover for tooltips (when not panning or lasso selecting)
        if event_type == QEvent.MouseMove and not is_panning:
            index = self._list_view.indexAt(event.pos())
            if index.isValid() and index != self._tooltip_index:
                # New item hovered
                self.schedule_tooltip(index)
            elif not index.isValid() and self._tooltip_index:
                # Left item area
                self.cancel_tooltip()

        elif event_type == QEvent.Leave:
            # Clear tooltip when mouse leaves viewport
            self.cancel_tooltip()

        return False
