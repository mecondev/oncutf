"""Module: file_operations_manager.py

Author: Michael Economou
Date: 2025-06-13

file_operations_manager.py
Manages file operations like rename, validation, and conflict resolution.
"""

import os
from typing import Any

from oncutf.core.pyqt_imports import QDesktopServices, QUrl
from oncutf.models.file_item import FileItem
from oncutf.ui.widgets.custom_message_dialog import CustomMessageDialog
from oncutf.utils.logger_factory import get_cached_logger
from oncutf.utils.path_utils import find_file_by_path
from oncutf.utils.renamer import Renamer

logger = get_cached_logger(__name__)


class FileOperationsManager:
    """Manages file operations like rename, validation, and conflict resolution."""

    def __init__(self, parent_window=None) -> None:
        """Initialize FileOperationsManager."""
        self.parent_window = parent_window
        logger.debug("[FileOperationsManager] Initialized", extra={"dev_only": True})

    def rename_files(
        self,
        selected_files: list[FileItem],
        modules_data: list[dict[str, Any]],
        post_transform: dict[str, Any],
        metadata_cache,
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
                CustomMessageDialog.show_warning(
                    self.parent_window, "Rename Warning", "No files are selected for renaming."
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
        from oncutf.utils.filename_validator import validate_filename_part

        # Create a safe conflict callback that doesn't block
        def safe_conflict_callback(_parent, filename):
            """Safe conflict callback that prevents blocking."""
            try:
                logger.info("[Rename] File conflict detected for: %s", filename)
                # For now, automatically skip conflicts to prevent blocking
                # TODO: Implement non-blocking conflict resolution UI
                return "skip"
            except Exception as e:
                logger.error("[Rename] Error in conflict callback: %s", e)
                return "skip"

        renamer = Renamer(
            files=selected_files,
            modules_data=modules_data,
            metadata_cache=metadata_cache,
            post_transform=post_transform,
            parent=self.parent_window,
            conflict_callback=safe_conflict_callback,
            validator=validate_filename_part,
        )

        results = renamer.rename()
        renamed_count = 0

        for result in results:
            if result.success:
                renamed_count += 1
                item = find_file_by_path(selected_files, result.old_path, "full_path")
                if item:
                    item.filename = os.path.basename(result.new_path)
                    item.full_path = result.new_path
            elif result.skip_reason:
                logger.info(
                    "[Rename] Skipped: %s — Reason: %s", result.old_path, result.skip_reason
                )
            elif result.error:
                logger.error("[Rename] Error: %s — %s", result.old_path, result.error)

        # Use specialized rename status method
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

        logger.info("[Rename] Completed: %d renamed out of %d total", renamed_count, len(results))

        # Store the completion dialog information to be shown after the post-rename workflow
        if renamed_count > 0 and self.parent_window:
            # Schedule the completion dialog to show after the post-rename workflow
            def show_completion_dialog():
                """Show the rename completion dialog after the workflow completes."""
                try:
                    if CustomMessageDialog.question(
                        self.parent_window,
                        "Rename Complete",
                        f"{renamed_count} file(s) renamed.\nOpen the folder?",
                        yes_text="Open Folder",
                        no_text="Close",
                    ):
                        QDesktopServices.openUrl(QUrl.fromLocalFile(current_folder_path))
                except Exception as e:
                    logger.error("[FileOperationsManager] Error showing completion dialog: %s", e)

            # Store the dialog function in the parent window for later execution
            if hasattr(self.parent_window, "pending_completion_dialog"):
                self.parent_window.pending_completion_dialog = show_completion_dialog
            else:
                # Fallback: schedule with timer manager for delayed execution
                from oncutf.utils.timer_manager import TimerPriority, TimerType, get_timer_manager

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
