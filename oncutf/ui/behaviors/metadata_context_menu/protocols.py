"""Protocol definitions for metadata context menu behavior.

Author: Michael Economou
Date: 2026-01-05
"""
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from PyQt5.QtCore import QModelIndex, QPoint
    from PyQt5.QtWidgets import QMenu, QWidget


class ContextMenuWidget(Protocol):
    """Protocol defining the interface required for metadata context menu behavior.

    This protocol specifies what methods a widget must provide to use
    MetadataContextMenuBehavior for context menu operations.
    """

    # From MetadataTreeView
    _current_menu: "QMenu | None"
    _current_file_path: str | None
    _is_placeholder_mode: bool

    # Behavior references
    _edit_behavior: Any
    _cache_behavior: Any

    def indexAt(self, pos: "QPoint") -> "QModelIndex":
        """Get the model index at the given position.

        Args:
            pos: Position in widget coordinates

        Returns:
            QModelIndex: Model index at position
        """
        ...

    def mapToGlobal(self, pos: "QPoint") -> "QPoint":
        """Map widget position to global screen coordinates.

        Args:
            pos: Position in widget coordinates

        Returns:
            QPoint: Global screen position
        """
        ...

    def property(self, name: str) -> Any:
        """Get widget property value.

        Args:
            name: Property name

        Returns:
            Any: Property value
        """
        ...

    def parent(self) -> "QWidget | None":
        """Get parent widget.

        Returns:
            QWidget | None: Parent widget
        """
        ...

    def _get_current_selection(self) -> list[Any]:
        """Get the currently selected file items.

        Returns:
            list[Any]: List of selected FileItem objects
        """
        ...


__all__ = ["ContextMenuWidget"]
