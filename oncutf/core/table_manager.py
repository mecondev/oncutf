"""
Module: table_manager.py

Author: Michael Economou
Date: 2025-05-31

table_manager.py
Manager for handling file table operations in the MainWindow.
Consolidates all table-related logic including sorting, clearing,
preparation, and selection management.
"""

from oncutf.core.pyqt_imports import Qt
from oncutf.models.file_item import FileItem
from oncutf.utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class TableManager:
    """
    Manager for handling all file table operations.

    This manager consolidates table-related logic that was previously scattered
    throughout the MainWindow, providing a clean interface for:
    - Table sorting operations
    - Table clearing and preparation
    - Selection management
    - File retrieval operations
    """

    def __init__(self, parent_window):
        """
        Initialize the TableManager.

        Args:
            parent_window: Reference to the MainWindow instance
        """
        self.parent_window = parent_window
        logger.debug("[TableManager] Initialized", extra={"dev_only": True})

    def sort_by_column(
        self, column: int, _order: Qt.SortOrder = None, force_order: Qt.SortOrder = None
    ) -> None:
        """
        Sorts the file table based on clicked header column or context menu.
        Toggle logic unless a force_order is explicitly provided.
        """
        if column == 0:
            return  # Do not sort the status/info column

        header = self.parent_window.file_table_view.horizontalHeader()
        current_column = header.sortIndicatorSection()
        current_order = header.sortIndicatorOrder()

        if force_order is not None:
            new_order = force_order
        elif column == current_column:
            new_order = (
                Qt.DescendingOrder if current_order == Qt.AscendingOrder else Qt.AscendingOrder
            )
        else:
            new_order = Qt.AscendingOrder

        self.parent_window.file_model.sort(column, new_order)
        header.setSortIndicator(column, new_order)

    def clear_file_table(self, message: str = "No folder selected") -> None:
        """
        Clears the file table and shows a placeholder message.
        """
        # Only clear metadata modifications if we're actually changing folders
        # This preserves modifications when reloading the same folder
        should_clear_modifications = (
            message != "No folder selected"  # User explicitly clearing
            or not hasattr(self.parent_window, "current_folder_path")  # No current folder
            or self.parent_window.current_folder_path is None  # Folder path is None
        )

        if should_clear_modifications:
            logger.debug(
                f"[TableManager] Clearing metadata modifications: {message}",
                extra={"dev_only": True},
            )
            self.parent_window.metadata_tree_view.clear_for_folder_change()
        else:
            logger.debug(
                f"[TableManager] Preserving metadata modifications: {message}",
                extra={"dev_only": True},
            )
            # Just clear the view without losing modifications
            self.parent_window.metadata_tree_view.clear_view()

        self.parent_window.file_model.set_files([])  # reset model with empty list
        self.parent_window.file_table_view.set_placeholder_visible(
            True
        )  # Show placeholder when empty
        # Prefer view-owned API to toggle header enabled state
        if hasattr(self.parent_window, "file_table_view") and hasattr(
            self.parent_window.file_table_view, "set_header_enabled"
        ):
            self.parent_window.file_table_view.set_header_enabled(False)
        else:
            # Fallback to previous behavior for compatibility
            if hasattr(self.parent_window, "header") and self.parent_window.header is not None:
                self.parent_window.header.setEnabled(False)  # disable header
        self.parent_window.status_manager.clear_file_table_status(
            self.parent_window.files_label, message
        )
        self.parent_window.update_files_label()

        # Update scrollbar visibility after clearing table
        # Use public API on FileTableView instead of calling internal method
        if hasattr(self.parent_window.file_table_view, "ensure_scrollbar_visibility"):
            self.parent_window.file_table_view.ensure_scrollbar_visibility()
        else:
            # Fallback to internal method for backwards compatibility
            self.parent_window.file_table_view._update_scrollbar_visibility()

        # No longer need column adjustment - columns maintain fixed widths

        # Explicitly clear preview tables and show placeholders
        self.parent_window.update_preview_tables_from_pairs([])

        # Also clear the preview tables directly to ensure they show placeholders
        if hasattr(self.parent_window, "preview_tables_view"):
            self.parent_window.preview_tables_view.clear_tables()

    def prepare_file_table(self, file_items: list[FileItem]) -> None:
        """
        Prepare the file table view with the given file items.

        Delegates the core table preparation to the FileTableView and handles
        application-specific logic like updating labels and preview maps.

        Args:
            file_items: List of FileItem objects to display in the table
        """
        # Delegate table preparation to the view itself
        self.parent_window.file_table_view.prepare_table(file_items)

        # CRITICAL: Hide placeholder when files are loaded
        if file_items:
            self.parent_window.file_table_view.set_placeholder_visible(False)
            logger.debug("[TableManager] Hidden file table placeholder - files loaded")
        else:
            self.parent_window.file_table_view.set_placeholder_visible(True)
            logger.debug("[TableManager] Shown file table placeholder - no files")

        # Handle application-specific setup
        # Store files in FileStore (centralized state management)
        self.parent_window.context.file_store.set_loaded_files(file_items)
        self.parent_window.file_model.folder_path = self.parent_window.current_folder_path
        self.parent_window.preview_map = {f.filename: f for f in file_items}

        # Enable header and update UI elements
        if hasattr(self.parent_window, "file_table_view") and hasattr(
            self.parent_window.file_table_view, "set_header_enabled"
        ):
            self.parent_window.file_table_view.set_header_enabled(True)
        else:
            if hasattr(self.parent_window, "header") and self.parent_window.header is not None:
                self.parent_window.header.setEnabled(True)

        self.parent_window.update_files_label()
        self.parent_window.update_preview_tables_from_pairs([])
        self.parent_window.rename_button.setEnabled(False)

        # If we're coming from a rename operation and have active modules, regenerate preview
        if self.parent_window.last_action == "rename":
            logger.debug(
                "[PrepareTable] Post-rename detected, preview will be updated after checked state restore"
            )

    def get_selected_files(self) -> list[FileItem]:
        """
        Returns a list of currently selected files (blue highlighted) in table display order.

        Returns:
            List of FileItem objects that are currently selected in the table view,
            sorted by their row position to maintain consistent rename order
        """
        if not self.parent_window.file_model or not self.parent_window.file_model.files:
            return []

        # Get currently selected rows from the file table view
        if not hasattr(self.parent_window, "file_table_view"):
            return []

        selection_model = self.parent_window.file_table_view.selectionModel()
        if not selection_model:
            return []

        selected_indexes = selection_model.selectedRows()
        # Sort by row number to maintain table display order (critical for consistent rename sequence)
        sorted_indexes = sorted(selected_indexes, key=lambda idx: idx.row())
        selected_files = []

        for index in sorted_indexes:
            row = index.row()
            if 0 <= row < len(self.parent_window.file_model.files):
                selected_files.append(self.parent_window.file_model.files[row])

        return selected_files

    def after_check_change(self) -> None:
        """
        Called after the selection state of any file is modified.

        Triggers UI refresh for the file table, updates the header state and label,
        and regenerates the filename preview.
        """
        self.parent_window.file_table_view.viewport().update()
        self.parent_window.update_files_label()
        self.parent_window.request_preview_update()

    def get_common_metadata_fields(self) -> list[str]:
        """
        Returns the intersection of metadata keys from all selected files.
        """
        selected_files = self.get_selected_files()
        if not selected_files:
            return []

        common_keys = None

        for file in selected_files:
            from oncutf.utils.metadata_cache_helper import get_metadata_cache_helper

            cache_helper = get_metadata_cache_helper(parent_window=self.parent_window)
            metadata = cache_helper.get_metadata_for_file(file)
            keys = set(metadata.keys())

            if common_keys is None:
                common_keys = keys
            else:
                common_keys &= keys  # intersection

        return sorted(common_keys) if common_keys else []

    def set_fields_from_list(self, field_names: list[str]) -> None:
        """
        Replaces the combo box entries with the given field names.
        """
        self.parent_window.combo.clear()
        for name in field_names:
            self.parent_window.combo.addItem(name, userData=name)

        # Trigger signal to refresh preview
        self.parent_window.updated.emit(self.parent_window)

    def restore_fileitem_metadata_from_cache(self) -> None:
        """
        After a folder reload (e.g. after rename), reassigns cached metadata
        to the corresponding FileItem objects in self.file_model.files.

        This allows icons and previews to remain consistent without rescanning.
        """
        restored = 0
        for file in self.parent_window.file_model.files:
            cached = self.parent_window.metadata_cache.get(file.full_path)
            if isinstance(cached, dict) and cached:
                file.metadata = cached
                restored += 1
        logger.info(f"[MetadataRestore] Restored metadata from cache for {restored} files.")
