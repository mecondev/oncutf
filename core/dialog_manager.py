"""
dialog_manager.py

Author: Michael Economou
Date: 2025-06-05

Manages all dialog and validation operations for the application.
Centralizes dialog creation, validation logic, and user confirmations.
"""

from typing import Optional, Tuple, List
from PyQt5.QtWidgets import (
    QMessageBox,
    QWidget,
    QDialog,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QCheckBox,
    QApplication
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon
import os

from utils.logger_helper import get_logger

logger = get_logger(__name__)


class DialogManager:
    """
    Manages all dialog and validation operations.

    Features:
    - Centralized dialog creation
    - Validation logic
    - User confirmations
    - Window centering
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DialogManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        logger.debug("[DialogManager] Initialized")

    def confirm_large_folder(self, folder_path: str, file_count: int) -> bool:
        """Show confirmation dialog for large folders"""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Large Folder Detected")
        msg.setText(f"Folder contains {file_count} files")
        msg.setInformativeText(f"This may take a while to process.\n\n{folder_path}")
        msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        msg.setDefaultButton(QMessageBox.Ok)

        return msg.exec_() == QMessageBox.Ok

    def check_large_files(self, files: List[str], max_size_mb: int = 100) -> Tuple[bool, List[str]]:
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

        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Large Files Detected")

        # Handle both FileItem objects and string paths
        file_names = []
        for f in files[:5]:
            if hasattr(f, 'filename'):  # FileItem object
                file_names.append(f.filename)
            else:  # String path
                file_names.append(os.path.basename(f))

        file_list = "\n".join(f"- {name}" for name in file_names)
        if len(files) > 5:
            file_list += f"\n... and {len(files) - 5} more"

        msg.setText(f"Found {len(files)} files larger than {max_size_mb}MB")
        msg.setInformativeText(f"Large files:\n{file_list}\n\nProcessing may take longer.")
        msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        msg.setDefaultButton(QMessageBox.Ok)

        return msg.exec_() == QMessageBox.Ok

    def prompt_file_conflict(self, old_name: str, new_name: str) -> bool:
        """Show confirmation dialog for file rename conflicts"""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("File Conflict")
        msg.setText(f"File already exists:\n{new_name}")
        msg.setInformativeText("Do you want to overwrite it?")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)

        return msg.exec_() == QMessageBox.Yes

    def center_window(self, window: QWidget):
        """Center a window on the screen"""
        if not window:
            return

        # Get screen geometry
        screen = QApplication.primaryScreen().geometry()

        # Get window geometry
        window_geometry = window.geometry()

        # Calculate center position
        x = (screen.width() - window_geometry.width()) // 2
        y = (screen.height() - window_geometry.height()) // 2

        # Move window
        window.move(x, y)

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
