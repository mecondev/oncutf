"""DEPRECATED: Backward compatibility stub for metadata_command_manager.

Author: Michael Economou
Date: 2025-12-28

This module has been moved to oncutf.core.metadata.command_manager.
This stub provides backward compatibility - update imports to use the new path.

New import path:
    from oncutf.core.metadata.command_manager import MetadataCommandManager
    from oncutf.core.metadata import get_metadata_command_manager
"""

import warnings

# Re-export everything from new location
from oncutf.core.metadata.command_manager import (
    MetadataCommandManager,
    cleanup_metadata_command_manager,
    get_metadata_command_manager,
)

__all__ = [
    "MetadataCommandManager",
    "cleanup_metadata_command_manager",
    "get_metadata_command_manager",
]

# Emit deprecation warning on import (only in development)
warnings.warn(
    "oncutf.core.metadata_command_manager is deprecated. "
    "Use oncutf.core.metadata.command_manager instead.",
    DeprecationWarning,
    stacklevel=2,
)
