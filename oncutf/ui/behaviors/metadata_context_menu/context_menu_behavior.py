"""Metadata context menu behavior - main coordinator.

Provides context menu functionality for metadata tree views through
composition of specialized handlers.

Author: Michael Economou
Date: 2026-01-05
"""
from typing import TYPE_CHECKING

from oncutf.ui.behaviors.metadata_context_menu.column_integration import ColumnIntegration
from oncutf.ui.behaviors.metadata_context_menu.key_mapping import (
    map_metadata_key_to_column_key,
)
from oncutf.ui.behaviors.metadata_context_menu.menu_builder import MenuBuilder
from oncutf.ui.behaviors.metadata_context_menu.protocols import ContextMenuWidget

if TYPE_CHECKING:
    from PyQt5.QtCore import QPoint


class MetadataContextMenuBehavior:
    """Behavior for metadata context menu operations in tree views.

    This behavior encapsulates all logic related to context menus:
    - Creating and displaying context menus
    - Managing column visibility in file view
    - Mapping metadata keys to file table columns

    Uses composition with specialized handlers:
    - MenuBuilder: Menu creation and display
    - ColumnIntegration: File view column operations
    """

    def __init__(self, widget: ContextMenuWidget) -> None:
        """Initialize the metadata context menu behavior.

        Args:
            widget: The host widget that provides menu operations
        """
        self._widget = widget
        self._column_integration = ColumnIntegration(widget)
        self._menu_builder = MenuBuilder(widget, self._column_integration)

    # =====================================
    # Public API
    # =====================================

    def show_context_menu(self, position: "QPoint") -> None:
        """Display context menu with available options.

        Args:
            position: Position where the context menu should appear
        """
        self._menu_builder.show_context_menu(position)

    def cleanup_menu(self) -> None:
        """Clean up the current menu reference."""
        self._menu_builder._cleanup_menu()

    # =====================================
    # Column Visibility Delegation
    # =====================================

    def _is_column_visible_in_file_view(self, key_path: str) -> bool:
        """Check if a column is already visible in the file view.

        Args:
            key_path: Metadata key path

        Returns:
            True if column is visible, False otherwise
        """
        return self._column_integration.is_column_visible_in_file_view(key_path)

    def _add_column_to_file_view(self, key_path: str) -> None:
        """Add a metadata column to the file view.

        Args:
            key_path: Metadata key path
        """
        self._column_integration.add_column_to_file_view(key_path)

    def _remove_column_from_file_view(self, key_path: str) -> None:
        """Remove a metadata column from the file view.

        Args:
            key_path: Metadata key path
        """
        self._column_integration.remove_column_from_file_view(key_path)

    def _get_file_table_view(self):
        """Get the file table view from the parent hierarchy.

        Returns:
            FileTableView or None if not found
        """
        return self._column_integration._get_file_table_view()

    # =====================================
    # Key Mapping Delegation
    # =====================================

    def _map_metadata_key_to_column_key(self, metadata_key: str) -> str | None:
        """Map a metadata key path to a file table column key.

        Args:
            metadata_key: Metadata key path (e.g., "EXIF:Make")

        Returns:
            Column key if found, None otherwise
        """
        return map_metadata_key_to_column_key(metadata_key)

    # =====================================
    # Icon Helper Delegation
    # =====================================

    def _get_menu_icon(self, icon_name: str):
        """Get menu icon using the icon loader system.

        Args:
            icon_name: Name of the icon to load

        Returns:
            QIcon or None if icon loading fails
        """
        return self._menu_builder._get_menu_icon(icon_name)


__all__ = ["MetadataContextMenuBehavior"]
