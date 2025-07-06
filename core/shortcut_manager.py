"""
Module: shortcut_manager.py

Author: Michael Economou
Date: 2025-05-31

ShortcutManager - Handles keyboard shortcuts
This manager centralizes keyboard shortcut handling including:
- Clear file table shortcut (Ctrl+Escape)
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
        Clear file table triggered by Ctrl+Escape shortcut.
        """
        logger.info("[MainWindow] CLEAR TABLE: Ctrl+Escape key pressed")

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

    def get_shortcut_status(self) -> dict:
        """
        Get current shortcut and initialization status.

        Returns:
            Dictionary with status information
        """
        return {
            "has_files": len(self.main_window.file_model.files) > 0,
            "current_folder": self.main_window.current_folder_path,
            "skip_metadata_mode": self.main_window.skip_metadata_mode,
            "force_extended_metadata": self.main_window.force_extended_metadata
        }
