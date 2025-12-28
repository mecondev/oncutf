"""Batch operations package.

Author: Michael Economou
Date: 2025-12-28

This package contains batch operation management for optimizing
database queries, cache operations, and file I/O operations.

Modules:
    operations_manager: BatchOperationsManager for grouping similar operations
"""

from oncutf.core.batch.operations_manager import (
    BatchOperation,
    BatchOperationsManager,
    BatchStats,
    get_batch_manager,
)

__all__ = [
    "BatchOperation",
    "BatchOperationsManager",
    "BatchStats",
    "get_batch_manager",
]
