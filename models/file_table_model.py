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
from PyQt5.QtCore import (
    Qt, QAbstractTableModel, QModelIndex, QVariant, pyqtSignal,
    QItemSelection, QItemSelectionRange, QItemSelectionModel
)
from PyQt5.QtGui import QColor
from models.file_item import FileItem
from utils.metadata_cache import MetadataEntry


# initialize logger
from utils.logger_helper import get_logger
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

        if role == Qt.BackgroundRole:
            file = self.files[index.row()]

            # Future extension: status-based row coloring
            status = getattr(file, "status", None)  # Optional attribute

            if status == "conflict":
                return QColor("#662222")
            elif status == "duplicate":
                return QColor("#444400")
            elif status == "valid":
                return QColor("#223344")

            # Default: respect QSS alternating background
            return QVariant()

        if role == Qt.DisplayRole:
            if col == 0:
                return " "
            if col == 1:
                return file.filename
            elif col == 2:
                return file.extension
            elif col == 3:
                return file.modified

        if role == Qt.ToolTipRole and index.column() == 1:
            file = self.files[index.row()]
            if file.full_path in self.parent_window.metadata_loaded_paths:
                return "Metadata loaded for this file"
            else:
                return "Metadata not loaded"

        if index.column() == 0 and role == Qt.UserRole:
            file = self.files[index.row()]
            entry = self.parent_window.metadata_cache.get_entry(file.full_path) if self.parent_window else None
            if isinstance(entry, MetadataEntry):
                return 'extended' if entry.is_extended else 'loaded'
            return 'missing'

        elif role == Qt.CheckStateRole and col == 0:
            return  QVariant()

        elif role == Qt.TextAlignmentRole:
            if col == 0:
                return Qt.AligVCenter | Qt.AlignCenter
            return Qt.AlignVCenter | Qt.AlignLeft

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
        Sorts the file list by the specified column and re-selects previously
        selected FileItems to preserve selection across sorting.
        """
        if not self.files:
            return

        # --- Preserve selection by object reference ---
        selection_model = self.parent_window.file_table_view.selectionModel()
        selected_items = [self.files[i.row()] for i in selection_model.selectedRows()]

        reverse = (order == Qt.DescendingOrder)

        if column == 1:
            self.files.sort(key=lambda f: f.filename.lower(), reverse=reverse)
        elif column == 2:
            self.files.sort(key=lambda f: f.extension.lower(), reverse=reverse)
        elif column == 3:
            self.files.sort(key=lambda f: f.modified, reverse=reverse)

        self.layoutChanged.emit()
        self.sort_changed.emit()

        # --- Restore selection after sort ---
        selection_model.clearSelection()
        selection = QItemSelection()

        for row, file in enumerate(self.files):
            if file in selected_items:
                top_left = self.index(row, 0)
                bottom_right = self.index(row, self.columnCount() - 1)
                selection_range = QItemSelectionRange(top_left, bottom_right)
                selection.append(selection_range)

        selection_model.select(selection, QItemSelectionModel.Select)

        self.parent_window.check_selection_and_show_metadata()

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
