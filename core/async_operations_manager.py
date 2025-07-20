"""
Module: async_operations_manager.py

Author: Michael Economou
Date: 2025-06-25

Async Operations Manager Module
This module provides asynchronous operations for OnCutF using asyncio.
It handles non-blocking file operations, UI updates, and parallel processing
for heavy operations to improve application responsiveness.
Features:
- Async file I/O operations
- Non-blocking metadata processing
- Parallel hash calculation
- Background task management
- Progress tracking and cancellation
- Integration with Qt event loop
- Thread-safe operations
"""

import asyncio
import os
import threading
import time
from collections.abc import Coroutine
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from queue import Queue
from typing import Any, Callable, Dict, List, Optional

import aiofiles

from core.pyqt_imports import QMutex, QMutexLocker, QObject, pyqtSignal
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


@dataclass
class AsyncTask:
    """Represents an asynchronous task."""

    task_id: str
    task_type: str
    coroutine: Coroutine
    priority: int = 5
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Any = None
    error: Optional[Exception] = None
    progress: float = 0.0
    cancellable: bool = True

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


class AsyncFileOperations:
    """
    Async file operations using aiofiles and asyncio.

    Provides non-blocking file I/O operations for better performance.
    """

    @staticmethod
    async def read_file_async(file_path: str) -> Optional[bytes]:
        """Read file asynchronously."""
        try:
            async with aiofiles.open(file_path, "rb") as file:
                content = await file.read()
                return content
        except Exception as e:
            logger.error(f"[AsyncFileOps] Error reading file {file_path}: {e}")
            return None

    @staticmethod
    async def write_file_async(file_path: str, content: bytes) -> bool:
        """Write file asynchronously."""
        try:
            async with aiofiles.open(file_path, "wb") as file:
                await file.write(content)
                return True
        except Exception as e:
            logger.error(f"[AsyncFileOps] Error writing file {file_path}: {e}")
            return False

    @staticmethod
    async def copy_file_async(
        source: str, destination: str, progress_callback: Optional[Callable] = None
    ) -> bool:
        """Copy file asynchronously with progress tracking."""
        try:
            file_size = os.path.getsize(source)
            chunk_size = 64 * 1024  # 64KB chunks
            bytes_copied = 0

            async with aiofiles.open(source, "rb") as src:
                async with aiofiles.open(destination, "wb") as dst:
                    while True:
                        chunk = await src.read(chunk_size)
                        if not chunk:
                            break

                        await dst.write(chunk)
                        bytes_copied += len(chunk)

                        if progress_callback:
                            progress = (bytes_copied / file_size) * 100
                            progress_callback(progress)

            return True
        except Exception as e:
            logger.error(f"[AsyncFileOps] Error copying file {source} to {destination}: {e}")
            return False

    @staticmethod
    async def calculate_hash_async(
        file_path: str, algorithm: str = "CRC32", progress_callback: Optional[Callable] = None
    ) -> Optional[str]:
        """Calculate file hash asynchronously."""
        try:
            if algorithm == "CRC32":
                import zlib

                hash_obj = zlib.crc32
                hash_value = 0
            else:
                logger.error(
                    f"[AsyncFileOps] Unsupported hash algorithm: {algorithm}. Only CRC32 is supported."
                )
                return None

            file_size = os.path.getsize(file_path)
            chunk_size = 64 * 1024  # 64KB chunks
            bytes_processed = 0

            async with aiofiles.open(file_path, "rb") as file:
                while True:
                    chunk = await file.read(chunk_size)
                    if not chunk:
                        break

                    if algorithm == "CRC32":
                        hash_value = hash_obj(chunk, hash_value)
                    else:
                        hash_obj.update(chunk)

                    bytes_processed += len(chunk)

                    if progress_callback:
                        progress = (bytes_processed / file_size) * 100
                        progress_callback(progress)

            # Return hash value
            if algorithm == "CRC32":
                return f"{hash_value & 0xffffffff:08X}"
            else:
                return hash_obj.hexdigest().upper()

        except Exception as e:
            logger.error(f"[AsyncFileOps] Error calculating hash for {file_path}: {e}")
            return None

    @staticmethod
    async def get_file_metadata_async(file_path: str) -> Optional[Dict[str, Any]]:
        """Get file metadata asynchronously."""
        try:
            # Use thread pool for CPU-intensive metadata extraction
            loop = asyncio.get_event_loop()

            def extract_metadata():
                from utils.metadata_loader import MetadataLoader

                loader = MetadataLoader()
                return loader.load_metadata(file_path, extended=False)

            metadata = await loop.run_in_executor(None, extract_metadata)
            return metadata

        except Exception as e:
            logger.error(f"[AsyncFileOps] Error getting metadata for {file_path}: {e}")
            return None


