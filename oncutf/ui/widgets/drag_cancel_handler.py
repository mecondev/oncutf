"""Drag Cancel Handler - Handles ESC key to cancel external drags.

Author: Michael Economou
Date: 2026-02-08

Monitors ESC key during external drag operations to cancel and hide overlay.
"""

from PyQt5.QtCore import QEvent, QObject, Qt
from PyQt5.QtWidgets import QApplication

from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.shared.timer_manager import cancel_timer, schedule_ui_update

logger = get_cached_logger(__name__)


class DragCancelHandler(QObject):
    """Event filter to handle ESC key for canceling drags."""

    def __init__(self):
        """Initialize drag cancel handler."""
        super().__init__()
        self._active = False
        self._timeout_timer_id: str | None = None
        self._was_cancelled = False

    def activate(self) -> None:
        """Activate ESC key monitoring."""
        if not self._active:
            QApplication.instance().installEventFilter(self)
            self._active = True
            self._was_cancelled = False
            if self._timeout_timer_id:
                cancel_timer(self._timeout_timer_id)
            self._timeout_timer_id = schedule_ui_update(self._auto_cancel, delay=3000)
            logger.debug("[DragCancel] ESC monitoring activated", extra={"dev_only": True})

    def deactivate(self) -> None:
        """Deactivate ESC key monitoring."""
        if self._active:
            QApplication.instance().removeEventFilter(self)
            self._active = False
            if self._timeout_timer_id:
                cancel_timer(self._timeout_timer_id)
                self._timeout_timer_id = None
            logger.debug("[DragCancel] ESC monitoring deactivated", extra={"dev_only": True})

    def _auto_cancel(self) -> None:
        if not self._active:
            return
        self._timeout_timer_id = None
        self._was_cancelled = True
        logger.info("[DragCancel] Auto-cancel after timeout")
        from oncutf.ui.widgets.drag_overlay import DragOverlayManager

        overlay_manager = DragOverlayManager.get_instance()
        overlay_manager.hide_overlay()
        self.deactivate()

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Filter events to catch ESC key.

        Args:
            obj: The object that received the event
            event: The event

        Returns:
            True if event was handled, False otherwise

        """
        if event.type() == QEvent.KeyPress and event.key() == Qt.Key_Escape:
            logger.info("[DragCancel] ESC pressed - canceling external drag")
            self._was_cancelled = True
            # Hide overlay
            from oncutf.ui.widgets.drag_overlay import DragOverlayManager

            overlay_manager = DragOverlayManager.get_instance()
            overlay_manager.hide_overlay()
            # Deactivate after handling
            self.deactivate()
            return True

        return False

    def was_cancelled(self) -> bool:
        return self._was_cancelled


# Global instance
_drag_cancel_handler: DragCancelHandler | None = None


def get_drag_cancel_handler() -> DragCancelHandler:
    """Get global drag cancel handler instance."""
    global _drag_cancel_handler
    if _drag_cancel_handler is None:
        _drag_cancel_handler = DragCancelHandler()
    return _drag_cancel_handler
