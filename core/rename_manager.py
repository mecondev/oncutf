"""
Module: rename_manager.py

Author: Michael Economou
Date: 2025-05-31

RenameManager - Handles rename operations and workflow
This manager centralizes rename operations including:
- Batch rename execution
- Post-rename workflow
- State restoration after rename
- Module dividers management
"""

from typing import TYPE_CHECKING

from oncutf.models.file_item import FileItem
from oncutf.utils.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from main_window import MainWindow

logger = get_cached_logger(__name__)


class RenameManager:
    """
    Manages rename operations and workflow for the main window.

    This manager handles:
    - Batch rename execution
    - Post-rename workflow and state restoration
    - Module dividers management
    - Rename-related UI updates
    """

    def __init__(self, main_window: "MainWindow"):
        """
        Initialize the RenameManager.

        Args:
            main_window: Reference to the main window instance
        """
        self.main_window = main_window
        self.pending_completion_dialog = None
        logger.debug("[RenameManager] Initialized", extra={"dev_only": True})

    def rename_files(self) -> None:
        """
        Execute the batch rename process for checked files using active rename modules.

        This method handles the complete rename workflow including validation,
        execution, folder reload, and state restoration.
        """
        from oncutf.utils.cursor_helper import wait_cursor

        with wait_cursor():
            selected_files = self.main_window.get_selected_files()
            rename_data = self.main_window.rename_modules_area.get_all_data()

            # Add post_transform data from final transform container
            post_transform_data = self.main_window.final_transform_container.get_data()
            rename_data["post_transform"] = post_transform_data

            post_transform = rename_data.get("post_transform", {})
            modules_data = rename_data.get("modules", [])

            # Store checked paths for restoration
            checked_paths = {f.full_path for f in self.main_window.file_model.files if f.checked}

            # Use FileOperationsManager to perform rename
            try:
                renamed_count = self.main_window.file_operations_manager.rename_files(
                    selected_files=selected_files,
                    modules_data=modules_data,
                    post_transform=post_transform,
                    metadata_cache=self.main_window.metadata_cache,
                    current_folder_path=self.main_window.current_folder_path,
                )
            except Exception as e:
                logger.error(f"[RenameManager] Critical error during rename: {e}")
                return

            # Record rename operation in history for undo functionality
            if renamed_count > 0:
                try:
                    # Collect actual rename operations that succeeded
                    rename_pairs = []
                    for file_item in selected_files:
                        if hasattr(file_item, "original_path") and file_item.original_path:
                            # File was renamed, record the operation
                            rename_pairs.append((file_item.original_path, file_item.full_path))
                        else:
                            # Fallback: assume rename based on current path and modules
                            old_path = file_item.full_path  # This might not be accurate
                            new_path = file_item.full_path  # Current path after rename
                            if old_path != new_path:
                                rename_pairs.append((old_path, new_path))

                    if rename_pairs and hasattr(self.main_window, "rename_history_manager"):
                        operation_id = self.main_window.rename_history_manager.record_rename_batch(
                            renames=rename_pairs,
                            modules_data=modules_data,
                            post_transform_data=post_transform,
                        )
                        if operation_id:
                            logger.info(
                                f"[RenameManager] Recorded rename operation {operation_id[:8]}... for undo"
                            )

                except Exception as e:
                    logger.warning(f"[RenameManager] Failed to record rename history: {e}")

            if renamed_count == 0:
                return

            # Execute post-rename workflow with safe delayed execution
            if renamed_count > 0:
                # Use TimerManager for safe delayed execution to avoid Qt object lifecycle issues
                from oncutf.utils.timer_manager import TimerPriority, TimerType, get_timer_manager

                def safe_post_rename_workflow():
                    """Safe wrapper for post-rename workflow with error handling."""
                    try:
                        # Check if main window is still valid
                        if not self.main_window or not hasattr(
                            self.main_window, "current_folder_path"
                        ):
                            logger.warning(
                                "[RenameManager] Main window no longer valid, skipping post-rename workflow"
                            )
                            return

                        logger.info("[RenameManager] Starting safe post-rename workflow")
                        self._execute_post_rename_workflow_safe(checked_paths)
                    except Exception as e:
                        logger.error(
                            f"[RenameManager] Error in post-rename workflow: {e}", exc_info=True
                        )
                        # Fallback: just show a simple status message
                        if hasattr(self.main_window, "set_status"):
                            self.main_window.set_status(
                                f"Rename completed: {renamed_count} files", auto_reset=True
                            )

                # Schedule the workflow with a small delay to let the rename operation complete
                get_timer_manager().schedule(
                    safe_post_rename_workflow,
                    delay=100,  # 100ms delay to ensure file system operations are complete
                    priority=TimerPriority.HIGH,
                    timer_type=TimerType.GENERIC,
                    timer_id="post_rename_workflow",
                )

                logger.info(
                    f"[RenameManager] Scheduled post-rename workflow for {renamed_count} files"
                )
            else:
                logger.info("[RenameManager] No files renamed, skipping post-rename workflow")

    def _execute_post_rename_workflow_safe(self, checked_paths: set[str]) -> None:
        """
        Execute the post-rename workflow with enhanced safety checks.

        Args:
            checked_paths: Set of file paths that were checked before rename
        """
        try:
            # Validate main window state
            if not self.main_window or not hasattr(self.main_window, "current_folder_path"):
                logger.warning("[RenameManager] Main window invalid, aborting post-rename workflow")
                return

            current_folder = self.main_window.current_folder_path
            if not current_folder:
                logger.warning("[RenameManager] No current folder, aborting post-rename workflow")
                return

            logger.debug("[RenameManager] Starting post-rename workflow")

            # Set last action for proper state tracking
            self.main_window.last_action = "rename"

            # Reload folder for faster loading
            logger.debug("[RenameManager] Reloading folder after rename")
            self.main_window.load_files_from_folder(current_folder)

            # Schedule state restoration after folder load completes
            def restore_state():
                """Restore UI state after folder reload."""
                logger.debug("[RenameManager] restore_state function called")
                try:
                    if not self.main_window or not hasattr(self.main_window, "file_model"):
                        logger.debug(
                            "[RenameManager] restore_state: main_window or file_model not available"
                        )
                        return

                    # Restore checked state
                    logger.debug("[RenameManager] restore_state: restoring checked state")
                    restored_count = self._restore_checked_state_safe(checked_paths)

                    # Restore metadata from cache
                    if hasattr(self.main_window, "restore_fileitem_metadata_from_cache"):
                        logger.debug("[RenameManager] restore_state: restoring metadata from cache")
                        self.main_window.restore_fileitem_metadata_from_cache()

                    # Regenerate preview with new filenames
                    if hasattr(self.main_window, "request_preview_update"):
                        logger.debug("[RenameManager] restore_state: regenerating preview")
                        self.main_window.request_preview_update()

                    # Update info icons safely
                    logger.debug("[RenameManager] restore_state: updating info icons")
                    self._update_info_icons_safe()

                    logger.info(
                        f"[RenameManager] Post-rename workflow completed: {restored_count} files restored"
                    )

                    # Execute pending completion dialog if available
                    logger.debug(
                        "[RenameManager] restore_state: checking for pending completion dialog"
                    )
                    if hasattr(self.main_window, "pending_completion_dialog"):
                        completion_dialog = self.main_window.pending_completion_dialog
                        logger.debug(
                            f"[RenameManager] restore_state: pending_completion_dialog exists: {completion_dialog is not None}"
                        )
                        if completion_dialog:
                            logger.debug("[RenameManager] Executing pending completion dialog")
                            # Schedule the dialog with a small delay to ensure UI is fully updated
                            from oncutf.utils.timer_manager import (
                                TimerPriority,
                                TimerType,
                                get_timer_manager,
                            )

                            get_timer_manager().schedule(
                                completion_dialog,
                                delay=100,  # 100ms delay to ensure UI is updated
                                priority=TimerPriority.LOW,
                                timer_type=TimerType.GENERIC,
                                timer_id="completion_dialog_execution",
                            )
                            # Clear the pending dialog
                            self.main_window.pending_completion_dialog = None
                            logger.debug("[RenameManager] Completion dialog scheduled and cleared")
                        else:
                            logger.debug("[RenameManager] No completion dialog to execute")
                    else:
                        logger.debug("[RenameManager] No pending_completion_dialog attribute found")

                except Exception as e:
                    logger.error(f"[RenameManager] Error in state restoration: {e}", exc_info=True)

            # Schedule state restoration with a small delay
            logger.debug("[RenameManager] Scheduling restore_state function")
            from oncutf.utils.timer_manager import TimerPriority, TimerType, get_timer_manager

            get_timer_manager().schedule(
                restore_state,
                delay=50,  # 50ms delay to let folder load complete
                priority=TimerPriority.HIGH,
                timer_type=TimerType.UI_UPDATE,
                timer_id="post_rename_state_restore",
            )

        except Exception as e:
            logger.error(
                f"[RenameManager] Critical error in post-rename workflow: {e}", exc_info=True
            )

    def _execute_post_rename_workflow(self, checked_paths: set[str]) -> None:
        """
        Execute the post-rename workflow including folder reload and state restoration.

        Args:
            checked_paths: Set of file paths that were checked before rename
        """
        # Post-rename workflow
        self.main_window.last_action = "rename"
        self.main_window.load_files_from_folder(self.main_window.current_folder_path)

        # Restore checked state
        restored_count = self._restore_checked_state(checked_paths)

        # Restore metadata from cache
        self.main_window.restore_fileitem_metadata_from_cache()

        # Regenerate preview with new filenames
        if self.main_window.last_action == "rename":
            logger.debug(
                "[PostRename] Regenerating preview with new filenames and restored checked state"
            )
            self.main_window.request_preview_update()

        # Force update info icons in column 0
        self._update_info_icons()

        logger.debug(
            f"[Rename] Restored {restored_count} checked out of {len(self.main_window.file_model.files)} files"
        )

    def _restore_checked_state_safe(self, checked_paths: set[str]) -> int:
        """
        Safely restore checked state for files after rename.

        Args:
            checked_paths: Set of file paths that were checked before rename

        Returns:
            Number of files whose checked state was restored
        """
        restored_count = 0
        try:
            if not self.main_window or not hasattr(self.main_window, "find_fileitem_by_path"):
                return 0

            for path in checked_paths:
                try:
                    file = self.main_window.find_fileitem_by_path(path)
                    if file:
                        file.checked = True
                        restored_count += 1
                except Exception as e:
                    logger.debug(f"[RenameManager] Could not restore checked state for {path}: {e}")
                    continue

        except Exception as e:
            logger.error(f"[RenameManager] Error in _restore_checked_state_safe: {e}")

        return restored_count

    def _restore_checked_state(self, checked_paths: set[str]) -> int:
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

    def _update_info_icons_safe(self) -> None:
        """Safely update info icons in column 0 after rename."""
        try:
            if not self.main_window or not hasattr(self.main_window, "file_model"):
                return

            file_model = self.main_window.file_model
            if not hasattr(file_model, "files") or not hasattr(file_model, "rowCount"):
                return

            file_table_view = getattr(self.main_window, "file_table_view", None)
            if not file_table_view:
                return

            # Update icons for each row
            for row in range(file_model.rowCount()):
                try:
                    if row < len(file_model.files):
                        file_item = file_model.files[row]
                        if hasattr(
                            self.main_window, "metadata_cache"
                        ) and self.main_window.metadata_cache.has(file_item.full_path):
                            index = file_model.index(row, 0)
                            rect = file_table_view.visualRect(index)
                            file_table_view.viewport().update(rect)
                except Exception as e:
                    logger.debug(f"[RenameManager] Could not update icon for row {row}: {e}")
                    continue

            # Update entire viewport
            file_table_view.viewport().update()

        except Exception as e:
            logger.error(f"[RenameManager] Error in _update_info_icons_safe: {e}")

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
        if hasattr(self.main_window, "rename_modules_area"):
            rename_data = self.main_window.rename_modules_area.get_all_data()

            # Add post_transform data from final transform container
            if hasattr(self.main_window, "final_transform_container"):
                post_transform_data = self.main_window.final_transform_container.get_data()
                rename_data["post_transform"] = post_transform_data
            else:
                rename_data["post_transform"] = {}

            return rename_data
        return {"modules": [], "post_transform": {}}

    def get_selected_files_for_rename(self) -> list[FileItem]:
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
