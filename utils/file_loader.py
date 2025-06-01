"""
utils/file_loader.py

Author: Michael Economou
Date: 2025-05-01

This utility module handles the logic for selecting and loading files
from one or more folders into the application's data model.

It supports recursive directory scanning, file type filtering, and
preparation of file data for use in the oncutf renaming system.
"""

import os
import glob
import datetime
from typing import TYPE_CHECKING

from PyQt5.QtWidgets import QFileDialog, QApplication
from PyQt5.QtCore import Qt
from models.file_item import FileItem
from config import ALLOWED_EXTENSIONS

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QTreeView, QFileSystemModel
    from PyQt5.QtCore import QModelIndex
    from widgets.main_window import MainWindow  # forward reference

# Initialize Logger
from utils.logger_helper import get_logger
logger = get_logger(__name__)


class FileLoaderMixin:
    """
    Mixin class that provides reusable logic for browsing and loading files.
    Intended to be inherited by MainWindow.
    """

    def handle_select(self: 'MainWindow') -> None:
        """
        Loads files from the folder currently selected in the tree view.
        """
        index = self.folder_tree.currentIndex()
        if not index.isValid():
            return

        folder_path = self.dir_model.filePath(index)
        self.current_folder_path = folder_path
        self.load_files_from_folder(folder_path)

    def handle_browse(self):
        """
        Opens a folder selection dialog and loads files from the selected folder.

        If the user holds the Ctrl key while selecting, metadata scan is skipped.
        """
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder", "/")

        if folder_path:
            # Detect modifier keys
            modifiers = QApplication.keyboardModifiers()
            skip_metadata = modifiers & Qt.ControlModifier

            # Optionally support ALT in the future
            # skip_metadata = modifiers & Qt.AltModifier

            logger.info(f"Folder selected: {folder_path}")
            logger.info(f"Ctrl pressed? {bool(skip_metadata)}")

            # Update folder path and load files
            self.load_files_from_folder(folder_path, skip_metadata=skip_metadata)

            # Sync with tree view if valid
            index = self.dir_model.index(folder_path)
            if index.isValid():
                self.folder_tree.setCurrentIndex(index)
                self.folder_tree.scrollTo(index)
