'''
file_table_model.py

Author: Michael Economou
Date: 2025-05-01

This module defines the FileTableModel class, which is a custom QAbstractTableModel
for displaying file data in a table view. The model manages file items, supports
sorting, and provides metadata status icons.

Classes:
    FileTableModel: Custom table model for file management.
'''

from datetime import datetime

from core.application_context import get_app_context
from core.persistent_metadata_cache import MetadataEntry
from core.pyqt_imports import (
    QAbstractTableModel,
    QColor,
    QIcon,
    QItemSelection,
    QItemSelectionModel,
    QItemSelectionRange,
    QModelIndex,
    QPainter,
    QPixmap,
    Qt,
    QVariant,
    pyqtSignal,
)
from models.file_item import FileItem
from utils.icons_loader import load_metadata_icons

# initialize logger
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class FileTableModel(QAbstractTableModel):
    """
    Table model for displaying and managing a list of FileItem objects
    in a QTableView. Supports row selection (blue highlighting), sorting, and preview updates.
    Now supports displaying both metadata and hash icons in column 0.
    """
    sort_changed = pyqtSignal()  # Emitted when sort() is called

    def __init__(self, parent_window=None):
        super().__init__()
        self.parent_window = parent_window
        self.files = []
        self._direct_loader = None
        self._cache_helper = None

        # Load icons for metadata status using the correct functions
        self.metadata_icons = load_metadata_icons()

    def _has_hash_cached(self, file_path: str) -> bool:
        """
        Check if a file has a hash stored in the persistent cache.

        Args:
            file_path: Full path to the file

        Returns:
            bool: True if file has a cached hash, False otherwise
        """
        try:
            from core.persistent_hash_cache import get_persistent_hash_cache
            cache = get_persistent_hash_cache()
            return cache.has_hash(file_path)
        except (ImportError, Exception) as e:
            logger.debug(f"[FileTableModel] Could not check hash cache: {e}")
            return False

    def _get_hash_value(self, file_path: str) -> str:
        """
        Get the hash value for a file from the persistent cache.

        Args:
            file_path: Full path to the file

        Returns:
            str: Hash value if found, empty string otherwise
        """
        try:
            from core.persistent_hash_cache import get_persistent_hash_cache
            cache = get_persistent_hash_cache()
            hash_value = cache.get_hash(file_path)
            return hash_value if hash_value else ""
        except (ImportError, Exception) as e:
            logger.debug(f"[FileTableModel] Could not get hash value: {e}")
            return ""

    def _create_combined_icon(self, metadata_status: str, hash_status: str) -> QIcon:
        """
        Create a combined icon showing metadata status (left) and hash status (right).
        Always shows both icons - uses grayout color for missing states.

        Args:
            metadata_status: Status of metadata ('loaded', 'extended', 'modified', 'invalid', 'none')
            hash_status: Status of hash ('hash' for available, 'none' for not available)

        Returns:
            QIcon: Combined icon with metadata and hash status
        """
        # Use the full STATUS_COLUMN width for proper spacing
        from config import FILE_TABLE_COLUMN_WIDTHS
        combined_width = FILE_TABLE_COLUMN_WIDTHS["STATUS_COLUMN"]  # 45px
        combined_height = 16
        combined_pixmap = QPixmap(combined_width, combined_height)
        combined_pixmap.fill(QColor(0, 0, 0, 0))

        painter = QPainter(combined_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Get metadata icon
        metadata_icon = self.metadata_icons.get(metadata_status)
        if metadata_icon:
            # Draw metadata icon on the left (2px from left edge)
            painter.drawPixmap(2, 0, metadata_icon)

        # Get hash icon
        hash_icon = self.metadata_icons.get(hash_status)
        if hash_icon:
            # Draw hash icon on the right (27px from left = 45-16-2 for 2px right margin)
            painter.drawPixmap(27, 0, hash_icon)

        painter.end()
        return QIcon(combined_pixmap)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.files) if self.files else 1

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 5  # Info, Filename, Filesize, Type, Modified

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> QVariant: # type: ignore
        if not index.isValid():
            return QVariant()

        row = index.row()
        col = index.column()

        if not self.files:
            if role == Qt.DisplayRole and col == 1: # type: ignore
                return ""
            if role == Qt.TextAlignmentRole: # type: ignore
                return Qt.AlignHCenter
            return QVariant()

        file = self.files[row]

        if role == Qt.BackgroundRole: # type: ignore
            status = getattr(file, "status", None)
            if status == "conflict":
                return QColor("#662222")
            elif status == "duplicate":
                return QColor("#444400")
            elif status == "valid":
                return QColor("#223344")
            return QVariant()

        if role == Qt.DisplayRole: # type: ignore
            if col == 0:
                return " "
            elif col == 1:
                return str(file.filename)
            elif col == 2:
                return str(file.get_human_readable_size())
            elif col == 3:
                return str(file.extension)
            elif col == 4:
                # Format the datetime for better display
                if isinstance(file.modified, datetime):
                    return file.modified.strftime("%Y-%m-%d %H:%M:%S")
                return str(file.modified)

        if role == Qt.ToolTipRole: # type: ignore
            tooltip_parts = []
            tooltip_parts.append(f"File: {file.filename}")

            # Use the same cache access method as the icon generation
            entry = None
            if self.parent_window and hasattr(self.parent_window, 'metadata_cache'):
                entry = self.parent_window.metadata_cache.get_entry(file.full_path)

            if entry and hasattr(entry, 'data') and entry.data:
                # Filter out internal metadata markers
                real_metadata = {k: v for k, v in entry.data.items() if not k.startswith('__')}
                metadata_count = len(real_metadata)

                if metadata_count > 0:
                    if hasattr(entry, 'is_extended') and entry.is_extended:
                        tooltip_parts.append(f"Extended Metadata: {metadata_count} values")
                    else:
                        tooltip_parts.append(f"Metadata: {metadata_count} values")
                else:
                    tooltip_parts.append("No metadata")
            else:
                tooltip_parts.append("No metadata")

            # Add hash info only if hash exists
            hash_value = self._get_hash_value(file.full_path)
            if hash_value:
                tooltip_parts.append(f"Hash: {hash_value}")

            return "\n".join(tooltip_parts)

        if role == Qt.DecorationRole and col == 0: # type: ignore
            # Use simple cache checking like the old system
            entry = None
            if self.parent_window and hasattr(self.parent_window, 'metadata_cache'):
                entry = self.parent_window.metadata_cache.get_entry(file.full_path)

            # Check if file has hash cached
            has_hash = self._has_hash_cached(file.full_path)

            # Determine metadata status
            metadata_status = "none"  # Default to grayout
            if entry:
                # Check if metadata has been modified
                if hasattr(entry, 'modified') and entry.modified:
                    metadata_status = "modified"
                elif entry.is_extended:
                    metadata_status = "extended"
                else:
                    metadata_status = "loaded"  # This is fast/basic metadata

            # Determine hash status
            hash_status = "hash" if has_hash else "none"

            # Always create combined icon with both statuses
            return self._create_combined_icon(metadata_status, hash_status)

        if col == 0 and role == Qt.UserRole: # type: ignore
            cache_helper = self._cache_helper
            if cache_helper:
                # Create temporary FileItem-like object for cache helper
                class TempFileItem:
                    def __init__(self, path):
                        self.full_path = path

                temp_file_item = TempFileItem(file.full_path)
                entry = cache_helper.get_cache_entry_for_file(temp_file_item)

                if isinstance(entry, MetadataEntry):
                    return 'extended' if entry.is_extended else 'loaded'
            return 'missing'

        elif role == Qt.CheckStateRole and col == 0: # type: ignore
            return QVariant()

        elif role == Qt.TextAlignmentRole: # type: ignore
            if col == 0:
                return Qt.AlignVCenter | Qt.AlignLeft
            elif col == 2:
                return Qt.AlignVCenter | Qt.AlignRight
            return Qt.AlignVCenter | Qt.AlignLeft

        return QVariant()

    def setData(self, index: QModelIndex, value, role: int = Qt.EditRole) -> bool: # type: ignore
        if not index.isValid() or not self.files:
            return False

        row = index.row()
        col = index.column()
        file = self.files[row]

        if role == Qt.CheckStateRole and col == 0: # type: ignore
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

    def flags(self, index: QModelIndex) -> Qt.ItemFlags: # type: ignore
        if not index.isValid() or not self.files:
            return Qt.NoItemFlags
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole): # type: ignore
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            headers = ["", "Filename", "Size", "Type", "Modified"]
            if 0 <= section < len(headers):
                return headers[section]
        return super().headerData(section, orientation, role)

    def sort(self, column: int, order: Qt.SortOrder = Qt.AscendingOrder) -> None: # type: ignore
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
        """Set the files to be displayed in the table."""
        self.beginResetModel()
        self.files = files
        self.endResetModel()

        # Immediate icon update for cached metadata/hash
        self._update_icons_immediately()

    def _update_icons_immediately(self) -> None:
        """Updates icons immediately for all files that have cached data."""
        if not self.files:
            return

        # Simple icon refresh like the old system
        top_left = self.index(0, 0)
        bottom_right = self.index(len(self.files) - 1, 0)
        self.dataChanged.emit(top_left, bottom_right, [Qt.DecorationRole, Qt.ToolTipRole])
        logger.debug(f"[FileTableModel] Updated icons immediately for {len(self.files)} files")

    def _delayed_icon_update(self) -> None:
        """Delayed icon update to ensure all cached data is available."""
        # This method is no longer needed - removed for performance improvement
        # The _update_icons_immediately() does all the work
        pass

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

    def refresh_icons(self):
        """
        Refresh all icons in column 0.
        Call this after hash operations to update hash icon display.
        """
        if not self.files:
            return

        # Emit dataChanged for the entire first column to refresh icons and tooltips
        top_left = self.index(0, 0)
        bottom_right = self.index(len(self.files) - 1, 0)
        self.dataChanged.emit(top_left, bottom_right, [Qt.DecorationRole, Qt.ToolTipRole])
        logger.debug(f"[FileTableModel] Refreshed icons for {len(self.files)} files")

    def refresh_icon_for_file(self, file_path: str):
        """
        Refresh icon for a specific file by path.
        More efficient than refreshing all icons.
        """
        if not self.files:
            return

        # Find the file in our list
        for i, file_item in enumerate(self.files):
            if file_item.full_path == file_path:
                index = self.index(i, 0)
                self.dataChanged.emit(index, index, [Qt.DecorationRole, Qt.ToolTipRole])
                logger.debug(f"[FileTableModel] Refreshed icon for {file_item.filename}")
                return

        logger.debug(f"[FileTableModel] File not found for icon refresh: {file_path}")

    def get_checked_files(self) -> list[FileItem]:
        """
        Returns a list of all checked files.

        Returns:
            list[FileItem]: List of checked FileItem objects
        """
        return [f for f in self.files if f.checked]


