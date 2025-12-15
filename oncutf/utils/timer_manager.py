"""
Module: timer_manager.py

Author: Michael Economou
Date: 2025-05-31

timer_manager.py
Centralized timer management system for improved performance and better control.
Provides optimized timer operations with automatic cleanup and debugging capabilities.
"""

import threading
import weakref
from collections.abc import Callable
from enum import Enum

from core.pyqt_imports import QObject, QTimer, pyqtSignal
from oncutf.utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class TimerPriority(Enum):
    """Timer priority levels for better scheduling."""

    IMMEDIATE = 0  # 0ms - immediate execution
    HIGH = 5  # 5ms - high priority UI updates
    NORMAL = 15  # 15ms - normal UI operations
    LOW = 50  # 50ms - low priority operations
    BACKGROUND = 100  # 100ms - background tasks
    CLEANUP = 200  # 200ms - cleanup operations
    DELAYED = 500  # 500ms - delayed operations


class TimerType(Enum):
    """Common timer operation types."""

    UI_UPDATE = "ui_update"
    DRAG_CLEANUP = "drag_cleanup"
    SELECTION_UPDATE = "selection_update"
    METADATA_LOAD = "metadata_load"
    SCROLL_ADJUST = "scroll_adjust"
    RESIZE_ADJUST = "resize_adjust"
    PREVIEW_UPDATE = "preview_update"
    STATUS_UPDATE = "status_update"
    GENERIC = "generic"


