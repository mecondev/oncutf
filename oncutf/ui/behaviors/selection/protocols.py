"""Protocol definitions for selection behavior.

Author: Michael Economou
Date: 2026-01-05
"""
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from oncutf.core.pyqt_imports import QModelIndex


class SelectableWidget(Protocol):
    """Protocol defining requirements for widgets that can use SelectionBehavior."""

    def selectionModel(self):
        """Return the selection model."""
        ...

    def model(self):
        """Return the data model."""
        ...

    def blockSignals(self, block: bool) -> bool:
        """Block/unblock signals."""
        ...

    def viewport(self):
        """Return the viewport widget."""
        ...

    def visualRect(self, index: "QModelIndex"):
        """Return visual rectangle for index."""
        ...

    def clearSelection(self) -> None:
        """Clear selection."""
        ...

    def keyboardModifiers(self):
        """Get current keyboard modifiers."""
        ...


__all__ = ["SelectableWidget"]