class AsyncTaskManager(QObject):
    """
    Manages asynchronous tasks with priority queue and progress tracking.

    Features:
    - Task scheduling with priorities
    - Progress tracking and cancellation
    - Parallel execution with thread pool
    - Integration with Qt event loop
    - Task statistics and monitoring
    """

    # Signals
    task_started = pyqtSignal(str)  # task_id
    task_completed = pyqtSignal(str, object)  # task_id, result
    task_failed = pyqtSignal(str, str)  # task_id, error_message
    task_progress = pyqtSignal(str, float)  # task_id, progress

    def __init__(self, max_workers: int = 4, parent=None):
        """
        Initialize async task manager.

        Args:
            max_workers: Maximum number of worker threads
            parent: Parent QObject
        """
        super().__init__(parent)

        self.max_workers = max_workers
        self._tasks: Dict[str, AsyncTask] = {}
        self._task_queue: Queue = Queue()
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()

        # Statistics
        self._total_tasks = 0
        self._completed_tasks = 0
        self._failed_tasks = 0

        # Thread safety
        self._mutex = QMutex()

        # Start event loop in separate thread
        self._start_event_loop()

        logger.info(f"[AsyncTaskManager] Initialized with {max_workers} workers")

    def _start_event_loop(self):
        """Start asyncio event loop in separate thread."""

        def run_event_loop():
            self._event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._event_loop)

            try:
                self._event_loop.run_until_complete(self._task_processor())
            except Exception as e:
                logger.error(f"[AsyncTaskManager] Event loop error: {e}")
            finally:
                self._event_loop.close()

        self._loop_thread = threading.Thread(target=run_event_loop, daemon=True)
        self._loop_thread.start()

    async def _task_processor(self):
        """Process tasks from the queue."""
        while not self._shutdown_event.is_set():
            try:
                # Check for new tasks
                if not self._task_queue.empty():
                    task_id = self._task_queue.get_nowait()

                    with QMutexLocker(self._mutex):
                        if task_id in self._tasks:
                            task = self._tasks[task_id]

                            # Start task execution
                            asyncio_task = asyncio.create_task(self._execute_task(task))
                            self._running_tasks[task_id] = asyncio_task

                # Wait a bit before checking again
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"[AsyncTaskManager] Task processor error: {e}")

    async def _execute_task(self, task: AsyncTask):
        """Execute a single task."""
        try:
            task.started_at = time.time()
            self.task_started.emit(task.task_id)

            # Execute the coroutine
            result = await task.coroutine

            # Mark as completed
            task.completed_at = time.time()
            task.result = result
            task.progress = 100.0

            with QMutexLocker(self._mutex):
                self._completed_tasks += 1
                if task.task_id in self._running_tasks:
                    del self._running_tasks[task.task_id]

            self.task_completed.emit(task.task_id, result)
            self.task_progress.emit(task.task_id, 100.0)

        except Exception as e:
            task.error = e
            task.completed_at = time.time()

            with QMutexLocker(self._mutex):
                self._failed_tasks += 1
                if task.task_id in self._running_tasks:
                    del self._running_tasks[task.task_id]

            self.task_failed.emit(task.task_id, str(e))
            logger.error(f"[AsyncTaskManager] Task {task.task_id} failed: {e}")

    def submit_task(
        self, task_id: str, coroutine: Coroutine, task_type: str = "generic", priority: int = 5
    ) -> bool:
        """
        Submit a task for async execution.

        Args:
            task_id: Unique task identifier
            coroutine: Coroutine to execute
            task_type: Type of task
            priority: Task priority (lower = higher priority)

        Returns:
            Success status
        """
        try:
            with QMutexLocker(self._mutex):
                if task_id in self._tasks:
                    logger.warning(f"[AsyncTaskManager] Task {task_id} already exists")
                    return False

                task = AsyncTask(
                    task_id=task_id, task_type=task_type, coroutine=coroutine, priority=priority
                )

                self._tasks[task_id] = task
                self._task_queue.put(task_id)
                self._total_tasks += 1

                logger.debug(f"[AsyncTaskManager] Submitted task: {task_id}")
                return True

        except Exception as e:
            logger.error(f"[AsyncTaskManager] Error submitting task {task_id}: {e}")
            return False

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task."""
        try:
            with QMutexLocker(self._mutex):
                if task_id in self._running_tasks:
                    asyncio_task = self._running_tasks[task_id]
                    asyncio_task.cancel()
                    del self._running_tasks[task_id]

                    if task_id in self._tasks:
                        self._tasks[task_id].completed_at = time.time()
                        self._tasks[task_id].error = Exception("Task cancelled")

                    logger.debug(f"[AsyncTaskManager] Cancelled task: {task_id}")
                    return True

                return False

        except Exception as e:
            logger.error(f"[AsyncTaskManager] Error cancelling task {task_id}: {e}")
            return False

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status information."""
        with QMutexLocker(self._mutex):
            if task_id not in self._tasks:
                return None

            task = self._tasks[task_id]
            return {
                "task_id": task.task_id,
                "task_type": task.task_type,
                "priority": task.priority,
                "progress": task.progress,
                "is_running": task.is_running,
                "is_completed": task.is_completed,
                "execution_time": task.execution_time,
                "error": str(task.error) if task.error else None,
            }

    def get_stats(self) -> Dict[str, Any]:
        """Get task manager statistics."""
        with QMutexLocker(self._mutex):
            return {
                "total_tasks": self._total_tasks,
                "completed_tasks": self._completed_tasks,
                "failed_tasks": self._failed_tasks,
                "running_tasks": len(self._running_tasks),
                "pending_tasks": self._task_queue.qsize(),
                "max_workers": self.max_workers,
            }

    def shutdown(self):
        """Shutdown task manager."""
        logger.info("[AsyncTaskManager] Shutting down...")

        # Cancel all running tasks
        with QMutexLocker(self._mutex):
            for task_id in list(self._running_tasks.keys()):
                self.cancel_task(task_id)

        # Signal shutdown
        self._shutdown_event.set()

        # Shutdown executor
        self._executor.shutdown(wait=True)

        # Wait for event loop thread
        if self._loop_thread and self._loop_thread.is_alive():
            self._loop_thread.join(timeout=5.0)

        logger.info("[AsyncTaskManager] Shutdown completed")


