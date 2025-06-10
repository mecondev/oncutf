"""
Drag Manager - Unified drag & drop state management

Author: Michael Economou
Date: 2025-06-10

This module provides centralized drag & drop state management to fix
the "sticky cursor" issue where drag operations don't clean up properly.

Features:
- Global drag state tracking
- Forced cleanup timers
- Qt event filtering
- Cursor restoration
"""

from typing import Optional

from PyQt5.QtCore import QEvent, QObject, Qt, QTimer
from PyQt5.QtWidgets import QApplication

from utils.logger_helper import get_logger

logger = get_logger(__name__)


class DragManager(QObject):
    """
    Centralized drag & drop state manager.

    Solves the sticky cursor issue by providing unified cleanup
    and state tracking across all widgets.
    """

    _instance: Optional['DragManager'] = None

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)

        # Ensure singleton
        if DragManager._instance is not None:
            raise RuntimeError("DragManager is a singleton. Use get_instance()")
        DragManager._instance = self

        # Drag state
        self._drag_active = False
        self._drag_source = None

        # Cleanup timer for forced cleanup
        self._cleanup_timer = QTimer(self)
        self._cleanup_timer.setSingleShot(True)
        self._cleanup_timer.timeout.connect(self._forced_cleanup)

        # Install global event filter
        app = QApplication.instance()
        if app:
            app.installEventFilter(self)

        logger.debug("🎯 DragManager initialized")

    @classmethod
    def get_instance(cls) -> 'DragManager':
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # =====================================
    # Drag State Management
    # =====================================

    def start_drag(self, source: str) -> None:
        """
        Register the start of a drag operation.

        Args:
            source: String identifier of the drag source widget
        """
        if self._drag_active:
            logger.warning(f"🎯 Drag already active from {self._drag_source}, starting new from {source}")

        self._drag_active = True
        self._drag_source = source

        # Start safety timer (5 seconds max drag duration)
        self._cleanup_timer.start(5000)

        logger.debug(f"🎯 Drag started from: {source}")

    def end_drag(self, source: str = None) -> None:
        """
        Register the end of a drag operation.

        Args:
            source: Optional source identifier for verification
        """
        if not self._drag_active:
            logger.debug("🎯 Drag end called but no drag active")
            return

        if source and source != self._drag_source:
            logger.warning(f"🎯 Drag end from {source} but started from {self._drag_source}")

        self._perform_cleanup()
        logger.debug(f"🎯 Drag ended from: {source or self._drag_source}")

    def is_drag_active(self) -> bool:
        """Check if a drag operation is currently active."""
        return self._drag_active

    def get_drag_source(self) -> Optional[str]:
        """Get the current drag source identifier."""
        return self._drag_source

    # =====================================
    # Cleanup Operations
    # =====================================

    def _perform_cleanup(self) -> None:
        """Perform actual cleanup operations."""
        # Stop timer
        if self._cleanup_timer.isActive():
            self._cleanup_timer.stop()

        # Restore cursor(s)
        cursor_count = 0
        while QApplication.overrideCursor():
            QApplication.restoreOverrideCursor()
            cursor_count += 1
            if cursor_count > 10:  # Safety limit
                logger.warning("🎯 Too many override cursors, breaking loop")
                break

        if cursor_count > 0:
            logger.debug(f"🎯 Restored {cursor_count} override cursors")

        # Reset state
        self._drag_active = False
        self._drag_source = None

        # Force UI update
        QApplication.processEvents()

    def _forced_cleanup(self) -> None:
        """Forced cleanup triggered by timer."""
        logger.warning(f"🎯 Forced drag cleanup after timeout (source: {self._drag_source})")
        self._perform_cleanup()

    def force_cleanup(self) -> None:
        """Public method to force immediate cleanup."""
        logger.info("🎯 Manual forced cleanup requested")
        self._perform_cleanup()

    # =====================================
    # Event Filtering
    # =====================================

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Global event filter to catch drag termination events."""
        if not self._drag_active:
            return False

        event_type = event.type()

        # Mouse events that should terminate drag
        if event_type in (QEvent.MouseButtonPress, QEvent.MouseButtonRelease):
            if event_type == QEvent.MouseButtonRelease:
                # Give a small delay for the drag operation to complete naturally
                QTimer.singleShot(100, self._check_and_cleanup)
            return False

        # Escape key terminates drag
        if event_type == QEvent.KeyPress:
            if hasattr(event, 'key') and event.key() == Qt.Key_Escape:
                logger.debug("🎯 Escape key pressed during drag, forcing cleanup")
                self.force_cleanup()
                return True  # Consume the escape key

        return False

    def _check_and_cleanup(self) -> None:
        """Check if drag is still active and cleanup if needed."""
        if self._drag_active:
            logger.debug("🎯 Drag still active after mouse release, performing cleanup")
            self._perform_cleanup()


# Global convenience functions
def start_drag(source: str) -> None:
    """Start a drag operation from the specified source."""
    DragManager.get_instance().start_drag(source)

def end_drag(source: str = None) -> None:
    """End a drag operation."""
    DragManager.get_instance().end_drag(source)

def force_cleanup_drag() -> None:
    """Force immediate drag cleanup."""
    DragManager.get_instance().force_cleanup()

def is_dragging() -> bool:
    """Check if a drag operation is active."""
    return DragManager.get_instance().is_drag_active()
