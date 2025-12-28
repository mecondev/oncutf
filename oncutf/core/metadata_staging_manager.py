"""DEPRECATED: Backward compatibility stub for metadata_staging_manager.

Author: Michael Economou
Date: 2025-12-28

This module has been moved to oncutf.core.metadata.staging_manager.
This stub provides backward compatibility - update imports to use the new path.

New import path:
    from oncutf.core.metadata.staging_manager import MetadataStagingManager
    from oncutf.core.metadata import get_metadata_staging_manager
"""

import warnings

# Re-export everything from new location
from oncutf.core.metadata.staging_manager import (
    MetadataStagingManager,
    get_metadata_staging_manager,
    set_metadata_staging_manager,
)

__all__ = [
    "MetadataStagingManager",
    "get_metadata_staging_manager",
    "set_metadata_staging_manager",
]

# Emit deprecation warning on import (only in development)
warnings.warn(
    "oncutf.core.metadata_staging_manager is deprecated. "
    "Use oncutf.core.metadata.staging_manager instead.",
    DeprecationWarning,
    stacklevel=2,
)
