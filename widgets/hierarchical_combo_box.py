"""
Module: hierarchical_combo_box.py

Author: Michael Economou
Date: 2025-01-27

This module provides a hierarchical QComboBox widget that displays items
in a tree-like structure with categories and subcategories.
It's designed to replace the flat list approach for large datasets
like metadata fields in the rename metadata module.
"""

import time
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

        # Debounce mechanism to prevent rapid successive clicks
        self._last_click_time = 0
        self._click_debounce_delay = 100  # 100ms debounce delay

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
        # Get from the tree view current index
        current_index = self.tree_view.currentIndex()
        if current_index.isValid():
            item = self.model.itemFromIndex(current_index)
            if item and item.flags() & Qt.ItemIsSelectable:
                data = item.data(Qt.UserRole)
                logger.debug(f"get_current_data from tree view: {data}")
                return data

        # Fallback: try to find by current text
        current_text = self.currentText()
        if current_text:
            logger.debug(f"Searching for item with text: {current_text}")
            for row in range(self.model.rowCount()):
                item = self.model.item(row)
                if item:
                    for child_row in range(item.rowCount()):
                        child_item = item.child(child_row)
                        if child_item and child_item.text() == current_text:
                            data = child_item.data(Qt.UserRole)
                            logger.debug(f"Found item with data: {data}")
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
        self.select_item_by_data(data)

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
        # Debounce mechanism to prevent rapid successive clicks
        current_time = int(time.time() * 1000)  # Current time in milliseconds
        if current_time - self._last_click_time < self._click_debounce_delay:
            logger.debug("Click debounced - too soon after previous click")
            return

        self._last_click_time = current_time

        item = self.model.itemFromIndex(index)
        if item and item.flags() & Qt.ItemIsSelectable:
            # This is a selectable item, not a category
            text = item.text()
            data = item.data(Qt.UserRole)

            # Update the combo box display text
            self.setCurrentText(text)

            # Emit signal
            self.item_selected.emit(text, data)

            logger.debug(f"Item clicked: {text} with data: {data}")

            # Use global timer manager to close popup with delay to avoid flickering
            try:
                from utils.timer_manager import TimerType, get_timer_manager
                timer_manager = get_timer_manager()
                timer_manager.schedule(
                    self.hidePopup,
                    delay=50,  # 50ms delay to avoid immediate close
                    timer_type=TimerType.UI_UPDATE,
                    timer_id="hierarchical_combo_popup_close"
                )
            except ImportError:
                # Fallback to immediate close if timer manager not available
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

    def populate_from_metadata_groups(self, groups: dict, default_key: str = None):
        """Populate the combo box from grouped metadata data."""
        self.model.clear()
        logger.debug(f"Populating combo box with groups: {list(groups.keys())}")

        first_item = None

        for group_name, items in groups.items():
            if items:  # Only add groups that have items
                group_item = QStandardItem(group_name)
                group_item.setFlags(Qt.ItemIsEnabled)

                for item_name, item_data in items:
                    child_item = QStandardItem(item_name)
                    child_item.setData(item_data, Qt.UserRole)
                    child_item.setFlags(child_item.flags() | Qt.ItemIsSelectable)
                    group_item.appendRow(child_item)

                    if first_item is None:
                        first_item = child_item

                self.model.appendRow(group_item)

        # Set the model
        self.setModel(self.model)

        # Force UI update
        self.model.layoutChanged.emit()

        # Select first item if available
        if first_item:
            combo_index = self.model.indexFromItem(first_item).row()
            self.setCurrentIndex(combo_index)

            index = self.model.indexFromItem(first_item)
            self.tree_view.setCurrentIndex(index)
            self.tree_view.scrollTo(index)

            self.setCurrentText(first_item.text())

            self.item_selected.emit(first_item.text(), first_item.data(Qt.UserRole))

            logger.debug(
                f"Selected first item: {first_item.text()} with data: {first_item.data(Qt.UserRole)}"
            )
        else:
            logger.warning("No items to populate in hierarchical combo box")

    def select_item_by_data(self, data: Any):
        """Select an item by its data value."""
        for row in range(self.model.rowCount()):
            item = self.model.item(row)
            if item:
                # Check children of group
                for child_row in range(item.rowCount()):
                    child_item = item.child(child_row)
                    if child_item and child_item.data(Qt.UserRole) == data:
                        combo_index = self.model.indexFromItem(child_item).row()
                        self.setCurrentIndex(combo_index)

                        index = self.model.indexFromItem(child_item)
                        self.tree_view.setCurrentIndex(index)
                        self.tree_view.scrollTo(index)

                        self.setCurrentText(child_item.text())

                        self.item_selected.emit(child_item.text(), child_item.data(Qt.UserRole))
                        logger.debug(
                            f"Selected item by data: {child_item.text()} with data: {data}"
                        )
                        return

        logger.warning(f"select_item_by_data: No item found with data: {data}")
