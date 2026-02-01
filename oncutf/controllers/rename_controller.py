"""Module: rename_controller.py.

Author: Michael Economou
Date: 2025-12-16

RenameController: Orchestrates rename operations.

This controller handles the rename workflow, coordinating between
UnifiedRenameEngine, FileStore, PreviewManager, and related services. It handles:
- Preview generation with validation
- Rename execution with conflict resolution
- Post-rename workflow (reload, restore state)
- Progress tracking for long operations

The controller is UI-agnostic and focuses on business logic orchestration.
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from oncutf.app.state.context import AppContext as ApplicationContext
    from oncutf.app.state.file_store import FileStore
    from oncutf.controllers.protocols import (
        RenameManagerProtocol,
        ValidationDialogProtocol,
    )
    from oncutf.core.rename.unified_rename_engine import UnifiedRenameEngine
    from oncutf.models.file_item import FileItem

logger = logging.getLogger(__name__)


class RenameController:
    """Controller for rename operations.

    Orchestrates rename workflows by coordinating UnifiedRenameEngine,
    PreviewManager, RenameManager, and related services. Provides a clean
    API for UI components to trigger rename operations without knowing
    implementation details.

    This controller adds orchestration logic on top of existing managers:
    - Workflow coordination (preview → validate → execute)
    - Error handling and result aggregation
    - State management across rename stages
    - Post-rename workflow orchestration

    Attributes:
        _unified_rename_engine: Engine for preview/validation/execution
        _rename_manager: Manager for rename execution and post-rename workflow
        _file_store: Store maintaining loaded file state
        _context: Application context for global state

    """

    def __init__(
        self,
        unified_rename_engine: Optional["UnifiedRenameEngine"] = None,
        rename_manager: Optional["RenameManagerProtocol"] = None,
        file_store: Optional["FileStore"] = None,
        context: Optional["ApplicationContext"] = None,
        validation_dialog: Optional["ValidationDialogProtocol"] = None,
    ) -> None:
        """Initialize RenameController.

        Args:
            unified_rename_engine: Engine for rename operations (injected)
            rename_manager: Manager for rename execution (injected)
            file_store: Store for maintaining file state (injected)
            context: Application context for global state (injected)
            validation_dialog: Handler for validation issue dialogs (injected)

        """
        logger.info("[RenameController] Initializing controller")
        self._unified_rename_engine = unified_rename_engine
        self._rename_manager = rename_manager
        self._file_store = file_store
        self._context = context
        self._validation_dialog = validation_dialog

        logger.debug(
            "[RenameController] Initialized with managers: "
            "unified_rename_engine=%s, rename_manager=%s, "
            "file_store=%s, context=%s, validation_dialog=%s",
            unified_rename_engine is not None,
            rename_manager is not None,
            file_store is not None,
            context is not None,
            validation_dialog is not None,
            extra={"dev_only": True},
        )

    # -------------------------------------------------------------------------
    # Preview Generation
    # -------------------------------------------------------------------------

    def generate_preview(
        self,
        file_items: list["FileItem"],
        modules_data: list[dict[str, Any]],
        post_transform: dict[str, Any],
        metadata_cache: Any,
    ) -> dict[str, Any]:
        """Generate rename preview for given files.

        This method orchestrates preview generation by:
        1. Validating input files and configuration
        2. Delegating to UnifiedRenameEngine for preview
        3. Updating PreviewManager with results
        4. Returning structured result

        Args:
            file_items: List of FileItem objects to preview
            modules_data: Module configuration for rename
            post_transform: Final transform settings
            metadata_cache: Metadata cache for module execution

        Returns:
            dict: {
                'success': bool,
                'name_pairs': List[Tuple[str, str]],  # (old, new) pairs
                'has_changes': bool,
                'errors': List[str]
            }

        """
        logger.info(
            "[RenameController] Generating preview for %d files",
            len(file_items),
        )

        # Validate inputs
        if not file_items:
            logger.warning("[RenameController] No files provided for preview")
            return {
                "success": False,
                "name_pairs": [],
                "has_changes": False,
                "errors": ["No files provided"],
            }

        if not self._unified_rename_engine:
            logger.error("[RenameController] UnifiedRenameEngine not available")
            return {
                "success": False,
                "name_pairs": [],
                "has_changes": False,
                "errors": ["Rename engine not initialized"],
            }

        try:
            # Generate preview using unified engine
            preview_result = self._unified_rename_engine.generate_preview(
                files=file_items,
                modules_data=modules_data,
                post_transform=post_transform,
                metadata_cache=metadata_cache,
            )

            # Extract results
            name_pairs = preview_result.name_pairs
            has_changes = preview_result.has_changes

            logger.debug(
                "[RenameController] Preview generated: %d pairs, has_changes=%s",
                len(name_pairs),
                has_changes,
                extra={"dev_only": True},
            )
        except Exception as e:
            logger.exception("[RenameController] Error generating preview")
            return {
                "success": False,
                "name_pairs": [],
                "has_changes": False,
                "errors": [f"Preview generation failed: {e!s}"],
            }
        else:
            return {
                "success": True,
                "name_pairs": name_pairs,
                "has_changes": has_changes,
                "errors": [],
            }

    def validate_preview(self, preview_pairs: list[tuple[str, str]]) -> dict[str, Any]:
        """Validate preview name pairs.

        This method orchestrates preview validation by:
        1. Checking for filename validity
        2. Detecting duplicates
        3. Detecting unchanged names
        4. Returning validation results

        Args:
            preview_pairs: List of (old_name, new_name) tuples

        Returns:
            dict: {
                'success': bool,
                'has_errors': bool,
                'valid_count': int,
                'invalid_count': int,
                'duplicate_count': int,
                'unchanged_count': int,
                'validation_items': List[ValidationItem],
                'errors': List[str]
            }

        """
        logger.info(
            "[RenameController] Validating %d preview pairs",
            len(preview_pairs),
        )

        if not self._unified_rename_engine:
            logger.error("[RenameController] UnifiedRenameEngine not available")
            return {
                "success": False,
                "has_errors": True,
                "valid_count": 0,
                "invalid_count": 0,
                "duplicate_count": 0,
                "unchanged_count": 0,
                "validation_items": [],
                "errors": ["Rename engine not initialized"],
            }

        try:
            # Validate using unified engine
            validation_result = self._unified_rename_engine.validate_preview(preview_pairs)

            logger.debug(
                "[RenameController] Validation complete: has_errors=%s, "
                "valid=%d, invalid=%d, duplicates=%d, unchanged=%d",
                validation_result.has_errors,
                validation_result.valid_count,
                validation_result.invalid_count,
                validation_result.duplicate_count,
                validation_result.unchanged_count,
                extra={"dev_only": True},
            )
        except Exception as e:
            logger.exception("[RenameController] Error validating preview")
            return {
                "success": False,
                "has_errors": True,
                "valid_count": 0,
                "invalid_count": 0,
                "duplicate_count": 0,
                "unchanged_count": 0,
                "validation_items": [],
                "errors": [f"Validation failed: {e!s}"],
            }
        else:
            return {
                "success": True,
                "has_errors": validation_result.has_errors,
                "valid_count": validation_result.valid_count,
                "invalid_count": validation_result.invalid_count,
                "duplicate_count": validation_result.duplicate_count,
                "unchanged_count": validation_result.unchanged_count,
                "validation_items": validation_result.items,
                "errors": [],
            }

    # -------------------------------------------------------------------------
    # Rename Execution
    # -------------------------------------------------------------------------

    def execute_rename(
        self,
        file_items: list["FileItem"],
        modules_data: list[dict[str, Any]],
        post_transform: dict[str, Any],
        metadata_cache: Any,
        current_folder: str | None = None,
    ) -> dict[str, Any]:
        """Execute rename operation with full workflow.

        This method orchestrates the complete rename workflow:
        1. Generate preview
        2. Validate preview
        3. Check for errors/conflicts
        4. Execute rename via UnifiedRenameEngine
        5. Trigger post-rename workflow (reload, restore state)

        Args:
            file_items: List of FileItem objects to rename
            modules_data: Module configuration for rename
            post_transform: Final transform settings
            metadata_cache: Metadata cache for module execution
            current_folder: Current folder path for post-rename reload

        Returns:
            dict: {
                'success': bool,
                'renamed_count': int,
                'failed_count': int,
                'skipped_count': int,
                'errors': List[str]
            }

        """
        logger.info(
            "[RenameController] Executing rename for %d files",
            len(file_items),
        )

        # Validate inputs
        if not file_items:
            logger.warning("[RenameController] No files provided for rename")
            return {
                "success": False,
                "renamed_count": 0,
                "failed_count": 0,
                "skipped_count": 0,
                "errors": ["No files provided"],
            }

        if not self._unified_rename_engine:
            logger.error("[RenameController] UnifiedRenameEngine not available")
            return {
                "success": False,
                "renamed_count": 0,
                "failed_count": 0,
                "skipped_count": 0,
                "errors": ["Rename engine not initialized"],
            }

        try:
            # Step 1: Generate preview
            preview_result = self._unified_rename_engine.generate_preview(
                files=file_items,
                modules_data=modules_data,
                post_transform=post_transform,
                metadata_cache=metadata_cache,
            )

            if not preview_result.has_changes:
                logger.info("[RenameController] No changes detected in preview")
                return {
                    "success": False,
                    "renamed_count": 0,
                    "failed_count": 0,
                    "skipped_count": len(file_items),
                    "errors": ["No changes detected"],
                }

            # Step 2: Validate preview
            validation_result = self._unified_rename_engine.validate_preview(
                preview_result.name_pairs
            )

            if validation_result.has_errors:
                logger.warning(
                    "[RenameController] Validation errors detected: invalid=%d, duplicates=%d",
                    validation_result.invalid_count,
                    validation_result.duplicate_count,
                )
                return {
                    "success": False,
                    "renamed_count": 0,
                    "failed_count": 0,
                    "skipped_count": len(file_items),
                    "errors": [
                        f"{validation_result.invalid_count} invalid filenames, "
                        f"{validation_result.duplicate_count} duplicates"
                    ],
                }

            # Step 3: Pre-execution validation
            logger.info("[RenameController] Validating files before execution...")
            from oncutf.core.pre_execution_validator import PreExecutionValidator

            validator = PreExecutionValidator(check_hash=False)
            validation_result = validator.validate(file_items)

            if not validation_result.is_valid:
                logger.warning(
                    "[RenameController] Pre-execution validation found %d issue(s)",
                    len(validation_result.issues),
                )

                # Show validation dialog (if UI available)
                user_decision = self._handle_validation_issues(validation_result)

                if user_decision == "cancel":
                    logger.info("[RenameController] User cancelled due to validation issues")
                    return {
                        "success": False,
                        "renamed_count": 0,
                        "failed_count": 0,
                        "skipped_count": len(file_items),
                        "errors": [validation_result.get_summary()],
                    }
                if user_decision == "refresh":
                    logger.info("[RenameController] User requested preview refresh")
                    return {
                        "success": False,
                        "renamed_count": 0,
                        "failed_count": 0,
                        "skipped_count": len(file_items),
                        "errors": ["Preview refresh requested"],
                        "refresh_requested": True,
                    }
                if user_decision == "skip":
                    logger.info(
                        "[RenameController] User chose to skip %d problematic files",
                        len(validation_result.issues),
                    )
                    # Continue with only valid files
                    file_items = validation_result.valid_files
                    # Rebuild preview for valid files only
                    preview_result = self._unified_rename_engine.generate_preview(
                        file_items, current_folder
                    )

            # Step 4: Execute rename
            logger.info("[RenameController] Executing rename operation...")

            # Extract new names from name_pairs
            new_names = [new_name for _, new_name in preview_result.name_pairs]

            execution_result = self._unified_rename_engine.execute_rename(
                files=file_items,
                new_names=new_names,
            )

            logger.info(
                "[RenameController] Rename complete: renamed=%d, failed=%d, skipped=%d",
                execution_result.renamed_count,
                execution_result.failed_count,
                execution_result.skipped_count,
            )

            # Step 4: Post-rename workflow (if rename manager available)
            if self._rename_manager and execution_result.renamed_count > 0:
                logger.debug(
                    "[RenameController] Triggering post-rename workflow",
                    extra={"dev_only": True},
                )
                # Extract checked paths before rename for restoration
                checked_paths = {
                    str(Path(item.full_path))
                    for item in file_items
                    if getattr(item, "is_checked", False)
                }

                # Delegate to RenameManager for post-rename workflow
                # Note: This is a hook for future integration
                # Currently, MainWindow handles this workflow
                logger.debug(
                    "[RenameController] Post-rename workflow would restore %d checked items",
                    len(checked_paths),
                    extra={"dev_only": True},
                )

            return {
                "success": execution_result.renamed_count > 0,
                "renamed_count": execution_result.renamed_count,
                "failed_count": execution_result.failed_count,
                "skipped_count": execution_result.skipped_count,
                "errors": [
                    result.error
                    for result in execution_result.results
                    if not result.success and result.error
                ],
            }

        except Exception as e:
            logger.exception("[RenameController] Error executing rename")
            return {
                "success": False,
                "renamed_count": 0,
                "failed_count": len(file_items),
                "skipped_count": 0,
                "errors": [f"Rename execution failed: {e!s}"],
            }

    # -------------------------------------------------------------------------
    # State Queries
    # -------------------------------------------------------------------------

    def has_pending_changes(self) -> bool:
        """Check if there are pending rename changes.

        Returns:
            bool: True if preview has changes that can be executed

        """
        if not self._unified_rename_engine:
            return False

        try:
            state = self._unified_rename_engine.state_manager.get_state()
        except Exception as e:
            logger.warning("[RenameController] Error checking pending changes: %s", str(e))
            return False
        else:
            return (
                state.preview_result is not None
                and state.preview_result.has_changes
                and not (state.validation_result and state.validation_result.has_errors)
            )
            return False

    def get_current_state(self) -> Any | None:
        """Get current rename state.

        Returns:
            Optional[RenameState]: Current state or None if not available

        """
        if not self._unified_rename_engine:
            return None

        try:
            return self._unified_rename_engine.state_manager.get_state()
        except Exception as e:
            logger.warning("[RenameController] Error getting current state: %s", str(e))
            return None

    def clear_state(self) -> None:
        """Clear rename state and cache."""
        if not self._unified_rename_engine:
            return

        try:
            self._unified_rename_engine.clear_cache()
            logger.debug(
                "[RenameController] State and cache cleared",
                extra={"dev_only": True},
            )
        except Exception as e:
            logger.warning("[RenameController] Error clearing state: %s", str(e))

    def _handle_validation_issues(self, validation_result: Any) -> str:
        """Handle validation issues by delegating to validation dialog handler.

        Args:
            validation_result: ValidationResult with issues

        Returns:
            str: User decision ("skip", "cancel", or "refresh")

        """
        # Use injected validation dialog handler if available
        if self._validation_dialog is not None:
            try:
                return self._validation_dialog.show_validation_issues(validation_result)
            except Exception as e:
                logger.error("[RenameController] Error with validation dialog: %s", str(e))
                return "cancel"

        # Fallback: cancel if no handler available
        logger.warning("[RenameController] No validation dialog handler available")
        return "cancel"
