"""oncutf.models.file_table.file_operations.

File operations management for file table model.

This module provides the FileOperationsManager class that handles file
add/remove operations, icon refresh, and file list management.

Author: Michael Economou
Date: 2026-01-01
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from oncutf.models.file_item import FileItem

from oncutf.core.application_context import get_app_context
from oncutf.core.pyqt_imports import QModelIndex, Qt
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class FileOperationsManager:
    """Manages file operations for file table display.

    Responsibilities:
        - Clear, set, and add files to the model
        - Refresh icons for all files or specific files
        - Update file metadata display
        - Manage tooltip cache invalidation
    """

    def __init__(self, model, icon_manager):
        """Initialize the FileOperationsManager.

        Args:
            model: Reference to FileTableModel (for Qt signal methods and files list)
            icon_manager: Reference to IconManager (for tooltip cache)

        """
        self.model = model
        self.icon_manager = icon_manager

    def clear(self) -> None:
        """Clear all files from the model."""
        self.model.beginResetModel()
        self.model.files = []
        self.model.endResetModel()

    def set_files(self, files: list["FileItem"]) -> None:
        """Set the files to be displayed in the table.

        Args:
            files: List of FileItem objects to display

        """
        logger.debug(
            "set_files called with %d files",
            len(files),
            extra={"dev_only": True},
        )
        self.model.beginResetModel()
        self.model.files = files

        # Clear tooltip cache when new files are loaded
        self.icon_manager.clear_tooltip_cache()

        self._update_icons_immediately()
        self.model.endResetModel()
        logger.debug(
            "set_files finished, now self.files has %d files",
            len(self.model.files),
            extra={"dev_only": True},
        )
        # Update custom tooltips for new files
        if hasattr(self.model, "_table_view_ref") and self.model._table_view_ref:
            self.setup_custom_tooltips(self.model._table_view_ref)
            # Ensure columns are reconfigured after model reset
            if hasattr(self.model._table_view_ref, "refresh_columns_after_model_change"):
                logger.debug(
                    "Calling refresh_columns_after_model_change, files in model: %d",
                    len(self.model.files),
                )
                self.model._table_view_ref.refresh_columns_after_model_change()

    def _update_icons_immediately(self) -> None:
        """Updates icons immediately for all files that have cached data."""
        if not self.model.files:
            return

        # Simple icon refresh like the old system
        top_left = self.model.index(0, 0)
        bottom_right = self.model.index(len(self.model.files) - 1, 0)
        self.model.dataChanged.emit(top_left, bottom_right, [Qt.DecorationRole, Qt.ToolTipRole])
        logger.debug(
            "[FileOperationsManager] Updated icons immediately for %d files",
            len(self.model.files),
            extra={"dev_only": True},
        )

    def add_files(self, new_files: list["FileItem"]) -> None:
        """Adds new files to the existing file list and updates the model.

        Args:
            new_files: List of new FileItem objects to add

        """
        if not new_files:
            return

        # Start row insertion
        start_row = len(self.model.files)
        self.model.beginInsertRows(QModelIndex(), start_row, start_row + len(new_files) - 1)

        # Add the new files to our list
        self.model.files.extend(new_files)

        # End row insertion
        self.model.endInsertRows()

        # Emit signal to update any views
        self.model.layoutChanged.emit()

        # Optionally notify parent window
        try:
            get_app_context()
            if self.model.parent_window:
                self.model.parent_window.update_files_label()
        except RuntimeError:
            if self.model.parent_window:
                self.model.parent_window.update_files_label()

    def refresh_icons(self) -> None:
        """Refresh all icons in column 0.
        Call this after hash operations to update hash icon display.
        """
        if not self.model.files:
            return

        # Clear tooltip cache to force regeneration with new metadata/hash status
        self.icon_manager.clear_tooltip_cache()

        # Emit dataChanged for the entire first column to refresh icons and tooltips
        top_left = self.model.index(0, 0)
        bottom_right = self.model.index(len(self.model.files) - 1, 0)
        self.model.dataChanged.emit(top_left, bottom_right, [Qt.DecorationRole, Qt.ToolTipRole])
        logger.debug(
            "[FileOperationsManager] Refreshed icons for %d files",
            len(self.model.files),
            extra={"dev_only": True},
        )

    def refresh_icon_for_file(self, file_path: str) -> None:
        """Refresh icon for a specific file by path.
        More efficient than refreshing all icons.
        """
        if not self.model.files:
            return

        # Invalidate tooltip cache for this specific file
        self.icon_manager.invalidate_tooltip(file_path)

        # Find the file in our list
        for i, file_item in enumerate(self.model.files):
            if file_item.full_path == file_path:
                index = self.model.index(i, 0)
                self.model.dataChanged.emit(index, index, [Qt.DecorationRole, Qt.ToolTipRole])
                logger.debug(
                    "[FileOperationsManager] Refreshed icon for %s",
                    file_item.filename,
                    extra={"dev_only": True},
                )
                return

        logger.debug(
            "[FileOperationsManager] File not found for icon refresh: %s",
            file_path,
            extra={"dev_only": True},
        )

    def get_checked_files(self) -> list["FileItem"]:
        """Returns a list of all checked files.

        Returns:
            List of checked FileItem objects

        """
        return [f for f in self.model.files if f.checked]

    def setup_custom_tooltips(self, table_view: Any) -> None:
        """Setup custom tooltips for all cells in the table view.

        Args:
            table_view: Reference to the table view widget

        """
        if not table_view:
            return

        # Store reference to table view for future updates
        self.model._table_view_ref = table_view

        logger.debug(
            "Custom tooltips are now handled through Qt.ToolTipRole in data() method",
            extra={"dev_only": True},
        )

    def update_file_metadata(self, file_item: "FileItem") -> None:
        """Update the row for the given file item.
        Emits dataChanged for the corresponding row.
        """
        try:
            # Find the row index for the file item
            row = self.model.files.index(file_item)

            top_left = self.model.index(row, 0)
            bottom_right = self.model.index(row, self.model.columnCount() - 1)

            # Emit dataChanged for all roles that might be affected by metadata update
            self.model.dataChanged.emit(
                top_left, bottom_right, [Qt.DecorationRole, Qt.ToolTipRole, Qt.DisplayRole]
            )
        except ValueError:
            # File item not found in the model
            pass
