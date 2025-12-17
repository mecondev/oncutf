"""oncutf.core.unified_rename_engine

Central rename engine and helpers for previewing, validating and executing
batch rename operations.

This module provides lightweight data classes that hold preview, validation
and execution results, managers for batching queries and caching, and the
`UnifiedRenameEngine` Qt-aware facade used by the UI layer. The implementation
keeps rename logic separate from filesystem operations where possible and
provides hooks for conflict resolution and validation.
"""

import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from oncutf.config import AUTO_RENAME_COMPANION_FILES, COMPANION_FILES_ENABLED
from oncutf.core.advanced_cache_manager import AdvancedCacheManager
from oncutf.core.batch_processor import BatchProcessorFactory
from oncutf.core.conflict_resolver import ConflictResolver
from oncutf.core.performance_monitor import get_performance_monitor, monitor_performance
from oncutf.core.pyqt_imports import QObject, pyqtSignal
from oncutf.models.file_item import FileItem
from oncutf.utils.companion_files_helper import CompanionFilesHelper
from oncutf.utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


@dataclass
class PreviewResult:
    """Container for preview generation output.

    Attributes:
        name_pairs: List of tuples of (original_filename, proposed_filename).
        has_changes: True if at least one proposed filename differs from the
            original.
        errors: Optional list of error messages captured during preview
            generation.
        timestamp: Time when preview was generated (for staleness checking).
    """

    name_pairs: list[tuple[str, str]]
    has_changes: bool
    errors: list[str] = None # type: ignore
    timestamp: float = 0.0  # Unix timestamp

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.timestamp == 0.0:
            import time
            self.timestamp = time.time()

    def is_stale(self, max_age_seconds: float = 300.0) -> bool:
        """Check if preview result is stale.

        Args:
            max_age_seconds: Maximum age before considering stale (default: 5 minutes)

        Returns:
            bool: True if preview is older than max_age_seconds
        """
        import time
        age = time.time() - self.timestamp
        return age > max_age_seconds

    def get_age_seconds(self) -> float:
        """Get age of preview result in seconds.

        Returns:
            float: Age in seconds
        """
        import time
        return time.time() - self.timestamp


@dataclass
class ValidationItem:
    """Validation information for a single file preview entry.

    Attributes:
        old_name: Original filename as shown in the UI.
        new_name: Proposed filename produced by the preview engine.
        is_valid: True when the proposed name passes filename validation.
        is_duplicate: True when the proposed name is a duplicate within the
            current preview set.
        is_unchanged: True when `old_name == new_name`.
        error_message: Optional human-readable validation error.
    """

    old_name: str
    new_name: str
    is_valid: bool
    is_duplicate: bool
    is_unchanged: bool
    error_message: str = ""


@dataclass
class ValidationResult:
    """Aggregate result of validating a preview.

    Attributes:
        items: List of :class:`ValidationItem` for each previewed file.
        duplicates: Set of filenames that were detected as duplicates.
        has_errors: True if any item failed validation.
        has_unchanged: True if all items are unchanged (no actual renames).
        unchanged_count: Number of unchanged files.
    """

    items: list[ValidationItem]
    duplicates: set[str]
    has_errors: bool = False
    has_unchanged: bool = False
    unchanged_count: int = 0

    def __post_init__(self):
        self.has_errors = any(not item.is_valid for item in self.items)
        self.unchanged_count = sum(1 for item in self.items if item.is_unchanged)
        self.has_unchanged = self.unchanged_count == len(self.items) if self.items else False


@dataclass
class ExecutionItem:
    """Result/plan entry for executing a single file rename.

    Attributes:
        old_path: Absolute path of the original file.
        new_path: Absolute path of the target filename.
        success: True when the rename was applied successfully.
        error_message: Optional error text if execution failed.
        skip_reason: Optional reason why the operation was skipped.
        is_conflict: True when a filesystem conflict was detected for the
            target path (existing file).
        conflict_resolved: True when a conflict was resolved (e.g. overwrite).
    """

    old_path: str
    new_path: str
    success: bool = False
    error_message: str = ""
    skip_reason: str = ""
    is_conflict: bool = False
    conflict_resolved: bool = False


