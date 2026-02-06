"""Thumbnail Viewport Pan Behavior.

Author: Michael Economou
Date: 2026-02-06

Provides pan (drag scroll) functionality for thumbnail viewport using middle mouse button.
"""

from typing import TYPE_CHECKING

from PyQt5.QtCore import QEvent, QPoint, Qt

from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from PyQt5.QtGui import QMouseEvent
    from PyQt5.QtWidgets import QListView

logger = get_cached_logger(__name__)


class ThumbnailViewportPanBehavior:
    """Handles middle mouse button pan (drag scroll) for thumbnail viewport."""

    def __init__(self, list_view: "QListView"):
        """Initialize pan behavior.

        Args:
            list_view: QListView widget to control

        """
        self._list_view = list_view
        self._is_panning = False
        self._pan_start_pos: QPoint | None = None

    def is_panning(self) -> bool:
        """Check if currently panning.

        Returns:
            True if panning is active

        """
        return self._is_panning

    def start_pan(self, pos: QPoint) -> None:
        """Start panning operation.

        Args:
            pos: Mouse position where pan started

        """
        self._is_panning = True
        self._pan_start_pos = pos
        self._list_view.viewport().setCursor(Qt.ClosedHandCursor)
        logger.debug("[PanBehavior] Pan started at %s", pos)

    def update_pan(self, pos: QPoint) -> None:
        """Update pan position (move viewport).

        Args:
            pos: Current mouse position

        """
        if not self._is_panning or not self._pan_start_pos:
            return

        delta = pos - self._pan_start_pos
        h_bar = self._list_view.horizontalScrollBar()
        v_bar = self._list_view.verticalScrollBar()

        h_bar.setValue(h_bar.value() - delta.x())
        v_bar.setValue(v_bar.value() - delta.y())

        self._pan_start_pos = pos

    def end_pan(self) -> None:
        """End panning operation."""
        if not self._is_panning:
            return

        self._is_panning = False
        self._pan_start_pos = None
        self._list_view.viewport().setCursor(Qt.ArrowCursor)
        logger.debug("[PanBehavior] Pan ended")

    def handle_event_filter(self, obj: "QListView", event: QEvent) -> bool:
        """Handle events from event filter.

        Args:
            obj: Watched object
            event: Event

        Returns:
            True if event handled, False otherwise

        """
        event_type = event.type()

        # Middle button press - start pan
        if event_type == QEvent.MouseButtonPress:
            if event.button() == Qt.MiddleButton:
                self.start_pan(event.pos())
                return True

        # Mouse move - update pan
        elif event_type == QEvent.MouseMove:
            if self._is_panning and self._pan_start_pos:
                self.update_pan(event.pos())
                return True

        # Middle button release - end pan
        elif (
            event_type == QEvent.MouseButtonRelease
            and event.button() == Qt.MiddleButton
            and self._is_panning
        ):
            self.end_pan()
            return True

        return False
