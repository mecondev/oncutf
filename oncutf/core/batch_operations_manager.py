"""DEPRECATED: Backward compatibility stub for batch_operations_manager.

Author: Michael Economou
Date: 2025-12-28

This module has been moved to oncutf.core.batch.operations_manager.
This stub provides backward compatibility - update imports to use the new path.

New import path:
    from oncutf.core.batch.operations_manager import BatchOperationsManager
    from oncutf.core.batch import get_batch_manager
"""

import warnings

# Re-export everything from new location
from oncutf.core.batch.operations_manager import (
    BatchOperation,
    BatchOperationsManager,
    BatchStats,
    cleanup_batch_manager,
    get_batch_manager,
)

__all__ = [
    "BatchOperation",
    "BatchOperationsManager",
    "BatchStats",
    "cleanup_batch_manager",
    "get_batch_manager",
]

# Emit deprecation warning on import (only in development)
warnings.warn(
    "oncutf.core.batch_operations_manager is deprecated. "
    "Use oncutf.core.batch.operations_manager instead.",
    DeprecationWarning,
    stacklevel=2,
)
