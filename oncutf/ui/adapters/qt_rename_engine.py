"""oncutf.ui.adapters.qt_rename_engine.

Qt-aware wrapper for UnifiedRenameEngine that adds signals.

This adapter wraps the pure Python UnifiedRenameEngine from core and emits
Qt signals after each major operation. UI code should use this class instead
of the core engine directly.

Author: Michael Economou
Date: 2026-01-26
"""

from collections.abc import Callable
from typing import Any

from PyQt5.QtCore import QObject, pyqtSignal

from oncutf.core.rename.data_classes import (
    ExecutionResult,
    PreviewResult,
    RenameState,
    ValidationResult,
)
from oncutf.core.rename.unified_rename_engine import UnifiedRenameEngine
from oncutf.models.file_item import FileItem
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class QtRenameEngine(QObject):
    """Qt-aware wrapper for UnifiedRenameEngine.

    This class wraps the pure Python UnifiedRenameEngine and adds Qt signals
    for UI updates. All business logic is delegated to the core engine.

    Signals:
        preview_updated: Emitted after preview generation
        validation_updated: Emitted after validation
        execution_completed: Emitted after rename execution
        state_changed: Emitted after state changes
    """

    # Central signal system
    preview_updated = pyqtSignal()
    validation_updated = pyqtSignal()
    execution_completed = pyqtSignal()
    state_changed = pyqtSignal()

    def __init__(self, engine: UnifiedRenameEngine | None = None) -> None:
        """Initialize Qt wrapper.

        Args:
            engine: Optional core engine instance. If None, creates new one.

        """
        super().__init__()
        self._engine = engine if engine is not None else UnifiedRenameEngine()
        logger.debug("[QtRenameEngine] Initialized with signal support")

    def generate_preview(
        self,
        files: list[FileItem],
        modules_data: list[dict[str, Any]],
        post_transform: dict[str, Any],
        metadata_cache: Any,
    ) -> PreviewResult:
        """Generate preview and emit signals.

        Args:
            files: List of files to preview
            modules_data: Module configuration data
            post_transform: Post-transform settings
            metadata_cache: Metadata cache instance

        Returns:
            PreviewResult with generated previews

        """
        result = self._engine.generate_preview(files, modules_data, post_transform, metadata_cache)
        self.preview_updated.emit()
        self.state_changed.emit()
        return result

    def validate_preview(self, preview_pairs: list[tuple[str, str]]) -> ValidationResult:
        """Validate preview and emit signals.

        Args:
            preview_pairs: List of (old_path, new_name) tuples

        Returns:
            ValidationResult with validation status

        """
        result = self._engine.validate_preview(preview_pairs)
        self.validation_updated.emit()
        self.state_changed.emit()
        return result

    def execute_rename(
        self,
        files: list[FileItem],
        new_names: list[str],
        conflict_callback: Callable[[Any, str], str] | None = None,
        validator: Any | None = None,
    ) -> ExecutionResult:
        """Execute rename and emit signals.

        Args:
            files: List of files to rename
            new_names: New names for files
            conflict_callback: Optional conflict resolution callback
            validator: Optional validator instance

        Returns:
            ExecutionResult with execution status

        """
        result = self._engine.execute_rename(files, new_names, conflict_callback, validator)
        self.execution_completed.emit()
        self.state_changed.emit()
        return result

    def get_current_state(self) -> RenameState:
        """Get current rename state."""
        return self._engine.get_current_state()

    def clear_cache(self) -> None:
        """Clear all caches."""
        self._engine.clear_cache()

    def get_hash_availability(self, files: list[FileItem]) -> dict[str, bool]:
        """Get hash availability for files."""
        return self._engine.get_hash_availability(files)

    def get_metadata_availability(self, files: list[FileItem]) -> dict[str, bool]:
        """Get metadata availability for files."""
        return self._engine.get_metadata_availability(files)

    def get_performance_stats(self) -> dict[str, Any]:
        """Get performance statistics."""
        return self._engine.get_performance_stats()

    def clear_performance_metrics(self) -> None:
        """Clear performance metrics."""
        self._engine.clear_performance_metrics()

    def get_advanced_cache_stats(self) -> dict[str, Any]:
        """Get advanced cache statistics."""
        return self._engine.get_advanced_cache_stats()

    def clear_advanced_cache(self) -> None:
        """Clear advanced cache."""
        self._engine.clear_advanced_cache()

    def get_batch_processor_stats(self) -> dict[str, Any]:
        """Get batch processor statistics."""
        return self._engine.get_batch_processor_stats()

    def reset_batch_processor_stats(self) -> None:
        """Reset batch processor statistics."""
        self._engine.reset_batch_processor_stats()

    def get_conflict_resolver_stats(self) -> dict[str, Any]:
        """Get conflict resolver statistics."""
        return self._engine.get_conflict_resolver_stats()

    def undo_last_operation(self) -> Any | None:
        """Undo last operation."""
        return self._engine.undo_last_operation()

    def clear_conflict_history(self) -> None:
        """Clear conflict resolution history."""
        self._engine.clear_conflict_history()

    def batch_process_files(
        self, files: list[FileItem], processor_func: Callable[[list[FileItem]], Any]
    ) -> list[Any]:
        """Process files in batches using the provided function."""
        return self._engine.batch_process_files(files, processor_func)

    def resolve_conflicts_batch(
        self, operations: list[tuple[str, str]], strategy: str = "timestamp"
    ) -> list[Any]:
        """Resolve conflicts in batch."""
        return self._engine.resolve_conflicts_batch(operations, strategy)

    @property
    def batch_query_manager(self):
        """Access to batch query manager."""
        return self._engine.batch_query_manager

    @property
    def cache_manager(self):
        """Access to cache manager."""
        return self._engine.cache_manager

    @property
    def preview_manager(self):
        """Access to preview manager."""
        return self._engine.preview_manager

    @property
    def validation_manager(self):
        """Access to validation manager."""
        return self._engine.validation_manager

    @property
    def execution_manager(self):
        """Access to execution manager."""
        return self._engine.execution_manager

    @property
    def state_manager(self):
        """Access to state manager."""
        return self._engine.state_manager

    @property
    def advanced_cache_manager(self):
        """Access to advanced cache manager."""
        return self._engine.advanced_cache_manager

    @property
    def batch_processor(self):
        """Access to batch processor."""
        return self._engine.batch_processor

    @property
    def conflict_resolver(self):
        """Access to conflict resolver."""
        return self._engine.conflict_resolver

    @property
    def performance_monitor(self):
        """Access to performance monitor."""
        return self._engine.performance_monitor
