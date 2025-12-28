"""DEPRECATED: Backward compatibility stub for unified_column_service.

Author: Michael Economou
Date: 2025-12-28

This module has been moved to oncutf.core.ui_managers.column_service.
This stub provides backward compatibility - update imports to use the new path.

New import path:
    from oncutf.core.ui_managers.column_service import UnifiedColumnService
    from oncutf.core.ui_managers import get_column_service
"""

import warnings

# Re-export everything from new location
from oncutf.core.ui_managers.column_service import (
    ColumnAlignment,
    ColumnConfig,
    UnifiedColumnService,
    get_column_service,
    invalidate_column_service,
)

__all__ = [
    "ColumnAlignment",
    "ColumnConfig",
    "UnifiedColumnService",
    "get_column_service",
    "invalidate_column_service",
]

# Emit deprecation warning on import (only in development)
warnings.warn(
    "oncutf.core.unified_column_service is deprecated. "
    "Use oncutf.core.ui_managers.column_service instead.",
    DeprecationWarning,
    stacklevel=2,
)
