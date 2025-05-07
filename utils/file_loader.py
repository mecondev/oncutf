"""
Module: file_loader.py

Author: Michael Economou
Date: 2025-05-01

This utility module handles the logic for selecting and loading files
from one or more folders into the application's data model.

It supports recursive directory scanning, file type filtering, and
preparation of file data for use in the ReNExif renaming system.
"""


import os
import glob
import datetime
from typing import TYPE_CHECKING

from PyQt5.QtWidgets import QFileDialog
from models.file_item import FileItem
from config import ALLOWED_EXTENSIONS

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QTreeView, QFileSystemModel
    from PyQt5.QtCore import QModelIndex
    from widgets.main_window import MainWindow  # forward reference


class FileLoaderMixin:
    """
    Mixin class that provides reusable logic for browsing and loading files.
    Intended to be inherited by MainWindow.
    """

    def handle_select(self: 'MainWindow') -> None:
        """
        Loads files from the folder currently selected in the tree view.
        """
        index = self.tree_view.currentIndex()
        if not index.isValid():
            return

        folder_path = self.dir_model.filePath(index)
        self.current_folder_path = folder_path
        self.load_files_from_folder(folder_path)

    def handle_browse(self: 'MainWindow') -> None:
        """
        Opens a folder selection dialog and loads files from the chosen folder.
        Also updates the tree view to match the selection.
        """
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder", "/")

        if folder_path:
            self.current_folder_path = folder_path
            self.load_files_from_folder(folder_path)

            index = self.dir_model.index(folder_path)
            if index.isValid():
                self.tree_view.setCurrentIndex(index)
                self.tree_view.scrollTo(index)

    def load_files_from_folder(self: 'MainWindow', folder_path: str) -> None:
        """
        Loads supported files from the given folder into the model.

        Args:
            folder_path (str): The absolute path of the selected folder.
        """
        all_files = glob.glob(os.path.join(folder_path, "*"))

        self.model.beginResetModel()
        self.model.files.clear()
        self.model.folder_path = folder_path

        for file_path in sorted(all_files):
            ext = os.path.splitext(file_path)[1][1:].lower()
            if ext in ALLOWED_EXTENSIONS:
                filename = os.path.basename(file_path)
                modified = datetime.datetime.fromtimestamp(
                    os.path.getmtime(file_path)
                ).strftime("%Y-%m-%d %H:%M:%S")
                self.model.files.append(FileItem(filename, ext, modified))

        self.model.endResetModel()

        # Sync state
        self.header.update_state(self.model.files)
        self.update_files_label()
        self.generate_preview_names()

