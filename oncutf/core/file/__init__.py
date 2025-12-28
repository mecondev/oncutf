"""File operations package.

Author: Michael Economou
Date: 2025-12-28

This package contains file operation management including:
- File operations (rename, move, copy)
- File validation with content-based identification
- Smart caching for validation results

Modules:
    operations_manager: FileOperationsManager for file operations
    validation_manager: FileValidationManager for content-based validation
"""

from oncutf.core.file.operations_manager import FileOperationsManager
from oncutf.core.file.validation_manager import (
    FileSignature,
    FileValidationManager,
    OperationType,
    ValidationAccuracy,
    ValidationResult,
    get_file_validation_manager,
)

__all__ = [
    "FileOperationsManager",
    "FileValidationManager",
    "FileSignature",
    "OperationType",
    "ValidationAccuracy",
    "ValidationResult",
    "get_file_validation_manager",
]
