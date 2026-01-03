"""Protocol definitions for column management behavior.

Author: Michael Economou
Date: 2026-01-05
"""
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from PyQt5.QtCore import QModelIndex
    from PyQt5.QtWidgets import QAbstractItemModel, QHeaderView, QWidget


class ColumnManageableWidget(Protocol):
    """Protocol for widgets that can use ColumnManagementBehavior.

    Defines required methods that widgets must implement to support
    column management functionality.
    """

    def horizontalHeader(self) -> "QHeaderView":
        """Return the horizontal header."""
        ...

    def model(self) -> "QAbstractItemModel":
        """Return the data model."""
        ...

    def setColumnWidth(self, column: int, width: int) -> None:
        """Set width of a column."""
        ...

    def columnWidth(self, column: int) -> int:
        """Get width of a column."""
        ...

    def viewport(self) -> "QWidget":
        """Return the viewport widget."""
        ...

    def updateGeometry(self) -> None:
        """Update geometry."""
        ...

    def indexAt(self, point) -> "QModelIndex":
        """Return index at point."""
        ...

    def is_empty(self) -> bool:
        """Check if the table is empty."""
        ...

    def _get_main_window(self):
        """Get reference to main window."""
        ...


__all__ = ["ColumnManageableWidget"]