@dataclass
class ExecutionResult:
    """Aggregate execution summary after attempting a batch rename.

    Attributes:
        items: List of :class:`ExecutionItem` for each attempted rename.
        success_count: Number of successful renames (computed).
        error_count: Number of items with an error message (computed).
        skipped_count: Number of items skipped (computed).
        conflicts_count: Number of items that hit a filesystem conflict
            (computed).
    """

    items: list[ExecutionItem]
    success_count: int = 0
    error_count: int = 0
    skipped_count: int = 0
    conflicts_count: int = 0

    def __post_init__(self):
        self.success_count = sum(1 for item in self.items if item.success) # type: ignore
        self.error_count = sum(1 for item in self.items if not item.success and item.error_message) # type: ignore
        self.skipped_count = sum(1 for item in self.items if not item.success and item.skip_reason) # type: ignore
        self.conflicts_count = sum(1 for item in self.items if item.is_conflict) # type: ignore


@dataclass
class RenameState:
    """Central container for the current rename workflow state.

    This object is used to keep the preview, validation and execution results
    together with the current file list and module configuration. UI code
    listens to state changes to update views.

    Attributes:
        files: List of :class:`models.file_item.FileItem` currently in the
            preview table.
        modules_data: Module configuration used to produce the preview.
        post_transform: Final transform settings applied after modules.
        metadata_cache: Reference to the metadata cache used during preview.
        preview_result: Latest :class:`PreviewResult` produced.
        validation_result: Latest :class:`ValidationResult` produced.
        execution_result: Latest :class:`ExecutionResult` produced.
        preview_changed / validation_changed / execution_changed: Flags set by
            :class:`RenameStateManager` when corresponding parts of the state
            change.
    """

    files: list[FileItem] = None # type: ignore
    modules_data: list[dict[str, Any]] = None # type: ignore
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
    """Batch helper to fetch availability information for sets of files.

    This manager centralizes queries that benefit from batch access patterns,
    such as checking whether CRC32 hashes or metadata exist for a list of
    files. The implementation uses the persistent caches defined elsewhere in
    the application to avoid expensive per-file operations.
    """

    def __init__(self):
        self._hash_cache = None
        self._metadata_cache = None

    def get_hash_availability(self, files: list[FileItem]) -> dict[str, bool]:
        """Return a mapping of file path -> whether a CRC32 hash exists.

        The function queries the persistent hash cache in batch and returns a
        dictionary mapping each file's absolute path to a boolean.
        """
        if not files:
            return {}

        try:
            from oncutf.core.persistent_hash_cache import get_persistent_hash_cache

            hash_cache = get_persistent_hash_cache()

            file_paths = [f.full_path for f in files if f.full_path]
            files_with_hash = hash_cache.get_files_with_hash_batch(file_paths, "CRC32")

            # Convert to boolean dict
            result = {}
            for file in files:
                if file.full_path:
                    result[file.full_path] = file.full_path in files_with_hash

            return result

        except Exception:
            logger.exception("[BatchQueryManager] Error getting hash availability")
            return {}

    def get_metadata_availability(self, files: list[FileItem]) -> dict[str, bool]:
        """Return a mapping of file path -> whether structured metadata is
        available for the file.

        The implementation reads the global application metadata cache via the
        application context and performs a lightweight presence check.
        """
        if not files:
            return {}

        try:
            # Get metadata cache
            from oncutf.core.application_context import get_app_context

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
                    logger.debug(
                        "[DEBUG] [UnifiedRenameEngine] get_metadata_availability: %s has_metadata=%s",
                        file.full_path,
                        has_metadata,
                        extra={"dev_only": True},
                    )
                    result[file.full_path] = has_metadata

            logger.debug(
                "[DEBUG] [UnifiedRenameEngine] get_metadata_availability result: %s",
                result,
                extra={"dev_only": True},
            )
            return result

        except Exception:
            logger.exception("[BatchQueryManager] Error getting metadata availability")
            return {}

    def _file_has_metadata(self, file_path: str, metadata_cache) -> bool:
        """Return True if the given file path has non-internal metadata.

        The method expects the metadata cache to expose an internal
        `_memory_cache` mapping where entries contain a `.data` attribute.
        Only non-internal keys (not starting with '_' and not path/filename)
        are considered metadata fields.
        """
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
        except Exception:
            logger.debug(
                "[BatchQueryManager] Error checking metadata for %s",
                file_path,
                exc_info=True,
            )
            return False