class TimerManager(QObject):
    """
    Centralized timer management with optimization and debugging capabilities.

    Features:
    - Automatic timer cleanup
    - Priority-based scheduling
    - Timer consolidation for similar operations
    - Memory leak prevention
    - Performance monitoring
    """

    # Signals for monitoring
    timer_started = pyqtSignal(str, int)  # timer_id, delay
    timer_finished = pyqtSignal(str)  # timer_id

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)

        # Thread safety
        self._lock = threading.RLock()

        # Active timers tracking
        self._active_timers: dict[str, QTimer] = {}
        self._timer_callbacks: dict[str, Callable] = {}
        self._timer_types: dict[str, TimerType] = {}

        # Performance tracking
        self._timer_count = 0
        self._completed_timers = 0

        # Cleanup tracking
        self._cleanup_refs: set[weakref.ref] = set()

        # Health tracking
        self._last_error: str | None = None
        self._failed_callbacks: int = 0

        logger.debug(
            "[TimerManager] Initialized with centralized timer control", extra={"dev_only": True}
        )

    def schedule(
        self,
        callback: Callable,
        delay: int | None = None,
        priority: TimerPriority = TimerPriority.NORMAL,
        timer_type: TimerType = TimerType.GENERIC,
        timer_id: str | None = None,
        consolidate: bool = True,
    ) -> str:
        """
        Schedule a callback to run after a delay.

        Args:
            callback: Function to call
            delay: Delay in milliseconds (None uses priority default)
            priority: Timer priority level
            timer_type: Type of operation for consolidation
            timer_id: Custom timer ID (auto-generated if None)
            consolidate: Whether to consolidate similar timers

        Returns:
            str: Timer ID for tracking/cancellation
        """
        with self._lock:
            # Use priority default delay if not specified
            if delay is None:
                delay = priority.value

            # Generate timer ID if not provided
            if timer_id is None:
                timer_id = f"{timer_type.value}_{self._timer_count}"
                self._timer_count += 1

            # Consolidate similar timers if requested
            if consolidate:
                existing_id = self._find_consolidatable_timer(timer_type, delay)
                if existing_id:
                    logger.debug(
                        f"[TimerManager] Consolidating timer {timer_id} with {existing_id}",
                        extra={"dev_only": True},
                    )
                    # Cancel the new timer request and use existing
                    return existing_id

            # Cancel existing timer with same ID
            if timer_id in self._active_timers:
                self.cancel(timer_id)

            # Create new timer
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(lambda: self._on_timer_finished(timer_id))

            # Store timer info
            self._active_timers[timer_id] = timer
            self._timer_callbacks[timer_id] = callback
            self._timer_types[timer_id] = timer_type

            # Start timer
            timer.start(delay)

            logger.debug(
                f"[TimerManager] Scheduled {timer_type.value} timer '{timer_id}' with {delay}ms delay",
                extra={"dev_only": True},
            )
            self.timer_started.emit(timer_id, delay)

            return timer_id

    def cancel(self, timer_id: str) -> bool:
        """
        Cancel a scheduled timer.

        Args:
            timer_id: Timer ID to cancel

        Returns:
            bool: True if timer was cancelled, False if not found
        """
        if timer_id not in self._active_timers:
            return False

        timer = self._active_timers[timer_id]
        timer.stop()
        timer.deleteLater()

        # Cleanup references
        del self._active_timers[timer_id]
        del self._timer_callbacks[timer_id]
        del self._timer_types[timer_id]

        logger.debug(f"[TimerManager] Cancelled timer '{timer_id}'", extra={"dev_only": True})
        return True

    def cancel_by_type(self, timer_type: TimerType) -> int:
        """
        Cancel all timers of a specific type.

        Args:
            timer_type: Type of timers to cancel

        Returns:
            int: Number of timers cancelled
        """
        # Create a copy to avoid dictionary changed size during iteration
        timer_items = list(self._timer_types.items())
        to_cancel = [timer_id for timer_id, t_type in timer_items if t_type == timer_type]

        cancelled_count = 0
        for timer_id in to_cancel:
            if self.cancel(timer_id):
                cancelled_count += 1

        if cancelled_count > 0:
            logger.debug(
                f"[TimerManager] Cancelled {cancelled_count} timers of type {timer_type.value}",
                extra={"dev_only": True},
            )

        return cancelled_count

    def _find_consolidatable_timer(self, timer_type: TimerType, delay: int) -> str | None:
        """Find existing timer that can be consolidated with new request."""
        # Create a copy of the items to avoid dictionary changed size during iteration
        timer_items = list(self._timer_types.items())

        for timer_id, existing_type in timer_items:
            if existing_type == timer_type:
                existing_timer = self._active_timers.get(timer_id)
                if existing_timer:
                    try:
                        # Check if timer is still active (protect against deleted timers)
                        if existing_timer.isActive():
                            # Check if delays are similar (within 10ms)
                            remaining = existing_timer.remainingTime()
                            if abs(remaining - delay) <= 10:
                                return timer_id
                    except RuntimeError:
                        # Timer has been deleted, remove it from our tracking
                        logger.debug(
                            f"[TimerManager] Removing deleted timer '{timer_id}'",
                            extra={"dev_only": True},
                        )
                        self._cleanup_deleted_timer(timer_id)
        return None

    def _cleanup_deleted_timer(self, timer_id: str) -> None:
        """Clean up references to a deleted timer."""
        if timer_id in self._active_timers:
            del self._active_timers[timer_id]
        if timer_id in self._timer_callbacks:
            del self._timer_callbacks[timer_id]
        if timer_id in self._timer_types:
            del self._timer_types[timer_id]

    def _on_timer_finished(self, timer_id: str) -> None:
        """Handle timer completion."""
        if timer_id not in self._active_timers:
            return

        callback = self._timer_callbacks.get(timer_id)
        timer_type = self._timer_types.get(timer_id)

        # Cleanup timer references
        timer = self._active_timers[timer_id]
        timer.deleteLater()
        del self._active_timers[timer_id]
        del self._timer_callbacks[timer_id]
        del self._timer_types[timer_id]

        # Execute callback
        if callback:
            try:
                callback()
                self._completed_timers += 1
                logger.debug(
                    f"[TimerManager] Executed {timer_type.value if timer_type else 'unknown'} timer '{timer_id}'",
                    extra={"dev_only": True},
                )
            except Exception as e:
                logger.error(f"[TimerManager] Error executing timer '{timer_id}': {e}")
                self._last_error = f"Timer {timer_id}: {e}"
                self._failed_callbacks += 1

        self.timer_finished.emit(timer_id)

    def get_active_count(self) -> int:
        """Get number of active timers."""
        return len(self._active_timers)

    def get_stats(self) -> dict[str, int]:
        """Get timer statistics."""
        return {
            "active_timers": len(self._active_timers),
            "total_scheduled": self._timer_count,
            "completed_timers": self._completed_timers,
            "pending_timers": len(self._active_timers),
        }

    def cleanup_all(self) -> int:
        """Cancel all active timers and cleanup."""
        cancelled_count = len(self._active_timers)

        for timer in self._active_timers.values():
            timer.stop()
            timer.deleteLater()

        self._active_timers.clear()
        self._timer_callbacks.clear()
        self._timer_types.clear()

        if cancelled_count > 0:
            logger.debug(
                f"[TimerManager] Cleaned up {cancelled_count} active timers",
                extra={"dev_only": True},
            )

        return cancelled_count

    def is_healthy(self) -> bool:
        """Check if timer manager is healthy.

        Returns:
            True if operating normally.
        """
        # Consider unhealthy if too many callbacks have failed
        return self._failed_callbacks < 10

    def last_error(self) -> str | None:
        """Get the last error message.

        Returns:
            Last error message or None if no errors.
        """
        return self._last_error

    def health_check(self) -> dict[str, any]:
        """Perform comprehensive health check.

        Returns:
            Dictionary with health status and metrics.
        """
        with self._lock:
            return {
                "healthy": self.is_healthy(),
                "active_timers": len(self._active_timers),
                "total_scheduled": self._timer_count,
                "completed": self._completed_timers,
                "failed_callbacks": self._failed_callbacks,
                "last_error": self._last_error,
            }


