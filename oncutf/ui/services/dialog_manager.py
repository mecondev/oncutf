"""Module: dialog_manager.py

Author: Michael Economou
Date: 2025-05-31

dialog_manager.py
Manages all dialog and validation operations for the application.
Centralizes dialog creation, validation logic, and user confirmations.
"""

import os

from oncutf.core.pyqt_imports import QApplication, QFileDialog, QWidget
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class DialogManager:
    """Manages all dialog and validation operations.

    Features:
    - Centralized dialog creation
    - Validation logic
    - User confirmations
    - Window centering
    """

    _instance = None

    def __new__(cls):
        """Ensure only one DialogManager instance exists (singleton pattern)."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the dialog manager (only once due to singleton pattern)."""
        if self._initialized:
            return

        self._initialized = True
        logger.debug("[DialogManager] Initialized", extra={"dev_only": True})

    def confirm_large_folder(self, folder_path: str, file_count: int) -> bool:
        """Show confirmation dialog for large folders"""
        from oncutf.ui.dialogs.custom_message_dialog import CustomMessageDialog

        return CustomMessageDialog.question(
            None,
            "Large Folder Detected",
            f"Folder contains {file_count} files.\n\nThis may take a while to process.\n\n{folder_path}",
            yes_text="Continue",
            no_text="Cancel",
        )

    def check_large_files(self, files: list[str], max_size_mb: int = 100) -> tuple[bool, list[str]]:
        """Check for large files and return list of oversized files"""
        oversized = []
        for file in files:
            try:
                size_mb = os.path.getsize(file) / (1024 * 1024)
                if size_mb > max_size_mb:
                    oversized.append(file)
            except OSError:
                continue

        return len(oversized) > 0, oversized

    def confirm_large_files(self, files, max_size_mb: int = 100) -> bool:
        """Show confirmation dialog for large files"""
        if not files:
            return True

        # First, check which files are actually large
        large_files = []
        for f in files:
            size_mb = 0
            if hasattr(f, "size") and f.size > 0:  # FileItem object with size
                size_mb = f.size / (1024 * 1024)
            elif hasattr(f, "full_path"):  # FileItem object, check file system
                try:
                    size_mb = os.path.getsize(f.full_path) / (1024 * 1024)
                except OSError:
                    continue
            elif isinstance(f, str):  # String path
                try:
                    size_mb = os.path.getsize(f) / (1024 * 1024)
                except OSError:
                    continue

            if size_mb > max_size_mb:
                large_files.append(f)

        # If no files are actually large, don't show dialog
        if not large_files:
            return True

        from oncutf.ui.dialogs.custom_message_dialog import CustomMessageDialog

        # Handle both FileItem objects and string paths
        file_names = []
        for f in large_files[:5]:
            if hasattr(f, "filename"):  # FileItem object
                file_names.append(f.filename)
            else:  # String path
                file_names.append(os.path.basename(f))

        file_list = "\n".join(f"- {name}" for name in file_names)
        if len(large_files) > 5:
            file_list += f"\n... and {len(large_files) - 5} more"

        message = f"Found {len(large_files)} files larger than {max_size_mb}MB:\n\n{file_list}\n\nProcessing may take longer."

        return CustomMessageDialog.question(
            None, "Large Files Detected", message, yes_text="Continue", no_text="Cancel"
        )

    def prompt_file_conflict(self, old_name: str, new_name: str) -> bool:  # noqa: ARG002
        """Show confirmation dialog for file rename conflicts"""
        from oncutf.ui.dialogs.custom_message_dialog import CustomMessageDialog

        return CustomMessageDialog.question(
            None,
            "File Conflict",
            f"File already exists:\n{new_name}\n\nDo you want to overwrite it?",
            yes_text="Overwrite",
            no_text="Cancel",
        )

    def confirm_unsaved_changes(self, parent: QWidget = None) -> str:
        """Show confirmation dialog for unsaved metadata changes with three options.

        Returns:
            str: One of 'save_and_close', 'close_without_saving', 'cancel'

        """
        from oncutf.ui.dialogs.custom_message_dialog import CustomMessageDialog

        return CustomMessageDialog.unsaved_changes(parent)

    def center_window(self, window: QWidget):
        """Center a window on the screen using multiscreen-aware positioning"""
        if not window:
            return

        from oncutf.utils.ui.multiscreen_helper import center_dialog_on_screen

        center_dialog_on_screen(window)

    def should_skip_folder_reload(self, folder_path: str) -> bool:
        """Check if folder reload should be skipped"""
        if not folder_path or not os.path.exists(folder_path):
            return True

        # Skip if not a directory
        if not os.path.isdir(folder_path):
            return True

        # Skip if empty
        try:
            if not os.listdir(folder_path):
                return True
        except OSError:
            return True

        return False

    def cleanup(self):
        """Close all open dialogs and clean up resources."""
        # Close any open message dialogs
        for widget in QApplication.topLevelWidgets():
            if hasattr(widget, "close") and "Dialog" in widget.__class__.__name__:
                widget.close()

        # Close any open file dialogs
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, QFileDialog):
                widget.close()

        # Process any pending events
        QApplication.processEvents()
