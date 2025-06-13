"""
file_operations_manager.py

Author: Michael Economou
Date: 2025-06-13

Manages file operations like rename, validation, and conflict resolution.
"""

import os
from typing import List, Optional

from core.qt_imports import QDesktopServices, QUrl
from core.config_imports import LARGE_FOLDER_WARNING_THRESHOLD, EXTENDED_METADATA_SIZE_LIMIT_MB
from models.file_item import FileItem
from utils.logger_helper import get_logger
from utils.renamer import Renamer
from widgets.custom_msgdialog import CustomMessageDialog

logger = get_logger(__name__)


class FileOperationsManager:
    """Manages file operations like rename, validation, and conflict resolution."""

    def __init__(self, parent_window=None):
        """Initialize FileOperationsManager."""
        self.parent_window = parent_window
        logger.debug("[FileOperationsManager] Initialized")

    def rename_files(
        self,
        selected_files: List[FileItem],
        modules_data: List[dict],
        post_transform: dict,
        metadata_cache,
        filename_validator,
        current_folder_path: str
    ) -> int:
        """Execute batch rename process."""
        if not current_folder_path:
            if self.parent_window:
                self.parent_window.set_status("No folder selected.", color="orange")
            return 0

        if not selected_files:
            if self.parent_window:
                self.parent_window.set_status("No files selected.", color="gray")
                CustomMessageDialog.show_warning(
                    self.parent_window, "Rename Warning", "No files are selected for renaming."
                )
            return 0

        logger.info(f"[Rename] Starting rename process for {len(selected_files)} files...")

        renamer = Renamer(
            files=selected_files,
            modules_data=modules_data,
            metadata_cache=metadata_cache,
            post_transform=post_transform,
            parent=self.parent_window,
            conflict_callback=CustomMessageDialog.rename_conflict_dialog,
            validator=filename_validator
        )

        results = renamer.rename()
        renamed_count = 0

        for result in results:
            if result.success:
                renamed_count += 1
                item = next((f for f in selected_files if f.full_path == result.old_path), None)
                if item:
                    item.filename = os.path.basename(result.new_path)
                    item.full_path = result.new_path
            elif result.skip_reason:
                logger.info(f"[Rename] Skipped: {result.old_path} — Reason: {result.skip_reason}")
            elif result.error:
                logger.error(f"[Rename] Error: {result.old_path} — {result.error}")

        if self.parent_window:
            self.parent_window.set_status(f"Renamed {renamed_count} file(s).", color="green", auto_reset=True)

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
        """Find FileItem by path."""
        for file_item in files:
            if file_item.full_path == path:
                return file_item
        return None

    def get_identity_name_pairs(self, files: List[FileItem]) -> List[tuple]:
        """Return identity name pairs for checked files."""
        return [
            (file.filename, file.filename)
            for file in files
            if file.checked
        ]
