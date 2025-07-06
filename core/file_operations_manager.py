"""
Module: file_operations_manager.py

Author: Michael Economou
Date: 2025-06-15

file_operations_manager.py
Manages file operations like rename, validation, and conflict resolution.
"""
import os
from typing import List, Optional

from config import STATUS_COLORS
from core.qt_imports import QDesktopServices, QUrl
from models.file_item import FileItem
from utils.logger_factory import get_cached_logger
from utils.path_utils import find_file_by_path
from utils.renamer import Renamer
from widgets.custom_msgdialog import CustomMessageDialog

logger = get_cached_logger(__name__)


class FileOperationsManager:
    """Manages file operations like rename, validation, and conflict resolution."""

    def __init__(self, parent_window=None) -> None:
        """Initialize FileOperationsManager."""
        self.parent_window = parent_window
        logger.debug("[FileOperationsManager] Initialized", extra={"dev_only": True})

    def rename_files(
        self,
        selected_files: List[FileItem],
        modules_data: List[dict],
        post_transform: dict,
        metadata_cache,
        current_folder_path: str
    ) -> int:
        """Execute batch rename process."""
        if not current_folder_path:
            if self.parent_window and hasattr(self.parent_window, 'status_manager'):
                self.parent_window.status_manager.set_validation_status(
                    "No folder selected",
                    validation_type="warning",
                    auto_reset=True
                )
            return 0

        if not selected_files:
            if self.parent_window and hasattr(self.parent_window, 'status_manager'):
                self.parent_window.status_manager.set_selection_status(
                    "No files selected for renaming",
                    selected_count=0,
                    total_count=0,
                    auto_reset=True
                )
                CustomMessageDialog.show_warning(
                    self.parent_window, "Rename Warning", "No files are selected for renaming."
                )
            return 0

        logger.info(f"[Rename] Starting rename process for {len(selected_files)} files...")

        # Start operation tracking
        operation_id = f"rename_{len(selected_files)}_files"
        if self.parent_window and hasattr(self.parent_window, 'status_manager'):
            self.parent_window.status_manager.start_operation(
                operation_id, "rename", f"Renaming {len(selected_files)} files"
            )

        # Import validator here to avoid circular imports
        from utils.filename_validator import validate_filename_part

        renamer = Renamer(
            files=selected_files,
            modules_data=modules_data,
            metadata_cache=metadata_cache,
            post_transform=post_transform,
            parent=self.parent_window,
            conflict_callback=lambda parent, filename: CustomMessageDialog.rename_conflict_dialog(parent, filename),
            validator=validate_filename_part
        )

        results = renamer.rename()
        renamed_count = 0

        for result in results:
            if result.success:
                renamed_count += 1
                item = find_file_by_path(selected_files, result.old_path, 'full_path')
                if item:
                    item.filename = os.path.basename(result.new_path)
                    item.full_path = result.new_path
            elif result.skip_reason:
                logger.info(f"[Rename] Skipped: {result.old_path} — Reason: {result.skip_reason}")
            elif result.error:
                logger.error(f"[Rename] Error: {result.old_path} — {result.error}")

        # Use specialized rename status method
        if self.parent_window and hasattr(self.parent_window, 'status_manager'):
            self.parent_window.status_manager.set_rename_status(
                f"Renamed {renamed_count} file(s)",
                renamed_count=renamed_count,
                success=True,
                auto_reset=True
            )

            # Finish operation tracking
            self.parent_window.status_manager.finish_operation(
                operation_id,
                success=renamed_count > 0,
                final_message=f"Rename operation completed: {renamed_count}/{len(selected_files)} files renamed"
            )

        logger.info(f"[Rename] Completed: {renamed_count} renamed out of {len(results)} total")

        if renamed_count > 0 and self.parent_window:
            if CustomMessageDialog.question(
                self.parent_window,
                "Rename Complete",
                f"{renamed_count} file(s) renamed.\nOpen the folder?",
                yes_text="Open Folder",
                no_text="Close"
            ):
                QDesktopServices.openUrl(QUrl.fromLocalFile(current_folder_path))

        return renamed_count

    def find_fileitem_by_path(self, files: List[FileItem], path: str) -> Optional[FileItem]:
        """Find FileItem by path using normalized comparison."""
        return find_file_by_path(files, path, 'full_path')

    def get_identity_name_pairs(self, files: List[FileItem]) -> List[tuple]:
        """Return identity name pairs for checked files."""
        return [
            (file.filename, file.filename)
            for file in files
            if file.checked
        ]