class SmartCacheManager:
    """Lightweight in-memory caches for preview, validation and execution.

    The caches use a small time-to-live (TTL) to avoid recomputing results
    during rapid UI interactions while keeping memory usage minimal.
    """

    def __init__(self):
        self._preview_cache: dict[str, tuple[PreviewResult, float]] = {}
        self._validation_cache: dict[str, tuple[ValidationResult, float]] = {}
        self._execution_cache: dict[str, tuple[ExecutionResult, float]] = {}
        self._cache_ttl = 0.1  # 100ms TTL

    def get_cached_preview(self, key: str) -> PreviewResult | None:
        """Return a cached :class:`PreviewResult` for `key` or ``None``.

        Entries older than the TTL are automatically invalidated.
        """
        if key in self._preview_cache:
            result, timestamp = self._preview_cache[key]
            if time.time() - timestamp < self._cache_ttl:
                return result
            else:
                del self._preview_cache[key]
        return None

    def cache_preview(self, key: str, result: PreviewResult) -> None:
        """Store a preview result in the cache under `key`.
        """
        self._preview_cache[key] = (result, time.time())

    def get_cached_validation(self, key: str) -> ValidationResult | None:
        """Return a cached :class:`ValidationResult` for `key` or ``None``.

        Entries older than the TTL are automatically invalidated.
        """
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

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return {
            "preview_cache_size": len(self._preview_cache),
            "validation_cache_size": len(self._validation_cache),
            "execution_cache_size": len(self._execution_cache),
            "cache_ttl": self._cache_ttl,
            "total_cached_items": len(self._preview_cache) + len(self._validation_cache) + len(self._execution_cache),
        }


