"""Rename operations module.

This module provides file renaming functionality including:
- RenameManager: High-level rename coordination
- RenameHistoryManager: Rename history and undo operations
- UnifiedRenameEngine: Core rename engine with preview and validation

The unified rename engine has been split into focused modules:
- data_classes: Result dataclasses (PreviewResult, ValidationResult, etc.)
- query_managers: BatchQueryManager and SmartCacheManager
- preview_manager: UnifiedPreviewManager
- validation_manager: UnifiedValidationManager
- execution_manager: UnifiedExecutionManager
- state_manager: RenameStateManager

Author: Michael Economou
Date: 2025-12-20
"""

from __future__ import annotations

from oncutf.core.rename.data_classes import (
    ExecutionItem,
    ExecutionResult,
    PreviewResult,
    RenameState,
    ValidationItem,
    ValidationResult,
)
from oncutf.core.rename.execution_manager import UnifiedExecutionManager
from oncutf.core.rename.preview_manager import UnifiedPreviewManager
from oncutf.core.rename.query_managers import BatchQueryManager, SmartCacheManager
from oncutf.core.rename.rename_history_manager import RenameHistoryManager
from oncutf.core.rename.rename_manager import RenameManager
from oncutf.core.rename.state_manager import RenameStateManager
from oncutf.core.rename.unified_rename_engine import UnifiedRenameEngine
from oncutf.core.rename.validation_manager import UnifiedValidationManager

__all__ = [
    # Main entry points
    "RenameHistoryManager",
    "RenameManager",
    "UnifiedRenameEngine",
    # Data classes
    "PreviewResult",
    "ValidationItem",
    "ValidationResult",
    "ExecutionItem",
    "ExecutionResult",
    "RenameState",
    # Managers
    "BatchQueryManager",
    "SmartCacheManager",
    "UnifiedPreviewManager",
    "UnifiedValidationManager",
    "UnifiedExecutionManager",
    "RenameStateManager",
]
