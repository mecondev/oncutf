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
        self._drag_start_time = None  # Track when drag started

        # Cleanup timer for forced cleanup (shorter interval)
        self._cleanup_timer = QTimer(self)
        self._cleanup_timer.setSingleShot(True)
        self._cleanup_timer.timeout.connect(self._forced_cleanup)

        # Monitoring timer for stuck states (every 2 seconds, less aggressive)
        self._monitor_timer = QTimer(self)
        self._monitor_timer.timeout.connect(self._check_stuck_state)
        self._monitor_timer.setInterval(2000)  # Increased from 500ms to 2 seconds

        # Install global event filter
        app = QApplication.instance()
        if app:
            app.installEventFilter(self)

        logger.debug("[DragManager] Initialized with enhanced monitoring")

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
            logger.warning(f"[DragManager] Drag already active from {self._drag_source}, forcing cleanup first")
            self._perform_cleanup()

        import time
        self._drag_active = True
        self._drag_source = source
        self._drag_start_time = time.time()

        # Start safety timer (5 seconds max drag duration - back to original)
        self._cleanup_timer.start(5000)

        # Start monitoring timer (disabled for now)
        # self._monitor_timer.start()

        logger.debug(f"[DragManager] Drag started from: {source}")

    def end_drag(self, source: str = None) -> None:
        """
        Register the end of a drag operation.

        Args:
            source: Optional source identifier for verification
        """
        if not self._drag_active:
            logger.debug("[DragManager] Drag end called but no drag active")
            return

        if source and source != self._drag_source:
            logger.warning(f"[DragManager] Drag end from {source} but started from {self._drag_source}")

        self._perform_cleanup()
        logger.debug(f"[DragManager] Drag ended from: {source or self._drag_source}")

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
        # Stop timers
        if self._cleanup_timer.isActive():
            self._cleanup_timer.stop()
        if self._monitor_timer.isActive():
            self._monitor_timer.stop()

        # Simple cursor restoration - just remove override cursors
        cursor_count = 0
        while QApplication.overrideCursor():
            QApplication.restoreOverrideCursor()
            cursor_count += 1
            if cursor_count > 10:  # Reasonable safety limit
                logger.warning("[DragManager] Too many override cursors, breaking loop")
                break

        if cursor_count > 0:
            logger.debug(f"[DragManager] Restored {cursor_count} override cursors")

        # Reset state
        self._drag_active = False
        self._drag_source = None
        self._drag_start_time = None

        # Simple UI update
        QApplication.processEvents()

        logger.debug("[DragManager] Cleanup completed")

    def _forced_cleanup(self) -> None:
        """Forced cleanup triggered by timer."""
        logger.warning(f"[DragManager] Forced drag cleanup after timeout (source: {self._drag_source})")
        self._perform_cleanup()

    def force_cleanup(self) -> None:
        """Public method to force immediate cleanup."""
        logger.info("[DragManager] Manual forced cleanup requested")
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
        if event_type in (QEvent.MouseButtonPress, QEvent.MouseButtonRelease, QEvent.MouseButtonDblClick):
            if event_type in (QEvent.MouseButtonRelease, QEvent.MouseButtonDblClick):
                # Give a small delay for the drag operation to complete naturally
                QTimer.singleShot(100, self._check_and_cleanup)
            elif event_type == QEvent.MouseButtonPress:
                # New mouse press during drag - check if it's been active long enough
                if self._drag_start_time:
                    import time
                    elapsed = time.time() - self._drag_start_time
                    if elapsed > 1.0:  # Only force cleanup if drag has been active for more than 1 second
                        QTimer.singleShot(10, self.force_cleanup)
            return False

        # Key events - only handle Escape
        if event_type == QEvent.KeyPress:
            if hasattr(event, 'key'):
                key = event.key()
                # Only Escape key terminates drag
                if key == Qt.Key_Escape:
                    logger.debug("[DragManager] Escape key pressed during drag, forcing cleanup")
                    self.force_cleanup()
                    return True  # Consume the escape key

        return False

    def _check_and_cleanup(self) -> None:
        """Check if drag is still active and cleanup if needed."""
        if self._drag_active:
            logger.debug("[DragManager] Drag still active after mouse release, performing cleanup")
            self._perform_cleanup()

    def _check_stuck_state(self) -> None:
        """Check for stuck states and force cleanup if needed."""
        if self._drag_active and self._drag_start_time:
            import time
            elapsed = time.time() - self._drag_start_time
            # Only consider it stuck if it's been active for more than 3 seconds
            if elapsed > 3.0:
                logger.warning(f"[DragManager] Drag stuck for {elapsed:.1f}s, forcing cleanup")
                self._perform_cleanup()
            else:
                logger.debug(f"[DragManager] Drag active for {elapsed:.1f}s, still normal")


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