class UnifiedPreviewManager:
    """Orchestrates preview generation using batch queries and caching.

    Responsibilities:
        - Compose rename output by applying modules to each file.
        - Use `BatchQueryManager` to supply availability hints (hash/metadata).
        - Cache results to reduce repeated computation during UI edits.
    """

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
        """Generate filename preview for `files`.

        Args:
            files: List of FileItem objects to preview.
            modules_data: Module configuration used to build names.
            post_transform: Final transform settings applied after module
                composition.
            metadata_cache: Reference to the metadata cache used by modules.

        Returns:
            A :class:`PreviewResult` containing proposed names and a flag
            indicating whether any change is present.
        """

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
                "[UnifiedPreviewManager] Preview generation took %.3fs for %d files",
                elapsed,
                len(files),
            )

        return result

    def _generate_cache_key(
        self, files: list[FileItem], modules_data: list[dict], post_transform: dict
    ) -> str:
        """Create a stable cache key for the preview parameters.

        The key incorporates file paths, module configuration and post-
        transform data. When JSON encoding fails for complex objects a
        fallback to `str()` is used.
        """
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
        """Produce (old_name, new_name) tuples for each file.

        The method applies configured modules and post-transforms, uses
        availability hints to short-circuit modules that require metadata or
        hashes, and validates generated basenames before returning them.
        """

        from oncutf.modules.name_transform_module import NameTransformModule

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
                    all_files=files,  # Pass full file list for scope-aware counters
                )

                # Strip extension from generated fullname
                new_basename = self._strip_extension_from_fullname(new_fullname, extension)

                # Apply post-transform if configured
                new_basename = self._apply_post_transform_if_needed(
                    new_basename, post_transform, has_name_transform
                )

                # Validate basename
                if not self._is_valid_filename_text(new_basename):
                    name_pairs.append((file.filename, file.filename))
                    continue

                # Build final filename
                new_name = self._build_final_filename(new_basename, extension)
                name_pairs.append((file.filename, new_name))

            except Exception:
                logger.warning(
                    "Failed to generate preview for %s",
                    file.filename,
                    exc_info=True,
                )
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
        all_files: list[FileItem] | None = None,
    ) -> str:
        """Apply rename modules for a single file, checking required data.

        Modules that depend on hash or metadata availability will be
        short-circuited and a sentinel string (e.g. "missing_hash") will be
        returned when preconditions are not met.

        Args:
            file: File being renamed
            modules_data: List of module configurations
            index: Global index in file list
            metadata_cache: Metadata cache
            hash_availability: Dict of hash availability per file
            metadata_availability: Dict of metadata availability per file
            all_files: Full file list (for scope-aware counters)
        """

        from oncutf.utils.preview_engine import apply_rename_modules

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

        # Apply modules normally with full file list for scope-aware counters
        return apply_rename_modules(modules_data, index, file, metadata_cache, all_files=all_files)

    def _strip_extension_from_fullname(self, fullname: str, extension: str) -> str:
        """Strip extension from fullname if present.

        Args:
            fullname: The full generated name (may include extension).
            extension: The original file extension (with dot).

        Returns:
            Basename without extension.
        """
        if extension and fullname.lower().endswith(extension.lower()):
            return fullname[: -(len(extension))]
        return fullname

    def _apply_post_transform_if_needed(
        self, basename: str, post_transform: dict[str, Any], has_transform: bool
    ) -> str:
        """Apply post-transform to basename if transform is active.

        Args:
            basename: The base name to transform.
            post_transform: Transform configuration dictionary.
            has_transform: Flag indicating if transform should be applied.

        Returns:
            Transformed basename or original if no transform.
        """
        if not has_transform:
            return basename

        from oncutf.modules.name_transform_module import NameTransformModule

        return NameTransformModule.apply_from_data(post_transform, basename)

    def _build_final_filename(self, basename: str, extension: str) -> str:
        """Build final filename from basename and extension.

        Args:
            basename: The validated base name.
            extension: The file extension (with dot, may be empty).

        Returns:
            Complete filename.
        """
        return f"{basename}{extension}" if extension else basename

    def _is_valid_filename_text(self, basename: str) -> bool:
        """Return True if `basename` is acceptable for use as a filename.

        Falls back to permissive behaviour if the validator import fails.
        """
        try:
            from oncutf.utils.validate_filename_text import is_valid_filename_text

            return is_valid_filename_text(basename)
        except ImportError:
            return True


class UnifiedValidationManager:
    """Validate preview results and detect duplicates.

    The class produces a :class:`ValidationResult` that contains per-file
    validation results and a set of duplicated target filenames.
    """

    def __init__(self, cache_manager: SmartCacheManager):
        self.cache_manager = cache_manager

    def validate_preview(self, preview_pairs: list[tuple[str, str]]) -> ValidationResult:
        """Validate a sequence of (old_name, new_name) pairs.

        Performs filename validation, duplicate detection and returns a
        :class:`ValidationResult` containing the findings.
        """

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
        """Validate `filename` and return (is_valid, error_message).

        The implementation delegates to :mod:`utils.filename_validator`.
        """
        try:
            from oncutf.utils.filename_validator import validate_filename_part

            basename = os.path.splitext(filename)[0]
            is_valid, error = validate_filename_part(basename)
            return is_valid, error or ""
        except Exception as e:
            return False, f"Validation error: {e}"


