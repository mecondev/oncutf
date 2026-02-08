"""Module: thread_pool_manager.py.

Author: Michael Economou
Date: 2025-06-25

Thread Pool Manager Module
This module provides an optimized thread pool management system for oncutf.
It handles intelligent work distribution, resource management optimization,
and advanced thread pool features for better performance.
Features:
- Dynamic thread pool sizing based on workload
- Priority-based task scheduling
- Resource-aware thread allocation
- Thread pool monitoring and statistics
- Integration with Qt worker threads
- Graceful shutdown and cleanup
- Work stealing for load balancing
"""

import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import psutil

from oncutf.utils.events import Observable, Signal
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class TaskPriority(Enum):
    """Task priority levels."""

    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5


@dataclass
class WorkerTask:
    """Represents a worker task."""

    task_id: str
    function: Callable[..., Any]
    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    result: Any = None
    error: Exception | None = None
    callback: Callable[..., Any] | None = None

    @property
    def is_completed(self) -> bool:
        """Check if task is completed."""
        return self.completed_at is not None

    @property
    def is_running(self) -> bool:
        """Check if task is running."""
        return self.started_at is not None and self.completed_at is None

    @property
    def execution_time(self) -> float:
        """Get task execution time."""
        if self.started_at is None:
            return 0.0
        end_time = self.completed_at or time.time()
        return end_time - self.started_at


@dataclass
class ThreadPoolStats:
    """Thread pool statistics."""

    active_threads: int
    max_threads: int
    queued_tasks: int
    completed_tasks: int
    failed_tasks: int
    total_execution_time: float
    average_execution_time: float
    cpu_usage_percent: float
    memory_usage_mb: float


class PriorityQueue:
    """Priority queue implementation for task scheduling.

    Tasks are ordered by priority and creation time.
    """

    def __init__(self) -> None:
        """Initialize priority queue."""
        self._queues: dict[TaskPriority, deque[WorkerTask]] = {
            priority: deque() for priority in TaskPriority
        }
        self._lock = threading.RLock()
        self._size = 0

    def put(self, task: WorkerTask) -> None:
        """Add task to queue."""
        with self._lock:
            self._queues[task.priority].append(task)
            self._size += 1

    def get(self) -> WorkerTask | None:
        """Get highest priority task."""
        with self._lock:
            for priority in TaskPriority:
                if self._queues[priority]:
                    task = self._queues[priority].popleft()
                    self._size -= 1
                    return task
            return None

    def size(self) -> int:
        """Get queue size."""
        with self._lock:
            return self._size

    def empty(self) -> bool:
        """Check if queue is empty."""
        return self.size() == 0

    def clear(self) -> None:
        """Clear all tasks from queue."""
        with self._lock:
            for priority_queue in self._queues.values():
                priority_queue.clear()
            self._size = 0


class SmartWorkerThread(threading.Thread, Observable):
    """Smart worker thread that can handle multiple types of tasks.

    Features:
    - Task execution with error handling
    - Progress reporting
    - Resource monitoring
    - Graceful shutdown
    """

    task_completed = Signal()  # task_id, result
    task_failed = Signal()  # task_id, error_message
    task_progress = Signal()  # task_id, progress

    def __init__(self, worker_id: str, task_queue: PriorityQueue, parent: Any = None) -> None:
        """Initialize smart worker thread.

        Args:
            worker_id: Unique worker identifier
            task_queue: Shared task queue
            parent: Parent object (for API compatibility)

        """
        threading.Thread.__init__(self, daemon=True)
        Observable.__init__(self)

        self.worker_id = worker_id
        self.task_queue = task_queue
        self._shutdown_requested = False
        self._current_task: WorkerTask | None = None
        self._tasks_processed = 0
        self._total_execution_time = 0.0

        logger.debug("[SmartWorkerThread] Created worker: %s", worker_id)

    def run(self) -> None:
        """Main thread execution loop."""
        logger.debug("[SmartWorkerThread] Worker %s started", self.worker_id)

        while not self._shutdown_requested:
            try:
                # Get next task
                task = self.task_queue.get()

                if task is None:
                    # No tasks available, sleep briefly
                    time.sleep(0.05)  # 50ms
                    continue

                # Execute task
                self._execute_task(task)

            except Exception:
                logger.exception("[SmartWorkerThread] Worker %s error", self.worker_id)

        logger.debug("[SmartWorkerThread] Worker %s stopped", self.worker_id)

    def _execute_task(self, task: WorkerTask) -> None:
        """Execute a single task."""
        try:
            self._current_task = task
            task.started_at = time.time()

            # Execute the function
            result = task.function(*task.args, **task.kwargs)

            # Mark as completed
            task.completed_at = time.time()
            task.result = result

            # Update statistics
            self._tasks_processed += 1
            self._total_execution_time += task.execution_time

            # Call completion callback if provided
            if task.callback:
                try:
                    task.callback(result)
                except Exception:
                    logger.exception(
                        "[SmartWorkerThread] Callback error for task %s",
                        task.task_id,
                    )

            # Emit completion signal
            self.task_completed.emit(task.task_id, result)

        except Exception as e:
            task.error = e
            task.completed_at = time.time()

            # Emit failure signal
            self.task_failed.emit(task.task_id, str(e))
            logger.exception("[SmartWorkerThread] Task %s failed", task.task_id)

            # Track error in manager (will be set via signal connection)
            # Note: Manager should connect to task_failed signal to update its health state

        finally:
            self._current_task = None

    def request_shutdown(self) -> None:
        """Request thread shutdown."""
        self._shutdown_requested = True
        logger.debug(
            "[SmartWorkerThread] Shutdown requested for worker: %s",
            self.worker_id,
        )

    def get_stats(self) -> dict[str, Any]:
        """Get worker statistics."""
        return {
            "worker_id": self.worker_id,
            "is_running": self.is_alive(),
            "tasks_processed": self._tasks_processed,
            "total_execution_time": self._total_execution_time,
            "average_execution_time": (
                self._total_execution_time / self._tasks_processed
                if self._tasks_processed > 0
                else 0.0
            ),
            "current_task": self._current_task.task_id if self._current_task else None,
        }


