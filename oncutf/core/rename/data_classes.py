"""oncutf.core.rename.data_classes.

Data classes for the unified rename engine.

This module contains lightweight data classes that hold preview, validation
and execution results used throughout the rename workflow.

Author: Michael Economou
Date: 2026-01-01
"""

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from oncutf.models.file_item import FileItem


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
    errors: list[str] | None = None
    timestamp: float = 0.0  # Unix timestamp

    def __post_init__(self) -> None:
        """Initialize default values for errors and timestamp."""
        if self.errors is None:
            self.errors = []
        if self.timestamp == 0.0:
            self.timestamp = time.time()

    def is_stale(self, max_age_seconds: float = 300.0) -> bool:
        """Check if preview result is stale.

        Args:
            max_age_seconds: Maximum age before considering stale (default: 5 minutes)

        Returns:
            bool: True if preview is older than max_age_seconds

        """
        age = time.time() - self.timestamp
        return age > max_age_seconds

    def get_age_seconds(self) -> float:
        """Get age of preview result in seconds.

        Returns:
            float: Age in seconds

        """
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
        valid_count: Number of valid, changed items (computed).
        invalid_count: Number of invalid items (computed).
        duplicate_count: Number of duplicate items (computed).

    """

    items: list[ValidationItem]
    duplicates: set[str]
    has_errors: bool = False
    has_unchanged: bool = False
    unchanged_count: int = 0
    valid_count: int = 0
    invalid_count: int = 0
    duplicate_count: int = 0

    def __post_init__(self) -> None:
        """Compute derived validation flags from items."""
        self.has_errors = any(not item.is_valid for item in self.items)
        self.unchanged_count = sum(1 for item in self.items if item.is_unchanged)
        self.has_unchanged = self.unchanged_count == len(self.items) if self.items else False
        self.valid_count = sum(1 for item in self.items if item.is_valid and not item.is_unchanged)
        self.invalid_count = sum(1 for item in self.items if not item.is_valid)
        self.duplicate_count = sum(1 for item in self.items if item.is_duplicate)


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

    Properties:
        renamed_count: Alias for success_count.
        failed_count: Alias for error_count.

    """

    items: list[ExecutionItem]
    success_count: int = 0
    error_count: int = 0
    skipped_count: int = 0
    conflicts_count: int = 0

    def __post_init__(self) -> None:
        """Compute success, error, skipped, and conflicts counts from items."""
        self.success_count = sum(1 for item in self.items if item.success)
        self.error_count = sum(1 for item in self.items if not item.success and item.error_message)
        self.skipped_count = sum(1 for item in self.items if not item.success and item.skip_reason)
        self.conflicts_count = sum(1 for item in self.items if item.is_conflict)

    @property
    def renamed_count(self) -> int:
        """Alias for success_count (semantic convenience)."""
        return self.success_count

    @property
    def failed_count(self) -> int:
        """Alias for error_count (semantic convenience)."""
        return self.error_count


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

    files: list["FileItem"] | None = None
    modules_data: list[dict[str, Any]] | None = None
    post_transform: dict[str, Any] | None = None
    metadata_cache: Any = None
    preview_result: PreviewResult | None = None
    validation_result: ValidationResult | None = None
    execution_result: ExecutionResult | None = None

    # State flags
    preview_changed: bool = False
    validation_changed: bool = False
    execution_changed: bool = False

    def __post_init__(self) -> None:
        """Initialize empty collections for None fields."""
        if self.files is None:
            self.files = []
        if self.modules_data is None:
            self.modules_data = []
        if self.post_transform is None:
            self.post_transform = {}
