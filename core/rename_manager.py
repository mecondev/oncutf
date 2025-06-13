"""
RenameManager - Handles rename operations and workflow

Author: Michael Economou
Date: 2025-01-27

This manager centralizes rename operations including:
- Batch rename execution
- Post-rename workflow
- State restoration after rename
- Module dividers management
"""

from typing import TYPE_CHECKING, List, Set

from models.file_item import FileItem
from utils.logger_helper import get_logger

if TYPE_CHECKING:
    from main_window import MainWindow

logger = get_logger(__name__)


class RenameManager:
    """
    Manages rename operations and workflow for the main window.

    This manager handles:
    - Batch rename execution
    - Post-rename workflow and state restoration
    - Module dividers management
    - Rename-related UI updates
    """

    def __init__(self, main_window: 'MainWindow'):
        """
        Initialize the RenameManager.

        Args:
            main_window: Reference to the main window instance
        """
        self.main_window = main_window
        logger.debug("[RenameManager] Initialized")

    def rename_files(self) -> None:
        """
        Execute the batch rename process for checked files using active rename modules.

        This method handles the complete rename workflow including validation,
        execution, folder reload, and state restoration.
        """
        selected_files = self.main_window.get_selected_files()
        rename_data = self.main_window.rename_modules_area.get_all_data()
        modules_data = rename_data.get("modules", [])
        post_transform = rename_data.get("post_transform", {})

        # Store checked paths for restoration
        checked_paths = {f.full_path for f in self.main_window.file_model.files if f.checked}

        # Use FileOperationsManager to perform rename
        renamed_count = self.main_window.file_operations_manager.rename_files(
            selected_files=selected_files,
            modules_data=modules_data,
            post_transform=post_transform,
            metadata_cache=self.main_window.metadata_cache,
            filename_validator=self.main_window.filename_validator,
            current_folder_path=self.main_window.current_folder_path
        )

        if renamed_count == 0:
            return

        # Execute post-rename workflow
        self._execute_post_rename_workflow(checked_paths)

    def _execute_post_rename_workflow(self, checked_paths: Set[str]) -> None:
        """
        Execute the post-rename workflow including folder reload and state restoration.

        Args:
            checked_paths: Set of file paths that were checked before rename
        """
        # Post-rename workflow
        self.main_window.last_action = "rename"
        self.main_window.load_files_from_folder(self.main_window.current_folder_path, skip_metadata=True)

        # Restore checked state
        restored_count = self._restore_checked_state(checked_paths)

        # Restore metadata from cache
        self.main_window.restore_fileitem_metadata_from_cache()

        # Regenerate preview with new filenames
        if self.main_window.last_action == "rename":
            logger.debug("[PostRename] Regenerating preview with new filenames and restored checked state")
            self.main_window.request_preview_update()

        # Force update info icons in column 0
        self._update_info_icons()

        logger.debug(f"[Rename] Restored {restored_count} checked out of {len(self.main_window.file_model.files)} files")

    def _restore_checked_state(self, checked_paths: Set[str]) -> int:
        """
        Restore checked state for files after rename.

        Args:
            checked_paths: Set of file paths that were checked before rename

        Returns:
            Number of files whose checked state was restored
        """
        restored_count = 0
        for path in checked_paths:
            file = self.main_window.find_fileitem_by_path(path)
            if file:
                file.checked = True
                restored_count += 1
        return restored_count

    def _update_info_icons(self) -> None:
        """Force update info icons in column 0 after rename."""
        for row in range(self.main_window.file_model.rowCount()):
            file_item = self.main_window.file_model.files[row]
            if self.main_window.metadata_cache.has(file_item.full_path):
                index = self.main_window.file_model.index(row, 0)
                rect = self.main_window.file_table_view.visualRect(index)
                self.main_window.file_table_view.viewport().update(rect)

        self.main_window.file_table_view.viewport().update()

    def update_module_dividers(self) -> None:
        """
        Updates the visibility of module dividers based on module position.
        """
        for index, module in enumerate(self.main_window.rename_modules):
            if hasattr(module, "divider"):
                module.divider.setVisible(index > 0)

    def get_rename_data(self) -> dict:
        """
        Get current rename data from modules area.

        Returns:
            Dictionary containing modules data and post_transform settings
        """
        if hasattr(self.main_window, 'rename_modules_area'):
            return self.main_window.rename_modules_area.get_all_data()
        return {"modules": [], "post_transform": {}}

    def get_selected_files_for_rename(self) -> List[FileItem]:
        """
        Get files selected for rename operation.

        Returns:
            List of FileItem objects that are checked/selected for rename
        """
        return self.main_window.get_selected_files()

    def is_rename_possible(self) -> bool:
        """
        Check if rename operation is possible.

        Returns:
            True if rename can be performed, False otherwise
        """
        selected_files = self.get_selected_files_for_rename()
        return len(selected_files) > 0 and bool(self.main_window.current_folder_path)
