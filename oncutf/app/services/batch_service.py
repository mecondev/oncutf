"""Batch operations service for UI isolation from core batch infrastructure.

This service provides a clean interface for UI components to access batch operation
functionality without directly depending on core.batch internals.

Author: Michael Economou
Date: 2026-01-24
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from oncutf.core.batch import BatchOperationsManager


class BatchService:
    """Service layer for batch operations.

    Provides UI-friendly access to batch operations manager.
    Lazy-loads manager on first use to avoid circular dependencies.
    """

    def __init__(self) -> None:
        """Initialize batch service."""
        self._batch_manager: BatchOperationsManager | None = None

    @property
    def batch_manager(self) -> BatchOperationsManager:
        """Get batch operations manager (lazy-loaded)."""
        if self._batch_manager is None:
            from oncutf.core.batch import BatchOperationsManager

            self._batch_manager = BatchOperationsManager()
        return self._batch_manager

    def process_batch(
        self, files: list[str], operation: str, **kwargs: Any
    ) -> dict[str, Any]:
        """Process batch operation on files.

        Args:
            files: List of file paths
            operation: Operation to perform
            **kwargs: Additional operation parameters

        Returns:
            Results dictionary with success/failure info

        """
        # TODO: Implement when BatchOperationsManager API is defined
        return {"success": False, "error": "Not yet implemented"}

    def get_operation_status(self, operation_id: str) -> dict[str, Any]:
        """Get status of a batch operation.

        Args:
            operation_id: ID of the operation

        Returns:
            Status dictionary

        """
        # TODO: Implement when BatchOperationsManager API is defined
        return {"success": False, "error": "Not yet implemented"}


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
