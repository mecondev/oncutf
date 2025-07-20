"""
Module: time_formatter.py

Author: Michael Economou
Date: 2025-06-10

time_formatter.py
Time formatting utilities for progress dialogs.
Formats elapsed and estimated time in human-readable format.
Features:
- Elapsed time formatting (3':20'', 1:24':15'')
- Estimated time formatting with ETA
- Progress rate calculation
- Cross-platform time handling
"""

import time
from typing import Optional, Tuple

from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class TimeTracker:
    """
    Tracks progress timing and calculates estimates.
    """

    def __init__(self):
        """Initialize the time tracker."""
        self.start_time = None
        self.last_update_time = None
        self.progress_history = []  # List of (timestamp, progress_percent) tuples
        self.max_history_size = 10  # Keep last 10 measurements for smoothing

    def start(self):
        """Start timing."""
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.progress_history = [(self.start_time, 0.0)]
        logger.debug("[TimeTracker] Started timing")

    def update_progress(self, current: int, total: int):
        """Update progress and calculate estimates."""
        if self.start_time is None:
            self.start()

        now = time.time()
        progress_percent = (current / total * 100) if total > 0 else 0

        # Add to history
        self.progress_history.append((now, progress_percent))

        # Keep only recent history
        if len(self.progress_history) > self.max_history_size:
            self.progress_history.pop(0)

        self.last_update_time = now

    def get_elapsed_time(self) -> float:
        """Get elapsed time in seconds."""
        if self.start_time is None:
            return 0.0
        return time.time() - self.start_time

    def get_estimated_total_time(self) -> Optional[float]:
        """Get estimated total time in seconds based on current progress rate."""
        if len(self.progress_history) < 2:
            return None

        # Use recent measurements for more accurate estimation
        recent_history = self.progress_history[-min(5, len(self.progress_history)) :]

        if len(recent_history) < 2:
            return None

        # Calculate average rate from recent history
        start_time, start_progress = recent_history[0]
        end_time, end_progress = recent_history[-1]

        time_diff = end_time - start_time
        progress_diff = end_progress - start_progress

        if time_diff <= 0 or progress_diff <= 0:
            return None

        # Calculate rate (percent per second)
        rate = progress_diff / time_diff

        # Estimate total time
        if rate > 0:
            total_time_estimate = 100 / rate
            return total_time_estimate

        return None

    def get_estimated_remaining_time(self) -> Optional[float]:
        """Get estimated remaining time in seconds."""
        total_estimate = self.get_estimated_total_time()
        if total_estimate is None:
            return None

        elapsed = self.get_elapsed_time()
        remaining = total_estimate - elapsed

        return max(0, remaining)


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string (e.g., "3':20''", "1:24':15''")
    """
    if seconds < 0:
        return "0''"

    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60

    if hours > 0:
        return f"{hours}:{minutes:02d}':'{secs:02d}''"
    elif minutes > 0:
        return f"{minutes}':'{secs:02d}''"
    else:
        return f"{secs}''"


def format_time_range(elapsed: float, estimated_total: Optional[float] = None) -> str:
    """
    Format time range showing elapsed/estimated.

    Args:
        elapsed: Elapsed time in seconds
        estimated_total: Estimated total time in seconds (optional)

    Returns:
        Formatted string (e.g., "3':20''/1:24':15''", "3':20''")
    """
    elapsed_str = format_duration(elapsed)

    if estimated_total is not None and estimated_total > 0:
        total_str = format_duration(estimated_total)
        return f"{elapsed_str}/{total_str}"
    else:
        return elapsed_str


class ProgressEstimator:
    """
    Combines time tracking with size tracking for comprehensive progress estimation.
    """

    def __init__(self):
        """Initialize the progress estimator."""
        self.time_tracker = TimeTracker()
        self.total_size = 0
        self.processed_size = 0

    def start(self, total_size: int = 0):
        """Start tracking progress."""
        self.time_tracker.start()
        self.total_size = total_size
        self.processed_size = 0

    def update(self, current_item: int, total_items: int, current_size: int = 0):
        """
        Update progress with both item count and size information.

        Args:
            current_item: Current item number (0-based)
            total_items: Total number of items
            current_size: Size processed so far (bytes)
        """
        self.time_tracker.update_progress(current_item, total_items)
        self.processed_size = current_size

    def get_size_info(self) -> Tuple[str, str]:
        """
        Get size information as formatted strings.

        Returns:
            Tuple of (processed_size_str, total_size_str)
        """
        from utils.file_size_formatter import format_file_size_system_compatible

        processed_str = format_file_size_system_compatible(self.processed_size)
        total_str = format_file_size_system_compatible(self.total_size)

        return processed_str, total_str

    def get_size_range(self) -> str:
        """
        Get size range as formatted string.

        Returns:
            Formatted string (e.g., "35MB/20GB")
        """
        processed_str, total_str = self.get_size_info()

        if self.total_size > 0:
            return f"{processed_str}/{total_str}"
        else:
            return processed_str

    def get_time_info(self) -> Tuple[float, Optional[float]]:
        """
        Get time information.

        Returns:
            Tuple of (elapsed_time, estimated_total_time)
        """
        elapsed = self.time_tracker.get_elapsed_time()
        estimated = self.time_tracker.get_estimated_total_time()
        return elapsed, estimated

    def get_time_range(self) -> str:
        """
        Get time range as formatted string.

        Returns:
            Formatted string (e.g., "3':20''/1:24':15''")
        """
        elapsed, estimated = self.get_time_info()
        return format_time_range(elapsed, estimated)

    def get_progress_summary(self) -> dict:
        """
        Get comprehensive progress summary.

        Returns:
            Dictionary with all progress information
        """
        elapsed, estimated_total = self.get_time_info()
        processed_str, total_str = self.get_size_info()

        return {
            "elapsed_time": elapsed,
            "estimated_total_time": estimated_total,
            "estimated_remaining_time": self.time_tracker.get_estimated_remaining_time(),
            "processed_size": self.processed_size,
            "total_size": self.total_size,
            "processed_size_str": processed_str,
            "total_size_str": total_str,
            "size_range": self.get_size_range(),
            "time_range": self.get_time_range(),
        }
