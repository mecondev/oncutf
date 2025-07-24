"""
Module: unified_rename_engine.py

Author: Michael Economou
Date: 2025-01-27

UnifiedRenameEngine - Central engine for all rename operations.
Integrates preview, validation, duplicate detection, and execution.
"""

import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from core.advanced_cache_manager import AdvancedCacheManager
from core.batch_processor import BatchProcessorFactory
from core.conflict_resolver import ConflictResolver
from core.performance_monitor import get_performance_monitor, monitor_performance
from core.pyqt_imports import QObject, pyqtSignal
from models.file_item import FileItem
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


@dataclass
class PreviewResult:
    """Preview generation result."""

    name_pairs: list[tuple[str, str]]
    has_changes: bool
    errors: list[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


@dataclass
class ValidationItem:
    """Validation result for a file."""

    old_name: str
    new_name: str
    is_valid: bool
    is_duplicate: bool
    is_unchanged: bool
    error_message: str = ""


@dataclass
class ValidationResult:
    """Αποτέλεσμα validation."""

    items: list[ValidationItem]
    duplicates: set[str]
    has_errors: bool = False

    def __post_init__(self):
        self.has_errors = any(not item.is_valid for item in self.items)


@dataclass
class ExecutionItem:
    """Execution result για ένα αρχείο."""

    old_path: str
    new_path: str
    success: bool
    error_message: str = ""
    skip_reason: str = ""
    is_conflict: bool = False
    conflict_resolved: bool = False


@dataclass
class ExecutionResult:
    """Αποτέλεσμα rename execution."""

    items: list[ExecutionItem]
    success_count: int = 0
    error_count: int = 0
    skipped_count: int = 0
    conflicts_count: int = 0

    def __post_init__(self):
        self.success_count = sum(1 for item in self.items if item.success)
        self.error_count = sum(1 for item in self.items if not item.success and item.error_message)
        self.skipped_count = sum(1 for item in self.items if not item.success and item.skip_reason)
        self.conflicts_count = sum(1 for item in self.items if item.is_conflict)


@dataclass
class RenameState:
    """Κεντρικό state για rename operations."""

    files: list[FileItem] = None
    modules_data: list[dict[str, Any]] = None
    post_transform: dict[str, Any] = None
    metadata_cache: Any = None
    preview_result: PreviewResult | None = None
    validation_result: ValidationResult | None = None
    execution_result: ExecutionResult | None = None

    # State flags
    preview_changed: bool = False
    validation_changed: bool = False
    execution_changed: bool = False

    def __post_init__(self):
        if self.files is None:
            self.files = []
        if self.modules_data is None:
            self.modules_data = []
        if self.post_transform is None:
            self.post_transform = {}


class BatchQueryManager:
    """Κεντρικός batch query manager για αποδοτικές queries."""

    def __init__(self):
        self._hash_cache = None
        self._metadata_cache = None

    def get_hash_availability(self, files: list[FileItem]) -> dict[str, bool]:
        """Single batch query για hash availability."""
        if not files:
            return {}

        try:
            from core.persistent_hash_cache import get_persistent_hash_cache

            hash_cache = get_persistent_hash_cache()

            file_paths = [f.full_path for f in files if f.full_path]
            files_with_hash = hash_cache.get_files_with_hash_batch(file_paths, "CRC32")

            # Convert to boolean dict
            result = {}
            for file in files:
                if file.full_path:
                    result[file.full_path] = file.full_path in files_with_hash

            return result

        except Exception as e:
            logger.error(f"[BatchQueryManager] Error getting hash availability: {e}")
            return {}

    def get_metadata_availability(self, files: list[FileItem]) -> dict[str, bool]:
        """Single batch query για metadata availability."""
        if not files:
            return {}

        try:
            # Get metadata cache
            from core.application_context import get_app_context

            context = get_app_context()
            if not context or not hasattr(context, "_metadata_cache"):
                return {}

            metadata_cache = context._metadata_cache
            if not metadata_cache:
                return {}

            result = {}
            for file in files:
                if file.full_path:
                    # Check if file has metadata
                    has_metadata = self._file_has_metadata(file.full_path, metadata_cache)
                    logger.debug(f"[DEBUG] [UnifiedRenameEngine] get_metadata_availability: {file.full_path} has_metadata={has_metadata}", extra={"dev_only": True})
                    result[file.full_path] = has_metadata

            logger.debug(f"[DEBUG] [UnifiedRenameEngine] get_metadata_availability result: {result}", extra={"dev_only": True})
            return result

        except Exception as e:
            logger.error(f"[BatchQueryManager] Error getting metadata availability: {e}")
            return {}

    def _file_has_metadata(self, file_path: str, metadata_cache) -> bool:
        """Check if a file has metadata."""
        try:
            if hasattr(metadata_cache, "_memory_cache"):
                entry = metadata_cache._memory_cache.get(file_path)
                if entry and hasattr(entry, "data") and entry.data:
                    # Check if there are any non-internal metadata fields
                    metadata_fields = {
                        k
                        for k in entry.data
                        if not k.startswith("_") and k not in {"path", "filename"}
                    }
                    return len(metadata_fields) > 0
            return False
        except Exception as e:
            logger.debug(f"[BatchQueryManager] Error checking metadata for {file_path}: {e}")
            return False


class SmartCacheManager:
    """Έξυπνο caching με intelligent invalidation."""

    def __init__(self):
        self._preview_cache: dict[str, tuple[PreviewResult, float]] = {}
        self._validation_cache: dict[str, tuple[ValidationResult, float]] = {}
        self._execution_cache: dict[str, tuple[ExecutionResult, float]] = {}
        self._cache_ttl = 0.1  # 100ms TTL

    def get_cached_preview(self, key: str) -> PreviewResult | None:
        """Get cached preview με smart invalidation."""
        if key in self._preview_cache:
            result, timestamp = self._preview_cache[key]
            if time.time() - timestamp < self._cache_ttl:
                return result
            else:
                del self._preview_cache[key]
        return None

    def cache_preview(self, key: str, result: PreviewResult) -> None:
        """Cache preview result."""
        self._preview_cache[key] = (result, time.time())

    def get_cached_validation(self, key: str) -> ValidationResult | None:
        """Get cached validation με smart invalidation."""
        if key in self._validation_cache:
            result, timestamp = self._validation_cache[key]
            if time.time() - timestamp < self._cache_ttl:
                return result
            else:
                del self._validation_cache[key]
        return None

    def cache_validation(self, key: str, result: ValidationResult) -> None:
        """Cache validation result."""
        self._validation_cache[key] = (result, time.time())

    def clear_cache(self) -> None:
        """Clear all caches."""
        self._preview_cache.clear()
        self._validation_cache.clear()
        self._execution_cache.clear()


class UnifiedPreviewManager:
    """Κεντρικός preview manager με smart caching και batch queries."""

    def __init__(self, batch_query_manager: BatchQueryManager, cache_manager: SmartCacheManager):
        self.batch_query_manager = batch_query_manager
        self.cache_manager = cache_manager

    def generate_preview(
        self,
        files: list[FileItem],
        modules_data: list[dict[str, Any]],
        post_transform: dict[str, Any],
        metadata_cache: Any,
    ) -> PreviewResult:
        """Generate preview με batch queries για hash/metadata."""

        if not files:
            return PreviewResult([], False)

        # Generate cache key
        cache_key = self._generate_cache_key(files, modules_data, post_transform)

        # Check cache first
        cached_result = self.cache_manager.get_cached_preview(cache_key)
        if cached_result:
            logger.debug("[UnifiedPreviewManager] Using cached preview")
            return cached_result

        # Get batch availability data
        hash_availability = self.batch_query_manager.get_hash_availability(files)
        metadata_availability = self.batch_query_manager.get_metadata_availability(files)

        # Generate preview
        start_time = time.time()
        name_pairs = self._generate_name_pairs(
            files,
            modules_data,
            post_transform,
            metadata_cache,
            hash_availability,
            metadata_availability,
        )

        # Check for changes
        has_changes = any(old_name != new_name for old_name, new_name in name_pairs)

        # Create result
        result = PreviewResult(name_pairs, has_changes)

        # Cache result
        self.cache_manager.cache_preview(cache_key, result)

        elapsed = time.time() - start_time
        if elapsed > 0.05:  # Log slow preview generation
            logger.info(
                f"[UnifiedPreviewManager] Preview generation took {elapsed:.3f}s for {len(files)} files"
            )

        return result

    def _generate_cache_key(
        self, files: list[FileItem], modules_data: list[dict], post_transform: dict
    ) -> str:
        """Generate cache key for preview results."""
        file_paths = tuple(f.full_path for f in files if f.full_path)
        import json

        try:
            modules_hash = hash(json.dumps(modules_data, sort_keys=True, default=str))
            transform_hash = hash(json.dumps(post_transform, sort_keys=True, default=str))
        except (TypeError, ValueError):
            modules_hash = hash(str(modules_data))
            transform_hash = hash(str(post_transform))

        return f"{hash(file_paths)}_{modules_hash}_{transform_hash}"

    def _generate_name_pairs(
        self,
        files: list[FileItem],
        modules_data: list[dict[str, Any]],
        post_transform: dict[str, Any],
        metadata_cache: Any,
        hash_availability: dict[str, bool],
        metadata_availability: dict[str, bool],
    ) -> list[tuple[str, str]]:
        """Generate name pairs με smart metadata/hash checking."""

        from modules.name_transform_module import NameTransformModule

        name_pairs = []
        has_name_transform = NameTransformModule.is_effective(post_transform)

        for idx, file in enumerate(files):
            try:
                basename, extension = os.path.splitext(file.filename)

                # Apply modules with availability context
                new_fullname = self._apply_modules_with_context(
                    file,
                    modules_data,
                    idx,
                    metadata_cache,
                    hash_availability,
                    metadata_availability,
                )

                if extension and new_fullname.lower().endswith(extension.lower()):
                    new_basename = new_fullname[: -(len(extension))]
                else:
                    new_basename = new_fullname

                if has_name_transform:
                    new_basename = NameTransformModule.apply_from_data(post_transform, new_basename)

                # Validate basename
                if not self._is_valid_filename_text(new_basename):
                    name_pairs.append((file.filename, file.filename))
                    continue

                new_name = f"{new_basename}{extension}" if extension else new_basename
                name_pairs.append((file.filename, new_name))

            except Exception as e:
                logger.warning(f"Failed to generate preview for {file.filename}: {e}")
                name_pairs.append((file.filename, file.filename))

        return name_pairs

    def _apply_modules_with_context(
        self,
        file: FileItem,
        modules_data: list[dict[str, Any]],
        index: int,
        metadata_cache: Any,
        hash_availability: dict[str, bool],
        metadata_availability: dict[str, bool],
    ) -> str:
        """Apply modules με context για hash/metadata availability."""

        from utils.preview_engine import apply_rename_modules

        # Check if this file has required data for modules
        for module_data in modules_data:
            if module_data.get("type") == "metadata":
                category = module_data.get("category")
                if category == "hash":
                    # Check if file has hash
                    if not hash_availability.get(file.full_path, False):
                        return "missing_hash"
                elif category == "metadata_keys":
                    # Check if file has metadata
                    if not metadata_availability.get(file.full_path, False):
                        return "missing_metadata"

        # Apply modules normally
        return apply_rename_modules(modules_data, index, file, metadata_cache)

    def _is_valid_filename_text(self, basename: str) -> bool:
        """Validate filename text."""
        try:
            from utils.validate_filename_text import is_valid_filename_text

            return is_valid_filename_text(basename)
        except ImportError:
            return True


class UnifiedValidationManager:
    """Κεντρικός validation manager με duplicate detection."""

    def __init__(self, cache_manager: SmartCacheManager):
        self.cache_manager = cache_manager

    def validate_preview(self, preview_pairs: list[tuple[str, str]]) -> ValidationResult:
        """Validate preview και detect duplicates."""

        # Generate cache key
        cache_key = self._generate_validation_cache_key(preview_pairs)

        # Check cache first
        cached_result = self.cache_manager.get_cached_validation(cache_key)
        if cached_result:
            logger.debug("[UnifiedValidationManager] Using cached validation")
            return cached_result

        results = []
        duplicates = set()
        seen_names = set()

        for old_name, new_name in preview_pairs:
            # Filename validation
            is_valid, error = self._validate_filename(new_name)

            # Duplicate detection
            is_duplicate = new_name in seen_names
            if is_duplicate:
                duplicates.add(new_name)
            else:
                seen_names.add(new_name)

            # No change detection
            is_unchanged = old_name == new_name

            results.append(
                ValidationItem(
                    old_name=old_name,
                    new_name=new_name,
                    is_valid=is_valid,
                    is_duplicate=is_duplicate,
                    is_unchanged=is_unchanged,
                    error_message=error,
                )
            )

        result = ValidationResult(results, duplicates)

        # Cache result
        self.cache_manager.cache_validation(cache_key, result)

        return result

    def _generate_validation_cache_key(self, preview_pairs: list[tuple[str, str]]) -> str:
        """Generate cache key for validation results."""
        return hash(tuple(preview_pairs))

    def _validate_filename(self, filename: str) -> tuple[bool, str]:
        """Validate filename."""
        try:
            from utils.filename_validator import validate_filename_part

            basename = os.path.splitext(filename)[0]
            is_valid, error = validate_filename_part(basename)
            return is_valid, error or ""
        except Exception as e:
            return False, f"Validation error: {e}"


class UnifiedExecutionManager:
    """Κεντρικός execution manager με smart conflict resolution."""

    def __init__(self):
        self.conflict_callback = None
        self.validator = None

    def execute_rename(
        self,
        files: list[FileItem],
        new_names: list[str],
        conflict_callback: Callable | None = None,
        validator: object | None = None,
    ) -> ExecutionResult:
        """Execute rename με smart conflict resolution."""

        self.conflict_callback = conflict_callback
        self.validator = validator

        if not files or not new_names:
            return ExecutionResult([])

        # Build execution plan
        execution_items = self._build_execution_plan(files, new_names)

        # Execute with conflict resolution
        results = []
        skip_all = False

        for item in execution_items:
            if skip_all:
                item.skip_reason = "skip_all"
                results.append(item)
                continue

            # Validate filename
            if self.validator:
                is_valid, error = self.validator(os.path.basename(item.new_path))
                if not is_valid:
                    item.error_message = error
                    results.append(item)
                    continue

            # Check for conflicts
            if os.path.exists(item.new_path):
                item.is_conflict = True
                resolution = self._resolve_conflict(item)

                if resolution == "skip":
                    item.skip_reason = "conflict_skipped"
                    results.append(item)
                    continue
                elif resolution == "skip_all":
                    skip_all = True
                    item.skip_reason = "conflict_skip_all"
                    results.append(item)
                    continue
                elif resolution == "overwrite":
                    item.conflict_resolved = True
                else:
                    # Cancel
                    break

            # Execute rename
            success = self._execute_single_rename(item)
            if success:
                item.success = True

            results.append(item)

        return ExecutionResult(results)

    def _build_execution_plan(
        self, files: list[FileItem], new_names: list[str]
    ) -> list[ExecutionItem]:
        """Build execution plan for rename operations."""
        items = []

        for file, new_name in zip(files, new_names, strict=False):
            old_path = file.full_path
            new_path = os.path.join(os.path.dirname(old_path), new_name)

            item = ExecutionItem(old_path=old_path, new_path=new_path, success=False)
            items.append(item)

        return items

    def _resolve_conflict(self, item: ExecutionItem) -> str:
        """Resolve file conflict."""
        if self.conflict_callback:
            try:
                return self.conflict_callback(None, os.path.basename(item.new_path))
            except Exception as e:
                logger.error(f"[UnifiedExecutionManager] Error in conflict callback: {e}")
                return "skip"
        return "skip"  # Default to skip

    def _execute_single_rename(self, item: ExecutionItem) -> bool:
        """Execute single rename operation."""
        try:
            from utils.rename_logic import is_case_only_change, safe_case_rename

            old_name = os.path.basename(item.old_path)
            new_name = os.path.basename(item.new_path)

            # Use safe case rename for case-only changes
            if is_case_only_change(old_name, new_name):
                return safe_case_rename(item.old_path, item.new_path)
            else:
                # Regular rename
                os.rename(item.old_path, item.new_path)
                return True

        except Exception as e:
            item.error_message = str(e)
            logger.error(f"[UnifiedExecutionManager] Rename failed for {item.old_path}: {e}")
            return False


class RenameStateManager:
    """Κεντρικός state manager για rename operations."""

    def __init__(self):
        self.current_state = RenameState()
        self._previous_state = None

    def update_state(self, new_state: RenameState) -> None:
        """Update state και detect changes."""
        self._previous_state = self.current_state
        self.current_state = new_state

        # Detect changes
        self._detect_state_changes()

    def _detect_state_changes(self) -> None:
        """Detect changes between previous and current state."""
        if not self._previous_state:
            return

        # Check preview changes
        if self._previous_state.preview_result != self.current_state.preview_result:
            self.current_state.preview_changed = True

        # Check validation changes
        if self._previous_state.validation_result != self.current_state.validation_result:
            self.current_state.validation_changed = True

        # Check execution changes
        if self._previous_state.execution_result != self.current_state.execution_result:
            self.current_state.execution_changed = True

    def get_state(self) -> RenameState:
        """Get current state."""
        return self.current_state

    def reset_changes(self) -> None:
        """Reset change flags."""
        self.current_state.preview_changed = False
        self.current_state.validation_changed = False
        self.current_state.execution_changed = False


class UnifiedRenameEngine(QObject):
    """
    Κεντρικός engine για όλες τις rename λειτουργίες.
    Ενσωματώνει preview, validation, duplicate detection, και execution.
    """

            # Central signal system
    preview_updated = pyqtSignal()
    validation_updated = pyqtSignal()
    execution_completed = pyqtSignal()
    state_changed = pyqtSignal()

    def __init__(self):
        super().__init__()

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
        """Generate preview με unified system."""
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

        self.preview_updated.emit()
        self.state_changed.emit()
        return result

    @monitor_performance("validate_preview")
    def validate_preview(self, preview_pairs: list[tuple[str, str]]) -> ValidationResult:
        """Validate preview με unified system."""
        result = self.validation_manager.validate_preview(preview_pairs)

        # Update state
        current_state = self.state_manager.get_state()
        current_state.validation_result = result
        self.state_manager.update_state(current_state)

        self.validation_updated.emit()
        self.state_changed.emit()
        return result

    @monitor_performance("execute_rename")
    def execute_rename(
        self,
        files: list[FileItem],
        new_names: list[str],
        conflict_callback: Callable | None = None,
        validator: object | None = None,
    ) -> ExecutionResult:
        """Execute rename με unified system."""
        result = self.execution_manager.execute_rename(
            files, new_names, conflict_callback, validator
        )

        # Update state
        current_state = self.state_manager.get_state()
        current_state.execution_result = result
        self.state_manager.update_state(current_state)

        self.execution_completed.emit()
        self.state_changed.emit()
        return result

    def get_current_state(self) -> RenameState:
        """Get current state."""
        return self.state_manager.get_state()

    def clear_cache(self) -> None:
        """Clear all caches."""
        self.cache_manager.clear_cache()
        logger.debug("[UnifiedRenameEngine] Cache cleared")

    def get_hash_availability(self, files: list[FileItem]) -> dict[str, bool]:
        """Get hash availability για files."""
        return self.batch_query_manager.get_hash_availability(files)

    def get_metadata_availability(self, files: list[FileItem]) -> dict[str, bool]:
        """Get metadata availability για files."""
        return self.batch_query_manager.get_metadata_availability(files)

    def get_performance_stats(self) -> dict[str, Any]:
        """Get performance statistics."""
        return self.performance_monitor.get_stats()

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

    def batch_process_files(self, files: list[FileItem], processor_func: Callable) -> list[Any]:
        """Process files in batches using the provided function."""
        return [processor_func(file) for file in files]

    def resolve_conflicts_batch(
        self, operations: list[tuple[str, str]], strategy: str = "timestamp"
    ) -> list[Any]:
        """Resolve conflicts in batch."""
        return self.conflict_resolver.batch_resolve_conflicts(operations, strategy)
