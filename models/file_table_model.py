'''
file_table_model.py

Author: Michael Economou
Date: 2025-05-01

This module defines the FileTableModel class, which is a PyQt5 QAbstractTableModel
for managing and displaying a list of FileItem objects in a QTableView. The model
supports functionalities such as row selection (blue highlighting), sorting by different
columns, and updating previews based on user interactions. It emits signals to
notify changes in sorting and interacts with a parent window for UI updates.

Classes:
    FileTableModel: A table model for displaying and managing file entries.
'''

from datetime import datetime
from PyQt5.QtCore import (
    QAbstractTableModel,
    QItemSelection,
    QItemSelectionModel,
    QItemSelectionRange,
    QModelIndex,
    Qt,
    QVariant,
    pyqtSignal,
)
from PyQt5.QtGui import QColor, QIcon

from core.application_context import get_app_context
from models.file_item import FileItem
from utils.icons_loader import load_metadata_icons

# initialize logger
from utils.logger_factory import get_cached_logger
from utils.metadata_cache import MetadataEntry

logger = get_cached_logger(__name__)


class FileTableModel(QAbstractTableModel):
    """
    Table model for displaying and managing a list of FileItem objects
    in a QTableView. Supports row selection (blue highlighting), sorting, and preview updates.
    """
    sort_changed = pyqtSignal()  # Emitted when sort() is called

    def __init__(self, parent_window=None):
        super().__init__()
        self.files: list[FileItem] = []  # List of file entries
        self.parent_window = parent_window  # Needed for triggering updates
        self.metadata_icons = load_metadata_icons()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.files) if self.files else 1

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 5  # Info, Filename, Filesize, Type, Modified

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> QVariant:
        if not index.isValid():
            return QVariant()

        row = index.row()
        col = index.column()

        if not self.files:
            if role == Qt.DisplayRole and col == 1:
                return ""
            if role == Qt.TextAlignmentRole:
                return Qt.AlignCenter
            return QVariant()

        file = self.files[row]

        if role == Qt.BackgroundRole:
            status = getattr(file, "status", None)
            if status == "conflict":
                return QColor("#662222")
            elif status == "duplicate":
                return QColor("#444400")
            elif status == "valid":
                return QColor("#223344")
            return QVariant()

        if role == Qt.DisplayRole:
            if col == 0:
                return " "
            elif col == 1:
                return file.filename
            elif col == 2:
                return file.get_human_readable_size()  # assumes method exists
            elif col == 3:
                return file.extension
            elif col == 4:
                # Format the datetime for better display
                if isinstance(file.modified, datetime):
                    return file.modified.strftime("%Y-%m-%d %H:%M:%S")
                return str(file.modified)

        if role == Qt.ToolTipRole and col == 1:
            entry = self.parent_window.metadata_cache.get_entry(file.full_path) if self.parent_window else None
            if entry and entry.data:
                metadata_count = len(entry.data)
                if entry.is_extended:
                    return f"Extended Metadata Loaded: {metadata_count} values"
                else:
                    return f"Metadata loaded: {metadata_count} values"
            else:
                return "Metadata not loaded"

        if role == Qt.DecorationRole and index.column() == 0:
            entry = self.parent_window.metadata_cache.get_entry(file.full_path) if self.parent_window else None
            if entry:
                # Check if metadata has been modified
                if hasattr(entry, 'modified') and entry.modified:
                    return QIcon(self.metadata_icons.get("modified"))
                elif entry.is_extended:
                    return QIcon(self.metadata_icons.get("extended"))
                return QIcon(self.metadata_icons.get("loaded"))

        if col == 0 and role == Qt.UserRole:
            entry = self.parent_window.metadata_cache.get_entry(file.full_path) if self.parent_window else None
            if isinstance(entry, MetadataEntry):
                return 'extended' if entry.is_extended else 'loaded'
            return 'missing'

        elif role == Qt.CheckStateRole and col == 0:
            return QVariant()

        elif role == Qt.TextAlignmentRole:
            if col == 0:
                return Qt.AlignVCenter | Qt.AlignCenter
            elif col == 2:
                return Qt.AlignVCenter | Qt.AlignRight
            return Qt.AlignVCenter | Qt.AlignLeft

        return QVariant()

    def setData(self, index: QModelIndex, value, role: int = Qt.EditRole) -> bool:
        if not index.isValid() or not self.files:
            return False

        row = index.row()
        col = index.column()
        file = self.files[row]

        if role == Qt.CheckStateRole and col == 0:
            new_checked = (value == Qt.Checked)
            if file.checked == new_checked:
                return False  # Don't do anything if it didn't change
            file.checked = new_checked

            self.dataChanged.emit(index, index, [Qt.CheckStateRole])

            # Try to update UI through ApplicationContext, fallback to parent_window
            try:
                get_app_context()
                # For now, we still need to access parent window for UI updates
                # This will be improved when we migrate UI update handling to context
                # Find parent window by traversing up the widget hierarchy
                import sys
                if hasattr(sys, '_getframe'):
                    # Try to get parent window from current widget hierarchy
                    # This is a transitional approach
                    pass

                # Use legacy approach for now until we fully migrate UI updates
                if self.parent_window:
                    self.parent_window.header.update_state(self.files)
                    self.parent_window.update_files_label()
                    self.parent_window.request_preview_update()
            except RuntimeError:
                # ApplicationContext not ready yet, use legacy approach
                if self.parent_window:
                    self.parent_window.header.update_state(self.files)
                    self.parent_window.update_files_label()
                    self.parent_window.request_preview_update()

            return True

        return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid() or not self.files:
            return Qt.NoItemFlags
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            headers = ["", "Filename", "Size", "Type", "Modified"]
            if 0 <= section < len(headers):
                return headers[section]
        return super().headerData(section, orientation, role)

    def sort(self, column: int, order: Qt.SortOrder = Qt.AscendingOrder) -> None:
        if not self.files:
            return

        # Try to get selection model from ApplicationContext, fallback to parent_window
        selection_model = None
        try:
            get_app_context()
            # For now, we still need to access parent window for selection model
            # This will be improved when we migrate selection handling to context
            if self.parent_window:
                selection_model = self.parent_window.file_table_view.selectionModel()
        except RuntimeError:
            # ApplicationContext not ready yet, use legacy approach
            if self.parent_window:
                selection_model = self.parent_window.file_table_view.selectionModel()

        if not selection_model:
            return

        selected_items = [self.files[i.row()] for i in selection_model.selectedRows()]

        reverse = (order == Qt.DescendingOrder)

        if column == 1:
            self.files.sort(key=lambda f: f.filename.lower(), reverse=reverse)
        elif column == 2:
            self.files.sort(key=lambda f: f.size if hasattr(f, 'size') else 0, reverse=reverse)
        elif column == 3:
            self.files.sort(key=lambda f: f.extension.lower(), reverse=reverse)
        elif column == 4:
            self.files.sort(key=lambda f: f.modified, reverse=reverse)

        self.layoutChanged.emit()
        self.sort_changed.emit()

        # Store current sort state in parent window for post-rename consistency
        if self.parent_window:
            self.parent_window.current_sort_column = column
            self.parent_window.current_sort_order = order
            logger.debug(f"[Model] Stored sort state: column={column}, order={order}", extra={"dev_only": True})

        selection_model.clearSelection()
        selection = QItemSelection()

        for row, file in enumerate(self.files):
            if file in selected_items:
                top_left = self.index(row, 0)
                bottom_right = self.index(row, self.columnCount() - 1)
                selection_range = QItemSelectionRange(top_left, bottom_right)
                selection.append(selection_range)
                logger.debug(f"[Model] dataChanged.emit() for row {row}")

        selection_model.select(selection, QItemSelectionModel.Select)

        # Try to refresh metadata tree through ApplicationContext, fallback to parent_window
        try:
            get_app_context()
            # For now, we still need to access parent window for metadata tree
            # This will be improved when we migrate metadata tree handling to context
            if self.parent_window:
                self.parent_window.metadata_tree_view.refresh_metadata_from_selection()
        except RuntimeError:
            # ApplicationContext not ready yet, use legacy approach
            if self.parent_window:
                self.parent_window.metadata_tree_view.refresh_metadata_from_selection()

    def clear(self):
        self.beginResetModel()
        self.files = []
        self.endResetModel()

    def set_files(self, files: list[FileItem]) -> None:
        self.beginResetModel()
        self.files = files
        self.endResetModel()

        for f in files:
            f.checked = False  # force clear

    def add_files(self, new_files: list[FileItem]) -> None:
        """
        Adds new files to the existing file list and updates the model.

        Args:
            new_files (list[FileItem]): List of new FileItem objects to add
        """
        if not new_files:
            return

        # Start row insertion
        start_row = len(self.files)
        self.beginInsertRows(QModelIndex(), start_row, start_row + len(new_files) - 1)

        # Add the new files to our list
        self.files.extend(new_files)

        # End row insertion
        self.endInsertRows()

        # Emit signal to update any views
        self.layoutChanged.emit()

        # Optionally notify parent window
        try:
            get_app_context()
            # For now, we still need to access parent window for UI updates
            # This will be improved when we migrate UI update handling to context
            if self.parent_window:
                self.parent_window.update_files_label()
        except RuntimeError:
            # ApplicationContext not ready yet, use legacy approach
            if self.parent_window:
                self.parent_window.update_files_label()
