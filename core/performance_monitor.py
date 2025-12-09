"""
Module: performance_monitor.py

Author: Michael Economou
Date: 2025-05-01

Performance Monitor for UnifiedRenameEngine
Provides metrics and monitoring for rename operations.
"""

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


@dataclass
class PerformanceMetric:
    """Single performance metric."""

    operation: str
    duration: float
    file_count: int
    timestamp: float
    success: bool = True
    error_message: str = ""


@dataclass
class PerformanceStats:
    """Performance statistics."""

    total_operations: int = 0
    total_duration: float = 0.0
    total_files: int = 0
    average_duration: float = 0.0
    average_files_per_operation: float = 0.0
    success_rate: float = 1.0
    error_count: int = 0

    # Recent performance (last 10 operations)
    recent_durations: deque = field(default_factory=lambda: deque(maxlen=10))
    recent_file_counts: deque = field(default_factory=lambda: deque(maxlen=10))

    def update(self, metric: "PerformanceMetric"):
        """Update stats with new metric."""
        self.total_operations += 1
        self.total_duration += metric.duration
        self.total_files += metric.file_count

        # Update averages
        self.average_duration = self.total_duration / self.total_operations
        self.average_files_per_operation = self.total_files / self.total_operations

        # Update recent metrics
        self.recent_durations.append(metric.duration)
        self.recent_file_counts.append(metric.file_count)

        # Update success rate
        if not metric.success:
            self.error_count += 1
        self.success_rate = (self.total_operations - self.error_count) / self.total_operations


class PerformanceMonitor:
    """Performance monitor for UnifiedRenameEngine."""

    def __init__(self):
        self.metrics: list[PerformanceMetric] = []
        self.stats_by_operation: dict[str, PerformanceStats] = defaultdict(PerformanceStats)
        self.operation_timers: dict[str, float] = {}

        # Performance thresholds
        self.slow_operation_threshold = 0.1  # 100ms
        self.very_slow_operation_threshold = 0.5  # 500ms

        logger.debug("[PerformanceMonitor] Initialized")

    def start_operation(self, operation: str) -> None:
        """Start timing an operation."""
        self.operation_timers[operation] = time.time()

    def end_operation(
        self, operation: str, file_count: int = 0, success: bool = True, error_message: str = ""
    ) -> None:
        """End timing an operation and record metric."""
        if operation not in self.operation_timers:
            logger.warning(f"[PerformanceMonitor] Operation {operation} was not started")
            return

        start_time = self.operation_timers.pop(operation)
        duration = time.time() - start_time

        # Create metric
        metric = PerformanceMetric(
            operation=operation,
            duration=duration,
            file_count=file_count,
            timestamp=time.time(),
            success=success,
            error_message=error_message,
        )

        # Record metric
        self.metrics.append(metric)
        self.stats_by_operation[operation].update(metric)

        # Log performance warnings
        self._log_performance_warnings(metric)

    def _log_performance_warnings(self, metric: PerformanceMetric) -> None:
        """Log warnings for slow operations."""
        if metric.duration > self.very_slow_operation_threshold:
            logger.warning(
                f"[PerformanceMonitor] Very slow {metric.operation}: {metric.duration:.3f}s "
                f"for {metric.file_count} files"
            )
        elif metric.duration > self.slow_operation_threshold:
            logger.info(
                f"[PerformanceMonitor] Slow {metric.operation}: {metric.duration:.3f}s "
                f"for {metric.file_count} files"
            )

    def get_stats(self, operation: str | None = None) -> PerformanceStats:
        """Get performance stats for operation or overall."""
        if operation:
            return self.stats_by_operation[operation]

        # Return overall stats
        overall_stats = PerformanceStats()
        for stats in self.stats_by_operation.values():
            overall_stats.total_operations += stats.total_operations
            overall_stats.total_duration += stats.total_duration
            overall_stats.total_files += stats.total_files
            overall_stats.error_count += stats.error_count

        if overall_stats.total_operations > 0:
            overall_stats.average_duration = (
                overall_stats.total_duration / overall_stats.total_operations
            )
            overall_stats.average_files_per_operation = (
                overall_stats.total_files / overall_stats.total_operations
            )
            overall_stats.success_rate = (
                overall_stats.total_operations - overall_stats.error_count
            ) / overall_stats.total_operations

        return overall_stats

    def get_recent_performance(self, operation: str, count: int = 5) -> list[PerformanceMetric]:
        """Get recent performance metrics for operation."""
        recent_metrics = [m for m in self.metrics if m.operation == operation]
        return recent_metrics[-count:]

    def clear_metrics(self) -> None:
        """Clear all metrics."""
        self.metrics.clear()
        self.stats_by_operation.clear()
        self.operation_timers.clear()
        logger.debug("[PerformanceMonitor] Metrics cleared")

    def get_performance_summary(self) -> dict[str, Any]:
        """Get comprehensive performance summary."""
        return {
            "total_operations": self.total_operations,
            "average_time": self.get_average_time(),
            "peak_time": self.peak_time,
            "total_time": self.total_time,
            "operation_counts": dict(self.operation_counts),
            "recent_operations": self.recent_operations[-10:],  # Last 10 operations
        }


class PerformanceDecorator:
    """Decorator for automatic performance monitoring."""

    def __init__(self, monitor: PerformanceMonitor, operation_name: str):
        self.monitor = monitor
        self.operation_name = operation_name

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            # Start timing
            self.monitor.start_operation(self.operation_name)

            try:
                # Execute function
                result = func(*args, **kwargs)

                # Determine file count from result
                file_count = 0
                if hasattr(result, "name_pairs"):
                    file_count = len(result.name_pairs)
                elif hasattr(result, "items"):
                    file_count = len(result.items)
                elif hasattr(result, "files"):
                    file_count = len(result.files)

                # End timing with success
                self.monitor.end_operation(self.operation_name, file_count, True)

                return result

            except Exception as e:
                # End timing with error
                self.monitor.end_operation(self.operation_name, 0, False, str(e))
                raise

        return wrapper


# Global performance monitor instance
_performance_monitor = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


def monitor_performance(operation_name: str):
    """Decorator for monitoring function performance."""
    return PerformanceDecorator(get_performance_monitor(), operation_name)
