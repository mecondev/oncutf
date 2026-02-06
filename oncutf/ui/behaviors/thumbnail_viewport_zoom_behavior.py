"""Thumbnail Viewport Zoom Behavior.

Author: Michael Economou
Date: 2026-02-06

Provides zoom functionality for thumbnail viewport:
- Zoom in/out via mouse wheel (Ctrl+Wheel)
- Zoom in/out via method calls
- Reset to default size
- Updates delegate and UI components
"""

from typing import TYPE_CHECKING

from PyQt5.QtCore import QEvent, Qt

from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from collections.abc import Callable

    from PyQt5.QtGui import QWheelEvent
    from PyQt5.QtWidgets import QSlider, QWidget

    from oncutf.ui.delegates.thumbnail_delegate import ThumbnailDelegate

logger = get_cached_logger(__name__)


class ThumbnailViewportZoomBehavior:
    """Handles zoom functionality for thumbnail viewport.

    Attributes:
        MIN_SIZE: Minimum thumbnail size (64px)
        MAX_SIZE: Maximum thumbnail size (256px)
        DEFAULT_SIZE: Default thumbnail size (128px)
        STEP: Zoom step size (16px)

    """

    MIN_SIZE = 64
    MAX_SIZE = 256
    DEFAULT_SIZE = 128
    STEP = 16

    def __init__(
        self,
        list_view: "QWidget",
        delegate: "ThumbnailDelegate",
        zoom_slider: "QSlider | None" = None,
        status_update_callback: "Callable[[], None] | None" = None,
    ):
        """Initialize zoom behavior.

        Args:
            list_view: QListView widget to control
            delegate: Thumbnail delegate to update
            zoom_slider: Optional zoom slider widget
            status_update_callback: Optional callback to update status label

        """
        self._list_view = list_view
        self._delegate = delegate
        self._zoom_slider = zoom_slider
        self._status_update_callback = status_update_callback
        self._current_size = self.DEFAULT_SIZE

    def get_current_size(self) -> int:
        """Get current thumbnail size.

        Returns:
            Current size in pixels

        """
        return self._current_size

    def set_size(self, size: int) -> None:
        """Set thumbnail size and update UI.

        Args:
            size: Thumbnail size in pixels (clamped to MIN/MAX)

        """
        size = max(self.MIN_SIZE, min(size, self.MAX_SIZE))

        if size != self._current_size:
            self._current_size = size
            self._delegate.set_thumbnail_size(size)

            # Update zoom slider if it exists (without triggering valueChanged signal)
            if self._zoom_slider:
                self._zoom_slider.blockSignals(True)
                self._zoom_slider.setValue(size)
                self._zoom_slider.setToolTip(f"Zoom: {size}px")
                self._zoom_slider.blockSignals(False)

            # Update status label via callback
            if self._status_update_callback:
                self._status_update_callback()

            # Force layout update
            self._list_view.scheduleDelayedItemsLayout()

            logger.debug("[ZoomBehavior] Thumbnail size changed to: %d", size)

    def zoom_in(self) -> None:
        """Increase thumbnail size by STEP."""
        new_size = self._current_size + self.STEP
        self.set_size(new_size)

    def zoom_out(self) -> None:
        """Decrease thumbnail size by STEP."""
        new_size = self._current_size - self.STEP
        self.set_size(new_size)

    def reset(self) -> None:
        """Reset thumbnail size to default."""
        self.set_size(self.DEFAULT_SIZE)

    def handle_wheel_event(self, event: "QWheelEvent") -> bool:
        """Handle mouse wheel event for zoom.

        Args:
            event: Wheel event

        Returns:
            True if event was handled (Ctrl+Wheel), False otherwise

        """
        # Only handle Ctrl+Wheel
        if not (event.modifiers() & Qt.ControlModifier):
            return False

        if event.angleDelta().y() > 0:
            self.zoom_in()
        else:
            self.zoom_out()

        return True

    def handle_event_filter(self, obj: "QWidget", event: QEvent) -> bool:
        """Handle events from event filter.

        Args:
            obj: Watched object
            event: Event

        Returns:
            True if event handled, False otherwise

        """
        if event.type() == QEvent.Wheel:
            return self.handle_wheel_event(event)

        return False