class ThreadPoolManager(Observable):
    """Advanced thread pool manager with intelligent work distribution.

    Features:
    - Dynamic thread pool sizing
    - Priority-based task scheduling
    - Resource-aware thread allocation
    - Work stealing for load balancing
    - Comprehensive monitoring and statistics
    """

    # Signals (Observable descriptors)
    task_submitted = Signal()  # task_id, priority
    task_completed = Signal()  # task_id, result
    task_failed = Signal()  # task_id, error_message
    pool_resized = Signal()  # new_size

    def __init__(
        self,
        min_threads: int = 2,
        max_threads: int | None = None,
        parent: Any = None,
    ):
        """Initialize thread pool manager.

        Args:
            min_threads: Minimum number of threads
            max_threads: Maximum number of threads (default: CPU count * 2)
            parent: Parent object (for API compatibility)

        """
        super().__init__()

        # Configuration
        self.min_threads = min_threads
        self.max_threads = max_threads or (psutil.cpu_count() * 2)
        self.target_queue_size = 10  # Resize pool when queue exceeds this

        # Thread pool
        self._workers: dict[str, SmartWorkerThread] = {}
        self._task_queue = PriorityQueue()
        self._tasks: dict[str, WorkerTask] = {}

        # Statistics
        self._total_tasks = 0
        self._completed_tasks = 0

        # Health tracking
        self._last_error: str | None = None
        self._failed_tasks_count: int = 0
        self._is_healthy: bool = True
        self._failed_tasks = 0
        self._total_execution_time = 0.0

        # Thread safety
        self._mutex = threading.Lock()

        # Monitoring timer
        from oncutf.app.services.ui_scheduler import (
            TimerPriority,
            TimerType,
            schedule_timer,
        )

        self._monitor_timer_id = schedule_timer(
            self._monitor_pool,
            delay=5000,
            timer_type=TimerType.UI_UPDATE,
            priority=TimerPriority.LOW,
            timer_id="thread_pool_monitor",
        )

        # Start with minimum threads
        self._resize_pool(self.min_threads)

        logger.info(
            "[ThreadPoolManager] Initialized with %d-%d threads",
            min_threads,
            self.max_threads,
        )

    def submit_task(
        self,
        task_id: str,
        function: Callable[..., Any],
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        callback: Callable[..., Any] | None = None,
    ) -> bool:
        """Submit a task for execution.

        Args:
            task_id: Unique task identifier
            function: Function to execute
            args: Function arguments
            kwargs: Function keyword arguments
            priority: Task priority
            callback: Optional completion callback

        Returns:
            Success status

        """
        if kwargs is None:
            kwargs = {}

        try:
            with self._mutex:
                if task_id in self._tasks:
                    logger.warning("[ThreadPoolManager] Task %s already exists", task_id)
                    return False

                task = WorkerTask(
                    task_id=task_id,
                    function=function,
                    args=args,
                    kwargs=kwargs,
                    priority=priority,
                    callback=callback,
                )

                self._tasks[task_id] = task
                self._task_queue.put(task)
                self._total_tasks += 1

                # Check if pool needs resizing
                self._check_pool_resize()

                self.task_submitted.emit(task_id, priority.name)
                logger.debug("[ThreadPoolManager] Submitted task: %s", task_id)
                return True

        except Exception:
            logger.exception("[ThreadPoolManager] Error submitting task %s", task_id)
            return False

    def _check_pool_resize(self) -> None:
        """Check if thread pool needs resizing."""
        queue_size = self._task_queue.size()
        current_threads = len(self._workers)

        # Expand pool if queue is getting large
        if queue_size > self.target_queue_size and current_threads < self.max_threads:
            new_size = min(current_threads + 1, self.max_threads)
            self._resize_pool(new_size)

        # Shrink pool if queue is empty and we have excess threads
        elif queue_size == 0 and current_threads > self.min_threads:
            # Check if workers are idle
            idle_workers = [
                worker_id
                for worker_id, worker in self._workers.items()
                if worker.get_stats()["current_task"] is None
            ]

            if len(idle_workers) > 1:  # Keep at least one idle worker
                worker_to_remove = idle_workers[0]
                self._remove_worker(worker_to_remove)

    def _resize_pool(self, new_size: int) -> None:
        """Resize thread pool to new size."""
        current_size = len(self._workers)

        if new_size > current_size:
            # Add workers
            for _i in range(new_size - current_size):
                worker_id = f"worker_{len(self._workers) + 1}"
                self._add_worker(worker_id)

        elif new_size < current_size:
            # Remove workers
            workers_to_remove = list(self._workers.keys())[: current_size - new_size]
            for worker_id in workers_to_remove:
                self._remove_worker(worker_id)

        if new_size != current_size:
            self.pool_resized.emit(new_size)
            logger.info(
                "[ThreadPoolManager] Pool resized from %d to %d",
                current_size,
                new_size,
            )

    def _add_worker(self, worker_id: str) -> None:
        """Add a new worker thread."""
        worker = SmartWorkerThread(worker_id, self._task_queue, self)
        worker.task_completed.connect(self._on_task_completed)
        worker.task_failed.connect(self._on_task_failed)

        self._workers[worker_id] = worker
        worker.start()

        logger.debug("[ThreadPoolManager] Added worker: %s", worker_id)

    def _remove_worker(
        self,
        worker_id: str,
        *,
        wait_ms: int = 5000,
        terminate_wait_ms: int = 1000,
    ) -> None:
        """Remove a worker thread.

        Args:
            worker_id: Worker identifier.
            wait_ms: Max milliseconds to wait for graceful stop.
            terminate_wait_ms: Max milliseconds to wait after terminate().

        """
        if worker_id in self._workers:
            worker = self._workers[worker_id]
            worker.request_shutdown()

            # Wait with timeout to prevent infinite hang
            worker.join(timeout=wait_ms / 1000.0)
            if worker.is_alive():
                logger.warning(
                    "[ThreadPoolManager] Worker %s did not stop gracefully (threading.Thread cannot be terminated)",
                    worker_id,
                )
                worker.join(timeout=terminate_wait_ms / 1000.0)
                if worker.is_alive():
                    logger.error(
                        "[ThreadPoolManager] Worker %s still running after %dms",
                        worker_id,
                        terminate_wait_ms,
                    )

            del self._workers[worker_id]
            logger.debug("[ThreadPoolManager] Removed worker: %s", worker_id)

    def _on_task_completed(self, task_id: str, result: Any) -> None:
        """Handle task completion."""
        with self._mutex:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                self._completed_tasks += 1
                self._total_execution_time += task.execution_time

                self.task_completed.emit(task_id, result)

    def _on_task_failed(self, task_id: str, error_message: str) -> None:
        """Handle task failure and update health tracking."""
        with self._mutex:
            self._failed_tasks += 1
            self.task_failed.emit(task_id, error_message)

            # Health tracking
            self._failed_tasks_count += 1
            self._last_error = f"Task {task_id}: {error_message}"

            # Mark as unhealthy if too many failures
            if self._failed_tasks_count > 10:
                self._is_healthy = False
                logger.warning(
                    "[ThreadPoolManager] Marked as unhealthy after %d failures",
                    self._failed_tasks_count,
                )

    def _monitor_pool(self) -> None:
        """Monitor pool performance and adjust as needed."""
        try:
            stats = self.get_stats()

            # Log performance metrics
            logger.debug(
                "[ThreadPoolManager] Pool stats: %d threads, %d queued, %.1f%% CPU",
                stats.active_threads,
                stats.queued_tasks,
                stats.cpu_usage_percent,
            )

            # Check for performance issues
            if stats.cpu_usage_percent > 90 and stats.active_threads < self.max_threads:
                # High CPU usage, consider adding threads
                self._resize_pool(min(stats.active_threads + 1, self.max_threads))

            elif stats.cpu_usage_percent < 30 and stats.active_threads > self.min_threads:
                # Low CPU usage, consider removing threads
                self._resize_pool(max(stats.active_threads - 1, self.min_threads))

        except Exception:
            logger.exception("[ThreadPoolManager] Monitor error")

    def get_stats(self) -> ThreadPoolStats:
        """Get thread pool statistics."""
        with self._mutex:
            # Get system stats
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory_info = psutil.virtual_memory()

            return ThreadPoolStats(
                active_threads=len(self._workers),
                max_threads=self.max_threads,
                queued_tasks=self._task_queue.size(),
                completed_tasks=self._completed_tasks,
                failed_tasks=self._failed_tasks,
                total_execution_time=self._total_execution_time,
                average_execution_time=(
                    self._total_execution_time / self._completed_tasks
                    if self._completed_tasks > 0
                    else 0.0
                ),
                cpu_usage_percent=cpu_percent,
                memory_usage_mb=memory_info.used / (1024 * 1024),
            )

    def get_worker_stats(self) -> list[dict[str, Any]]:
        """Get individual worker statistics."""
        with self._mutex:
            return [worker.get_stats() for worker in self._workers.values()]

    def clear_completed_tasks(self) -> None:
        """Clear completed tasks from memory."""
        with self._mutex:
            completed_tasks = [
                task_id for task_id, task in self._tasks.items() if task.is_completed
            ]

            for task_id in completed_tasks:
                del self._tasks[task_id]

            logger.debug(
                "[ThreadPoolManager] Cleared %d completed tasks",
                len(completed_tasks),
            )

    def is_healthy(self) -> bool:
        """Check if thread pool is healthy.

        Returns:
            True if the pool is operating normally.

        """
        return self._is_healthy and len(self._workers) > 0

    def last_error(self) -> str | None:
        """Get the last error message.

        Returns:
            Last error message or None if no errors.

        """
        return self._last_error

    def health_check(self) -> dict[str, Any]:
        """Perform comprehensive health check.

        Returns:
            Dictionary with health status and metrics.

        """
        active_workers = sum(1 for w in self._workers.values() if w.is_alive())

        return {
            "healthy": self.is_healthy(),
            "total_workers": len(self._workers),
            "active_workers": active_workers,
            "queued_tasks": self._task_queue.size(),
            "total_tasks_processed": self._completed_tasks,
            "failed_tasks": self._failed_tasks_count,
            "last_error": self._last_error,
        }

    def shutdown(
        self,
        *,
        worker_wait_ms: int = 5000,
        terminate_wait_ms: int = 1000,
    ) -> None:
        """Shutdown thread pool manager.

        Args:
            worker_wait_ms: Max milliseconds per worker to wait for graceful stop.
            terminate_wait_ms: Max milliseconds to wait after terminate().

        """
        logger.info("[ThreadPoolManager] Shutting down...")

        # Stop monitoring
        if hasattr(self, "_monitor_timer_id") and self._monitor_timer_id:
            from oncutf.app.services.ui_scheduler import cancel_timer

            cancel_timer(self._monitor_timer_id)

        # Clear task queue
        self._task_queue.clear()

        # Shutdown all workers
        for worker_id in list(self._workers.keys()):
            self._remove_worker(
                worker_id,
                wait_ms=worker_wait_ms,
                terminate_wait_ms=terminate_wait_ms,
            )

        logger.info("[ThreadPoolManager] Shutdown completed")


