"""Batch operations package.

Author: Michael Economou
Date: 2025-12-28

This package contains batch operation management for optimizing
database queries, cache operations, and file I/O operations.

Modules:
    operations_manager: BatchOperationsManager for grouping similar operations
    processor: BatchProcessor for parallel batch processing
"""

from oncutf.core.batch.operations_manager import (
    BatchOperation,
    BatchOperationsManager,
    BatchStats,
    get_batch_manager,
)
from oncutf.core.batch.processor import (
    BatchProcessor,
    BatchProcessorFactory,
)

__all__ = [
    "BatchOperation",
    "BatchOperationsManager",
    "BatchStats",
    "get_batch_manager",
    "BatchProcessor",
    "BatchProcessorFactory",
]
