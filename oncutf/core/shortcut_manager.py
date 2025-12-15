"""
Module: shortcut_manager.py

Author: Michael Economou
Date: 2025-05-01

ShortcutManager - Handles keyboard shortcuts
This manager centralizes keyboard shortcut handling including:
- Clear file table shortcut (Shift+Escape)
- History dialog shortcut (Ctrl+Shift+Z)
- Results hash list shortcut (Ctrl+L)
- Future keyboard shortcuts can be added here

Note: Undo/Redo shortcuts (Ctrl+Z, Ctrl+R) are local to metadata tree widget.
"""

import os
from typing import TYPE_CHECKING

from oncutf.core.pyqt_imports import Qt
from oncutf.utils.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.ui.main_window import MainWindow

logger = get_cached_logger(__name__)


class ShortcutManager:
    """
    Manages keyboard shortcuts for the main window.

    This manager handles:
    - Clear file table shortcut functionality
    - Undo/Redo functionality for metadata operations
    - History dialog for viewing command history
    - Future keyboard shortcuts can be added here
    """

    def __init__(self, main_window: "MainWindow"):
        """
        Initialize the ShortcutManager.

        Args:
            main_window: Reference to the main window instance
        """
        self.main_window = main_window
        logger.debug("[ShortcutManager] Initialized", extra={"dev_only": True})

    def clear_file_table_shortcut(self) -> None:
        """
        Clear file table triggered by Shift+Escape shortcut.
        """
        logger.info("[MainWindow] CLEAR TABLE: Shift+Escape key pressed")

        if not self.main_window.file_model.files:
            logger.info("[MainWindow] CLEAR TABLE: No files to clear")
            if hasattr(self.main_window, "status_manager"):
                self.main_window.status_manager.set_selection_status(
                    "No files to clear", selected_count=0, total_count=0, auto_reset=True
                )
            return

        # Clear the file table
        self.main_window.clear_file_table("Press Escape to clear, or drag folders here")
        # Clear folder state via ApplicationContext (centralized state management)
        self.main_window.context.set_current_folder(None, False)
        self.main_window.current_sort_column = 1  # Reset to filename column
        self.main_window.current_sort_order = Qt.AscendingOrder  # Reset to ascending

        if hasattr(self.main_window, "status_manager"):
            self.main_window.status_manager.set_file_operation_status(
                "File table cleared", success=True, auto_reset=True
            )
            # Override the reset delay for quick feedback
            if self.main_window.status_manager._status_timer:
                self.main_window.status_manager._status_timer.stop()
                self.main_window.status_manager._status_timer.start(1000)  # 1 second

        logger.info("[MainWindow] CLEAR TABLE: File table cleared successfully")

    def undo_metadata_operation(self) -> None:
        """
        Undo the last metadata operation triggered by Ctrl+Z shortcut.
        """
        logger.info("[MainWindow] UNDO: Ctrl+Z key pressed")

        try:
            # Get the metadata command manager
            from oncutf.core.metadata_command_manager import get_metadata_command_manager

            command_manager = get_metadata_command_manager()

            if command_manager.undo():
                logger.info("[MainWindow] UNDO: Operation undone successfully")

                # Show status message
                if hasattr(self.main_window, "status_manager"):
                    description = command_manager.get_undo_description()
                    if description:
                        self.main_window.status_manager.set_file_operation_status(
                            f"Undone: {description}", success=True, auto_reset=True
                        )
                    else:
                        self.main_window.status_manager.set_file_operation_status(
                            "Operation undone", success=True, auto_reset=True
                        )
            else:
                logger.info("[MainWindow] UNDO: No operations to undo")

                # Show status message
                if hasattr(self.main_window, "status_manager"):
                    self.main_window.status_manager.set_file_operation_status(
                        "No operations to undo", success=False, auto_reset=True
                    )

        except Exception as e:
            logger.error(f"[MainWindow] UNDO: Error during undo operation: {e}")

            # Show error message
            if hasattr(self.main_window, "status_manager"):
                self.main_window.status_manager.set_file_operation_status(
                    "Undo operation failed", success=False, auto_reset=True
                )

    def redo_metadata_operation(self) -> None:
        """
        Redo the last undone metadata operation triggered by Ctrl+Shift+Z shortcut.
        """
        logger.info("[MainWindow] REDO: Ctrl+Shift+Z key pressed")

        try:
            # Get the metadata command manager
            from oncutf.core.metadata_command_manager import get_metadata_command_manager

            command_manager = get_metadata_command_manager()

            if command_manager.redo():
                logger.info("[MainWindow] REDO: Operation redone successfully")

                # Show status message
                if hasattr(self.main_window, "status_manager"):
                    description = command_manager.get_redo_description()
                    if description:
                        self.main_window.status_manager.set_file_operation_status(
                            f"Redone: {description}", success=True, auto_reset=True
                        )
                    else:
                        self.main_window.status_manager.set_file_operation_status(
                            "Operation redone", success=True, auto_reset=True
                        )
            else:
                logger.info("[MainWindow] REDO: No operations to redo")

                # Show status message
                if hasattr(self.main_window, "status_manager"):
                    self.main_window.status_manager.set_file_operation_status(
                        "No operations to redo", success=False, auto_reset=True
                    )

        except Exception as e:
            logger.error(f"[MainWindow] REDO: Error during redo operation: {e}")

            # Show error message
            if hasattr(self.main_window, "status_manager"):
                self.main_window.status_manager.set_file_operation_status(
                    "Redo operation failed", success=False, auto_reset=True
                )

    def show_history_dialog(self) -> None:
        """
        Show the command history dialog triggered by Ctrl+Shift+Z shortcut.
        """
        logger.info("[MainWindow] HISTORY: Ctrl+Shift+Z key pressed")

        try:
            # Show the metadata history dialog
            from oncutf.ui.widgets.metadata_history_dialog import show_metadata_history_dialog

            show_metadata_history_dialog(self.main_window)

            logger.info("[MainWindow] HISTORY: History dialog shown successfully")

        except Exception as e:
            logger.error(f"[MainWindow] HISTORY: Error showing history dialog: {e}")

            # Show error message
            if hasattr(self.main_window, "status_manager"):
                self.main_window.status_manager.set_file_operation_status(
                    "Failed to show history dialog", success=False, auto_reset=True
                )

    def show_rename_history_dialog(self) -> None:
        """
        Show the rename history dialog.
        """
        logger.info("[MainWindow] RENAME_HISTORY: Showing rename history dialog")

        try:
            # Show the rename history dialog
            from oncutf.ui.widgets.rename_history_dialog import show_rename_history_dialog

            show_rename_history_dialog(self.main_window)

            logger.info("[MainWindow] RENAME_HISTORY: Rename history dialog shown successfully")

        except Exception as e:
            logger.error(f"[MainWindow] RENAME_HISTORY: Error showing rename history dialog: {e}")

            # Show error message
            if hasattr(self.main_window, "status_manager"):
                self.main_window.status_manager.set_file_operation_status(
                    "Failed to show rename history dialog", success=False, auto_reset=True
                )

    def show_results_hash_list(self) -> None:
        """
        Show the results hash list dialog triggered by Ctrl+L shortcut.

        Requirements:
        - Files must be selected
        - At least one selected file must have a hash
        """
        logger.info("[MainWindow] RESULTS_HASH_LIST: Ctrl+L key pressed")

        try:
            # Check if there are any files loaded
            if not self.main_window.file_model or not self.main_window.file_model.files:
                logger.info("[MainWindow] RESULTS_HASH_LIST: No files loaded")
                if hasattr(self.main_window, "status_manager"):
                    self.main_window.status_manager.set_selection_status(
                        "No files loaded", selected_count=0, total_count=0, auto_reset=True
                    )
                return

            # Get selected files (not all files)
            selected_files = self.main_window.get_selected_files_ordered() if hasattr(self.main_window, 'get_selected_files_ordered') else []

            if not selected_files:
                logger.info("[MainWindow] RESULTS_HASH_LIST: No files selected")
                if hasattr(self.main_window, "status_manager"):
                    self.main_window.status_manager.set_selection_status(
                        "No files selected", selected_count=0, total_count=len(self.main_window.file_model.files), auto_reset=True
                    )
                return

            hash_cache = getattr(self.main_window, "hash_cache", None)

            if not hash_cache:
                logger.warning("[MainWindow] RESULTS_HASH_LIST: No hash cache available")
                if hasattr(self.main_window, "status_manager"):
                    self.main_window.status_manager.set_file_operation_status(
                        "Hash cache not available", success=False, auto_reset=True
                    )
                return

            # Check which selected files have hashes
            selected_file_paths = [f.full_path for f in selected_files]
            files_with_hash_paths = hash_cache.get_files_with_hash_batch(selected_file_paths, "CRC32")

            if not files_with_hash_paths:
                logger.info(f"[MainWindow] RESULTS_HASH_LIST: No hashes found for any of {len(selected_files)} selected files")
                if hasattr(self.main_window, "status_manager"):
                    self.main_window.status_manager.set_file_operation_status(
                        f"No hashes in {len(selected_files)} selected file(s)", success=False, auto_reset=True
                    )
                return

            # Build hash results dictionary (only for selected files with hashes)
            hash_results = {}
            for file_path in files_with_hash_paths:
                hash_value = hash_cache.get_hash(file_path, "CRC32")
                if hash_value:
                    # Get filename from path
                    file_name = os.path.basename(file_path)
                    hash_results[file_name] = hash_value

            if not hash_results:
                logger.info("[MainWindow] RESULTS_HASH_LIST: Hash data retrieved but empty")
                if hasattr(self.main_window, "status_manager"):
                    self.main_window.status_manager.set_file_operation_status(
                        "No hash data available", success=False, auto_reset=True
                    )
                return

            # Prepare dialog title with selection info
            total_selected = len(selected_files)
            files_with_hash_count = len(hash_results)

            if files_with_hash_count == total_selected:
                # All selected files have hashes
                dialog_title = f"Hash Results - {files_with_hash_count} file(s)"
            else:
                # Only some selected files have hashes
                dialog_title = f"Hash Results - {files_with_hash_count} of {total_selected} selected file(s)"

            # Get or create the results table dialog with hash data
            from oncutf.ui.widgets.results_table_dialog import ResultsTableDialog

            if not hasattr(self.main_window, "results_dialog") or self.main_window.results_dialog is None:
                self.main_window.results_dialog = ResultsTableDialog(
                    self.main_window,
                    title=dialog_title,
                    left_header="Filename",
                    right_header="CRC32 Hash",
                    data=hash_results,
                    config_key="results_hash_list"
                )
            else:
                # Update existing dialog with new data
                self.main_window.results_dialog.data = hash_results
                self.main_window.results_dialog.model.set_data(hash_results)
                self.main_window.results_dialog.title_label.setText(f"{files_with_hash_count} items")
                self.main_window.results_dialog.setWindowTitle(dialog_title)

            # Show the dialog
            self.main_window.results_dialog.show()
            self.main_window.results_dialog.raise_()
            self.main_window.results_dialog.activateWindow()

            logger.info(f"[MainWindow] RESULTS_HASH_LIST: Results hash list dialog shown successfully with {len(hash_results)} hashes from {len(selected_files)} selected files")

        except Exception as e:
            logger.error(f"[MainWindow] RESULTS_HASH_LIST: Error showing results dialog: {e}")

            # Show error message
            if hasattr(self.main_window, "status_manager"):
                self.main_window.status_manager.set_file_operation_status(
                    "Failed to show results dialog", success=False, auto_reset=True
                )

    def get_shortcut_status(self) -> dict:
        """
        Get current shortcut and initialization status.

        Returns:
            Dictionary with status information
        """
        # Get command manager status
        command_status = {}
        try:
            from oncutf.core.metadata_command_manager import get_metadata_command_manager

            command_manager = get_metadata_command_manager()
            command_status = {
                "can_undo": command_manager.can_undo(),
                "can_redo": command_manager.can_redo(),
                "undo_description": command_manager.get_undo_description(),
                "redo_description": command_manager.get_redo_description(),
            }
        except Exception as e:
            logger.warning(f"[ShortcutManager] Error getting command status: {e}")
            command_status = {
                "can_undo": False,
                "can_redo": False,
                "undo_description": None,
                "redo_description": None,
            }

        return {
            "has_files": len(self.main_window.file_model.files) > 0,
            "current_folder": self.main_window.current_folder_path,
            "force_extended_metadata": self.main_window.force_extended_metadata,
            **command_status,
        }
