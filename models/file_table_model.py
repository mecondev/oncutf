"""
file_table_model.py

Author: Michael Economou
Date: 2025-05-01

This module defines the FileTableModel class, which is a custom QAbstractTableModel
for displaying file data in a table view. The model manages file items, supports
sorting, and provides metadata status icons.

Classes:
    FileTableModel: Custom table model for file management.
"""

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
        logger.debug("FileTableModel __init__ called")
        self.parent_window = parent_window
        logger.debug(f"[FileTableModel] __init__: parent_window={self.parent_window}")
        self.files = []
        self._direct_loader = None
        self._cache_helper = None

        # Load icons for metadata status using the correct functions
        self.metadata_icons = load_metadata_icons()

        # Dynamic columns support
        self._visible_columns = self._load_default_visible_columns()
        self._column_mapping = self._create_column_mapping()

    def _load_default_visible_columns(self) -> list:
        """Load default visible columns configuration."""
        from config import FILE_TABLE_COLUMN_CONFIG

        visible_columns = []
        for column_key, column_config in FILE_TABLE_COLUMN_CONFIG.items():
            if column_config["default_visible"]:
                visible_columns.append(column_key)

        return visible_columns

    def _create_column_mapping(self) -> dict:
        """Create mapping from column index to column key."""
        mapping = {}  # Column 0 is hardcoded status column, not in mapping
        for i, column_key in enumerate(self._visible_columns):
            mapping[i + 1] = column_key  # Dynamic columns start from index 1
        logger.debug(f"_create_column_mapping: {mapping}")
        return mapping

    def update_visible_columns(self, visible_columns: list) -> None:
        logger.debug(f"[FileTableModel] update_visible_columns called with: {visible_columns}")
        if visible_columns != self._visible_columns:
            self.beginResetModel()
            self._visible_columns = visible_columns.copy()
            self._column_mapping = self._create_column_mapping()
            logger.debug(f"[FileTableModel] _column_mapping after update: {self._column_mapping}")
            logger.debug(f"[FileTableModel] files after update: {len(self.files)} files")
            logger.debug(f"[FileTableModel] parent_window after update: {self.parent_window}")
            self.endResetModel()
            # Ενημέρωση του view για αλλαγή στηλών
            if hasattr(self, '_table_view_ref') and self._table_view_ref:
                if hasattr(self._table_view_ref, 'refresh_columns_after_model_change'):
                    logger.debug("[FileTableModel] Calling refresh_columns_after_model_change after visible columns update")
                    self._table_view_ref.refresh_columns_after_model_change()
                if hasattr(self._table_view_ref, '_update_scrollbar_visibility'):
                    logger.debug("[FileTableModel] Forcing horizontal scrollbar update after visible columns update")
                    self._table_view_ref._update_scrollbar_visibility()

    def get_visible_columns(self) -> list:
        return self._visible_columns.copy()

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        count = len(self._visible_columns) + 1  # +1 για τη status column
        logger.debug(f"[FileTableModel] columnCount called, returning {count}")
        return count

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

    def _get_unified_tooltip(self, file) -> str:
        """Get unified tooltip for all columns showing metadata and hash status."""
        tooltip_parts = []

        # Add metadata status
        if self.parent_window and hasattr(self.parent_window, "metadata_cache"):
            entry = self.parent_window.metadata_cache.get_entry(file.full_path)
            if entry and hasattr(entry, 'data') and entry.data:
                field_count = len(entry.data)
                # Check the is_extended property of the MetadataEntry object
                if hasattr(entry, 'is_extended') and entry.is_extended:
                    tooltip_parts.append(f"{field_count} extended metadata loaded")
                else:
                    tooltip_parts.append(f"{field_count} metadata loaded")
            else:
                tooltip_parts.append("no metadata")

        # Add hash status
        if self._has_hash_cached(file.full_path):
            hash_value = self._get_hash_value(file.full_path)
            if hash_value:
                tooltip_parts.append(f"Hash: {hash_value}")
            else:
                tooltip_parts.append("Hash available")
        else:
            tooltip_parts.append("No hash")

        return "\n".join(tooltip_parts)

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
        # Use hardcoded width for status column (column 0)
        combined_width = 50  # Fixed width for status column
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
            # Draw hash icon on the right (32px from left = 50-16-2 for 2px right margin)
            painter.drawPixmap(32, 0, hash_icon)

        painter.end()
        return QIcon(combined_pixmap)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        count = len(self.files)
        logger.debug(f"[FileTableModel] rowCount called, returning {count}")
        return count

    def _get_column_data(self, file, column_key: str, role: int):
        """Get data for a specific column key."""
        if role == Qt.DisplayRole:
            if column_key == "filename":
                return str(file.filename)
            elif column_key == "file_size":
                return str(file.get_human_readable_size())
            elif column_key == "type":
                return str(file.extension)
            elif column_key == "modified":
                if isinstance(file.modified, datetime):
                    return file.modified.strftime("%Y-%m-%d %H:%M:%S")
                return str(file.modified)
            elif column_key == "file_hash":
                return self._get_hash_value(file.full_path)
            # For metadata columns, try to get from metadata cache
            else:
                # Try to get metadata value from cache
                if self.parent_window and hasattr(self.parent_window, "metadata_cache"):
                    try:
                        entry = self.parent_window.metadata_cache.get_entry(file.full_path)
                        if entry and hasattr(entry, 'data') and entry.data:
                            # Use centralized metadata field mapper
                            from utils.metadata_field_mapper import MetadataFieldMapper

                            value = MetadataFieldMapper.get_metadata_value(entry.data, column_key)
                            return value
                    except Exception as e:
                        logger.debug(f"Error accessing metadata cache for {column_key}: {e}")

                # Fallback: try to get from file item metadata directly
                if hasattr(file, 'metadata') and file.metadata:
                    try:
                        # Use centralized metadata field mapper for fallback too
                        from utils.metadata_field_mapper import MetadataFieldMapper

                        value = MetadataFieldMapper.get_metadata_value(file.metadata, column_key)
                        if value:
                            return value
                    except Exception as e:
                        logger.debug(f"Error accessing file metadata for {column_key}: {e}")

                return ""  # Empty string for missing metadata

        elif role == Qt.TextAlignmentRole:
            # Get alignment from configuration
            from config import FILE_TABLE_COLUMN_CONFIG
            column_config = FILE_TABLE_COLUMN_CONFIG.get(column_key, {})
            alignment = column_config.get('alignment', 'left')

            # Map alignment strings to Qt constants
            if alignment == 'right':
                return Qt.AlignRight | Qt.AlignVCenter
            elif alignment == 'center':
                return Qt.AlignCenter
            else:  # left or default
                return Qt.AlignLeft | Qt.AlignVCenter

        return QVariant()

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> QVariant:  # type: ignore
        logger.debug(f"[FileTableModel] data called: row={index.row()}, col={index.column()}, role={role}")
        logger.debug(f"[FileTableModel] data: parent_window={self.parent_window}, has_metadata_cache={hasattr(self.parent_window, 'metadata_cache') if self.parent_window else None}")
        if not index.isValid() or index.row() >= len(self.files):
            return QVariant()
        if index.column() == 0:
            # Status column logic...
            file = self.files[index.row()]
            if role == Qt.DisplayRole:
                return ""
            if role == Qt.DecorationRole:
                # Επιστροφή icon ανάλογα με το status
                return QVariant()  # ή το κατάλληλο QIcon
            return QVariant()
        col_key = self._column_mapping.get(index.column())
        if not col_key:
            logger.debug(f"data(): no column_key for col {index.column()}")
            return QVariant()
        file = self.files[index.row()]
        if role == Qt.ToolTipRole:
            pass
        result = self._get_column_data(file, col_key, role)
        if role == Qt.DisplayRole:
            logger.debug(f"data(): row={index.row()}, col={index.column()}, key={col_key}, value={result}")
        return result

    def setData(self, index: QModelIndex, value, role: int = Qt.EditRole) -> bool:  # type: ignore
        if not index.isValid() or not self.files:
            return False

        row = index.row()
        col = index.column()
        file = self.files[row]

        # Handle checkbox in status column (column 0)
        if role == Qt.CheckStateRole and col == 0:
            new_checked = value == Qt.Checked
            if file.checked == new_checked:
                return False  # Don't do anything if it didn't change
            file.checked = new_checked

            self.dataChanged.emit(index, index, [Qt.CheckStateRole])

            # Try to update UI through ApplicationContext, fallback to parent_window
            try:
                get_app_context()
                # For now, we still need to access parent window for UI updates
                # This will be improved when we migrate UI update handling to context
                import sys

                if hasattr(sys, "_getframe"):
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

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:  # type: ignore
        if not index.isValid() or not self.files:
            return Qt.NoItemFlags

        base_flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable

        # Enable checkbox only in status column (column 0)
        if index.column() == 0:
            base_flags |= Qt.ItemIsUserCheckable

        return base_flags

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):  # type: ignore
        logger.debug(f"headerData called, section={section}, orientation={orientation}, role={role}, files={len(self.files)}")
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section == 0:
                return ""  # Δεν εμφανίζουμε τίτλο στη status column
            col_key = self._column_mapping.get(section)
            return col_key if col_key else ""
        return super().headerData(section, orientation, role)

    def sort(self, column: int, order: Qt.SortOrder = Qt.AscendingOrder) -> None:  # type: ignore
        if not self.files:
            return

        # Get column key from mapping
        column_key = self._column_mapping.get(column)
        if not column_key:
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

        reverse = order == Qt.DescendingOrder

        # Sort based on column key
        if column_key == "filename":
            self.files.sort(key=lambda f: f.filename.lower(), reverse=reverse)
        elif column_key == "file_size":
            self.files.sort(key=lambda f: f.size if hasattr(f, "size") else 0, reverse=reverse)
        elif column_key == "type":
            self.files.sort(key=lambda f: f.extension.lower(), reverse=reverse)
        elif column_key == "modified":
            self.files.sort(key=lambda f: f.modified, reverse=reverse)
        elif column_key == "file_hash":
            self.files.sort(key=lambda f: self._get_hash_value(f.full_path), reverse=reverse)
        else:
            # For metadata columns, sort by the metadata value
            def get_metadata_sort_key(file):
                if self.parent_window and hasattr(self.parent_window, "metadata_cache"):
                    entry = self.parent_window.metadata_cache.get_entry(file.full_path)
                    if entry and hasattr(entry, 'data') and entry.data:
                        # Map column keys to metadata keys (using actual EXIF/QuickTime keys)
                        # Use centralized metadata field mapper for sorting
                        from utils.metadata_field_mapper import MetadataFieldMapper

                        # Get possible metadata keys for this column
                        possible_keys = MetadataFieldMapper.get_metadata_keys_for_field(column_key)

                        # Find the first available key in the metadata
                        found_value = None
                        for key in possible_keys:
                            if key in entry.data:
                                found_value = entry.data[key]
                                break

                        if found_value is not None:
                            # Special handling for image size (sort by width)
                            if column_key == "image_size":
                                try:
                                    # Extract width from "widthxheight" format
                                    if 'x' in str(found_value):
                                        width = str(found_value).split('x')[0]
                                        return int(width)
                                    else:
                                        return int(found_value)
                                except (ValueError, TypeError):
                                    return 0
                            # For numeric values, try to convert to int/float for proper sorting
                            elif column_key in ["iso", "video_fps", "video_avg_bitrate", "rotation"]:
                                try:
                                    # Extract numeric part from strings like "100" or "100.0"
                                    numeric_str = str(found_value).split()[0]  # Take first word
                                    if '.' in numeric_str:
                                        return float(numeric_str)
                                    else:
                                        return int(numeric_str)
                                except (ValueError, TypeError):
                                    return 0
                            else:
                                return str(found_value).lower()  # String sorting (case-insensitive)

                # Return appropriate default value based on column type
                if column_key in ["iso", "video_fps", "video_avg_bitrate", "rotation", "image_size"]:
                    return 0  # Default numeric value for numeric columns
                else:
                    return ""  # Default string value for text columns

            self.files.sort(key=get_metadata_sort_key, reverse=reverse)

        self.layoutChanged.emit()
        self.sort_changed.emit()

        # Store current sort state in parent window for post-rename consistency
        if self.parent_window:
            self.parent_window.current_sort_column = column
            self.parent_window.current_sort_order = order
            logger.debug(
                f"[Model] Stored sort state: column={column}, order={order}",
                extra={"dev_only": True},
            )

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
        logger.debug(f"set_files called with {len(files)} files")
        self.beginResetModel()
        self.files = files
        # self._update_column_mapping()  # Αφαιρείται γιατί δεν χρειάζεται και προκαλεί σφάλμα
        self._update_icons_immediately()
        self.endResetModel()
        logger.debug(f"set_files finished, now self.files has {len(self.files)} files")
        # Update custom tooltips for new files
        if hasattr(self, '_table_view_ref') and self._table_view_ref:
            self.setup_custom_tooltips(self._table_view_ref)
            # Ensure columns are reconfigured after model reset
            if hasattr(self._table_view_ref, 'refresh_columns_after_model_change'):
                logger.debug(f"Calling refresh_columns_after_model_change, files in model: {len(self.files)}")
                self._table_view_ref.refresh_columns_after_model_change()

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

    def setup_custom_tooltips(self, table_view) -> None:
        """Setup custom tooltips for all cells in the table view."""
        # This method is no longer needed - tooltips are now handled through Qt.ToolTipRole in data() method
        # Keep method for backward compatibility but make it a no-op
        if not table_view:
            return

        # Store reference to table view for future updates
        self._table_view_ref = table_view

        logger.debug("Custom tooltips are now handled through Qt.ToolTipRole in data() method")