# Global timer manager instance
_timer_manager: TimerManager | None = None


def get_timer_manager() -> TimerManager:
    """Get the global timer manager instance."""
    global _timer_manager
    if _timer_manager is None:
        _timer_manager = TimerManager()
    return _timer_manager


# Convenience functions for common operations
def schedule_ui_update(callback: Callable, delay: int = 15, timer_id: str | None = None) -> str:
    """Schedule a UI update operation."""
    return get_timer_manager().schedule(
        callback, delay, TimerPriority.NORMAL, TimerType.UI_UPDATE, timer_id
    )


def schedule_drag_cleanup(callback: Callable, delay: int = 50, timer_id: str | None = None) -> str:
    """Schedule a drag cleanup operation."""
    return get_timer_manager().schedule(
        callback, delay, TimerPriority.LOW, TimerType.DRAG_CLEANUP, timer_id
    )


def schedule_selection_update(
    callback: Callable, delay: int = 15, timer_id: str | None = None
) -> str:
    """Schedule a selection update operation."""
    return get_timer_manager().schedule(
        callback, delay, TimerPriority.NORMAL, TimerType.SELECTION_UPDATE, timer_id
    )


def schedule_metadata_load(
    callback: Callable, delay: int = 100, timer_id: str | None = None
) -> str:
    """Schedule a metadata loading operation."""
    return get_timer_manager().schedule(
        callback, delay, TimerPriority.BACKGROUND, TimerType.METADATA_LOAD, timer_id
    )


def schedule_scroll_adjust(callback: Callable, delay: int = 10, timer_id: str | None = None) -> str:
    """Schedule a scroll adjustment operation."""
    return get_timer_manager().schedule(
        callback, delay, TimerPriority.HIGH, TimerType.SCROLL_ADJUST, timer_id
    )


def schedule_preview_update(callback: Callable, delay: int = 300, timer_id: str | None = None) -> str:
    """Schedule a preview update operation with debounce."""
    return get_timer_manager().schedule(
        callback, delay, TimerPriority.NORMAL, TimerType.PREVIEW_UPDATE, timer_id
    )


def schedule_resize_adjust(callback: Callable, delay: int = 10, timer_id: str | None = None) -> str:
    """Schedule a resize adjustment operation."""
    return get_timer_manager().schedule(
        callback, delay, TimerPriority.HIGH, TimerType.RESIZE_ADJUST, timer_id
    )


def schedule_dialog_close(callback: Callable, delay: int = 500, timer_id: str | None = None) -> str:
    """Schedule a dialog close operation with delay."""
    return get_timer_manager().schedule(
        callback, delay, TimerPriority.DELAYED, TimerType.GENERIC, timer_id
    )


def cancel_timer(timer_id: str) -> bool:
    """Cancel a specific timer."""
    return get_timer_manager().cancel(timer_id)


def cancel_timers_by_type(timer_type: TimerType) -> int:
    """Cancel all timers of a specific type."""
    return get_timer_manager().cancel_by_type(timer_type)


def cleanup_all_timers() -> int:
    """Cancel all active timers."""
    return get_timer_manager().cleanup_all()
