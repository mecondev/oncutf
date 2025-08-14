"""Centralized drag & drop state manager.

Solves the sticky cursor issue by providing unified cleanup
and state tracking across all widgets.

Author: Michael Economou
Date: 2025-05-31
"""


from core.pyqt_imports import QApplication, QEvent, QObject, Qt, QTimer
from utils.logger_factory import get_cached_logger
from utils.timer_manager import schedule_drag_cleanup

logger = get_cached_logger(__name__)


class DragManager(QObject):
    """
    Centralized drag & drop state manager.

    Solves the sticky cursor issue by providing unified cleanup
    and state tracking across all widgets.
    """

    _instance: "DragManager | None" = None

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)

        # Ensure singleton
        if DragManager._instance is not None:
            raise RuntimeError("DragManager is a singleton. Use get_instance()")
        DragManager._instance = self

        # Drag state
        self._drag_active = False
        self._drag_source = None
        self._drag_start_time = None  # Track when drag started
        self._cleanup_count = 0  # Track cleanup attempts
        self._last_cleanup_time = None  # Prevent excessive cleanup

        # Primary cleanup timer - only one timer active at a time
        self._cleanup_timer = QTimer(self)
        self._cleanup_timer.setSingleShot(True)
        self._cleanup_timer.timeout.connect(self._safety_cleanup)

        # Install global event filter
        app = QApplication.instance()
        if app:
            app.installEventFilter(self)

        logger.debug("[DragManager] Initialized with smart cleanup", extra={"dev_only": True})

    @classmethod
    def get_instance(cls) -> "DragManager":
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
            logger.warning(f"[DragManager] Drag already active from {self._drag_source}")
            return  # Don't interrupt active drag

        import time

        self._drag_active = True
        self._drag_source = source
        self._drag_start_time = time.time()

        # Reset cleanup count for new drag
        self._cleanup_count = 0

        # Start safety timer (longer timeout - 10 seconds)
        self._cleanup_timer.start(10000)

        logger.debug(f"[DragManager] Drag started from: {source}", extra={"dev_only": True})

    def end_drag(self, source: str = None) -> None:
        """
        Register the end of a drag operation.

        Args:
            source: Optional source identifier for verification
        """
        if not self._drag_active:
            logger.debug(
                "[DragManager] Drag end called but no drag active", extra={"dev_only": True}
            )
            return

        if source and source != self._drag_source:
            logger.warning(
                f"[DragManager] Drag end from {source} but started from {self._drag_source}"
            )

        self._perform_cleanup()
        logger.debug(
            f"[DragManager] Drag ended from: {source or self._drag_source}",
            extra={"dev_only": True},
        )

    def is_drag_active(self) -> bool:
        """Check if a drag operation is currently active."""
        return self._drag_active

    def get_drag_source(self) -> str | None:
        """Get the current drag source identifier."""
        return self._drag_source

    # =====================================
    # Cleanup Operations
    # =====================================

    def _can_cleanup(self) -> bool:
        """Check if cleanup is allowed (prevent excessive cleanup)."""
        if self._last_cleanup_time is None:
            return True

        import time

        elapsed = time.time() - self._last_cleanup_time
        return elapsed > 0.5  # Minimum 500ms between cleanups

    def _perform_cleanup(self) -> None:
        """Perform actual cleanup operations."""
        if not self._can_cleanup():
            logger.debug(
                "[DragManager] Cleanup skipped - too soon after last cleanup",
                extra={"dev_only": True},
            )
            return

        import time

        self._last_cleanup_time = time.time()
        self._cleanup_count += 1

        # Stop timer
        if self._cleanup_timer.isActive():
            self._cleanup_timer.stop()

        # Restore all override cursors (with safety limit)
        cursor_count = 0
        while QApplication.overrideCursor() and cursor_count < 5:
            QApplication.restoreOverrideCursor()
            cursor_count += 1

        if cursor_count > 0:
            logger.debug(
                f"[DragManager] Restored {cursor_count} override cursors", extra={"dev_only": True}
            )

        # Reset state
        self._drag_active = False
        self._drag_source = None
        self._drag_start_time = None

        logger.debug(
            f"[DragManager] Cleanup completed (attempt #{self._cleanup_count})",
            extra={"dev_only": True},
        )

    def _force_restore_cursor(self) -> None:
        """Force restore cursor to normal state with extra safety measures."""
        try:
            # First, try normal restoration
            cursor_count = 0
            while QApplication.overrideCursor() and cursor_count < 10:
                QApplication.restoreOverrideCursor()
                cursor_count += 1

            # If we restored cursors, log it
            if cursor_count > 0:
                logger.debug(
                    f"[DragManager] Force-restored {cursor_count} override cursors",
                    extra={"dev_only": True},
                )

            # As a last resort, set cursor explicitly to arrow
            if QApplication.overrideCursor():
                QApplication.setOverrideCursor(Qt.ArrowCursor)
                logger.debug(
                    "[DragManager] Set explicit arrow cursor as fallback", extra={"dev_only": True}
                )

        except Exception as e:
            logger.warning(f"[DragManager] Error during cursor restoration: {e}")

    def _safety_cleanup(self) -> None:
        """Safety cleanup triggered by timer (only for stuck drags)."""
        if self._drag_active:
            logger.warning(
                f"[DragManager] Safety cleanup after timeout (source: {self._drag_source})"
            )

            # Force cursor restoration before general cleanup
            self._force_restore_cursor()

            self._perform_cleanup()

    def force_cleanup(self) -> None:
        """Public method to force immediate cleanup (used by Escape key)."""
        if not self._drag_active:
            logger.debug(
                "[DragManager] Force cleanup called but no drag active", extra={"dev_only": True}
            )
            return

        logger.info("[DragManager] Manual forced cleanup requested", extra={"dev_only": True})
        self._perform_cleanup()

    # =====================================
    # Event Filtering
    # =====================================

    def eventFilter(self, _obj: QObject, event: QEvent) -> bool:
        """Global event filter to catch drag termination events."""
        if not self._drag_active:
            return False

        event_type = event.type()

        # Key events - only Escape terminates drag
        if event_type == QEvent.KeyPress:
            if hasattr(event, "key"):
                key = event.key()
                if key == Qt.Key_Escape:
                    logger.debug(
                        "[DragManager] Escape key pressed during drag", extra={"dev_only": True}
                    )

                    # Check if FileLoadingDialog is active
                    from widgets.metadata_waiting_dialog import MetadataWaitingDialog

                    active_dialogs = [
                        w
                        for w in QApplication.topLevelWidgets()
                        if isinstance(w, MetadataWaitingDialog) and w.isVisible()
                    ]

                    if active_dialogs:
                        logger.debug(
                            "[DragManager] FileLoadingDialog is active, allowing it to handle ESC",
                            extra={"dev_only": True},
                        )
                        return False  # Let dialog handle ESC

                    # Force cleanup on ESC
                    self.force_cleanup()
                    return True  # Event handled

        # Mouse release - check after a delay
        if event_type == QEvent.MouseButtonRelease:  # type: ignore
            # Give more time for normal drag completion
            schedule_drag_cleanup(self._check_and_cleanup, 200)

        # Window focus events - only after significant time
        if event_type in (QEvent.WindowDeactivate, QEvent.ApplicationDeactivate):  # type: ignore
            if self._drag_start_time:
                import time

                elapsed = time.time() - self._drag_start_time
                if elapsed > 3.0:  # Only cleanup after 3 seconds
                    logger.debug(
                        "[DragManager] Window deactivated after long drag", extra={"dev_only": True}
                    )
                    schedule_drag_cleanup(self.force_cleanup, 500)

        return False

    def _check_and_cleanup(self) -> None:
        """Check if drag is still active and cleanup if needed."""
        if self._drag_active:
            # Check if it's been long enough to consider it stuck
            if self._drag_start_time:
                import time

                elapsed = time.time() - self._drag_start_time
                if elapsed > 2.0:  # Only cleanup long-running drags
                    logger.debug(
                        "[DragManager] Long drag still active after mouse release",
                        extra={"dev_only": True},
                    )
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
