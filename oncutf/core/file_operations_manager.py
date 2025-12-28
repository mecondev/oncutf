"""DEPRECATED: Backward compatibility stub for file_operations_manager.

Author: Michael Economou
Date: 2025-12-28

This module has been moved to oncutf.core.file.operations_manager.
This stub provides backward compatibility - update imports to use the new path.

New import path:
    from oncutf.core.file.operations_manager import FileOperationsManager
"""

import warnings

# Re-export everything from new location
from oncutf.core.file.operations_manager import FileOperationsManager

__all__ = ["FileOperationsManager"]

# Emit deprecation warning on import (only in development)
warnings.warn(
    "oncutf.core.file_operations_manager is deprecated. "
    "Use oncutf.core.file.operations_manager instead.",
    DeprecationWarning,
    stacklevel=2,
)
