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
            operation: Operation to perform
            **kwargs: Additional operation parameters

        Returns:
            Results dictionary with success/failure info

        """
        # TODO: Implement when BatchOperationsManager API is defined (see: https://github.com/mecondev/oncutf/issues/1#issue-3880442485)
        return {"success": False, "error": "Not yet implemented"}

    def get_operation_status(self, operation_id: str) -> dict[str, Any]:
        """Get status of a batch operation.

        Args:
            operation_id: ID of the operation

        Returns:
            Status dictionary

        """
        # TODO: Implement when BatchOperationsManager API is defined (see: https://github.com/mecondev/oncutf/issues/1#issue-3880442485)
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
