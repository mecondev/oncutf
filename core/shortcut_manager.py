"""
Module: shortcut_manager.py

Author: Michael Economou
Date: 2025-01-15

ShortcutManager - Handles keyboard shortcuts
This manager centralizes keyboard shortcut handling including:
- Clear file table shortcut (Shift+Escape)
- Undo/Redo shortcuts (Ctrl+Z, Ctrl+Shift+Z)
- History dialog shortcut (Ctrl+H)
- Future keyboard shortcuts can be added here
"""
from typing import TYPE_CHECKING

from core.pyqt_imports import Qt
from utils.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from main_window import MainWindow

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

    def __init__(self, main_window: 'MainWindow'):
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
            if hasattr(self.main_window, 'status_manager'):
                self.main_window.status_manager.set_selection_status(
                    "No files to clear",
                    selected_count=0,
                    total_count=0,
                    auto_reset=True
                )
            return

        # Clear the file table
        self.main_window.clear_file_table("Press Escape to clear, or drag folders here")
        self.main_window.current_folder_path = None  # Reset current folder
        self.main_window.current_folder_is_recursive = False  # Reset recursive state
        self.main_window.current_sort_column = 1  # Reset to filename column
        self.main_window.current_sort_order = Qt.AscendingOrder  # Reset to ascending

        if hasattr(self.main_window, 'status_manager'):
            self.main_window.status_manager.set_file_operation_status(
                "File table cleared",
                success=True,
                auto_reset=True
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
            from core.metadata_command_manager import get_metadata_command_manager
            command_manager = get_metadata_command_manager()

            if command_manager.undo():
                logger.info("[MainWindow] UNDO: Operation undone successfully")

                # Show status message
                if hasattr(self.main_window, 'status_manager'):
                    description = command_manager.get_undo_description()
                    if description:
                        self.main_window.status_manager.set_file_operation_status(
                            f"Undone: {description}",
                            success=True,
                            auto_reset=True
                        )
                    else:
                        self.main_window.status_manager.set_file_operation_status(
                            "Operation undone",
                            success=True,
                            auto_reset=True
                        )
            else:
                logger.info("[MainWindow] UNDO: No operations to undo")

                # Show status message
                if hasattr(self.main_window, 'status_manager'):
                    self.main_window.status_manager.set_file_operation_status(
                        "No operations to undo",
                        success=False,
                        auto_reset=True
                    )

        except Exception as e:
            logger.error(f"[MainWindow] UNDO: Error during undo operation: {e}")

            # Show error message
            if hasattr(self.main_window, 'status_manager'):
                self.main_window.status_manager.set_file_operation_status(
                    "Undo operation failed",
                    success=False,
                    auto_reset=True
                )

    def redo_metadata_operation(self) -> None:
        """
        Redo the last undone metadata operation triggered by Ctrl+Shift+Z shortcut.
        """
        logger.info("[MainWindow] REDO: Ctrl+Shift+Z key pressed")

        try:
            # Get the metadata command manager
            from core.metadata_command_manager import get_metadata_command_manager
            command_manager = get_metadata_command_manager()

            if command_manager.redo():
                logger.info("[MainWindow] REDO: Operation redone successfully")

                # Show status message
                if hasattr(self.main_window, 'status_manager'):
                    description = command_manager.get_redo_description()
                    if description:
                        self.main_window.status_manager.set_file_operation_status(
                            f"Redone: {description}",
                            success=True,
                            auto_reset=True
                        )
                    else:
                        self.main_window.status_manager.set_file_operation_status(
                            "Operation redone",
                            success=True,
                            auto_reset=True
                        )
            else:
                logger.info("[MainWindow] REDO: No operations to redo")

                # Show status message
                if hasattr(self.main_window, 'status_manager'):
                    self.main_window.status_manager.set_file_operation_status(
                        "No operations to redo",
                        success=False,
                        auto_reset=True
                    )

        except Exception as e:
            logger.error(f"[MainWindow] REDO: Error during redo operation: {e}")

            # Show error message
            if hasattr(self.main_window, 'status_manager'):
                self.main_window.status_manager.set_file_operation_status(
                    "Redo operation failed",
                    success=False,
                    auto_reset=True
                )

    def show_history_dialog(self) -> None:
        """
        Show the command history dialog triggered by Ctrl+H shortcut.
        """
        logger.info("[MainWindow] HISTORY: Ctrl+H key pressed")

        try:
            # Show the metadata history dialog
            from widgets.metadata_history_dialog import show_metadata_history_dialog
            show_metadata_history_dialog(self.main_window)

            logger.info("[MainWindow] HISTORY: History dialog shown successfully")

        except Exception as e:
            logger.error(f"[MainWindow] HISTORY: Error showing history dialog: {e}")

            # Show error message
            if hasattr(self.main_window, 'status_manager'):
                self.main_window.status_manager.set_file_operation_status(
                    "Failed to show history dialog",
                    success=False,
                    auto_reset=True
                )

    def show_rename_history_dialog(self) -> None:
        """
        Show the rename history dialog.
        """
        logger.info("[MainWindow] RENAME_HISTORY: Showing rename history dialog")

        try:
            # Show the rename history dialog
            from widgets.rename_history_dialog import show_rename_history_dialog
            show_rename_history_dialog(self.main_window)

            logger.info("[MainWindow] RENAME_HISTORY: Rename history dialog shown successfully")

        except Exception as e:
            logger.error(f"[MainWindow] RENAME_HISTORY: Error showing rename history dialog: {e}")

            # Show error message
            if hasattr(self.main_window, 'status_manager'):
                self.main_window.status_manager.set_file_operation_status(
                    "Failed to show rename history dialog",
                    success=False,
                    auto_reset=True
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
            from core.metadata_command_manager import get_metadata_command_manager
            command_manager = get_metadata_command_manager()
            command_status = {
                "can_undo": command_manager.can_undo(),
                "can_redo": command_manager.can_redo(),
                "undo_description": command_manager.get_undo_description(),
                "redo_description": command_manager.get_redo_description()
            }
        except Exception as e:
            logger.warning(f"[ShortcutManager] Error getting command status: {e}")
            command_status = {
                "can_undo": False,
                "can_redo": False,
                "undo_description": None,
                "redo_description": None
            }

        return {
            "has_files": len(self.main_window.file_model.files) > 0,
            "current_folder": self.main_window.current_folder_path,
            "skip_metadata_mode": self.main_window.skip_metadata_mode,
            "force_extended_metadata": self.main_window.force_extended_metadata,
            **command_status
        }
