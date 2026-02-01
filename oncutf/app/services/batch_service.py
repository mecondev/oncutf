"""Batch operations service for UI isolation from core batch infrastructure.

This service provides a clean interface for UI components to access batch operation
functionality without directly depending on core.batch internals.

Author: Michael Economou
Date: 2026-01-24
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from oncutf.app.ports.infra_protocols import BatchOperationsManagerProtocol


# Factory function - registered during bootstrap
_batch_manager_factory: Any = None


def register_batch_manager_factory(factory: Any) -> None:
    """Register factory for creating batch manager instances."""
    global _batch_manager_factory
    _batch_manager_factory = factory


class BatchService:
    """Service layer for batch operations.

    Provides UI-friendly access to batch operations manager.
    Lazy-loads manager on first use to avoid circular dependencies.
    """

    def __init__(self) -> None:
        """Initialize batch service."""
        self._batch_manager: BatchOperationsManagerProtocol | None = None

    @property
    def batch_manager(self) -> BatchOperationsManagerProtocol | None:
        """Get batch operations manager (lazy-loaded via factory)."""
        if self._batch_manager is None and _batch_manager_factory is not None:
            self._batch_manager = _batch_manager_factory()
        return self._batch_manager

    def process_batch(self, files: list[str], operation: str, **kwargs: Any) -> dict[str, Any]:
        """Process batch operation on files.

        Args:
            files: List of file paths
            operation: Operation to perform ('metadata_set', 'hash_store', etc.)
            **kwargs: Additional operation parameters

        Returns:
            Results dictionary with success/failure info

        """
        if not self.batch_manager:
            return {"success": False, "error": "Batch manager not initialized"}

        try:
            # Queue operations based on operation type
            if operation == "metadata_set":
                metadata = kwargs.get("metadata", {})
                is_extended = kwargs.get("is_extended", False)
                for file_path in files:
                    self.batch_manager.queue_metadata_set(file_path, metadata, is_extended)

            elif operation == "hash_store":
                hash_value = kwargs.get("hash_value", "")
                algorithm = kwargs.get("algorithm", "crc32")
                for file_path in files:
                    self.batch_manager.queue_hash_store(file_path, hash_value, algorithm)

            elif operation == "file_io":
                io_operation = kwargs.get("io_operation", "read")
                for file_path in files:
                    self.batch_manager.queue_file_operation(file_path, io_operation, kwargs)

            else:
                return {"success": False, "error": f"Unknown operation: {operation}"}

            # Flush if requested
            if kwargs.get("flush", False):
                flush_results = self.batch_manager.flush_all()
                return {"success": True, "flushed": flush_results}

            return {"success": True, "queued": len(files)}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_operation_status(self, operation_id: str) -> dict[str, Any]:
        """Get status of batch operations.

        Args:
            operation_id: ID of the operation type to query
                         (e.g., 'metadata_set', 'hash_store', 'all')

        Returns:
            Status dictionary with pending operations and statistics

        """
        if not self.batch_manager:
            return {"success": False, "error": "Batch manager not initialized"}

        try:
            if operation_id == "all":
                pending = self.batch_manager.get_pending_operations()
                stats_obj = self.batch_manager.get_stats()
                # Convert stats object to dict for JSON serialization
                return {
                    "success": True,
                    "pending_operations": pending,
                    "total_pending": sum(pending.values()),
                    "stats": {
                        "total_operations": (
                            stats_obj.total_operations
                            if hasattr(stats_obj, "total_operations")
                            else stats_obj.get("total_operations", 0)
                        ),
                        "batched_operations": (
                            stats_obj.batched_operations
                            if hasattr(stats_obj, "batched_operations")
                            else stats_obj.get("batched_operations", 0)
                        ),
                        "batch_flushes": (
                            stats_obj.batch_flushes
                            if hasattr(stats_obj, "batch_flushes")
                            else stats_obj.get("batch_flushes", 0)
                        ),
                        "average_batch_size": (
                            stats_obj.average_batch_size
                            if hasattr(stats_obj, "average_batch_size")
                            else stats_obj.get("average_batch_size", 0.0)
                        ),
                        "total_time_saved": (
                            stats_obj.total_time_saved
                            if hasattr(stats_obj, "total_time_saved")
                            else stats_obj.get("total_time_saved", 0.0)
                        ),
                    },
                }

            pending = self.batch_manager.get_pending_operations()
            return {
                "success": True,
                "operation_type": operation_id,
                "pending_count": pending.get(operation_id, 0),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}


# Singleton instance
_batch_service: BatchService | None = None


def get_batch_service() -> BatchService:
    """Get singleton batch service instance.

    Returns:
        BatchService instance

    """
    global _batch_service
    if _batch_service is None:
        _batch_service = BatchService()
    return _batch_service
