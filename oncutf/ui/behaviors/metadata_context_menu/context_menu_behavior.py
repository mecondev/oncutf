"""Metadata context menu behavior - main coordinator.

Provides context menu functionality for metadata tree views through
composition of specialized handlers.

Author: Michael Economou
Date: 2026-01-05
"""
from typing import TYPE_CHECKING

from oncutf.ui.behaviors.metadata_context_menu.menu_builder import MenuBuilder
from oncutf.ui.behaviors.metadata_context_menu.protocols import ContextMenuWidget

if TYPE_CHECKING:
    from PyQt5.QtCore import QPoint


class MetadataContextMenuBehavior:
    """Behavior for metadata context menu operations in tree views.

    This behavior encapsulates all logic related to context menus.

    Uses composition with specialized handlers:
    - MenuBuilder: Menu creation and display
    """

    def __init__(self, widget: ContextMenuWidget) -> None:
        """Initialize the metadata context menu behavior.

        Args:
            widget: The host widget that provides menu operations

        """
        self._widget = widget
        self._menu_builder = MenuBuilder(widget)

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
