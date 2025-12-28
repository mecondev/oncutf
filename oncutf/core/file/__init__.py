"""File operations package.

Author: Michael Economou
Date: 2025-12-28
Updated: 2025-12-28

This package contains all file-related functionality:
- File operations (rename, move, copy)
- File validation with content-based identification
- File loading and directory scanning
- File store and state management
- Filesystem monitoring

Modules:
    operations_manager: FileOperationsManager for file operations
    validation_manager: FileValidationManager for content-based validation
    load_manager: FileLoadManager for loading files from directories
    store: FileStore for centralized file state management
    monitor: FilesystemMonitor for watching file changes
"""

from oncutf.core.file.load_manager import FileLoadManager
from oncutf.core.file.monitor import FilesystemMonitor
from oncutf.core.file.operations_manager import FileOperationsManager
from oncutf.core.file.store import FileStore
from oncutf.core.file.validation_manager import (
    FileSignature,
    FileValidationManager,
    OperationType,
    ValidationAccuracy,
    ValidationResult,
    get_file_validation_manager,
)

__all__ = [
    # Operations
    "FileOperationsManager",
    # Validation
    "FileValidationManager",
    "FileSignature",
    "OperationType",
    "ValidationAccuracy",
    "ValidationResult",
    "get_file_validation_manager",
    # Loading & Store
    "FileLoadManager",
    "FileStore",
    # Monitoring
    "FilesystemMonitor",
]
