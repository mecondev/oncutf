"""
Module: hierarchical_combo_box.py

Author: Michael Economou
Date: 2025-01-27

This module provides a hierarchical QComboBox widget that displays items
in a tree-like structure with categories and subcategories.
It's designed to replace the flat list approach for large datasets
like metadata fields in the rename metadata module.
"""

from typing import Any

from core.pyqt_imports import (
    QComboBox,
    QStandardItem,
    QStandardItemModel,
    Qt,
    QTreeView,
    QWidget,
    pyqtSignal,
)
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class HierarchicalComboBox(QComboBox):
    """
    A QComboBox that displays items in a hierarchical tree structure.

    Features:
    - Tree-like display with expandable categories
    - Non-selectable category headers
    - Custom styling for categories vs items
    - Maintains compatibility with QComboBox API
    """

    # Signal emitted when an item is selected (not categories)
    item_selected = pyqtSignal(str, object)  # text, user_data

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        # Create tree view for hierarchical display
        self.tree_view = QTreeView()
        self.tree_view.setHeaderHidden(True)
        self.tree_view.setRootIsDecorated(True)
        self.tree_view.setItemsExpandable(True)
        self.tree_view.setExpandsOnDoubleClick(True)

        # Set the tree view as the popup
        self.setView(self.tree_view)

        # Create model
        self.model = QStandardItemModel()
        self.tree_view.setModel(self.model)

        # Connect signals
        self.tree_view.clicked.connect(self._on_item_clicked)
        self.tree_view.doubleClicked.connect(self._on_item_double_clicked)

        # Track categories for easy access
        self._categories: dict[str, QStandardItem] = {}

        # Apply styling
        self._apply_styling()

    def _apply_styling(self):
        """Apply custom styling for the hierarchical combo box."""
        # Basic styling for the combo box
        self.setStyleSheet("""
            QComboBox {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 4px 8px;
                background: white;
                min-height: 20px;
            }

            QComboBox:hover {
                border-color: #999;
            }

            QComboBox:focus {
                border-color: #0078d4;
            }

            QComboBox::drop-down {
                border: none;
                background: transparent;
                width: 18px;
            }

            QComboBox::down-arrow {
                image: url(resources/icons/feather_icons/chevrons-down.svg);
                width: 12px;
                height: 12px;
            }
        """)

        # Styling for the tree view popup
        self.tree_view.setStyleSheet("""
            QTreeView {
                background: white;
                border: 1px solid #ccc;
                border-radius: 4px;
                outline: none;
            }

            QTreeView::item {
                padding: 4px 8px;
                border: none;
            }

            QTreeView::item:hover {
                background-color: #f0f0f0;
            }

            QTreeView::item:selected {
                background-color: #0078d4;
                color: white;
            }

            QTreeView::branch {
                background: transparent;
            }

            QTreeView::branch:has-children:!has-siblings:closed,
            QTreeView::branch:closed:has-children:has-siblings {
                image: url(resources/icons/feather_icons/chevron-right.svg);
            }

            QTreeView::branch:open:has-children:!has-siblings,
            QTreeView::branch:open:has-children:has-siblings {
                image: url(resources/icons/feather_icons/chevron-down.svg);
            }
        """)

    def add_category(self, category_name: str, category_data: Any = None) -> QStandardItem:
        """
        Add a new category to the hierarchical combo box.

        Args:
            category_name: Display name for the category
            category_data: Optional data associated with the category

        Returns:
            The created category item
        """
        category_item = QStandardItem(category_name)
        if category_data:
            category_item.setData(category_data, Qt.UserRole)

        # Make category non-selectable
        category_item.setFlags(category_item.flags() & ~Qt.ItemIsSelectable)

        # Style category differently
        category_item.setBackground(Qt.lightGray)
        category_item.setForeground(Qt.darkGray)

        # Add to model and track
        self.model.appendRow(category_item)
        self._categories[category_name] = category_item

        return category_item

    def add_item_to_category(self, category_name: str, item_text: str, item_data: Any = None) -> QStandardItem:
        """
        Add an item to a specific category.

        Args:
            category_name: Name of the category to add the item to
            item_text: Display text for the item
            item_data: Optional data associated with the item

        Returns:
            The created item
        """
        if category_name not in self._categories:
            logger.warning(f"Category '{category_name}' not found, creating it")
            self.add_category(category_name)

        category_item = self._categories[category_name]
        item = QStandardItem(item_text)

        if item_data:
            item.setData(item_data, Qt.UserRole)

        # Make item selectable
        item.setFlags(item.flags() | Qt.ItemIsSelectable)

        # Add to category
        category_item.appendRow(item)

        return item

    def add_item(self, item_text: str, item_data: Any = None) -> QStandardItem:
        """
        Add an item to the root level (no category).

        Args:
            item_text: Display text for the item
            item_data: Optional data associated with the item

        Returns:
            The created item
        """
        item = QStandardItem(item_text)

        if item_data:
            item.setData(item_data, Qt.UserRole)

        # Make item selectable
        item.setFlags(item.flags() | Qt.ItemIsSelectable)

        # Add to root
        self.model.appendRow(item)

        return item

    def clear(self):
        """Clear all items and categories."""
        super().clear()
        self.model.clear()
        self._categories.clear()

    def get_current_data(self) -> Any:
        """Get the data of the currently selected item."""
        current_index = self.tree_view.currentIndex()
        if current_index.isValid():
            item = self.model.itemFromIndex(current_index)
            if item and item.flags() & Qt.ItemIsSelectable:
                return item.data(Qt.UserRole)
        return None

    def get_current_text(self) -> str:
        """Get the text of the currently selected item."""
        current_index = self.tree_view.currentIndex()
        if current_index.isValid():
            item = self.model.itemFromIndex(current_index)
            if item and item.flags() & Qt.ItemIsSelectable:
                return item.text()
        return ""

    def set_current_data(self, data: Any):
        """Set the current selection by data value."""
        for row in range(self.model.rowCount()):
            item = self.model.item(row)
            if item:
                # Check if this is a category
                if item.flags() & Qt.ItemIsSelectable:
                    if item.data(Qt.UserRole) == data:
                        self.tree_view.setCurrentIndex(self.model.indexFromItem(item))
                        return
                else:
                    # Check children of category
                    for child_row in range(item.rowCount()):
                        child_item = item.child(child_row)
                        if child_item and child_item.data(Qt.UserRole) == data:
                            self.tree_view.setCurrentIndex(self.model.indexFromItem(child_item))
                            return

    def expand_all(self):
        """Expand all categories."""
        self.tree_view.expandAll()

    def collapse_all(self):
        """Collapse all categories."""
        self.tree_view.collapseAll()

    def expand_category(self, category_name: str):
        """Expand a specific category."""
        if category_name in self._categories:
            category_item = self._categories[category_name]
            category_index = self.model.indexFromItem(category_item)
            self.tree_view.expand(category_index)

    def _on_item_clicked(self, index):
        """Handle item click in the tree view."""
        item = self.model.itemFromIndex(index)
        if item and item.flags() & Qt.ItemIsSelectable:
            # This is a selectable item, not a category
            text = item.text()
            data = item.data(Qt.UserRole)

            # Update the combo box display
            self.setEditText(text)

            # Emit signal
            self.item_selected.emit(text, data)

            # Close the popup
            self.hidePopup()

    def _on_item_double_clicked(self, index):
        """Handle item double click in the tree view."""
        item = self.model.itemFromIndex(index)
        if item and item.flags() & Qt.ItemIsSelectable:
            # Same as single click for selectable items
            self._on_item_clicked(index)
        else:
            # For categories, toggle expansion
            if self.tree_view.isExpanded(index):
                self.tree_view.collapse(index)
            else:
                self.tree_view.expand(index)

    def populate_from_metadata_groups(self, grouped_data: dict[str, list[tuple[str, Any]]]):
        """
        Populate the combo box from grouped metadata data.

        Args:
            grouped_data: Dictionary with category names as keys and lists of (text, data) tuples as values
        """
        self.clear()

        for category_name, items in grouped_data.items():
            if items:  # Only add categories that have items
                self.add_category(category_name)

                for item_text, item_data in sorted(items):
                    self.add_item_to_category(category_name, item_text, item_data)

        # Expand all categories by default
        self.expand_all()
