"""Tree navigation utilities for metadata editing.

This module provides utilities for navigating the metadata tree structure,
finding items by path, and restoring selections.

Author: Michael Economou
Date: 2026-01-01
"""

from typing import TYPE_CHECKING

from PyQt5.QtCore import QModelIndex, Qt

from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.ui.behaviors.metadata_edit.metadata_edit_behavior import EditableWidget

logger = get_cached_logger(__name__)


class TreeNavigator:
    """Provides tree navigation utilities for metadata tree views.

    Handles:
    - Getting path from root to an item
    - Finding items by their display path
    - Finding items by their metadata key path
    - Restoring selection after operations
    """

    def __init__(self, widget: "EditableWidget") -> None:
        """Initialize the tree navigator.

        Args:
            widget: The host widget that provides tree access

        """
        self._widget = widget

    def get_item_path(self, index: QModelIndex) -> list[str]:
        """Get the path from root to the given index.

        Args:
            index: QModelIndex to get path for

        Returns:
            list[str]: List of display texts from root to index

        """
        path: list[str] = []
        current = index

        while current.isValid():
            text = current.data(Qt.ItemDataRole.DisplayRole)
            path.insert(0, text)
            current = current.parent()

        return path

    def find_item_by_path(self, path: list[str]) -> QModelIndex | None:
        """Find an item in the tree by its path from root.

        Args:
            path: List of display texts from root to target item

        Returns:
            QModelIndex if found, None otherwise

        """
        if not path:
            return None

        model = self._widget.model()
        if not model:
            return None

        # Start from root
        current_index = QModelIndex()

        for text in path:
            found = False
            row_count = model.rowCount(current_index)

            for row in range(row_count):
                child_index = model.index(row, 0, current_index)
                if child_index.data(Qt.ItemDataRole.DisplayRole) == text:
                    current_index = child_index
                    found = True
                    break

            if not found:
                logger.debug("Path item not found: %s", text)
                return None

        return current_index

    def find_path_by_key(self, key_path: str) -> list[str] | None:
        """Find the tree path (display names) for a given metadata key path.

        Args:
            key_path: Metadata key like "File:FileName" or "EXIF:Make"

        Returns:
            List of display names from root to item, e.g. ["File Info", "File Name"]
            None if not found

        """
        model = self._widget.model()
        if not model:
            return None

        # Search recursively through the tree
        def search_tree(parent_index: QModelIndex, target_key: str) -> list[str] | None:
            row_count = model.rowCount(parent_index)
            for row in range(row_count):
                index = model.index(row, 0, parent_index)

                # Check if this item's key matches
                item_data = index.data(Qt.ItemDataRole.UserRole)
                if item_data and isinstance(item_data, dict):
                    item_key = item_data.get("key", "")
                    if item_key == target_key:
                        # Found it! Build the path
                        return self.get_item_path(index)

                # Search children recursively
                child_path = search_tree(index, target_key)
                if child_path:
                    return child_path

            return None

        return search_tree(QModelIndex(), key_path)

    def restore_selection(self, path: list[str]) -> None:
        """Restore selection to the given path.

        Args:
            path: List of display names from root to item

        """
        restored_index = self.find_item_by_path(path)
        if restored_index and restored_index.isValid():
            self._widget.setCurrentIndex(restored_index)
            self._widget.scrollTo(restored_index)
            logger.debug("Restored selection to: %s", " > ".join(path))
        else:
            logger.debug("Could not restore selection, path not found")

    def get_key_path(self, index: QModelIndex) -> str:
        """Return the full key path for the given index.

        Args:
            index: QModelIndex to get key path for

        Returns:
            str: Key path like "EXIF/DateTimeOriginal" or "XMP/Creator"

        """
        if not index.isValid():
            return ""

        # If on Value column, get the corresponding Key
        if index.column() == 1:
            index = index.sibling(index.row(), 0)

        # Get the text of the current item
        item_text = index.data()

        # Find the parent group
        parent_index = index.parent()
        if parent_index.isValid():
            parent_text = parent_index.data()
            return f"{parent_text}/{item_text}"

        return item_text
