"""oncutf.core.rename.execution_manager.

Execution management for the unified rename engine.

This module provides the UnifiedExecutionManager class that executes
rename operations with conflict resolution support.

Author: Michael Economou
Date: 2026-01-01
"""

import os
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from oncutf.models.file_item import FileItem

from oncutf.config import AUTO_RENAME_COMPANION_FILES, COMPANION_FILES_ENABLED
from oncutf.core.rename.data_classes import ExecutionItem, ExecutionResult
from oncutf.utils.filesystem.companion_files_helper import CompanionFilesHelper
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class UnifiedExecutionManager:
    """Execute rename operations with conflict resolution support.

    This manager builds an execution plan, invokes an optional validator,
    resolves filesystem conflicts via a callback and applies renames using a
    safe-case rename helper when necessary.
    """

    def __init__(self):
        """Initialize the execution manager with no conflict callback or validator."""
        self.conflict_callback: Callable[[Any, str], str] | None = None
        self.validator: Callable[[str], tuple[bool, str]] | None = None

    def execute_rename(
        self,
        files: list["FileItem"],
        new_names: list[str],
        conflict_callback: Callable[[Any, str], str] | None = None,
        validator: Any | None = None,
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
        self, files: list["FileItem"], new_names: list[str]
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
        self, files: list["FileItem"], new_names: list[str]
    ) -> list[ExecutionItem]:
        """Build execution plan for companion files that should be renamed alongside main files."""
        companion_items: list[ExecutionItem] = []

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
                            old_path=old_companion_path, new_path=new_companion_path, success=False
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
            from oncutf.utils.naming.rename_logic import is_case_only_change, safe_case_rename

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
