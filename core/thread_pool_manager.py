"""
Module: thread_pool_manager.py

Author: Michael Economou
Date: 2025-06-25

Thread Pool Manager Module
This module provides an optimized thread pool management system for OnCutF.
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
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import psutil

from core.pyqt_imports import QMutex, QMutexLocker, QObject, QThread, QTimer, pyqtSignal
from utils.logger_factory import get_cached_logger

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
    function: Callable
    args: tuple
    kwargs: dict
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Any = None
    error: Optional[Exception] = None
    callback: Optional[Callable] = None

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
    """
    Priority queue implementation for task scheduling.

    Tasks are ordered by priority and creation time.
    """

    def __init__(self):
        """Initialize priority queue."""
        self._queues: Dict[TaskPriority, deque] = {
            priority: deque() for priority in TaskPriority
        }
        self._lock = threading.RLock()
        self._size = 0

    def put(self, task: WorkerTask):
        """Add task to queue."""
        with self._lock:
            self._queues[task.priority].append(task)
            self._size += 1

    def get(self) -> Optional[WorkerTask]:
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

    def clear(self):
        """Clear all tasks from queue."""
        with self._lock:
            for priority_queue in self._queues.values():
                priority_queue.clear()
            self._size = 0


class SmartWorkerThread(QThread):
    """
    Smart worker thread that can handle multiple types of tasks.

    Features:
    - Task execution with error handling
    - Progress reporting
    - Resource monitoring
    - Graceful shutdown
    """

    task_completed = pyqtSignal(str, object)  # task_id, result
    task_failed = pyqtSignal(str, str)        # task_id, error_message
    task_progress = pyqtSignal(str, float)    # task_id, progress

    def __init__(self, worker_id: str, task_queue: PriorityQueue, parent=None):
        """
        Initialize smart worker thread.

        Args:
            worker_id: Unique worker identifier
            task_queue: Shared task queue
            parent: Parent QObject
        """
        super().__init__(parent)

        self.worker_id = worker_id
        self.task_queue = task_queue
        self._shutdown_requested = False
        self._current_task: Optional[WorkerTask] = None
        self._tasks_processed = 0
        self._total_execution_time = 0.0

        logger.debug(f"[SmartWorkerThread] Created worker: {worker_id}")

    def run(self):
        """Main thread execution loop."""
        logger.debug(f"[SmartWorkerThread] Worker {self.worker_id} started")

        while not self._shutdown_requested:
            try:
                # Get next task
                task = self.task_queue.get()

                if task is None:
                    # No tasks available, sleep briefly
                    self.msleep(50)
                    continue

                # Execute task
                self._execute_task(task)

            except Exception as e:
                logger.error(f"[SmartWorkerThread] Worker {self.worker_id} error: {e}")

        logger.debug(f"[SmartWorkerThread] Worker {self.worker_id} stopped")

    def _execute_task(self, task: WorkerTask):
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
                except Exception as e:
                    logger.error(f"[SmartWorkerThread] Callback error for task {task.task_id}: {e}")

            # Emit completion signal
            self.task_completed.emit(task.task_id, result)

        except Exception as e:
            task.error = e
            task.completed_at = time.time()

            # Emit failure signal
            self.task_failed.emit(task.task_id, str(e))
            logger.error(f"[SmartWorkerThread] Task {task.task_id} failed: {e}")

        finally:
            self._current_task = None

    def request_shutdown(self):
        """Request thread shutdown."""
        self._shutdown_requested = True
        logger.debug(f"[SmartWorkerThread] Shutdown requested for worker: {self.worker_id}")

    def get_stats(self) -> Dict[str, Any]:
        """Get worker statistics."""
        return {
            'worker_id': self.worker_id,
            'is_running': self.isRunning(),
            'tasks_processed': self._tasks_processed,
            'total_execution_time': self._total_execution_time,
            'average_execution_time': (
                self._total_execution_time / self._tasks_processed
                if self._tasks_processed > 0 else 0.0
            ),
            'current_task': self._current_task.task_id if self._current_task else None
        }


class ThreadPoolManager(QObject):
    """
    Advanced thread pool manager with intelligent work distribution.

    Features:
    - Dynamic thread pool sizing
    - Priority-based task scheduling
    - Resource-aware thread allocation
    - Work stealing for load balancing
    - Comprehensive monitoring and statistics
    """

    # Signals
    task_submitted = pyqtSignal(str, str)      # task_id, priority
    task_completed = pyqtSignal(str, object)   # task_id, result
    task_failed = pyqtSignal(str, str)         # task_id, error_message
    pool_resized = pyqtSignal(int)             # new_size

    def __init__(self, min_threads: int = 2, max_threads: int = None, parent=None):
        """
        Initialize thread pool manager.

        Args:
            min_threads: Minimum number of threads
            max_threads: Maximum number of threads (default: CPU count * 2)
            parent: Parent QObject
        """
        super().__init__(parent)

        # Configuration
        self.min_threads = min_threads
        self.max_threads = max_threads or (psutil.cpu_count() * 2)
        self.target_queue_size = 10  # Resize pool when queue exceeds this

        # Thread pool
        self._workers: Dict[str, SmartWorkerThread] = {}
        self._task_queue = PriorityQueue()
        self._tasks: Dict[str, WorkerTask] = {}

        # Statistics
        self._total_tasks = 0
        self._completed_tasks = 0
        self._failed_tasks = 0
        self._total_execution_time = 0.0

        # Thread safety
        self._mutex = QMutex()

        # Monitoring timer
        self._monitor_timer = QTimer()
        self._monitor_timer.timeout.connect(self._monitor_pool)
        self._monitor_timer.start(5000)  # Check every 5 seconds

        # Start with minimum threads
        self._resize_pool(self.min_threads)

        logger.info(f"[ThreadPoolManager] Initialized with {min_threads}-{self.max_threads} threads")

    def submit_task(self, task_id: str, function: Callable, args: tuple = (),
                   kwargs: dict = None, priority: TaskPriority = TaskPriority.NORMAL,
                   callback: Optional[Callable] = None) -> bool:
        """
        Submit a task for execution.

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
            with QMutexLocker(self._mutex):
                if task_id in self._tasks:
                    logger.warning(f"[ThreadPoolManager] Task {task_id} already exists")
                    return False

                task = WorkerTask(
                    task_id=task_id,
                    function=function,
                    args=args,
                    kwargs=kwargs,
                    priority=priority,
                    callback=callback
                )

                self._tasks[task_id] = task
                self._task_queue.put(task)
                self._total_tasks += 1

                # Check if pool needs resizing
                self._check_pool_resize()

                self.task_submitted.emit(task_id, priority.name)
                logger.debug(f"[ThreadPoolManager] Submitted task: {task_id}")
                return True

        except Exception as e:
            logger.error(f"[ThreadPoolManager] Error submitting task {task_id}: {e}")
            return False

    def _check_pool_resize(self):
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
                worker_id for worker_id, worker in self._workers.items()
                if worker.get_stats()['current_task'] is None
            ]

            if len(idle_workers) > 1:  # Keep at least one idle worker
                worker_to_remove = idle_workers[0]
                self._remove_worker(worker_to_remove)

    def _resize_pool(self, new_size: int):
        """Resize thread pool to new size."""
        current_size = len(self._workers)

        if new_size > current_size:
            # Add workers
            for i in range(new_size - current_size):
                worker_id = f"worker_{len(self._workers) + 1}"
                self._add_worker(worker_id)

        elif new_size < current_size:
            # Remove workers
            workers_to_remove = list(self._workers.keys())[:current_size - new_size]
            for worker_id in workers_to_remove:
                self._remove_worker(worker_id)

        if new_size != current_size:
            self.pool_resized.emit(new_size)
            logger.info(f"[ThreadPoolManager] Pool resized from {current_size} to {new_size}")

    def _add_worker(self, worker_id: str):
        """Add a new worker thread."""
        worker = SmartWorkerThread(worker_id, self._task_queue, self)
        worker.task_completed.connect(self._on_task_completed)
        worker.task_failed.connect(self._on_task_failed)

        self._workers[worker_id] = worker
        worker.start()

        logger.debug(f"[ThreadPoolManager] Added worker: {worker_id}")

    def _remove_worker(self, worker_id: str):
        """Remove a worker thread."""
        if worker_id in self._workers:
            worker = self._workers[worker_id]
            worker.request_shutdown()
            worker.wait(5000)  # Wait up to 5 seconds

            if worker.isRunning():
                worker.terminate()
                worker.wait(1000)

            del self._workers[worker_id]
            logger.debug(f"[ThreadPoolManager] Removed worker: {worker_id}")

    def _on_task_completed(self, task_id: str, result: Any):
        """Handle task completion."""
        with QMutexLocker(self._mutex):
            if task_id in self._tasks:
                task = self._tasks[task_id]
                self._completed_tasks += 1
                self._total_execution_time += task.execution_time

                self.task_completed.emit(task_id, result)

    def _on_task_failed(self, task_id: str, error_message: str):
        """Handle task failure."""
        with QMutexLocker(self._mutex):
            self._failed_tasks += 1
            self.task_failed.emit(task_id, error_message)

    def _monitor_pool(self):
        """Monitor pool performance and adjust as needed."""
        try:
            stats = self.get_stats()

            # Log performance metrics
            logger.debug(f"[ThreadPoolManager] Pool stats: {stats['active_threads']} threads, "
                        f"{stats['queued_tasks']} queued, {stats['cpu_usage_percent']:.1f}% CPU")

            # Check for performance issues
            if stats['cpu_usage_percent'] > 90 and stats['active_threads'] < self.max_threads:
                # High CPU usage, consider adding threads
                self._resize_pool(min(stats['active_threads'] + 1, self.max_threads))

            elif stats['cpu_usage_percent'] < 30 and stats['active_threads'] > self.min_threads:
                # Low CPU usage, consider removing threads
                self._resize_pool(max(stats['active_threads'] - 1, self.min_threads))

        except Exception as e:
            logger.error(f"[ThreadPoolManager] Monitor error: {e}")

    def get_stats(self) -> ThreadPoolStats:
        """Get thread pool statistics."""
        with QMutexLocker(self._mutex):
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
                    if self._completed_tasks > 0 else 0.0
                ),
                cpu_usage_percent=cpu_percent,
                memory_usage_mb=memory_info.used / (1024 * 1024)
            )

    def get_worker_stats(self) -> List[Dict[str, Any]]:
        """Get individual worker statistics."""
        with QMutexLocker(self._mutex):
            return [worker.get_stats() for worker in self._workers.values()]

    def clear_completed_tasks(self):
        """Clear completed tasks from memory."""
        with QMutexLocker(self._mutex):
            completed_tasks = [
                task_id for task_id, task in self._tasks.items()
                if task.is_completed
            ]

            for task_id in completed_tasks:
                del self._tasks[task_id]

            logger.debug(f"[ThreadPoolManager] Cleared {len(completed_tasks)} completed tasks")

    def shutdown(self):
        """Shutdown thread pool manager."""
        logger.info("[ThreadPoolManager] Shutting down...")

        # Stop monitoring
        if self._monitor_timer.isActive():
            self._monitor_timer.stop()

        # Clear task queue
        self._task_queue.clear()

        # Shutdown all workers
        for worker_id in list(self._workers.keys()):
            self._remove_worker(worker_id)

        logger.info("[ThreadPoolManager] Shutdown completed")


# Global thread pool manager instance
_thread_pool_manager_instance: Optional[ThreadPoolManager] = None


def get_thread_pool_manager() -> ThreadPoolManager:
    """Get global thread pool manager instance."""
    global _thread_pool_manager_instance
    if _thread_pool_manager_instance is None:
        _thread_pool_manager_instance = ThreadPoolManager()
    return _thread_pool_manager_instance


def initialize_thread_pool(min_threads: int = 2, max_threads: int = None) -> ThreadPoolManager:
    """Initialize thread pool manager."""
    global _thread_pool_manager_instance
    _thread_pool_manager_instance = ThreadPoolManager(min_threads, max_threads)
    return _thread_pool_manager_instance


# Convenience functions
def submit_task(task_id: str, function: Callable, args: tuple = (),
               kwargs: dict = None, priority: TaskPriority = TaskPriority.NORMAL,
               callback: Optional[Callable] = None) -> bool:
    """Submit task using global thread pool."""
    return get_thread_pool_manager().submit_task(task_id, function, args, kwargs, priority, callback)


def get_pool_stats() -> ThreadPoolStats:
    """Get thread pool statistics."""
    return get_thread_pool_manager().get_stats()
