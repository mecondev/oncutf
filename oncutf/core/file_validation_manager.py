"""DEPRECATED: Backward compatibility stub for file_validation_manager.

Author: Michael Economou
Date: 2025-12-28

This module has been moved to oncutf.core.file.validation_manager.
This stub provides backward compatibility - update imports to use the new path.

New import path:
    from oncutf.core.file.validation_manager import FileValidationManager
    from oncutf.core.file import get_file_validation_manager, OperationType
"""

import warnings

# Re-export everything from new location
from oncutf.core.file.validation_manager import (
    FileSignature,
    FileValidationManager,
    OperationType,
    ValidationAccuracy,
    ValidationResult,
    ValidationThresholds,
    get_file_validation_manager,
)

__all__ = [
    "FileSignature",
    "FileValidationManager",
    "OperationType",
    "ValidationAccuracy",
    "ValidationResult",
    "ValidationThresholds",
    "get_file_validation_manager",
]

# Emit deprecation warning on import (only in development)
warnings.warn(
    "oncutf.core.file_validation_manager is deprecated. "
    "Use oncutf.core.file.validation_manager instead.",
    DeprecationWarning,
    stacklevel=2,
)
