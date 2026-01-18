"""oncutf.models.file_table.data_provider

Qt model data interface for file table model.

This module provides the DataProvider class that handles Qt model data
methods including data(), setData(), flags(), headerData(), and rowCount().

Author: Michael Economou
Date: 2026-01-01
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from oncutf.models.file_item import FileItem
    from oncutf.models.file_table.column_manager import ColumnManager
    from oncutf.models.file_table.icon_manager import IconManager

from oncutf.core.application_context import get_app_context
from oncutf.core.pyqt_imports import QModelIndex, Qt, QVariant
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class DataProvider:
    """Provides Qt model data interface for file table display.

    Responsibilities:
        - Implement data() for displaying cell content
        - Implement setData() for editing cells (checkboxes)
        - Provide flags() for cell behavior
        - Provide headerData() for column headers
        - Format data appropriately for different roles
    """

    def __init__(
        self,
        model,
        column_manager: "ColumnManager",
        icon_manager: "IconManager",
        parent_window: Any = None,
    ):
        """Initialize the DataProvider.

        Args:
            model: Reference to FileTableModel (for files list and signals)
            column_manager: Reference to ColumnManager (for column mapping)
            icon_manager: Reference to IconManager (for icons and tooltips)
            parent_window: Reference to parent MainWindow (for metadata cache)

        """
        self.model = model
        self.column_manager = column_manager
        self.icon_manager = icon_manager
        self.parent_window = parent_window

    def row_count(self) -> int:
        """Return the number of rows (files) in the model.

        Returns:
            Number of files currently loaded

        """
        return len(self.model.files)

    def column_count(self) -> int:
        """Return the number of columns in the model.

        Returns:
            Number of visible columns + 1 for status column

        """
        return self.column_manager.get_column_count()

    def get_column_data(self, file: "FileItem", column_key: str, role: int) -> Any:
        """Get data for a specific column key.

        Args:
            file: FileItem to get data for
            column_key: Column identifier
            role: Qt item role

        Returns:
            Data appropriate for the role

        """
        if role == Qt.DisplayRole:
            if column_key == "filename":
                return str(file.filename)
            elif column_key == "color":
                # Color column shows no text, only icon
                return ""
            elif column_key == "file_size":
                return str(file.get_human_readable_size())
            elif column_key == "type":
                return str(file.extension)
            elif column_key == "modified":
                if isinstance(file.modified, datetime):
                    return file.modified.strftime("%Y-%m-%d %H:%M:%S")
                # file.modified may be str in edge cases
                return str(file.modified)  # type: ignore[unreachable]
            elif column_key == "file_hash":
                return self.icon_manager.get_hash_value(file.full_path)
            # For metadata columns, try to get from metadata cache
            else:
                return self._get_metadata_value(file, column_key)

        elif role == Qt.DecorationRole:
            # Show color swatch for color column
            if column_key == "color":
                color_value = getattr(file, "color", "none")
                if color_value and color_value != "none":
                    return self.icon_manager.create_color_icon(color_value)
                return QVariant()
            return QVariant()

        elif role == Qt.TextAlignmentRole:
            # Get alignment from UnifiedColumnService
            from oncutf.core.ui_managers import get_column_service

            service = get_column_service()
            config = service.get_column_config(column_key)
            if config:
                return config.qt_alignment
            # Default fallback
            return Qt.AlignLeft | Qt.AlignVCenter

        return QVariant()

    def _get_metadata_value(self, file: "FileItem", column_key: str) -> str:
        """Get metadata value for a file and column.

        Args:
            file: FileItem to get metadata for
            column_key: Metadata column key

        Returns:
            Metadata value as string or empty string if not found

        """
        # Try to get metadata value from cache
        if self.parent_window and hasattr(self.parent_window, "metadata_cache"):
            try:
                entry = self.parent_window.metadata_cache.get_entry(file.full_path)
                if entry and hasattr(entry, "data") and entry.data:
                    # Use centralized metadata field mapper
                    from oncutf.core.metadata.field_mapper import MetadataFieldMapper

                    value = MetadataFieldMapper.get_metadata_value(entry.data, column_key)
                    return value
            except Exception:
                logger.debug(
                    "Error accessing metadata cache for %s",
                    column_key,
                    exc_info=True,
                    extra={"dev_only": True},
                )

        # Fallback: try to get from file item metadata directly
        if hasattr(file, "metadata") and file.metadata:
            try:
                from oncutf.core.metadata.field_mapper import MetadataFieldMapper

                value = MetadataFieldMapper.get_metadata_value(file.metadata, column_key)
                if value:
                    return value
            except Exception:
                logger.debug(
                    "Error accessing file metadata for %s",
                    column_key,
                    exc_info=True,
                    extra={"dev_only": True},
                )

        return ""  # Empty string for missing metadata

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        """Get data for the given index and role.

        Args:
            index: Model index
            role: Qt item role

        Returns:
            Data appropriate for the role

        """
        if not index.isValid() or index.row() >= len(self.model.files):
            return QVariant()

        file = self.model.files[index.row()]

        # Support Qt.UserRole for thumbnail viewport (returns FileItem)
        if role == Qt.UserRole:
            return file

        if index.column() == 0:
            # Status column logic
            return self._get_status_column_data(file, role)

        col_key = self.column_manager.get_column_key(index.column())
        if not col_key:
            return None

        if role == Qt.ToolTipRole:
            # Return unified tooltip for all columns
            return self.icon_manager.get_unified_tooltip(file)

        return self.get_column_data(file, col_key, role)

    def _get_status_column_data(self, file: "FileItem", role: int) -> Any:
        """Get data for the status column (column 0).

        Args:
            file: FileItem to get data for
            role: Qt item role

        Returns:
            Data appropriate for the role

        """
        if role == Qt.DisplayRole:
            return QVariant()

        if role == Qt.DecorationRole:
            # Determine metadata status
            metadata_status = "none"

            # Check staging manager for modified status
            is_modified = False
            try:
                from oncutf.core.metadata import get_metadata_staging_manager

                staging_manager = get_metadata_staging_manager()
                if staging_manager and staging_manager.has_staged_changes(file.full_path):
                    is_modified = True
            except Exception:
                pass

            if self.parent_window and hasattr(self.parent_window, "metadata_cache"):
                entry = self.parent_window.metadata_cache.get_entry(file.full_path)
                if entry and hasattr(entry, "data") and entry.data:
                    # Check modified status first
                    if is_modified or (hasattr(entry, "modified") and entry.modified):
                        metadata_status = "modified"
                    elif hasattr(entry, "is_extended") and entry.is_extended:
                        metadata_status = "extended"
                    else:
                        metadata_status = "loaded"

            # Determine hash status
            hash_status = "hash" if self.icon_manager.has_hash_cached(file.full_path) else "none"

            # Create and return combined icon
            return self.icon_manager.create_combined_icon(metadata_status, hash_status)

        if role == Qt.CheckStateRole:
            return Qt.Checked if file.checked else Qt.Unchecked

        if role == Qt.ToolTipRole:
            return self.icon_manager.get_unified_tooltip(file)

        return None

    def set_data(self, index: QModelIndex, value: Any, role: int = Qt.EditRole) -> bool:
        """Set data for the given index.

        Args:
            index: Model index
            value: New value
            role: Qt item role

        Returns:
            True if data was set successfully

        """
        if not index.isValid() or not self.model.files:
            return False

        row = index.row()
        col = index.column()
        file = self.model.files[row]

        # Handle checkbox in status column (column 0)
        if role == Qt.CheckStateRole and col == 0:
            new_checked = value == Qt.Checked
            if file.checked == new_checked:
                return False  # Don't do anything if it didn't change
            file.checked = new_checked

            self.model.dataChanged.emit(index, index, [Qt.CheckStateRole])

            # Update UI
            self._update_ui_after_check_change()

            return True

        return False

    def _update_ui_after_check_change(self) -> None:
        """Update UI elements after checkbox state change."""
        try:
            get_app_context()
            if self.parent_window:
                self.parent_window.header.update_state(self.model.files)
                self.parent_window.update_files_label()
                self.parent_window.request_preview_update()
        except RuntimeError:
            if self.parent_window:
                self.parent_window.header.update_state(self.model.files)
                self.parent_window.update_files_label()
                self.parent_window.request_preview_update()

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        """Get item flags for the given index.

        Args:
            index: Model index

        Returns:
            Qt item flags

        """
        if not index.isValid() or not self.model.files:
            return Qt.ItemFlags(Qt.NoItemFlags)

        base_flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable

        # Enable checkbox only in status column (column 0)
        if index.column() == 0:
            base_flags |= Qt.ItemIsUserCheckable

        return base_flags

    def header_data(
        self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole
    ) -> Any:
        """Get header data for the given section.

        Args:
            section: Column/row index
            orientation: Horizontal or vertical
            role: Qt item role

        Returns:
            Header data for the section

        """
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                if section == 0:
                    return ""  # Don't display title in status column

                col_key = self.column_manager.get_column_key(section)
                if col_key:
                    # Get the proper title from configuration
                    from oncutf.config import FILE_TABLE_COLUMN_CONFIG

                    config = FILE_TABLE_COLUMN_CONFIG.get(col_key, {})
                    # Use display_title if available (for headers), fallback to title
                    title = config.get("display_title") or config.get("title", col_key)

                    logger.debug(
                        "[HeaderData] Section %d -> column '%s' -> display_title '%s'",
                        section,
                        col_key,
                        title,
                        extra={"dev_only": True},
                    )
                    return title
                logger.warning(
                    "[HeaderData] No column mapping found for section %d",
                    section,
                )
                return ""

            # NOTE: Header tooltips are rendered by InteractiveHeader via TooltipHelper
            # for consistent styling across platforms.

        return None

