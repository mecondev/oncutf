"""
file_table_model.py

This module defines the FileTableModel class, which is a PyQt5 QAbstractTableModel
for managing and displaying a list of FileItem objects in a QTableView. The model
supports functionalities such as checkboxes for selection, sorting by different
columns, and updating previews based on user interactions. It emits signals to
notify changes in sorting and interacts with a parent window for UI updates.

Classes:
    FileTableModel: A table model for displaying and managing file entries.

Author: Michael Economou
Date: 2025-05-01
"""

from typing import Optional
from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex, QVariant, pyqtSignal
from models.file_item import FileItem

# initialize logger
from logger_helper import get_logger
logger = get_logger(__name__)


class FileTableModel(QAbstractTableModel):
    """
    Table model for displaying and managing a list of FileItem objects
    in a QTableView. Supports checkboxes, sorting, and preview updates.
    """
    sort_changed = pyqtSignal()  # Emitted when sort() is called

    def __init__(self, parent_window=None):
        super().__init__()
        self.files: list[FileItem] = []  # List of file entries
        self.parent_window = parent_window  # Needed for triggering updates

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """
        Returns the number of rows. Shows 1 row if empty to display a placeholder.
        """
        return len(self.files) if self.files else 1

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """
        Returns the number of columns (Checkbox, Filename, Filetype, Date).
        """
        return 4

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> QVariant:
        """
        Returns the data for a given index and role.
        Displays placeholder text if file list is empty.
        """
        if not index.isValid():
            return QVariant()

        row = index.row()
        col = index.column()

        if not self.files:
            if role == Qt.DisplayRole and col == 1:
                return "No files loaded"
            if role == Qt.TextAlignmentRole:
                return Qt.AlignCenter
            return QVariant()

        file = self.files[row]

        if role == Qt.DisplayRole:
            if col == 1:
                return file.filename
            elif col == 2:
                return file.filetype
            elif col == 3:
                return file.date

        elif role == Qt.CheckStateRole and col == 0:
            return Qt.Checked if file.checked else Qt.Unchecked

        elif role == Qt.TextAlignmentRole:
            if col == 0:
                return Qt.AlignCenter
            return Qt.AlignLeft

        return QVariant()

    def setData(self, index: QModelIndex, value, role: int = Qt.EditRole) -> bool:
        """
        Called when the user interacts with a checkbox (column 0).
        Updates the `checked` state and triggers UI updates.
        """
        if not index.isValid() or not self.files:
            return False

        row = index.row()
        col = index.column()
        file = self.files[row]

        if role == Qt.CheckStateRole and col == 0:
            file.checked = (value == Qt.Checked)
            self.dataChanged.emit(index, index, [Qt.CheckStateRole])

            # Trigger preview & header checkbox state update
            if self.parent_window:
                self.parent_window.header.update_state(self.files)
                self.parent_window.update_files_label()
                self.parent_window.generate_preview_names()

            return True

        return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        """
        Defines interactivity per column.
        Placeholder row is not selectable or editable.
        """
        if not index.isValid():
            return Qt.NoItemFlags

        if not self.files:
            return Qt.NoItemFlags

        if index.column() == 0:
            return Qt.ItemIsEnabled | Qt.ItemIsUserCheckable
        else:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        """
        Returns header text for each column.
        """
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            headers = ["", "Filename", "Type", "Modified"]
            if 0 <= section < len(headers):
                return headers[section]

        return super().headerData(section, orientation, role)

    def sort(self, column: int, order: Qt.SortOrder = Qt.AscendingOrder) -> None:
        """
        Sorts the file list by the specified column.
        Also triggers preview update.
        """
        if not self.files:
            return

        reverse = (order == Qt.DescendingOrder)

        if column == 1:
            self.files.sort(key=lambda f: f.filename.lower(), reverse=reverse)
        elif column == 2:
            self.files.sort(key=lambda f: f.filetype.lower(), reverse=reverse)
        elif column == 3:
            self.files.sort(key=lambda f: f.date, reverse=reverse)

        self.layoutChanged.emit()
        self.sort_changed.emit()  # Let the MainWindow refresh preview

    def clear(self):
        """
        Clears the file list and refreshes the table.
        """
        self.beginResetModel()
        self.files = []
        self.endResetModel()

    def set_files(self, files: list[FileItem]) -> None:
        """
        Replaces the file list and refreshes the table.
        """
        self.beginResetModel()
        self.files = files
        self.endResetModel()
