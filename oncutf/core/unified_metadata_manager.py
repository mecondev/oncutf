"""DEPRECATED: Backward compatibility stub for unified_metadata_manager.

Author: Michael Economou
Date: 2025-12-28

This module has been moved to oncutf.core.metadata.unified_manager.
This stub provides backward compatibility - update imports to use the new path.

New import path:
    from oncutf.core.metadata.unified_manager import UnifiedMetadataManager
    from oncutf.core.metadata import get_unified_metadata_manager
"""

import warnings

# Re-export everything from new location
from oncutf.core.metadata.unified_manager import (
    UnifiedMetadataManager,
    cleanup_unified_metadata_manager,
    get_unified_metadata_manager,
)

__all__ = [
    "UnifiedMetadataManager",
    "cleanup_unified_metadata_manager",
    "get_unified_metadata_manager",
]

# Emit deprecation warning on import (only in development)
warnings.warn(
    "oncutf.core.unified_metadata_manager is deprecated. "
    "Use oncutf.core.metadata.unified_manager instead.",
    DeprecationWarning,
    stacklevel=2,
)
