"""Centralized drag & drop state manager.

Solves the sticky cursor issue by providing unified cleanup
and state tracking across all widgets.

Author: Michael Economou
Date: 2025-05-31
"""

from oncutf.core.pyqt_imports import QApplication, QEvent, QObject, Qt
from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.shared.timer_manager import cancel_timer, schedule_drag_cleanup

logger = get_cached_logger(__name__)


class DragManager(QObject):
    """Centralized drag & drop state manager.

    Solves the sticky cursor issue by providing unified cleanup
    and state tracking across all widgets.
    """

    _instance: "DragManager | None" = None

    def __init__(self, parent: QObject | None = None):
        """Initialize singleton drag manager with state tracking."""
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

        # Safety cleanup timer ID (managed by TimerManager)
        self._cleanup_timer_id: str | None = None

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
        """Register the start of a drag operation.

        Args:
            source: String identifier of the drag source widget

        """
        if self._drag_active:
            logger.warning("[DragManager] Drag already active from %s", self._drag_source)
            return  # Don't interrupt active drag

        import time

        self._drag_active = True
        self._drag_source = source
        self._drag_start_time = time.time()

        # Reset cleanup count for new drag
        self._cleanup_count = 0

        # Start safety timer via TimerManager (10 second timeout)
        # Cancel previous timer if still active
        if self._cleanup_timer_id:
            cancel_timer(self._cleanup_timer_id)
        self._cleanup_timer_id = schedule_drag_cleanup(self._safety_cleanup, delay=10000)

        logger.debug("[DragManager] Drag started from: %s", source, extra={"dev_only": True})

    def end_drag(self, source: str = None) -> None:
        """Register the end of a drag operation.

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
                "[DragManager] Drag end from %s but started from %s",
                source,
                self._drag_source,
            )

        self._perform_cleanup()
        logger.debug(
            "[DragManager] Drag ended from: %s",
            source or self._drag_source,
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

        # Stop timer via TimerManager
        if self._cleanup_timer_id:
            cancel_timer(self._cleanup_timer_id)
            self._cleanup_timer_id = None

        # Restore all override cursors (with safety limit)
        cursor_count = 0
        while QApplication.overrideCursor() and cursor_count < 5:
            QApplication.restoreOverrideCursor()
            cursor_count += 1

        if cursor_count > 0:
            logger.debug(
                "[DragManager] Restored %d override cursors",
                cursor_count,
                extra={"dev_only": True},
            )

        # Reset state
        self._drag_active = False
        self._drag_source = None
        self._drag_start_time = None

        logger.debug(
            "[DragManager] Cleanup completed (attempt #%d)",
            self._cleanup_count,
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
                    "[DragManager] Force-restored %d override cursors",
                    cursor_count,
                    extra={"dev_only": True},
                )

            # As a last resort, set cursor explicitly to arrow
            if QApplication.overrideCursor():
                QApplication.setOverrideCursor(Qt.ArrowCursor)
                logger.debug(
                    "[DragManager] Set explicit arrow cursor as fallback", extra={"dev_only": True}
                )

        except Exception as e:
            logger.warning("[DragManager] Error during cursor restoration: %s", e)

    def _safety_cleanup(self) -> None:
        """Safety cleanup triggered by timer (only for stuck drags)."""
        if self._drag_active:
            logger.debug(
                "[DragManager] Safety cleanup after timeout (source: %s)",
                self._drag_source,
                extra={"dev_only": True},
            )

            # Force cursor restoration before general cleanup
            self._force_restore_cursor()

            self._perform_cleanup()

    def force_cleanup(self) -> None:
        """Public method to force immediate cleanup (used by Escape key).

        This is called when ESC is pressed during a drag operation.
        It immediately terminates the drag and cleans up all visual feedback.
        """
        if not self._drag_active:
            logger.debug(
                "[DragManager] Force cleanup called but no drag active", extra={"dev_only": True}
            )
            return

        logger.info(
            "[DragManager] Force cleanup requested (ESC pressed) - terminating drag immediately"
        )

        # First, end all visual feedback immediately
        from oncutf.core.drag.drag_visual_manager import end_drag_visual

        end_drag_visual()

        # Then perform standard cleanup (cursors, state)
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

                    # Check if ProgressDialog is active
                    from oncutf.utils.ui.progress_dialog import ProgressDialog

                    active_dialogs = [
                        w
                        for w in QApplication.topLevelWidgets()
                        if isinstance(w, ProgressDialog) and w.isVisible()
                    ]

                    if active_dialogs:
                        logger.debug(
                            "[DragManager] ProgressDialog is active, allowing it to handle ESC",
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
