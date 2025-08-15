"""Hierarchical QComboBox widget with tree-like structure support.

This module provides a hierarchical QComboBox widget that displays items
in a tree-like structure with categories and subcategories.
It's designed to replace the flat list approach for large datasets
like metadata fields in the rename metadata module.

Author: Michael Economou
Date: 2025-01-27
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
from widgets.ui_delegates import TreeViewItemDelegate

logger = get_cached_logger(__name__)


class _AliasHeaderTreeView(QTreeView):
	"""QTreeView subclass providing a headerHidden() alias for compatibility tests.

	Exposes headerHidden() that forwards to isHeaderHidden() to accommodate
	test suites expecting the old method name.
	"""

	def headerHidden(self) -> bool:  # pragma: no cover - trivial alias
		return self.isHeaderHidden()


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

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # Create tree view for hierarchical display
        self.tree_view = _AliasHeaderTreeView()
        self.tree_view.setObjectName("hier_combo_popup")
        self.tree_view.setHeaderHidden(True)
        self.tree_view.setRootIsDecorated(True)  # Show branch indicators for all items
        self.tree_view.setItemsExpandable(True)
        self.tree_view.setIndentation(16)  # Set smaller indent (default is 20px)
        self.tree_view.setAlternatingRowColors(False)

        # Enable mouse tracking for hover effects
        self.tree_view.setMouseTracking(True)

        # Use CSS-only approach for simplicity (no delegate needed)

        # Set the tree view as the popup
        self.setView(self.tree_view)

        # Create model
        self.model: QStandardItemModel = QStandardItemModel()
        self.tree_view.setModel(self.model)

        # Set the delegate
        self.delegate = TreeViewItemDelegate(self.tree_view)
        self.tree_view.setItemDelegate(self.delegate)
        self.delegate.install_event_filter(self.tree_view)

        # Connect signals
        self.tree_view.clicked.connect(self._on_item_clicked)
        self.tree_view.doubleClicked.connect(self._on_item_double_clicked)

        # Connect mouse events for hover tracking
        # self.tree_view.viewport().installEventFilter(self) # This line is removed as per the new_code

        # Track categories for easy access
        self._categories: dict[str, QStandardItem] = {}

    def eventFilter(self, obj: QWidget, event) -> bool:
        """Handle mouse events for hover tracking."""
        viewport = self.tree_view.viewport()
        if obj == viewport:
            if event.type() == event.MouseMove:
                # Get the item under the mouse
                pos = event.pos()
                index = self.tree_view.indexAt(pos)
                delegate = self.tree_view.itemDelegate()
                if isinstance(delegate, TreeViewItemDelegate):
                    delegate.hovered_index = index if index.isValid() else None
                if hasattr(obj, "update"):
                    obj.update()
            elif event.type() == event.Leave:
                # Clear hover when mouse leaves the viewport
                delegate = self.tree_view.itemDelegate()
                if isinstance(delegate, TreeViewItemDelegate):
                    delegate.hovered_index = None
                if hasattr(obj, "update"):
                    obj.update()

        return super().eventFilter(obj, event)

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
            item.setData(item_data, Qt.ItemDataRole.UserRole)

        # Make item selectable
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsSelectable)

        # Add to root
        self.model.appendRow(item)

        return item

    def clear(self) -> None:
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
            if item and item.flags() & Qt.ItemFlag.ItemIsSelectable:
                data = item.data(Qt.ItemDataRole.UserRole)
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
                            data = child_item.data(Qt.ItemDataRole.UserRole)
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
            if item and item.flags() & Qt.ItemFlag.ItemIsSelectable:
                return item.text()

        # Fallback to the combo box current text
        return self.currentText()

    def set_current_data(self, data: Any) -> None:
        """Set the current selection by data value."""
        logger.debug(f"set_current_data called with data: {data}")
        self.select_item_by_data(data)

    def expand_all(self) -> None:
        """Expand all categories."""
        self.tree_view.expandAll()

    def collapse_all(self) -> None:
        """Collapse all categories."""
        self.tree_view.collapseAll()

    def expand_category(self, category_name: str) -> None:
        """Expand a specific category."""
        if category_name in self._categories:
            category_item = self._categories[category_name]
            category_index = self.model.indexFromItem(category_item)
            self.tree_view.expand(category_index)

    def _on_item_clicked(self, index) -> None:
        """Handle item click in the tree view."""
        item = self.model.itemFromIndex(index)
        if item and item.flags() & Qt.ItemFlag.ItemIsSelectable:
            # This is a selectable item, not a category
            text = item.text()
            data = item.data(Qt.ItemDataRole.UserRole)

            # Update the combo box display text
            self.setCurrentText(text)

            # Emit signal
            self.item_selected.emit(text, data)

            logger.debug(f"Item clicked: {text} with data: {data}")

            # Close the popup
            self.hidePopup()
        else:
            # For categories, toggle expansion on single click too
            if self.tree_view.isExpanded(index):
                self.tree_view.collapse(index)
            else:
                self.tree_view.expand(index)

    def _on_item_double_clicked(self, index) -> None:
        """Handle item double click in the tree view."""
        item = self.model.itemFromIndex(index)
        if item and item.flags() & Qt.ItemFlag.ItemIsSelectable:
            # Same as single click for selectable items
            self._on_item_clicked(index)
        else:
            # For categories, toggle expansion
            if self.tree_view.isExpanded(index):
                self.tree_view.collapse(index)
            else:
                self.tree_view.expand(index)

    def setCurrentText(self, text: str) -> None:
        """Set the current text display of the combo box."""
        # Override to work with our custom view
        super().setCurrentText(text)

    def currentText(self) -> str:
        """Get the current text display of the combo box."""
        return super().currentText()

    def populate_from_metadata_groups(self, groups: dict, default_key: str | None = None) -> None:  # noqa: ARG002
        """Populate the combo box from grouped metadata data."""
        self.model.clear()
        # Ensure categories map is reset for fresh population
        self._categories.clear()
        logger.debug(f"Populating combo box with groups: {list(groups.keys())}")

        first_item = None

        # Detect single-group case to flatten items directly under root
        non_empty_groups = [(g, items) for g, items in groups.items() if items]
        if len(non_empty_groups) == 1:
            _, items = non_empty_groups[0]
            for item_name, item_data in items:
                child_item = QStandardItem(item_name)
                child_item.setData(item_data, Qt.ItemDataRole.UserRole)
                child_item.setFlags(child_item.flags() | Qt.ItemFlag.ItemIsSelectable)
                self.model.appendRow(child_item)
                if first_item is None:
                    first_item = child_item
        else:
            for group_name, items in groups.items():
                if items:  # Only add groups that have items
                    group_item = QStandardItem(group_name)
                    group_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                    # Track category item for expand_category()
                    self._categories[group_name] = group_item

                    for item_name, item_data in items:
                        child_item = QStandardItem(item_name)
                        child_item.setData(item_data, Qt.ItemDataRole.UserRole)
                        child_item.setFlags(child_item.flags() | Qt.ItemFlag.ItemIsSelectable)
                        group_item.appendRow(child_item)

                        if first_item is None:
                            first_item = child_item

                    self.model.appendRow(group_item)

        # Set the model
        self.setModel(self.model)

        # Force UI update
        self.model.layoutChanged.emit()

        # Now set the expansion state properly (after model is set)
        group_names = list(groups.keys())
        for i, group_name in enumerate(group_names):
            if groups[group_name]:  # Only if group has items
                # Find the group item and set expansion
                for row in range(self.model.rowCount()):
                    item = self.model.item(row)
                    if item and item.text() == group_name:
                        category_index = self.model.indexFromItem(item)
                        # Expand only the first category, collapse others
                        self.tree_view.setExpanded(category_index, i == 0)
                        break

        # Select first item if available
        if first_item:
            combo_index = self.model.indexFromItem(first_item).row()
            self.setCurrentIndex(combo_index)

            index = self.model.indexFromItem(first_item)
            self.tree_view.setCurrentIndex(index)
            self.tree_view.scrollTo(index)

            self.setCurrentText(first_item.text())

            self.item_selected.emit(first_item.text(), first_item.data(Qt.ItemDataRole.UserRole))

            logger.debug(
                f"Selected first item: {first_item.text()} with data: {first_item.data(Qt.ItemDataRole.UserRole)}"
            )
        else:
            logger.warning("No items to populate in hierarchical combo box")

    def select_item_by_data(self, data: Any) -> None:
        """Select an item by its data value."""
        for row in range(self.model.rowCount()):
            item = self.model.item(row)
            if item:
                # Check children of group
                for child_row in range(item.rowCount()):
                    child_item = item.child(child_row)
                    if child_item and child_item.data(Qt.ItemDataRole.UserRole) == data:
                        combo_index = self.model.indexFromItem(child_item).row()
                        self.setCurrentIndex(combo_index)

                        index = self.model.indexFromItem(child_item)
                        self.tree_view.setCurrentIndex(index)
                        self.tree_view.scrollTo(index)

                        self.setCurrentText(child_item.text())

                        self.item_selected.emit(child_item.text(), child_item.data(Qt.ItemDataRole.UserRole))
                        logger.debug(
                            f"Selected item by data: {child_item.text()} with data: {data}"
                        )
                        return

        logger.warning(f"select_item_by_data: No item found with data: {data}")