class UnifiedExecutionManager:
    """Execute rename operations with conflict resolution support.

    This manager builds an execution plan, invokes an optional validator,
    resolves filesystem conflicts via a callback and applies renames using a
    safe-case rename helper when necessary.
    """

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
        """Attempt to rename `files` to `new_names`.

        Args:
            files: Sequence of FileItem objects in original order.
            new_names: Corresponding list of target filenames (not paths).
            conflict_callback: Optional callable used to resolve conflicts.
            validator: Optional callable accepting a basename and returning
                (is_valid, error_message).

        Returns:
            An :class:`ExecutionResult` summarizing the applied operations.
        """

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
            # Skip items already marked as successful (e.g., unchanged files)
            if item.success:
                results.append(item)
                continue

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
        """Construct ExecutionItem objects pairing source and target paths.

        The function zips the provided lists and produces an ExecutionItem for
        each pair. Files with no actual name change are included but marked
        as already successful to avoid unnecessary filesystem operations while
        maintaining proper accounting.
        """
        items = []
        unchanged_count = 0

        for file, new_name in zip(files, new_names, strict=False):
            old_path = file.full_path
            old_name = file.filename
            new_path = os.path.join(os.path.dirname(old_path), new_name)

            # Create execution item
            item = ExecutionItem(old_path=old_path, new_path=new_path, success=False)

            # Mark unchanged files as already successful (no-op)
            if old_name == new_name:
                item.success = True
                item.skip_reason = "unchanged"
                unchanged_count += 1

            items.append(item)

        if unchanged_count > 0:
            logger.info(
                "[UnifiedRenameEngine] %d files already have correct names (will process %d files with changes)",
                unchanged_count,
                len(items) - unchanged_count,
            )

        # Add companion file renames if enabled
        if COMPANION_FILES_ENABLED and AUTO_RENAME_COMPANION_FILES:
            logger.info(
                "[UnifiedRenameEngine] Companion files enabled: building companion execution plan for %d files",
                len(files),
            )
            companion_items = self._build_companion_execution_plan(files, new_names)
            items.extend(companion_items)
            logger.info(
                "[UnifiedRenameEngine] Added %d companion file renames to execution plan",
                len(companion_items),
            )
        else:
            logger.debug(
                "[UnifiedRenameEngine] Companion rename disabled (ENABLED=%s, AUTO_RENAME=%s)",
                COMPANION_FILES_ENABLED,
                AUTO_RENAME_COMPANION_FILES,
            )

        return items

    def _build_companion_execution_plan(
        self, files: list[FileItem], new_names: list[str]
    ) -> list[ExecutionItem]:
        """Build execution plan for companion files that should be renamed alongside main files."""
        companion_items = []

        if not files:
            return companion_items

        try:
            # Get all files in the folder for companion detection
            folder_path = os.path.dirname(files[0].full_path)
            folder_files = []
            try:
                folder_files = [
                    os.path.join(folder_path, f)
                    for f in os.listdir(folder_path)
                    if os.path.isfile(os.path.join(folder_path, f))
                ]
            except OSError:
                return companion_items

            # Process each main file for companion renames
            for file, new_name in zip(files, new_names, strict=False):
                companions = CompanionFilesHelper.find_companion_files(file.full_path, folder_files)

                if companions:
                    # Generate companion rename pairs
                    new_path = os.path.join(folder_path, new_name)
                    companion_renames = CompanionFilesHelper.get_companion_rename_pairs(
                        file.full_path, new_path, companions
                    )

                    # Create execution items for companions
                    for old_companion_path, new_companion_path in companion_renames:
                        companion_item = ExecutionItem(
                            old_path=old_companion_path,
                            new_path=new_companion_path,
                            success=False
                        )
                        companion_items.append(companion_item)
                        logger.debug(
                            "[UnifiedExecutionManager] Added companion rename: %s -> %s",
                            os.path.basename(old_companion_path),
                            os.path.basename(new_companion_path),
                        )

        except Exception:
            logger.warning(
                "[UnifiedExecutionManager] Error building companion execution plan",
                exc_info=True,
            )

        if companion_items:
            logger.info(
                "[UnifiedExecutionManager] Added %d companion file renames",
                len(companion_items),
            )

        return companion_items

    def _resolve_conflict(self, item: ExecutionItem) -> str:
        """Invoke the conflict callback to resolve a filesystem conflict.

        The callback is expected to return one of: 'skip', 'skip_all', 'overwrite'
        or raise / return another sentinel to cancel the whole operation.
        """
        if self.conflict_callback:
            try:
                return self.conflict_callback(None, os.path.basename(item.new_path))
            except Exception:
                logger.exception("[UnifiedExecutionManager] Error in conflict callback")
                return "skip"
        return "skip"  # Default to skip

    def _execute_single_rename(self, item: ExecutionItem) -> bool:
        """Perform a single filesystem rename, returning True on success.

        Uses a safe-case rename helper for case-only changes on case-
        insensitive filesystems, falling back to `os.rename` for regular
        moves.
        """
        try:
            from oncutf.utils.rename_logic import is_case_only_change, safe_case_rename

            old_name = os.path.basename(item.old_path)
            new_name = os.path.basename(item.new_path)

            # Skip if no change (same name, same path)
            if old_name == new_name and item.old_path == item.new_path:
                logger.debug(
                    "[UnifiedExecutionManager] Skipping unchanged file: %s",
                    old_name,
                )
                return True  # Not an error, just no-op

            # Use safe case rename for case-only changes
            if is_case_only_change(old_name, new_name):
                return safe_case_rename(item.old_path, item.new_path)
            else:
                # Regular rename
                os.rename(item.old_path, item.new_path)
                return True

        except Exception as e:
            item.error_message = str(e)
            logger.exception(
                "[UnifiedExecutionManager] Rename failed for %s",
                item.old_path,
            )
            return False


