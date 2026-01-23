"""Module: utils.py.

Author: Michael Economou
Date: 2026-01-02

Utility classes for file tree view widget.

Contains helper classes like DragCancelFilter that prevent selection
clearing during drag operations.
"""

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class DragCancelFilter:
    """Filter that prevents selection clearing during drag operations.

    This is used to maintain file selection when dragging from FileTableView
    to MetadataTreeView, especially when no modifier keys are pressed.
    """

    def __init__(self) -> None:
        """Initialize drag cancel filter with inactive state."""
        self._active = False
        self._preserved_selection: set = set()

    def activate(self) -> None:
        """Activate the filter to preserve current selection."""
        self._active = True
        logger.debug(
            "[DragCancelFilter] Activated - preserving selection", extra={"dev_only": True}
        )

    def deactivate(self) -> None:
        """Deactivate the filter."""
        if self._active:
            self._active = False
            self._preserved_selection.clear()
            logger.debug("[DragCancelFilter] Deactivated", extra={"dev_only": True})

    def preserve_selection(self, selection: set) -> None:
        """Store selection to preserve during drag.

        Args:
            selection: Set of items to preserve

        """
        self._preserved_selection = selection.copy()

    def get_preserved_selection(self) -> set:
        """Get preserved selection.

        Returns:
            Copy of the preserved selection set

        """
        return self._preserved_selection.copy()

    def is_active(self) -> bool:
        """Check if filter is active.

        Returns:
            True if filter is active

        """
        return self._active


# Global instance for application-wide use
_drag_cancel_filter = DragCancelFilter()


def get_drag_cancel_filter() -> DragCancelFilter:
    """Get the global drag cancel filter instance.

    Returns:
        Global DragCancelFilter instance

    """
    return _drag_cancel_filter
