"""DEPRECATED: Backward compatibility stub for metadata_operations_manager.

Author: Michael Economou
Date: 2025-12-28

This module has been moved to oncutf.core.metadata.operations_manager.
This stub provides backward compatibility - update imports to use the new path.

New import path:
    from oncutf.core.metadata.operations_manager import MetadataOperationsManager
"""

import warnings

# Re-export everything from new location
from oncutf.core.metadata.operations_manager import MetadataOperationsManager

__all__ = ["MetadataOperationsManager"]

# Emit deprecation warning on import (only in development)
warnings.warn(
    "oncutf.core.metadata_operations_manager is deprecated. "
    "Use oncutf.core.metadata.operations_manager instead.",
    DeprecationWarning,
    stacklevel=2,
)
