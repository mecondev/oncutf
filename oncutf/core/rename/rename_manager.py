"""Module: rename_manager.py

Author: Michael Economou
Date: 2025-05-31

RenameManager - Handles rename operations and workflow
This manager centralizes rename operations including:
- Batch rename execution
- Post-rename workflow
- State restoration after rename
- Module dividers management
"""

from typing import Any

from oncutf.models.file_item import FileItem
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class RenameManager:
    """Manages rename operations and workflow for the main window.

    This manager handles:
    - Batch rename execution
    - Post-rename workflow and state restoration
    - Module dividers management
    - Rename-related UI updates
    """

    def __init__(self, main_window: Any):
        """Initialize the RenameManager.

        Args:
            main_window: Reference to the main window instance

        """
        self.main_window: Any = main_window
        self.pending_completion_dialog = None
        self._rename_cursor_context: Any = None  # Context manager for wait cursor during rename
        logger.debug("[RenameManager] Initialized", extra={"dev_only": True})

    def _restore_wait_cursor(self) -> None:
        """Restore cursor after rename operation."""
        from contextlib import suppress

        if self._rename_cursor_context is not None:
            with suppress(Exception):
                self._rename_cursor_context.__exit__(None, None, None)
            self._rename_cursor_context = None

    def rename_files(self) -> None:
        """Execute the batch rename process for checked files using active rename modules.

        This method handles the complete rename workflow including validation,
        execution, folder reload, and state restoration.
        """
        from oncutf.utils.ui.cursor_helper import wait_cursor

        # Start wait cursor IMMEDIATELY for user feedback
        # It will be restored when post-rename workflow completes
        self._rename_cursor_context = wait_cursor()
        self._rename_cursor_context.__enter__()

        selected_files = self.main_window.get_selected_files()
        rename_data = self.main_window.rename_modules_area.get_all_data()

        # Add post_transform data from final transform container
        post_transform_data = self.main_window.final_transform_container.get_data()
        rename_data["post_transform"] = post_transform_data

        post_transform = rename_data.get("post_transform", {})
        modules_data = rename_data.get("modules", [])

        # Store checked paths for restoration
        checked_paths = {f.full_path for f in self.main_window.file_model.files if f.checked}
        # Store selected paths for restoration
        selected_paths = {f.full_path for f in selected_files}

        # Use FileOperationsManager to perform rename
        try:
            renamed_count = self.main_window.file_operations_manager.rename_files(
                selected_files=selected_files,
                modules_data=modules_data,
                post_transform=post_transform,
                metadata_cache=self.main_window.metadata_cache,
                current_folder_path=self.main_window.context.get_current_folder(),
            )
        except Exception as e:
            logger.error("[RenameManager] Critical error during rename: %s", e)
            self._restore_wait_cursor()
            return

        # Record rename operation in history for undo functionality
        new_checked_paths = set()
        new_selected_paths = set()

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

                # Map paths for restoration
                path_map = dict(rename_pairs)

                # Map checked paths
                for path in checked_paths:
                    new_checked_paths.add(path_map.get(path, path))

                # Map selected paths
                for path in selected_paths:
                    new_selected_paths.add(path_map.get(path, path))

                if rename_pairs and hasattr(self.main_window, "rename_history_manager"):
                    operation_id = self.main_window.rename_history_manager.record_rename_batch(
                        renames=rename_pairs,
                        modules_data=modules_data,
                        post_transform_data=post_transform,
                    )
                    if operation_id:
                        logger.info(
                            "[RenameManager] Recorded rename operation %s... for undo",
                            operation_id[:8],
                        )

            except Exception as e:
                logger.warning("[RenameManager] Failed to record rename history: %s", e)

        if renamed_count == 0:
            self._restore_wait_cursor()
            return

        # Execute post-rename workflow with safe delayed execution
        # Use TimerManager for safe delayed execution to avoid Qt object lifecycle issues
        from oncutf.utils.shared.timer_manager import (
            TimerPriority,
            TimerType,
            get_timer_manager,
        )

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
                    self._restore_wait_cursor()
                    return

                logger.info("[RenameManager] Starting safe post-rename workflow")
                self._results: dict[str, Any] = {}
                self._execute_post_rename_workflow_safe(new_checked_paths, new_selected_paths)
            except Exception as e:
                logger.exception(
                    "[RenameManager] Error in post-rename workflow: %s",
                    e,
                )
                self._restore_wait_cursor()
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
            "[RenameManager] Scheduled post-rename workflow for %d files",
            renamed_count,
        )

    def _execute_post_rename_workflow_safe(
        self, checked_paths: set[str], selected_paths: set[str] | None = None
    ) -> None:
        """Execute the post-rename workflow with enhanced safety checks.

        Args:
            checked_paths: Set of file paths that were checked before rename
            selected_paths: Set of file paths that were selected before rename (mapped to new names)

        """
        try:
            # Validate main window state
            if not self.main_window or not hasattr(self.main_window, "context"):
                logger.warning("[RenameManager] Main window invalid, aborting post-rename workflow")
                return

            current_folder = self.main_window.context.get_current_folder()
            if not current_folder:
                logger.warning("[RenameManager] No current folder, aborting post-rename workflow")
                return

            logger.debug("[RenameManager] Starting post-rename workflow")

            # Set last action for proper state tracking
            self.main_window.last_action = "rename"

            # Reload folder for faster loading
            logger.debug("[RenameManager] Reloading folder after rename")
            # Schedule state restoration AFTER folder load is complete.
            # NOTE: Folder loads can be streaming (many model resets). A fixed delay races and
            # can lose selection due to later UI refresh calls.
            def restore_state() -> None:
                """Restore UI state after reload."""
                logger.debug("[RenameManager] restore_state function called")
                try:
                    if not self.main_window or not hasattr(self.main_window, "file_model"):
                        logger.debug(
                            "[RenameManager] restore_state: main_window or file_model not available"
                        )
                        return

                    # Use FileTableStateHelper for consistent restoration
                    from oncutf.core.application_context import get_app_context
                    from oncutf.utils.ui.file_table_state_helper import (
                        FileTableState,
                        FileTableStateHelper,
                    )

                    state = FileTableState(
                        selected_paths=list(selected_paths) if selected_paths else [],
                        checked_paths=checked_paths,
                        anchor_row=None,
                        scroll_position=0,
                    )

                    context = get_app_context()
                    # Call restore SYNCHRONOUSLY - we already debounced via files_loaded signal
                    FileTableStateHelper.restore_state_sync(
                        self.main_window.file_table_view,
                        context,
                        state,
                    )

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

                    logger.info("[RenameManager] Post-rename workflow completed")

                    # Restore wait cursor now that everything is done
                    self._restore_wait_cursor()

                    # Execute pending completion dialog if available
                    logger.debug(
                        "[RenameManager] restore_state: checking for pending completion dialog"
                    )
                    if hasattr(self.main_window, "pending_completion_dialog"):
                        completion_dialog = self.main_window.pending_completion_dialog
                        logger.debug(
                            "[RenameManager] restore_state: pending_completion_dialog exists: %s",
                            completion_dialog is not None,
                        )
                        if completion_dialog:
                            logger.debug("[RenameManager] Executing pending completion dialog")
                            # Schedule the dialog with a small delay to ensure UI is fully updated
                            from oncutf.utils.shared.timer_manager import (
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
                    logger.exception(
                        "[RenameManager] Error in state restoration: %s",
                        e,
                    )

            # Debounced restore: wait until FileStore.files_loaded stops firing.
            from contextlib import suppress

            from oncutf.core.application_context import get_app_context
            from oncutf.utils.shared.timer_manager import (
                TimerPriority,
                TimerType,
                get_timer_manager,
            )

            # get_app_context() may raise if the application context is not initialized
            try:
                context = get_app_context()
            except Exception:
                context = None

            file_store = getattr(context, "file_store", None) if context else None
            if not file_store or not hasattr(file_store, "files_loaded"):
                logger.warning(
                    "[RenameManager] FileStore/files_loaded not available; using fallback timer"
                )
                self.main_window.load_files_from_folder(current_folder)
                get_timer_manager().schedule(
                    restore_state,
                    delay=500,
                    priority=TimerPriority.HIGH,
                    timer_type=TimerType.UI_UPDATE,
                    timer_id="post_rename_state_restore_fallback",
                )
                return

            restore_timer_id = "post_rename_state_restore_debounced"
            disconnected = {"done": False}

            def disconnect_listener() -> None:
                if disconnected["done"]:
                    return
                with suppress(Exception):
                    file_store.files_loaded.disconnect(on_files_loaded)
                disconnected["done"] = True

            def finalize_restore() -> None:
                disconnect_listener()
                restore_state()

            def on_files_loaded(_files: list[Any]) -> None:
                # Each files_loaded event cancels the previous timer_id; restore happens
                # only after the last event (i.e. when loading is effectively complete).
                get_timer_manager().schedule(
                    finalize_restore,
                    delay=150,
                    priority=TimerPriority.HIGH,
                    timer_type=TimerType.UI_UPDATE,
                    timer_id=restore_timer_id,
                    consolidate=False,
                )

            # Connect BEFORE triggering the load.
            try:
                file_store.files_loaded.connect(on_files_loaded)
            except Exception:
                logger.warning(
                    "[RenameManager] Failed to connect to files_loaded; using fallback timer"
                )
                self.main_window.load_files_from_folder(current_folder)
                get_timer_manager().schedule(
                    restore_state,
                    delay=500,
                    priority=TimerPriority.HIGH,
                    timer_type=TimerType.UI_UPDATE,
                    timer_id="post_rename_state_restore_fallback",
                )
                return

            # Trigger the folder reload.
            self.main_window.load_files_from_folder(current_folder)

            # Also schedule a safety fallback in case no files_loaded is emitted.
            get_timer_manager().schedule(
                finalize_restore,
                delay=800,
                priority=TimerPriority.HIGH,
                timer_type=TimerType.UI_UPDATE,
                timer_id="post_rename_state_restore_safety",
                consolidate=False,
            )

        except Exception as e:
            logger.exception(
                "[RenameManager] Critical error in post-rename workflow: %s",
                e,
            )

    def _execute_post_rename_workflow(self, checked_paths: set[str]) -> None:
        """Execute the post-rename workflow including folder reload and state restoration.

        Args:
            checked_paths: Set of file paths that were checked before rename

        """
        # Post-rename workflow
        self.main_window.last_action = "rename"
        self.main_window.load_files_from_folder(self.main_window.context.get_current_folder())

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
            "[Rename] Restored %d checked out of %d files",
            restored_count,
            len(self.main_window.file_model.files),
        )

    def _restore_checked_state_safe(self, checked_paths: set[str]) -> int:
        """Safely restore checked state for files after rename.

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
                    logger.debug(
                        "[RenameManager] Could not restore checked state for %s: %s",
                        path,
                        e,
                    )
                    continue

        except Exception as e:
            logger.error("[RenameManager] Error in _restore_checked_state_safe: %s", e)

        return restored_count

    def _restore_checked_state(self, checked_paths: set[str]) -> int:
        """Restore checked state for files after rename.

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
                    logger.debug(
                        "[RenameManager] Could not update icon for row %d: %s",
                        row,
                        e,
                    )
                    continue

            # Update entire viewport
            file_table_view.viewport().update()

        except Exception as e:
            logger.error("[RenameManager] Error in _update_info_icons_safe: %s", e)

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
        """Updates the visibility of module dividers based on module position."""
        for index, module in enumerate(self.main_window.rename_modules):
            if hasattr(module, "divider"):
                module.divider.setVisible(index > 0)

    def get_rename_data(self) -> dict[str, Any]:
        """Get current rename data from modules area.

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
        """Get files selected for rename operation.

        Returns:
            List of FileItem objects that are checked/selected for rename

        """
        return self.main_window.get_selected_files()

    def is_rename_possible(self) -> bool:
        """Check if rename operation is possible.

        Returns:
            True if rename can be performed, False otherwise

        """
        selected_files = self.get_selected_files_for_rename()
        return len(selected_files) > 0 and bool(self.main_window.context.get_current_folder())