# Global thread pool manager instance
_thread_pool_manager_instance: ThreadPoolManager | None = None


def get_thread_pool_manager() -> ThreadPoolManager:
    """Get global thread pool manager instance."""
    global _thread_pool_manager_instance
    if _thread_pool_manager_instance is None:
        _thread_pool_manager_instance = ThreadPoolManager()
    return _thread_pool_manager_instance


def initialize_thread_pool(
    min_threads: int = 2, max_threads: int | None = None
) -> ThreadPoolManager:
    """Initialize thread pool manager."""
    global _thread_pool_manager_instance
    _thread_pool_manager_instance = ThreadPoolManager(min_threads, max_threads)
    return _thread_pool_manager_instance


# Convenience functions
def submit_task(
    task_id: str,
    function: Callable[..., Any],
    args: tuple[Any, ...] = (),
    kwargs: dict[str, Any] | None = None,
    priority: TaskPriority = TaskPriority.NORMAL,
    callback: Callable[..., None] | None = None,
) -> bool:
    """Submit task using global thread pool."""
    return get_thread_pool_manager().submit_task(
        task_id, function, args, kwargs, priority, callback
    )


def get_pool_stats() -> ThreadPoolStats:
    """Get thread pool statistics."""
    return get_thread_pool_manager().get_stats()
