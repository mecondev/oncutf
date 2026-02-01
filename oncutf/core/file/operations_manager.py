"""Module: file_operations_manager.py.

Author: Michael Economou
Date: 2025-06-13

file_operations_manager.py
Manages file operations like rename, validation, and conflict resolution.

Uses ConflictResolutionPort for UI decoupling (Phase 5).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from oncutf.app.ports.conflict_resolution import ConflictResolutionPort
    from oncutf.core.rename.unified_rename_engine import UnifiedRenameEngine
    from oncutf.models.file_item import FileItem

from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices

from oncutf.app.services.user_interaction import (
    show_question_message,
    show_warning_message,
)
from oncutf.utils.filesystem.path_utils import find_file_by_path
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class FileOperationsManager:
    """Manages file operations like rename, validation, and conflict resolution."""

    def __init__(
        self,
        parent_window: Any = None,
        conflict_resolution: ConflictResolutionPort | None = None,
    ) -> None:
        """Initialize FileOperationsManager.

        Args:
            parent_window: Reference to main window
            conflict_resolution: Port for conflict resolution dialogs (injected)

        """
        self.parent_window = parent_window
        self._conflict_resolution = conflict_resolution
        logger.debug("[FileOperationsManager] Initialized", extra={"dev_only": True})

    @property
    def conflict_resolution(self) -> ConflictResolutionPort:
        """Lazy-load conflict resolution adapter from QtAppContext."""
        if self._conflict_resolution is None:
            from oncutf.app.state.context import get_app_context

            context = get_app_context()
            self._conflict_resolution = context.get_manager("conflict_resolution")
            if self._conflict_resolution is None:
                raise RuntimeError("ConflictResolutionPort not registered in QtAppContext")
        return self._conflict_resolution

    def rename_files(
        self,
        selected_files: list[FileItem],
        modules_data: list[dict[str, Any]],
        post_transform: dict[str, Any],
        metadata_cache: Any,
        current_folder_path: str,
    ) -> int:
        """Execute batch rename process."""
        if not current_folder_path:
            if self.parent_window and hasattr(self.parent_window, "status_manager"):
                self.parent_window.status_manager.set_validation_status(
                    "No folder selected", validation_type="warning", auto_reset=True
                )
            return 0

        if not selected_files:
            if self.parent_window and hasattr(self.parent_window, "status_manager"):
                self.parent_window.status_manager.set_selection_status(
                    "No files selected for renaming",
                    selected_count=0,
                    total_count=0,
                    auto_reset=True,
                )
            show_warning_message(
                self.parent_window,
                "Rename Warning",
                "No files are selected for renaming.",
            )
            return 0

        logger.info("[Rename] Starting rename process for %d files...", len(selected_files))

        # Start operation tracking
        operation_id = f"rename_{len(selected_files)}_files"
        if self.parent_window and hasattr(self.parent_window, "status_manager"):
            self.parent_window.status_manager.start_operation(
                operation_id, "rename", f"Renaming {len(selected_files)} files"
            )

        # Import validator here to avoid circular imports
        from oncutf.utils.naming.filename_validator import validate_filename_part

        # State for "Apply to All" functionality
        remembered_action: str | None = None

        # Conflict resolution callback with UI dialog
        def conflict_callback(_parent: Any, filename: str) -> str:
            """Resolve conflicts with user interaction via dialog.

            Args:
                _parent: Parent window (unused, we use self.parent_window)
                filename: Target filename that conflicts

            Returns:
                str: One of "skip", "overwrite", "rename", "skip_all", "cancel"

            """
            nonlocal remembered_action

            try:
                # If user previously chose "Apply to All", use that action
                if remembered_action is not None:
                    return remembered_action

                # Get original filename from FileItem
                original_filename = "unknown"
                for file_item in selected_files:
                    if Path(file_item.full_path).name != filename:
                        # This is the conflicting file (old name != new name)
                        original_filename = file_item.filename
                        break

                logger.info(
                    "[Rename] Showing conflict dialog: %s -> %s",
                    original_filename,
                    filename,
                )

                # Show conflict resolution dialog
                action, apply_to_all = self.conflict_resolution.show_conflict(
                    old_filename=original_filename,
                    new_filename=filename,
                    parent=self.parent_window,
                )

                # Remember action if "Apply to All" was checked
                if apply_to_all and action in ("skip", "overwrite", "rename"):
                    remembered_action = action
                    logger.info(
                        "[Rename] Remembering action '%s' for remaining conflicts",
                        action,
                    )

                # Handle "rename" action (add numeric suffix)
                if action == "rename":
                    # Let the renamer handle suffix generation
                    # For now, we'll use overwrite but renamer should add suffix
                    # This needs coordination with Renamer class
                    action = "overwrite"  # Temporary: treat as overwrite
                    logger.warning(
                        "[Rename] 'rename' action not fully implemented, using 'overwrite'"
                    )

                return action

            except Exception as e:
                logger.error("[Rename] Error in conflict callback: %s", e)
                return "skip"

        # Get UnifiedRenameEngine from parent window
        if not self.parent_window or not hasattr(self.parent_window, "unified_rename_engine"):
            logger.error("[Rename] UnifiedRenameEngine not available in parent window")
            if self.parent_window and hasattr(self.parent_window, "status_manager"):
                self.parent_window.status_manager.finish_operation(
                    operation_id,
                    success=False,
                    final_message="Rename engine not initialized",
                )
            return 0

        engine: UnifiedRenameEngine = self.parent_window.unified_rename_engine

        # Step 1: Generate preview using unified engine
        try:
            preview_result = engine.generate_preview(
                files=selected_files,
                modules_data=modules_data,
                post_transform=post_transform,
                metadata_cache=metadata_cache,
            )
            new_names = [new_name for _, new_name in preview_result.name_pairs]
        except Exception as e:
            logger.exception("[Rename] Error generating preview")
            if self.parent_window and hasattr(self.parent_window, "status_manager"):
                self.parent_window.status_manager.finish_operation(
                    operation_id,
                    success=False,
                    final_message=f"Preview generation failed: {e}",
                )
            return 0

        # Step 2: Execute rename using unified engine
        try:
            execution_result = engine.execute_rename(
                files=selected_files,
                new_names=new_names,
                conflict_callback=conflict_callback,
                validator=validate_filename_part,
            )
        except Exception as e:
            logger.exception("[Rename] Error executing rename")
            if self.parent_window and hasattr(self.parent_window, "status_manager"):
                self.parent_window.status_manager.finish_operation(
                    operation_id,
                    success=False,
                    final_message=f"Rename execution failed: {e}",
                )
            return 0

        # Step 3: Update FileItem objects from execution results
        renamed_count = 0
        for exec_item in execution_result.items:
            if exec_item.success:
                renamed_count += 1
                item = find_file_by_path(selected_files, exec_item.old_path, "full_path")
                if item:
                    item.filename = Path(exec_item.new_path).name
                    item.full_path = exec_item.new_path
            elif exec_item.skip_reason:
                logger.info(
                    "[Rename] Skipped: %s — Reason: %s",
                    exec_item.old_path,
                    exec_item.skip_reason,
                )
            elif exec_item.error_message:
                logger.error(
                    "[Rename] Error: %s — %s",
                    exec_item.old_path,
                    exec_item.error_message,
                )

        logger.info(
            "[Rename] Completed: %d renamed out of %d total",
            renamed_count,
            len(execution_result.items),
        )
        if self.parent_window and hasattr(self.parent_window, "status_manager"):
            self.parent_window.status_manager.set_rename_status(
                f"Renamed {renamed_count} file(s)",
                renamed_count=renamed_count,
                success=True,
                auto_reset=True,
            )

            # Finish operation tracking
            self.parent_window.status_manager.finish_operation(
                operation_id,
                success=renamed_count > 0,
                final_message=f"Rename operation completed: {renamed_count}/{len(selected_files)} files renamed",
            )

        # Store the completion dialog information to be shown after the post-rename workflow
        if renamed_count > 0 and self.parent_window:
            # Schedule the completion dialog to show after the post-rename workflow
            def show_completion_dialog() -> None:
                """Show the rename completion dialog after the workflow completes."""
                try:
                    if show_question_message(
                        self.parent_window,
                        "Rename Complete",
                        f"{renamed_count} file(s) renamed.\nOpen the folder?",
                    ):
                        QDesktopServices.openUrl(QUrl.fromLocalFile(current_folder_path))
                except Exception as e:
                    logger.error("[FileOperationsManager] Error showing completion dialog: %s", e)

            # Store the dialog function in the parent window for later execution
            if hasattr(self.parent_window, "pending_completion_dialog"):
                self.parent_window.pending_completion_dialog = show_completion_dialog
            else:
                # Fallback: schedule with timer manager for delayed execution
                from oncutf.utils.shared.timer_manager import (
                    TimerPriority,
                    TimerType,
                    get_timer_manager,
                )

                get_timer_manager().schedule(
                    show_completion_dialog,
                    delay=300,  # 300ms delay to let post-rename workflow complete
                    priority=TimerPriority.LOW,
                    timer_type=TimerType.GENERIC,
                    timer_id="rename_completion_dialog",
                )

        return renamed_count

    def find_fileitem_by_path(self, files: list[FileItem], path: str) -> FileItem | None:
        """Find FileItem by path using normalized comparison."""
        return find_file_by_path(files, path, "full_path")

    def get_identity_name_pairs(self, files: list[FileItem]) -> list[tuple[str, str]]:
        """Return identity name pairs for checked files."""
        return [(file.filename, file.filename) for file in files if file.checked]
