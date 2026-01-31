"""Module: batch_operations_manager.py.

Author: Michael Economou
Date: 2025-06-20

batch_operations_manager.py
This module provides batch operations optimization for database queries, cache operations,
and file I/O operations. It groups similar operations together to reduce overhead and
improve performance, especially for large file sets.
Features:
- Batch metadata cache operations
- Batch hash cache operations
- Batch database queries with transactions
- Batch file I/O operations
- Automatic flush mechanisms with size/time thresholds
- Thread-safe operation batching
"""

import threading
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


@dataclass
class BatchOperation:
    """Represents a single operation to be batched."""

    operation_type: str  # 'metadata_set', 'hash_store', 'db_query', etc.
    key: str  # Primary key for the operation
    data: Any  # Operation data
    callback: Callable[..., None] | None = None  # Optional callback after operation
    timestamp: datetime = field(default_factory=datetime.now)
    priority: int = 50  # Lower number = higher priority


@dataclass
class BatchStats:
    """Statistics for batch operations monitoring."""

    total_operations: int = 0
    batched_operations: int = 0
    individual_operations: int = 0
    batch_flushes: int = 0
    average_batch_size: float = 0.0
    total_time_saved: float = 0.0  # Estimated time saved by batching


class BatchOperationsManager:
    """Manages batch operations for improved performance.

    Automatically batches similar operations together and flushes them
    based on size thresholds, time intervals, or manual triggers.
    """

    def __init__(self, parent_window: Any | None = None) -> None:
        """Initialize batch operations manager with configuration and locks."""
        self.parent_window = parent_window

        # Batch storage by operation type
        self._batches: dict[str, list[BatchOperation]] = defaultdict(list)
        self._batch_lock = threading.RLock()

        # Configuration
        self._max_batch_size = 50  # Maximum operations per batch
        self._max_batch_age = 2.0  # Maximum seconds to hold operations
        self._auto_flush_enabled = True

        # Statistics
        self._stats = BatchStats()

        # Auto-flush timer
        self._flush_timer: threading.Timer | None = None
        self._last_flush_time = time.time()

        # Operation handlers
        self._operation_handlers: dict[str, Callable[[list[BatchOperation]], None]] = {
            "metadata_set": self._handle_metadata_batch,
            "hash_store": self._handle_hash_batch,
            "db_query": self._handle_db_batch,
            "file_io": self._handle_file_io_batch,
            "cache_update": self._handle_cache_batch,
        }

        logger.info("[BatchOperationsManager] Initialized with intelligent batching")

    def queue_metadata_set(
        self,
        file_path: str,
        metadata: dict[str, Any],
        is_extended: bool = False,
        callback: Callable[..., Any] | None = None,
        priority: int = 50,
    ) -> None:
        """Queue a metadata cache set operation for batching."""
        operation = BatchOperation(
            operation_type="metadata_set",
            key=file_path,
            data={"metadata": metadata, "is_extended": is_extended},
            callback=callback,
            priority=priority,
        )
        self._queue_operation(operation)

    def queue_hash_store(
        self,
        file_path: str,
        hash_value: str,
        algorithm: str = "crc32",
        callback: Callable[..., Any] | None = None,
        priority: int = 50,
    ) -> None:
        """Queue a hash cache store operation for batching."""
        operation = BatchOperation(
            operation_type="hash_store",
            key=file_path,
            data={"hash_value": hash_value, "algorithm": algorithm},
            callback=callback,
            priority=priority,
        )
        self._queue_operation(operation)

    def queue_db_query(
        self,
        query_type: str,
        query: str,
        params: tuple[Any, ...] = (),
        callback: Callable[..., Any] | None = None,
        priority: int = 50,
    ) -> None:
        """Queue a database query for batching."""
        operation = BatchOperation(
            operation_type="db_query",
            key=f"{query_type}_{hash(query)}",
            data={"query_type": query_type, "query": query, "params": params},
            callback=callback,
            priority=priority,
        )
        self._queue_operation(operation)

    def queue_file_operation(
        self,
        operation_type: str,
        file_path: str,
        data: Any = None,
        callback: Callable[..., Any] | None = None,
        priority: int = 50,
    ) -> None:
        """Queue a file I/O operation for batching."""
        operation = BatchOperation(
            operation_type="file_io",
            key=f"{operation_type}_{file_path}",
            data={
                "operation_type": operation_type,
                "file_path": file_path,
                "data": data,
            },
            callback=callback,
            priority=priority,
        )
        self._queue_operation(operation)

    def _queue_operation(self, operation: BatchOperation) -> None:
        """Queue an operation for batching."""
        with self._batch_lock:
            batch_type = operation.operation_type

            # Check if we should replace an existing operation (same key)
            existing_ops = self._batches[batch_type]
            for i, existing_op in enumerate(existing_ops):
                if existing_op.key == operation.key:
                    # Replace with newer operation (higher priority wins)
                    if operation.priority <= existing_op.priority:
                        existing_ops[i] = operation
                        logger.debug("[BatchOps] Replaced operation: %s", operation.key)
                        return

            # Add new operation
            self._batches[batch_type].append(operation)
            self._stats.total_operations += 1

            logger.debug(
                "[BatchOps] Queued %s: %s (batch size: %d)",
                batch_type,
                operation.key,
                len(existing_ops) + 1,
            )

            # Check if we should auto-flush
            if self._auto_flush_enabled:
                self._check_auto_flush(batch_type)

    def _check_auto_flush(self, batch_type: str) -> None:
        """Check if we should auto-flush a specific batch type."""
        batch = self._batches[batch_type]
        current_time = time.time()

        # Flush if batch is full
        if len(batch) >= self._max_batch_size:
            logger.debug(
                "[BatchOps] Auto-flush triggered by size: %s (%d ops)",
                batch_type,
                len(batch),
            )
            self._flush_batch_type(batch_type)
            return

        # Flush if oldest operation is too old
        if batch and (current_time - batch[0].timestamp.timestamp()) > self._max_batch_age:
            logger.debug("[BatchOps] Auto-flush triggered by age: %s", batch_type)
            self._flush_batch_type(batch_type)
            return

    def flush_all(self) -> dict[str, int]:
        """Flush all pending batches immediately.

        Returns:
            Dict mapping batch type to number of operations flushed

        """
        results = {}

        with self._batch_lock:
            for batch_type in list(self._batches.keys()):
                if self._batches[batch_type]:
                    results[batch_type] = self._flush_batch_type(batch_type)

        logger.info("[BatchOps] Flushed all batches: %s", results)
        return results

    def flush_batch_type(self, batch_type: str) -> int:
        """Flush a specific batch type.

        Args:
            batch_type: Type of batch to flush

        Returns:
            Number of operations flushed

        """
        with self._batch_lock:
            return self._flush_batch_type(batch_type)

    def _flush_batch_type(self, batch_type: str) -> int:
        """Internal method to flush a batch type (assumes lock is held)."""
        batch = self._batches[batch_type]
        if not batch:
            return 0

        # Sort by priority (lower number = higher priority) and timestamp
        batch.sort(key=lambda op: (op.priority, op.timestamp))

        start_time = time.time()
        operations_count = len(batch)

        try:
            # Get the appropriate handler
            handler = self._operation_handlers.get(batch_type)
            if not handler:
                logger.warning("[BatchOps] No handler for batch type: %s", batch_type)
                return 0

            # Execute the batch
            handler(batch)

            # Update statistics
            self._stats.batched_operations += operations_count
            self._stats.batch_flushes += 1

            # Update average batch size
            total_batches = self._stats.batch_flushes
            self._stats.average_batch_size = (
                self._stats.average_batch_size * (total_batches - 1) + operations_count
            ) / total_batches

            # Estimate time saved (rough heuristic)
            batch_time = time.time() - start_time
            estimated_individual_time = operations_count * 0.01  # 10ms per operation
            time_saved = max(0, estimated_individual_time - batch_time)
            self._stats.total_time_saved += time_saved

            logger.info(
                "[BatchOps] Flushed %s: %d ops in %.3fs (saved ~%.3fs)",
                batch_type,
                operations_count,
                batch_time,
                time_saved,
            )

        except Exception as e:
            logger.error("[BatchOps] Error flushing %s: %s", batch_type, e)
            # Execute callbacks with error
            for operation in batch:
                if operation.callback:
                    try:
                        operation.callback(success=False, error=e)
                    except Exception as callback_error:
                        logger.error("[BatchOps] Callback error: %s", callback_error)
        finally:
            # Clear the batch
            self._batches[batch_type].clear()
            self._last_flush_time = time.time()

        return operations_count

    def _handle_metadata_batch(self, operations: list[BatchOperation]) -> None:
        """Handle a batch of metadata cache set operations."""
        if not self.parent_window or not hasattr(self.parent_window, "metadata_cache"):
            logger.warning("[BatchOps] No metadata cache available")
            return

        cache = self.parent_window.metadata_cache
        success_count = 0

        # Group operations by extended flag for better batching
        extended_ops: list[BatchOperation] = []
        regular_ops: list[BatchOperation] = []

        for op in operations:
            if op.data.get("is_extended", False):
                extended_ops.append(op)
            else:
                regular_ops.append(op)

        # Process each group
        for ops_group, _is_extended in [(regular_ops, False), (extended_ops, True)]:
            if not ops_group:
                continue

            try:
                # Use batch transaction if available
                if hasattr(cache, "begin_batch"):
                    cache.begin_batch()

                for operation in ops_group:
                    try:
                        cache.set(
                            operation.key,
                            operation.data["metadata"],
                            is_extended=operation.data["is_extended"],
                        )
                        success_count += 1

                        # Execute callback on success
                        if operation.callback:
                            operation.callback(success=True)

                    except Exception as e:
                        logger.error(
                            "[BatchOps] Metadata set failed for %s: %s",
                            operation.key,
                            e,
                        )
                        if operation.callback:
                            operation.callback(success=False, error=e)

                # Commit batch if available
                if hasattr(cache, "commit_batch"):
                    cache.commit_batch()

            except Exception as e:
                logger.error("[BatchOps] Metadata batch failed: %s", e)
                if hasattr(cache, "rollback_batch"):
                    cache.rollback_batch()

        logger.debug(
            "[BatchOps] Metadata batch: %d/%d successful",
            success_count,
            len(operations),
        )

    def _handle_hash_batch(self, operations: list[BatchOperation]) -> None:
        """Handle a batch of hash cache store operations."""
        if not self.parent_window or not hasattr(self.parent_window, "hash_cache"):
            logger.warning("[BatchOps] No hash cache available")
            return

        cache = self.parent_window.hash_cache
        success_count = 0

        try:
            # Use batch transaction if available
            if hasattr(cache, "begin_batch"):
                cache.begin_batch()

            for operation in operations:
                try:
                    # Use the cache's store_hash method
                    if hasattr(cache, "store_hash"):
                        cache.store_hash(
                            operation.key,
                            operation.data["hash_value"],
                            operation.data.get("algorithm", "crc32"),
                        )
                    else:
                        # Fallback to direct database access
                        cache._db_manager.store_hash(
                            operation.key,
                            operation.data["hash_value"],
                            operation.data.get("algorithm", "crc32"),
                        )

                    success_count += 1

                    # Execute callback on success
                    if operation.callback:
                        operation.callback(success=True)

                except Exception as e:
                    logger.error("[BatchOps] Hash store failed for %s: %s", operation.key, e)
                    if operation.callback:
                        operation.callback(success=False, error=e)

            # Commit batch if available
            if hasattr(cache, "commit_batch"):
                cache.commit_batch()

        except Exception as e:
            logger.error("[BatchOps] Hash batch failed: %s", e)
            if hasattr(cache, "rollback_batch"):
                cache.rollback_batch()

        logger.debug("[BatchOps] Hash batch: %d/%d successful", success_count, len(operations))

    def _handle_db_batch(self, operations: list[BatchOperation]) -> None:
        """Handle a batch of database query operations."""
        if not self.parent_window or not hasattr(self.parent_window, "db_manager"):
            logger.warning("[BatchOps] No database manager available")
            return

        db_manager = self.parent_window.db_manager
        success_count = 0

        # Group operations by query type for better batching
        query_groups: defaultdict[str, list[BatchOperation]] = defaultdict(list)
        for op in operations:
            query_type = op.data["query_type"]
            query_groups[query_type].append(op)

        for query_type, ops in query_groups.items():
            try:
                # Use transaction for each query type group
                with db_manager.transaction():
                    for operation in ops:
                        try:
                            query = operation.data["query"]
                            params = operation.data["params"]

                            if query_type == "SELECT":
                                result = db_manager.execute_query(query, params)
                            else:
                                result = db_manager.execute_update(query, params)

                            success_count += 1

                            # Execute callback with result
                            if operation.callback:
                                operation.callback(success=True, result=result)

                        except Exception as e:
                            logger.error("[BatchOps] DB query failed: %s: %s", query, e)
                            if operation.callback:
                                operation.callback(success=False, error=e)

            except Exception as e:
                logger.error("[BatchOps] DB batch failed for %s: %s", query_type, e)

        logger.debug("[BatchOps] DB batch: %d/%d successful", success_count, len(operations))

    def _handle_file_io_batch(self, operations: list[BatchOperation]) -> None:
        """Handle a batch of file I/O operations."""
        # Group by operation type
        read_ops: list[BatchOperation] = []
        write_ops: list[BatchOperation] = []

        for op in operations:
            op_type = op.data["operation_type"]
            if op_type in ["read", "stat", "exists"]:
                read_ops.append(op)
            elif op_type in ["write", "copy", "move"]:
                write_ops.append(op)

        # Process read operations (can be parallelized)
        if read_ops:
            self._handle_file_read_batch(read_ops)

        # Process write operations (sequential for safety)
        if write_ops:
            self._handle_file_write_batch(write_ops)

    def _handle_file_read_batch(self, operations: list[BatchOperation]) -> None:
        """Handle batch file read operations."""
        success_count = 0

        for operation in operations:
            try:
                file_path: str = operation.data["file_path"]
                op_type: str = operation.data["operation_type"]
                result: Any = None

                if op_type == "read":
                    with Path(file_path).open("rb") as f:
                        result = f.read()
                elif op_type == "stat":
                    import os

                    result = Path(file_path).stat()
                elif op_type == "exists":
                    import os

                    result = Path(file_path).exists()
                else:
                    result = None

                success_count += 1

                if operation.callback:
                    operation.callback(success=True, result=result)

            except Exception as e:
                logger.error("[BatchOps] File read failed for %s: %s", operation.key, e)
                if operation.callback:
                    operation.callback(success=False, error=e)

        logger.debug(
            "[BatchOps] File read batch: %d/%d successful",
            success_count,
            len(operations),
        )

    def _handle_file_write_batch(self, operations: list[BatchOperation]) -> None:
        """Handle batch file write operations."""
        success_count = 0

        for operation in operations:
            try:
                file_path = operation.data["file_path"]
                op_type = operation.data["operation_type"]
                data = operation.data.get("data")

                if op_type == "write" and data:
                    with Path(file_path).open("wb") as f:
                        f.write(data)
                elif op_type == "copy":
                    import shutil

                    shutil.copy2(file_path, data)  # data = destination
                elif op_type == "move":
                    import shutil

                    shutil.move(file_path, data)  # data = destination

                success_count += 1

                if operation.callback:
                    operation.callback(success=True)

            except Exception as e:
                logger.error("[BatchOps] File write failed for %s: %s", operation.key, e)
                if operation.callback:
                    operation.callback(success=False, error=e)

        logger.debug(
            "[BatchOps] File write batch: %d/%d successful",
            success_count,
            len(operations),
        )

    def _handle_cache_batch(self, operations: list[BatchOperation]) -> None:
        """Handle batch cache update operations."""
        # This is a generic handler for other cache operations
        success_count = 0

        for operation in operations:
            try:
                # Execute the operation (implementation depends on specific cache type)
                success_count += 1

                if operation.callback:
                    operation.callback(success=True)

            except Exception as e:
                logger.error("[BatchOps] Cache operation failed for %s: %s", operation.key, e)
                if operation.callback:
                    operation.callback(success=False, error=e)

        logger.debug("[BatchOps] Cache batch: %d/%d successful", success_count, len(operations))

    def get_stats(self) -> BatchStats:
        """Get current batch operation statistics."""
        return self._stats

    def get_pending_operations(self) -> dict[str, int]:
        """Get count of pending operations by type."""
        with self._batch_lock:
            return {batch_type: len(ops) for batch_type, ops in self._batches.items() if ops}

    def set_config(
        self,
        max_batch_size: int | None = None,
        max_batch_age: float | None = None,
        auto_flush: bool | None = None,
    ) -> None:
        """Configure batch operation parameters."""
        if max_batch_size is not None:
            self._max_batch_size = max_batch_size
        if max_batch_age is not None:
            self._max_batch_age = max_batch_age
        if auto_flush is not None:
            self._auto_flush_enabled = auto_flush

        logger.info(
            "[BatchOps] Config updated: batch_size=%d, batch_age=%ss, auto_flush=%s",
            self._max_batch_size,
            self._max_batch_age,
            self._auto_flush_enabled,
        )

    def cleanup(self) -> None:
        """Clean up resources and flush all pending operations."""
        logger.info("[BatchOps] Starting cleanup...")

        # Flush all pending operations
        self.flush_all()

        # Stop any timers
        if self._flush_timer:
            self._flush_timer.cancel()
            self._flush_timer = None

        # Clear all batches
        with self._batch_lock:
            self._batches.clear()

        logger.info("[BatchOps] Cleanup completed. Final stats: %s", self._stats)


# Global instance
_global_batch_manager: BatchOperationsManager | None = None


def get_batch_manager(parent_window: Any = None) -> BatchOperationsManager:
    """Get or create the global batch operations manager."""
    global _global_batch_manager

    if _global_batch_manager is None:
        _global_batch_manager = BatchOperationsManager(parent_window)
        logger.info("[BatchOps] Created global batch operations manager")

    return _global_batch_manager


def cleanup_batch_manager() -> None:
    """Clean up the global batch operations manager."""
    global _global_batch_manager

    if _global_batch_manager:
        _global_batch_manager.cleanup()
        _global_batch_manager = None
        logger.info("[BatchOps] Global batch operations manager cleaned up")
