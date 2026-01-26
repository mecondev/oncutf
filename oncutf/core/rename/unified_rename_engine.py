"""oncutf.core.rename.unified_rename_engine.

Central rename engine facade for previewing, validating and executing
batch rename operations.

This module provides the `UnifiedRenameEngine` pure Python facade used by
controllers and business logic. For Qt-aware signals, use QtRenameEngine
from oncutf.ui.adapters.

The engine respects the preview -> validate -> execute workflow and
provides callbacks for state change notifications.

Author: Michael Economou
Date: 2026-01-01
"""

from collections.abc import Callable
from dataclasses import asdict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from oncutf.models.file_item import FileItem

from oncutf.core.batch.processor import BatchProcessorFactory
from oncutf.core.cache.advanced_cache_manager import AdvancedCacheManager
from oncutf.core.conflict_resolver import ConflictResolver
from oncutf.core.performance_monitor import get_performance_monitor, monitor_performance
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
from oncutf.core.rename.state_manager import RenameStateManager
from oncutf.core.rename.validation_manager import UnifiedValidationManager
from oncutf.models.file_item import FileItem
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)

# Re-export data classes for backward compatibility
__all__ = [
    "BatchQueryManager",
    "ExecutionItem",
    "ExecutionResult",
    "PreviewResult",
    "RenameState",
    "RenameStateManager",
    "SmartCacheManager",
    "UnifiedExecutionManager",
    "UnifiedPreviewManager",
    "UnifiedRenameEngine",
    "UnifiedValidationManager",
    "ValidationItem",
    "ValidationResult",
]


class UnifiedRenameEngine:
    """Pure Python facade for the unified rename workflow.

    This Qt-free object exposes high-level methods for:
        - generating previews (`generate_preview`)
        - validating previewed names (`validate_preview`)
        - executing renames with conflict handling (`execute_rename`)

    For Qt signals, use QtRenameEngine from oncutf.ui.adapters.
    Callbacks can be registered for state change notifications.
    """

    def __init__(self) -> None:
        """Initialize the rename engine with all managers and caches."""
        # Initialize managers
        self.batch_query_manager = BatchQueryManager()
        self.cache_manager = SmartCacheManager()
        self.preview_manager = UnifiedPreviewManager(self.batch_query_manager, self.cache_manager)
        self.validation_manager = UnifiedValidationManager(self.cache_manager)
        self.execution_manager = UnifiedExecutionManager()
        self.state_manager = RenameStateManager()

        # Initialize Phase 4 components
        self.advanced_cache_manager = AdvancedCacheManager()
        self.batch_processor = BatchProcessorFactory.create_processor("smart")
        self.conflict_resolver = ConflictResolver()

        # Initialize performance monitor
        self.performance_monitor = get_performance_monitor()

        logger.debug("[UnifiedRenameEngine] Initialized with Phase 4 components")

    @monitor_performance("generate_preview")
    def generate_preview(
        self,
        files: list[FileItem],
        modules_data: list[dict[str, Any]],
        post_transform: dict[str, Any],
        metadata_cache: Any,
    ) -> PreviewResult:
        """Generate preview with unified system."""
        result = self.preview_manager.generate_preview(
            files, modules_data, post_transform, metadata_cache
        )

        # Update state
        new_state = RenameState(
            files=files,
            modules_data=modules_data,
            post_transform=post_transform,
            metadata_cache=metadata_cache,
            preview_result=result,
        )
        self.state_manager.update_state(new_state)

        return result

    @monitor_performance("validate_preview")
    def validate_preview(self, preview_pairs: list[tuple[str, str]]) -> ValidationResult:
        """Validate preview with unified system."""
        result = self.validation_manager.validate_preview(preview_pairs)

        # Update state
        current_state = self.state_manager.get_state()
        current_state.validation_result = result
        self.state_manager.update_state(current_state)

        return result

    @monitor_performance("execute_rename")
    def execute_rename(
        self,
        files: list[FileItem],
        new_names: list[str],
        conflict_callback: Callable[[Any, str], str] | None = None,
        validator: Any | None = None,
    ) -> ExecutionResult:
        """Execute rename with unified system."""
        result = self.execution_manager.execute_rename(
            files, new_names, conflict_callback, validator
        )

        # Update state
        current_state = self.state_manager.get_state()
        current_state.execution_result = result
        self.state_manager.update_state(current_state)

        return result

    def get_current_state(self) -> RenameState:
        """Get current state."""
        return self.state_manager.get_state()

    def clear_cache(self) -> None:
        """Clear all caches."""
        self.cache_manager.clear_cache()
        logger.debug("[UnifiedRenameEngine] Cache cleared")

    def get_hash_availability(self, files: list[FileItem]) -> dict[str, bool]:
        """Get hash availability for files."""
        return self.batch_query_manager.get_hash_availability(files)

    def get_metadata_availability(self, files: list[FileItem]) -> dict[str, bool]:
        """Get metadata availability for files."""
        return self.batch_query_manager.get_metadata_availability(files)

    def get_performance_stats(self) -> dict[str, Any]:
        """Get performance statistics."""
        stats = self.performance_monitor.get_stats()
        return asdict(stats)

    def clear_performance_metrics(self) -> None:
        """Clear performance metrics."""
        self.performance_monitor.clear_metrics()

    # Phase 4 Integration Methods

    def get_advanced_cache_stats(self) -> dict[str, Any]:
        """Get advanced cache statistics."""
        return self.cache_manager.get_stats()

    def clear_advanced_cache(self) -> None:
        """Clear advanced cache."""
        self.cache_manager.clear_cache()

    def get_batch_processor_stats(self) -> dict[str, Any]:
        """Get batch processor statistics."""
        return self.batch_processor.get_stats()

    def reset_batch_processor_stats(self) -> None:
        """Reset batch processor statistics."""
        self.batch_processor.reset_stats()

    def get_conflict_resolver_stats(self) -> dict[str, Any]:
        """Get conflict resolver statistics."""
        return self.conflict_resolver.get_stats()

    def undo_last_operation(self) -> Any | None:
        """Undo last operation."""
        return self.conflict_resolver.undo_last_operation()

    def clear_conflict_history(self) -> None:
        """Clear conflict resolution history."""
        self.conflict_resolver.clear_history()

    def batch_process_files(
        self, files: list[FileItem], processor_func: Callable[[list[FileItem]], Any]
    ) -> list[Any]:
        """Process files in batches using the provided function.

        The processor_func should accept a list of FileItem objects and return
        a result object for that batch.
        """
        batch_size = 50  # Process in batches of 50 files
        results = []

        for i in range(0, len(files), batch_size):
            batch = files[i : i + batch_size]
            batch_result = processor_func(batch)
            results.append(batch_result)

        return results

    def resolve_conflicts_batch(
        self, operations: list[tuple[str, str]], strategy: str = "timestamp"
    ) -> list[Any]:
        """Resolve conflicts in batch."""
        return self.conflict_resolver.batch_resolve_conflicts(operations, strategy)
