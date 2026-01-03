"""Column visibility integration with file table view.

Handles add/remove column operations from metadata context menu.

Author: Michael Economou
Date: 2026-01-05
"""
from typing import TYPE_CHECKING

from oncutf.ui.behaviors.metadata_context_menu.key_mapping import (
    map_metadata_key_to_column_key,
)
from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.ui.behaviors.metadata_context_menu.protocols import ContextMenuWidget

logger = get_cached_logger(__name__)


class ColumnIntegration:
    """Manages column visibility integration with file table view."""

    def __init__(self, widget: "ContextMenuWidget"):
        """Initialize column integration.

        Args:
            widget: The host widget
        """
        self._widget = widget

    def is_column_visible_in_file_view(self, key_path: str) -> bool:
        """Check if a column is already visible in the file view.

        Args:
            key_path: Metadata key path

        Returns:
            True if column is visible, False otherwise
        """
        try:
            # Get the file table view
            file_table_view = self._get_file_table_view()
            if not file_table_view:
                return False

            # Check if column is in visible columns configuration
            visible_columns = getattr(file_table_view, "_visible_columns", {})

            # Map metadata key to column key
            column_key = map_metadata_key_to_column_key(key_path)
            if not column_key:
                return False

            # Check if column is visible
            from oncutf.config import FILE_TABLE_COLUMN_CONFIG

            if column_key in FILE_TABLE_COLUMN_CONFIG:
                default_visible = FILE_TABLE_COLUMN_CONFIG[column_key]["default_visible"]
                return visible_columns.get(column_key, default_visible)

        except Exception as e:
            logger.warning("Error checking column visibility: %s", e)

        return False

    def add_column_to_file_view(self, key_path: str) -> None:
        """Add a metadata column to the file view.

        Args:
            key_path: Metadata key path
        """
        try:
            # Get the file table view
            file_table_view = self._get_file_table_view()
            if not file_table_view:
                return

            # Map metadata key to column key
            column_key = map_metadata_key_to_column_key(key_path)
            if not column_key:
                return

            # Update visibility configuration
            if hasattr(file_table_view, "_visible_columns"):
                file_table_view._visible_columns[column_key] = True

                # Save configuration
                if hasattr(file_table_view, "_save_column_visibility_config"):
                    file_table_view._save_column_visibility_config()

                # Update table display
                if hasattr(file_table_view, "_update_table_columns"):
                    file_table_view._update_table_columns()

                logger.info(
                    "Added column '%s' -> '%s' to file view",
                    key_path,
                    column_key,
                )

        except Exception as e:
            logger.exception("Error adding column to file view: %s", e)

    def remove_column_from_file_view(self, key_path: str) -> None:
        """Remove a metadata column from the file view.

        Args:
            key_path: Metadata key path
        """
        try:
            # Get the file table view
            file_table_view = self._get_file_table_view()
            if not file_table_view:
                return

            # Map metadata key to column key
            column_key = map_metadata_key_to_column_key(key_path)
            if not column_key:
                return

            # Update visibility configuration
            if hasattr(file_table_view, "_visible_columns"):
                file_table_view._visible_columns[column_key] = False

                # Save configuration
                if hasattr(file_table_view, "_save_column_visibility_config"):
                    file_table_view._save_column_visibility_config()

                # Update table display
                if hasattr(file_table_view, "_update_table_columns"):
                    file_table_view._update_table_columns()

                logger.info(
                    "Removed column '%s' -> '%s' from file view",
                    key_path,
                    column_key,
                )

        except Exception as e:
            logger.exception("Error removing column from file view: %s", e)

    def _get_file_table_view(self):
        """Get the file table view from the parent hierarchy.

        Returns:
            FileTableView or None if not found
        """
        try:
            # Look for file table view in parent hierarchy
            parent = self._widget.parent()
            while parent:
                if hasattr(parent, "file_table_view"):
                    return parent.file_table_view

                # Check if parent has file_table attribute
                if hasattr(parent, "file_table"):
                    return parent.file_table

                # Check for main window with file table
                if hasattr(parent, "findChild"):
                    from oncutf.ui.widgets.file_table_view import FileTableView

                    file_table = parent.findChild(FileTableView)
                    if file_table:
                        return file_table

                parent = parent.parent()

        except Exception as e:
            logger.warning("Error finding file table view: %s", e)

        return None


__all__ = ["ColumnIntegration"]