class RenameStateManager:
    """Manage a `RenameState` instance and detect changes between updates.

    The manager stores the prior state and sets boolean flags on the new
    state object when preview/validation/execution results change.
    """

    def __init__(self):
        self.current_state = RenameState()
        self._previous_state = None

    def update_state(self, new_state: RenameState) -> None:
        """Replace the current state with `new_state` and compute change flags.
        """
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
    """Facade connecting UI code to the unified rename workflow.

    This Qt-aware object exposes high-level methods used by the UI to:
        - generate previews (`generate_preview`)
        - validate previewed names (`validate_preview`)
        - execute renames with conflict handling (`execute_rename`)

    Signals are emitted after each major stage to allow the UI to update.
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

        self.preview_updated.emit()
        self.state_changed.emit()
        return result

    @monitor_performance("validate_preview")
    def validate_preview(self, preview_pairs: list[tuple[str, str]]) -> ValidationResult:
        """Validate preview with unified system."""
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
        """Execute rename with unified system."""
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
        """Get hash availability for files."""
        return self.batch_query_manager.get_hash_availability(files)

    def get_metadata_availability(self, files: list[FileItem]) -> dict[str, bool]:
        """Get metadata availability for files."""
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
        """Process files in batches using the provided function.

        The processor_func should accept a list of FileItem objects and return
        a result object for that batch.
        """
        batch_size = 50  # Process in batches of 50 files
        results = []

        for i in range(0, len(files), batch_size):
            batch = files[i:i + batch_size]
            batch_result = processor_func(batch)
            results.append(batch_result)

        return results

    def resolve_conflicts_batch(
        self, operations: list[tuple[str, str]], strategy: str = "timestamp"
    ) -> list[Any]:
        """Resolve conflicts in batch."""
        return self.conflict_resolver.batch_resolve_conflicts(operations, strategy)
