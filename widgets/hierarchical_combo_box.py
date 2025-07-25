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
                min-width: 200px;
                max-height: 300px;
            }

            QTreeView::item {
                padding: 4px 8px;
                border: none;
                min-height: 20px;
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
        # First try to get from the tree view current index
        current_index = self.tree_view.currentIndex()
        if current_index.isValid():
            item = self.model.itemFromIndex(current_index)
            if item and item.flags() & Qt.ItemIsSelectable:
                data = item.data(Qt.UserRole)
                logger.debug(f"get_current_data from tree view: {data}")
                return data

        # If no valid selection in tree view, try to find by current text
        current_text = self.currentText()
        if current_text:
            logger.debug(f"Searching for item with text: {current_text}")
            for row in range(self.model.rowCount()):
                item = self.model.item(row)
                if item:
                    # Check if this is a category
                    if item.flags() & Qt.ItemIsSelectable:
                        if item.text() == current_text:
                            data = item.data(Qt.UserRole)
                            logger.debug(f"Found root item with data: {data}")
                            return data
                    else:
                        # Check children of category
                        for child_row in range(item.rowCount()):
                            child_item = item.child(child_row)
                            if child_item and child_item.text() == current_text:
                                data = child_item.data(Qt.UserRole)
                                logger.debug(f"Found child item with data: {data}")
                                return data

        logger.warning(f"get_current_data: No item found for text '{current_text}'")
        return None

    def get_current_text(self) -> str:
        """Get the text of the currently selected item."""
        # First try to get from the tree view current index
        current_index = self.tree_view.currentIndex()
        if current_index.isValid():
            item = self.model.itemFromIndex(current_index)
            if item and item.flags() & Qt.ItemIsSelectable:
                return item.text()

        # Fallback to the combo box current text
        return self.currentText()

    def set_current_data(self, data: Any):
        """Set the current selection by data value."""
        logger.debug(f"set_current_data called with data: {data}")

        for row in range(self.model.rowCount()):
            item = self.model.item(row)
            if item:
                # Check if this is a category
                if item.flags() & Qt.ItemIsSelectable:
                    if item.data(Qt.UserRole) == data:
                        self.tree_view.setCurrentIndex(self.model.indexFromItem(item))
                        self.setCurrentText(item.text())
                        self.setEditText(item.text())  # Ensure edit text is updated
                        # Force the combo box to display the text
                        self.setCurrentText(item.text())
                        # Force update the display
                        self.force_update_display(item.text())
                        # Set the display text using the new method
                        self.set_display_text(item.text())
                        logger.debug(f"Set current data to root item: {item.text()}")
                        return
                else:
                    # Check children of category
                    for child_row in range(item.rowCount()):
                        child_item = item.child(child_row)
                        if child_item and child_item.data(Qt.UserRole) == data:
                            self.tree_view.setCurrentIndex(self.model.indexFromItem(child_item))
                            self.setCurrentText(child_item.text())
                            self.setEditText(child_item.text())  # Ensure edit text is updated
                            # Force the combo box to display the text
                            self.setCurrentText(child_item.text())
                            # Force update the display
                            self.force_update_display(child_item.text())
                            # Set the display text using the new method
                            self.set_display_text(child_item.text())
                            logger.debug(f"Set current data to child item: {child_item.text()}")
                            return

        logger.warning(f"set_current_data: No item found with data: {data}")

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

            # Update the combo box display text
            self.setCurrentText(text)
            self.setEditText(text)  # Ensure the edit text is also updated

            # Force the combo box to display the text
            self.setCurrentText(text)

            # Force update the display
            self.force_update_display(text)

            # Set the display text using the new method
            self.set_display_text(text)

            # Emit signal
            self.item_selected.emit(text, data)

            logger.debug(f"Item clicked: {text} with data: {data}")

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

    def setCurrentText(self, text: str):
        """Set the current text display of the combo box."""
        # Override to work with our custom view
        super().setCurrentText(text)

    def currentText(self) -> str:
        """Get the current text display of the combo box."""
        return super().currentText()

    def force_update_display(self, text: str):
        """Force the combo box to update its display with the given text."""
        # Set the text in multiple ways to ensure it's displayed
        self.setCurrentText(text)
        self.setEditText(text)

        # Force a repaint
        self.update()

        logger.debug(f"Force updated display with text: {text}")

    def set_display_text(self, text: str):
        """Set the display text of the combo box and ensure it's visible."""
        # Set the text in the combo box
        self.setCurrentText(text)
        self.setEditText(text)

        # Force the combo box to show the text
        self.setCurrentText(text)

        # Force a repaint
        self.update()

        logger.debug(f"Set display text to: {text}")

    def schedule_display_update(self, text: str, delay_ms: int = 50):
        """Schedule a delayed display update."""
        try:
            from utils.timer_manager import schedule_ui_update
            schedule_ui_update(lambda: self.set_display_text(text), delay_ms)
            logger.debug(f"Scheduled display update for text: {text} in {delay_ms}ms")
        except Exception as e:
            logger.warning(f"Could not schedule display update: {e}")
            # Fallback to immediate update
            self.set_display_text(text)

    def populate_from_metadata_groups(self, grouped_data: dict[str, list[tuple[str, Any]]]):
        """Populate the combo box from grouped metadata data."""
        self.clear()
        logger.debug(f"Populating combo box with groups: {list(grouped_data.keys())}")

        first_item = None

        for category_name, items in grouped_data.items():
            if items:  # Only add categories that have items
                category_item = self.add_category(category_name)

                for item_text, item_data in sorted(items):
                    item = self.add_item_to_category(category_name, item_text, item_data)
                    if first_item is None:
                        first_item = item

        # Expand all categories
        self.expand_all()

        # Select first item if available
        if first_item:
            # Set the current text in the combo box
            self.setCurrentText(first_item.text())

            # Set the current index in the tree view
            index = self.model.indexFromItem(first_item)
            self.tree_view.setCurrentIndex(index)

            # Ensure the combo box shows the selected text
            self.setEditText(first_item.text())

            # Force the combo box to display the text
            self.setCurrentText(first_item.text())

            # Force update the display
            self.force_update_display(first_item.text())

            # Set the display text using the new method
            self.set_display_text(first_item.text())

            # Schedule a delayed display update
            self.schedule_display_update(first_item.text(), 100)

            # Emit signal for first item
            self.item_selected.emit(first_item.text(), first_item.data(Qt.UserRole))

            logger.debug(f"Selected first item: {first_item.text()} with data: {first_item.data(Qt.UserRole)}")
        else:
            logger.warning("No items to populate in hierarchical combo box")
