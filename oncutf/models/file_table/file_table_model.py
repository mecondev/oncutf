"""oncutf.models.file_table.file_table_model.

Main file table model for displaying file data in a table view.

This module provides the FileTableModel class, a custom QAbstractTableModel
for displaying file data. The model delegates functionality to specialized
managers for icons, sorting, columns, data, and file operations.

Author: Michael Economou
Date: 2026-01-01
"""

from typing import Any, Literal

from oncutf.core.application_context import get_app_context
from oncutf.core.pyqt_imports import (
    QAbstractTableModel,
    QItemSelection,
    QItemSelectionModel,
    QItemSelectionRange,
    QModelIndex,
    Qt,
    pyqtSignal,
)
from oncutf.models.file_item import FileItem
from oncutf.models.file_table.data_provider import DataProvider
from oncutf.models.file_table.icon_manager import IconManager
from oncutf.models.file_table.model_column_manager import ColumnManager
from oncutf.models.file_table.model_file_operations import FileOperationsManager
from oncutf.models.file_table.sort_manager import SortManager
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class FileTableModel(QAbstractTableModel):
    """Table model for displaying and managing a list of FileItem objects
    in a QTableView. Supports row selection (blue highlighting), sorting, and preview updates.

    This class acts as an orchestrator, delegating to specialized managers:
    - IconManager: Status icons and tooltips
    - SortManager: File sorting logic
    - ColumnManager: Column visibility and mapping
    - DataProvider: Qt model data interface
    - FileOperationsManager: File add/remove/refresh
    """

    sort_changed = pyqtSignal()  # Emitted when sort() is called

    def __init__(self, parent_window: Any = None) -> None:
        """Initialize the FileTableModel.

        Args:
            parent_window: Reference to parent MainWindow (optional)

        """
        super().__init__()
        logger.debug("FileTableModel __init__ called", extra={"dev_only": True})
        self.parent_window: Any = parent_window
        self.files: list[FileItem] = []
        self._direct_loader = None
        self._table_view_ref = None

        # Order mode tracking (for thumbnail viewport integration)
        self._order_mode: Literal["manual", "sorted"] = "sorted"  # Default to sorted
        self._current_sort_key: str | None = None
        self._current_sort_reverse: bool = False
        self._current_folder_path: str | None = None

        # Initialize managers
        self._icon_manager = IconManager(parent_window)
        self._column_manager = ColumnManager(self)
        self._sort_manager = SortManager(parent_window, self._icon_manager.get_hash_value)
        self._data_provider = DataProvider(
            self, self._column_manager, self._icon_manager, parent_window
        )
        self._file_ops = FileOperationsManager(self, self._icon_manager)

    # ==================== Column Management (delegated) ====================

    @property
    def _visible_columns(self) -> list[str]:
        """Get visible columns from column manager."""
        return self._column_manager._visible_columns

    @_visible_columns.setter
    def _visible_columns(self, value: list[str]) -> None:
        """Set visible columns in column manager."""
        self._column_manager._visible_columns = value

    @property
    def _column_mapping(self) -> dict[int, str]:
        """Get column mapping from column manager."""
        return self._column_manager._column_mapping

    @_column_mapping.setter
    def _column_mapping(self, value: dict[int, str]) -> None:
        """Set column mapping in column manager."""
        self._column_manager._column_mapping = value

    @property
    def _tooltip_cache(self) -> dict[str, str]:
        """Get tooltip cache from icon manager."""
        return self._icon_manager._tooltip_cache

    @property
    def metadata_icons(self):
        """Get metadata icons from icon manager."""
        return self._icon_manager.metadata_icons

    def update_visible_columns(self, visible_columns: list[str]) -> None:
        """Update the list of visible columns and refresh the model."""
        self._column_manager.update_visible_columns(visible_columns)

    def get_visible_columns(self) -> list[str]:
        """Get the current list of visible column keys."""
        return self._column_manager.get_visible_columns()

    def debug_column_state(self) -> None:
        """Debug method to print current column state."""
        self._column_manager.debug_column_state()
        logger.debug("[ColumnDebug] Row count: %d", self.rowCount(), extra={"dev_only": True})
        logger.debug("[ColumnDebug] Files loaded: %d", len(self.files), extra={"dev_only": True})

    # ==================== Qt Model Interface (delegated) ====================

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return the number of columns."""
        return self._data_provider.column_count()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return the number of rows (files) in the model."""
        return self._data_provider.row_count()

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        """Get data for the given index and role."""
        return self._data_provider.data(index, role)

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.EditRole) -> bool:
        """Set data for the given index."""
        return self._data_provider.set_data(index, value, role)

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        """Get item flags for the given index."""
        return self._data_provider.flags(index)

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole
    ) -> Any:
        """Get header data for the given section."""
        result = self._data_provider.header_data(section, orientation, role)
        if result is not None:
            return result
        return super().headerData(section, orientation, role)

    # ==================== Icon/Status Methods (delegated) ====================

    def _has_hash_cached(self, file_path: str) -> bool:
        """Check if a file has a hash stored in the persistent cache."""
        return self._icon_manager.has_hash_cached(file_path)

    def _get_hash_value(self, file_path: str) -> str:
        """Get the hash value for a file from the persistent cache."""
        return self._icon_manager.get_hash_value(file_path)

    def _get_unified_tooltip(self, file: Any) -> str:
        """Get unified tooltip for all columns showing metadata and hash status."""
        return self._icon_manager.get_unified_tooltip(file)

    def _create_combined_icon(self, metadata_status: str, hash_status: str):
        """Create a combined icon showing metadata status and hash status."""
        return self._icon_manager.create_combined_icon(metadata_status, hash_status)

    def _create_color_icon(self, hex_color: str):
        """Create a color swatch icon for the color column."""
        return self._icon_manager.create_color_icon(hex_color)

    # ==================== File Operations (delegated) ====================

    def clear(self) -> None:
        """Clear all files from the model."""
        self._file_ops.clear()

    def set_files(self, files: list[FileItem]) -> None:
        """Set the files to be displayed in the table."""
        self._file_ops.set_files(files)

    def add_files(self, new_files: list[FileItem]) -> None:
        """Adds new files to the existing file list and updates the model."""
        self._file_ops.add_files(new_files)

    def refresh_icons(self) -> None:
        """Refresh all icons in column 0."""
        self._file_ops.refresh_icons()

    def refresh_icon_for_file(self, file_path: str) -> None:
        """Refresh icon for a specific file by path."""
        self._file_ops.refresh_icon_for_file(file_path)

    def get_checked_files(self) -> list[FileItem]:
        """Returns a list of all checked files."""
        return self._file_ops.get_checked_files()

    def setup_custom_tooltips(self, table_view) -> None:
        """Setup custom tooltips for all cells in the table view."""
        self._file_ops.setup_custom_tooltips(table_view)

    def update_file_metadata(self, file_item: FileItem) -> None:
        """Update the row for the given file item."""
        self._file_ops.update_file_metadata(file_item)

    # ==================== Sorting (partially delegated) ====================

    def sort(self, column: int, order: Qt.SortOrder = Qt.AscendingOrder) -> None:
        """Sort files by the specified column."""
        if not self.files:
            return

        # Get column key from mapping
        column_key = self._column_mapping.get(column)
        if not column_key:
            return

        # Get selection model
        selection_model = self._get_selection_model()
        if not selection_model:
            return

        selected_items = [self.files[i.row()] for i in selection_model.selectedRows()]
        reverse = order == Qt.DescendingOrder

        # Sort files using sort manager
        self.files = self._sort_manager.sort_files(self.files, column_key, reverse)

        self.layoutChanged.emit()
        self.sort_changed.emit()

        # Store current sort state in parent window
        if self.parent_window:
            self.parent_window.current_sort_column = column
            self.parent_window.current_sort_order = order
            logger.debug(
                "[Model] Stored sort state: column=%d, order=%s",
                column,
                order,
                extra={"dev_only": True},
            )

        # Restore selection
        self._restore_selection(selection_model, selected_items)

        # Refresh metadata tree
        self._refresh_metadata_tree()

    def _get_selection_model(self):
        """Get the selection model from parent window."""
        selection_model = None
        try:
            get_app_context()
            if self.parent_window:
                selection_model = self.parent_window.file_table_view.selectionModel()
        except RuntimeError:
            if self.parent_window:
                selection_model = self.parent_window.file_table_view.selectionModel()
        return selection_model

    def _restore_selection(self, selection_model, selected_items: list[FileItem]) -> None:
        """Restore selection after sorting."""
        selection_model.clearSelection()
        selection = QItemSelection()

        for row, file in enumerate(self.files):
            if file in selected_items:
                top_left = self.index(row, 0)
                bottom_right = self.index(row, self.columnCount() - 1)
                selection_range = QItemSelectionRange(top_left, bottom_right)
                selection.append(selection_range)
                logger.debug(
                    "[Model] dataChanged.emit() for row %d",
                    row,
                    extra={"dev_only": True},
                )

        selection_model.select(selection, QItemSelectionModel.Select)

    def _refresh_metadata_tree(self) -> None:
        """Refresh metadata tree after sorting."""
        try:
            get_app_context()
            if self.parent_window:
                self.parent_window.metadata_tree_view.refresh_metadata_from_selection()
        except RuntimeError:
            if self.parent_window:
                self.parent_window.metadata_tree_view.refresh_metadata_from_selection()

    # ==================== Order Mode Management (for Thumbnail Viewport) ====================

    @property
    def order_mode(self) -> Literal["manual", "sorted"]:
        """Get current order mode.

        Returns:
            "manual" if manual drag reorder active, "sorted" if Qt sort active

        """
        return self._order_mode

    def set_order_mode(
        self,
        mode: Literal["manual", "sorted"],
        sort_key: str | None = None,
        reverse: bool = False,
    ) -> None:
        """Set order mode and apply sorting if needed.

        Args:
            mode: "manual" for manual drag order, "sorted" for automatic sort
            sort_key: Column key to sort by (if mode is "sorted")
            reverse: Reverse sort order

        """
        self._order_mode = mode
        self._current_sort_key = sort_key
        self._current_sort_reverse = reverse

        if mode == "sorted" and sort_key:
            # Apply sort
            self._apply_sort_by_key(sort_key, reverse)
            # Clear manual order from DB
            self._clear_manual_order_db()
            logger.info(
                "[FileTableModel] Order mode set to sorted: %s (reverse=%s)",
                sort_key,
                reverse,
            )
        elif mode == "manual":
            # Load manual order from DB
            self._load_manual_order_db()
            logger.info("[FileTableModel] Order mode set to manual")

        self.layoutChanged.emit()

    def _apply_sort_by_key(self, key: str, reverse: bool) -> None:
        """Apply sorting by key.

        Args:
            key: Sort key ("filename", "color", etc.)
            reverse: Reverse order

        """
        if not self.files:
            return

        # Sort using sort manager
        self.files = self._sort_manager.sort_files(self.files, key, reverse)
        logger.debug("[FileTableModel] Sorted %d files by %s", len(self.files), key)

    def _load_manual_order_db(self) -> None:
        """Load manual order from database and reorder files."""
        if not self._current_folder_path:
            logger.debug("[FileTableModel] No folder path set, skipping manual order load")
            return

        try:
            from oncutf.core.application_context import get_app_context

            db_manager = get_app_context().get_manager("database")
            if not db_manager:
                logger.warning("[FileTableModel] Database manager not available")
                return

            thumbnail_store = db_manager.thumbnail_store
            file_paths = thumbnail_store.get_folder_order(self._current_folder_path)

            if not file_paths:
                logger.debug(
                    "[FileTableModel] No manual order found for folder: %s",
                    self._current_folder_path,
                )
                return

            # Reorder files based on DB order
            file_map = {f.full_path: f for f in self.files}
            ordered_files = []

            # Add files in DB order
            for path in file_paths:
                if path in file_map:
                    ordered_files.append(file_map[path])

            # Add any files not in DB order (new files)
            for file in self.files:
                if file not in ordered_files:
                    ordered_files.append(file)

            self.files = ordered_files
            logger.info(
                "[FileTableModel] Loaded manual order: %d files",
                len(file_paths),
            )

        except Exception as e:
            logger.error("[FileTableModel] Failed to load manual order: %s", e)

    def _clear_manual_order_db(self) -> None:
        """Clear manual order from database when switching to sorted mode."""
        if not self._current_folder_path:
            return

        try:
            from oncutf.core.application_context import get_app_context

            db_manager = get_app_context().get_manager("database")
            if not db_manager:
                return

            thumbnail_store = db_manager.thumbnail_store
            thumbnail_store.clear_folder_order(self._current_folder_path)
            logger.debug(
                "[FileTableModel] Cleared manual order for folder: %s",
                self._current_folder_path,
            )

        except Exception as e:
            logger.error("[FileTableModel] Failed to clear manual order: %s", e)

    def save_manual_order(self) -> None:
        """Save current file order to database (for manual mode).

        Called by ThumbnailViewportWidget after drag reorder.

        """
        if self._order_mode != "manual" or not self._current_folder_path:
            return

        try:
            from oncutf.core.application_context import get_app_context

            db_manager = get_app_context().get_manager("database")
            if not db_manager:
                return

            thumbnail_store = db_manager.thumbnail_store
            file_paths = [f.full_path for f in self.files]
            thumbnail_store.save_folder_order(self._current_folder_path, file_paths)

            logger.info(
                "[FileTableModel] Saved manual order: %d files",
                len(file_paths),
            )

        except Exception as e:
            logger.error("[FileTableModel] Failed to save manual order: %s", e)

    def set_current_folder(self, folder_path: str) -> None:
        """Set current folder path for order persistence.

        Args:
            folder_path: Absolute folder path

        """
        self._current_folder_path = folder_path
        logger.debug("[FileTableModel] Current folder set to: %s", folder_path)

    # ==================== Internal Methods ====================

    def _get_column_data(self, file: Any, column_key: str, role: int) -> Any:
        """Get data for a specific column key."""
        return self._data_provider.get_column_data(file, column_key, role)

    def _update_icons_immediately(self) -> None:
        """Updates icons immediately for all files that have cached data."""
        self._file_ops._update_icons_immediately()

    def _delayed_icon_update(self) -> None:
        """Delayed icon update (no-op for backward compatibility)."""