class AsyncOperationsManager(QObject):
    """
    High-level async operations manager for OnCutF.

    Provides convenient async operations for common tasks like:
    - File hash calculation
    - Metadata extraction
    - File operations
    - Batch processing
    """

    # Signals
    operation_started = pyqtSignal(str, str)  # operation_id, operation_type
    operation_completed = pyqtSignal(str, object)  # operation_id, result
    operation_failed = pyqtSignal(str, str)  # operation_id, error_message
    operation_progress = pyqtSignal(str, float)  # operation_id, progress

    def __init__(self, max_workers: int = 4, parent=None):
        """
        Initialize async operations manager.

        Args:
            max_workers: Maximum number of worker threads
            parent: Parent QObject
        """
        super().__init__(parent)

        self.task_manager = AsyncTaskManager(max_workers, self)
        self.file_ops = AsyncFileOperations()

        # Connect signals
        self.task_manager.task_started.connect(self._on_task_started)
        self.task_manager.task_completed.connect(self._on_task_completed)
        self.task_manager.task_failed.connect(self._on_task_failed)
        self.task_manager.task_progress.connect(self._on_task_progress)

        logger.info("[AsyncOperationsManager] Initialized")

    def _on_task_started(self, task_id: str):
        """Handle task started signal."""
        status = self.task_manager.get_task_status(task_id)
        if status:
            self.operation_started.emit(task_id, status["task_type"])

    def _on_task_completed(self, task_id: str, result: Any):
        """Handle task completed signal."""
        self.operation_completed.emit(task_id, result)

    def _on_task_failed(self, task_id: str, error_message: str):
        """Handle task failed signal."""
        self.operation_failed.emit(task_id, error_message)

    def _on_task_progress(self, task_id: str, progress: float):
        """Handle task progress signal."""
        self.operation_progress.emit(task_id, progress)

    def calculate_file_hash_async(
        self, file_path: str, algorithm: str = "CRC32", operation_id: Optional[str] = None
    ) -> str:
        """
        Calculate file hash asynchronously.

        Args:
            file_path: Path to file
            algorithm: Hash algorithm
            operation_id: Optional operation identifier

        Returns:
            Operation ID for tracking
        """
        if operation_id is None:
            operation_id = f"hash_{int(time.time() * 1000)}"

        def progress_callback(progress: float):
            self.operation_progress.emit(operation_id, progress)

        coroutine = self.file_ops.calculate_hash_async(file_path, algorithm, progress_callback)
        self.task_manager.submit_task(operation_id, coroutine, "hash_calculation")

        return operation_id

    def extract_metadata_async(self, file_path: str, operation_id: Optional[str] = None) -> str:
        """
        Extract file metadata asynchronously.

        Args:
            file_path: Path to file
            operation_id: Optional operation identifier

        Returns:
            Operation ID for tracking
        """
        if operation_id is None:
            operation_id = f"metadata_{int(time.time() * 1000)}"

        coroutine = self.file_ops.get_file_metadata_async(file_path)
        self.task_manager.submit_task(operation_id, coroutine, "metadata_extraction")

        return operation_id

    def process_files_batch_async(
        self,
        file_paths: List[str],
        operation_type: str = "hash",
        operation_id: Optional[str] = None,
    ) -> str:
        """
        Process multiple files asynchronously.

        Args:
            file_paths: List of file paths
            operation_type: Type of operation ('hash' or 'metadata')
            operation_id: Optional operation identifier

        Returns:
            Operation ID for tracking
        """
        if operation_id is None:
            operation_id = f"batch_{operation_type}_{int(time.time() * 1000)}"

        async def batch_processor():
            results = {}
            total_files = len(file_paths)

            for i, file_path in enumerate(file_paths):
                try:
                    if operation_type == "hash":
                        result = await self.file_ops.calculate_hash_async(file_path)
                    elif operation_type == "metadata":
                        result = await self.file_ops.get_file_metadata_async(file_path)
                    else:
                        result = None

                    results[file_path] = result

                    # Update progress
                    progress = ((i + 1) / total_files) * 100
                    self.operation_progress.emit(operation_id, progress)

                except Exception as e:
                    results[file_path] = None
                    logger.error(f"[AsyncOpsManager] Error processing {file_path}: {e}")

            return results

        self.task_manager.submit_task(operation_id, batch_processor(), f"batch_{operation_type}")
        return operation_id

    def get_operation_status(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get operation status."""
        return self.task_manager.get_task_status(operation_id)

    def cancel_operation(self, operation_id: str) -> bool:
        """Cancel an operation."""
        return self.task_manager.cancel_task(operation_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get operations statistics."""
        return self.task_manager.get_stats()

    def shutdown(self):
        """Shutdown operations manager."""
        self.task_manager.shutdown()


# Global async operations manager instance
_async_ops_manager_instance: Optional[AsyncOperationsManager] = None


def get_async_operations_manager() -> AsyncOperationsManager:
    """Get global async operations manager instance."""
    global _async_ops_manager_instance
    if _async_ops_manager_instance is None:
        _async_ops_manager_instance = AsyncOperationsManager()
    return _async_ops_manager_instance


def initialize_async_operations(max_workers: int = 4) -> AsyncOperationsManager:
    """Initialize async operations manager."""
    global _async_ops_manager_instance
    _async_ops_manager_instance = AsyncOperationsManager(max_workers)
    return _async_ops_manager_instance
