"""Hierarchical QComboBox widget with tree-like structure support.

This module provides a hierarchical QComboBox widget that displays items
in a tree-like structure with categories and subcategories.
It's designed to replace the flat list approach for large datasets
like metadata fields in the rename metadata module.

Author: Michael Economou
Date: 2025-05-01
"""

from typing import Any

from oncutf.core.pyqt_imports import (
    QComboBox,
    QEvent,
    QSize,
    QStandardItem,
    QStandardItemModel,
    Qt,
    QTreeView,
    QWidget,
    pyqtSignal,
)
from oncutf.ui.widgets.ui_delegates import TreeViewItemDelegate
from oncutf.utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class _AliasHeaderTreeView(QTreeView):
    """QTreeView subclass providing a headerHidden() alias for compatibility tests."""

    def headerHidden(self) -> bool:
        return self.isHeaderHidden()


class HierarchicalComboBox(QComboBox):
    """A QComboBox that displays items in a hierarchical tree structure."""

    # Signal emitted when an item is selected (not categories) — legacy immediate
    item_selected = pyqtSignal(str, object)  # text, user_data
    # New signal emitted after popup is closed and selection is final — avoids races
    selection_confirmed = pyqtSignal(str, object)  # text, user_data

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # Internal state for reliable data retrieval
        self._current_selected_data = None

        # Create tree view for hierarchical display
        self.tree_view = _AliasHeaderTreeView()
        self.tree_view.setObjectName("hier_combo_popup")
        self.tree_view.setHeaderHidden(True)
        self.tree_view.setRootIsDecorated(True)
        self.tree_view.setItemsExpandable(True)
        self.tree_view.setIndentation(24)
        self.tree_view.setAlternatingRowColors(False)
        self.tree_view.setIconSize(QSize(16, 16))
        self.tree_view.setMouseTracking(True)

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
        # Also handle mouse release for drag selection
        self.tree_view.pressed.connect(self._on_item_pressed)

        # Track categories for easy access
        self._categories: dict[str, QStandardItem] = {}

        # Flag to prevent popup from reopening after selection (timed)
        self._closing_popup = False
        self._closing_unblock_ms = 150

        # Track last selected item to detect changes
        self._last_selected_data = None
        self._selected_item_data = None
        self._pressed_item_data = None

        # Install event filter on the combobox to block mouse events during closing
        self.installEventFilter(self)

    def showPopup(self):
        """Show the tree view popup."""
        # Call parent implementation to properly set up the view
        super().showPopup()

        # Ensure proper expansion after showing
        if hasattr(self, "_categories") and self._categories:
            # Expand first category by default
            first_category = list(self._categories.keys())[0]
            self.expand_category(first_category)

        logger.debug(
            "[HierarchicalComboBox] Popup shown with proper expansion", extra={"dev_only": True}
        )

    def hidePopup(self):
        """Hide the tree view popup."""
        super().hidePopup()
        logger.debug("[HierarchicalComboBox] Popup hidden", extra={"dev_only": True})

    def eventFilter(self, obj, event):
        """Filter events to prevent popup from reopening during closing (timed)."""
        if obj == self and self._closing_popup:
            event_type = event.type()
            if event_type == QEvent.MouseButtonPress:  # type: ignore
                # Block only immediate press events on combobox while timed blocker active
                if not self.view().isVisible():
                    logger.debug(
                        "[HierarchicalComboBox] Blocked mouse press during popup timed closing",
                        extra={"dev_only": True},
                    )
                    return True  # Block the event
        return super().eventFilter(obj, event)

    def _on_item_pressed(self, index) -> None:
        """Handle item press (mouse down) in the tree view."""
        if not index.isValid():
            return

        item = self.model.itemFromIndex(index)
        if not item:
            return

        # Check if this is a selectable item (not a category)
        if item.flags() & Qt.ItemFlag.ItemIsSelectable:
            # Store the pressed item for potential selection
            self._pressed_item_data = item.data(Qt.ItemDataRole.UserRole)
        else:
            self._pressed_item_data = None

    def _on_item_clicked(self, index) -> None:
        """Handle item click in the tree view."""
        if not index.isValid():
            return

        item = self.model.itemFromIndex(index)
        if not item:
            return

        # Check if this is a selectable item (not a category)
        if item.flags() & Qt.ItemFlag.ItemIsSelectable:
            text = item.text()
            data = item.data(Qt.ItemDataRole.UserRole)

            # Update internal state immediately
            self._current_selected_data = data

            logger.debug(
                "[HierarchicalComboBox] Item clicked: %s (%s)",
                text,
                data,
                extra={"dev_only": True},
            )

            # Update display
            self.setCurrentText(text)

            # Emit legacy immediate signal (kept for backwards compatibility)
            self.item_selected.emit(text, data)

            # Hide popup immediately after selection
            self.hidePopup()

            # Start short timed blocker to avoid immediate re-open mouse press race
            from oncutf.utils.timer_manager import TimerType, get_timer_manager

            self._closing_popup = True
            get_timer_manager().schedule(
                lambda: setattr(self, "_closing_popup", False),
                delay=self._closing_unblock_ms,
                timer_type=TimerType.UI_UPDATE,
                timer_id="hierarchical_combo_closing",
            )

            # Emit confirmed selection after popup has closed (next event loop)
            get_timer_manager().schedule(
                lambda: self.selection_confirmed.emit(text, data),
                delay=0,
                timer_type=TimerType.UI_UPDATE,
                timer_id="hierarchical_combo_confirm",
            )
        # For categories, toggle expansion
        elif self.tree_view.isExpanded(index):
            self.tree_view.collapse(index)
        else:
            self.tree_view.expand(index)

    def _on_item_double_clicked(self, index) -> None:
        """Handle item double click in the tree view."""
        if not index.isValid():
            return

        item = self.model.itemFromIndex(index)
        if not item:
            return

        # Single click is enough for selection
        if item.flags() & Qt.ItemFlag.ItemIsSelectable:
            pass
        # For categories, toggle expansion
        elif self.tree_view.isExpanded(index):
            self.tree_view.collapse(index)
        else:
            self.tree_view.expand(index)

    def clear(self) -> None:
        """Clear all items and categories."""
        super().clear()
        self.model.clear()
        self._categories.clear()
        self._current_selected_data = None

    def get_current_data(self) -> Any:
        """Get the data of the currently selected item."""
        # Priority 1: Explicitly tracked data (most reliable after click)
        if hasattr(self, "_current_selected_data") and self._current_selected_data is not None:
            return self._current_selected_data

        # Priority 2: Tree view current index
        current_index = self.tree_view.currentIndex()
        if current_index.isValid():
            item = self.model.itemFromIndex(current_index)
            if item and item.flags() & Qt.ItemFlag.ItemIsSelectable:
                return item.data(Qt.ItemDataRole.UserRole)

        # Fallback to searching by text
        current_text = self.currentText()
        for row in range(self.model.rowCount()):
            item = self.model.item(row)
            if item:
                for child_row in range(item.rowCount()):
                    child_item = item.child(child_row)
                    if child_item and child_item.text() == current_text:
                        return child_item.data(Qt.ItemDataRole.UserRole)

        # Fallback to last selected data (handles cases where current index was reset)
        if self._selected_item_data is not None:
            return self._selected_item_data

        return None

    def get_current_text(self) -> str:
        """Get the text of the currently selected item."""
        current_index = self.tree_view.currentIndex()
        if current_index.isValid():
            item = self.model.itemFromIndex(current_index)
            if item and item.flags() & Qt.ItemFlag.ItemIsSelectable:
                return item.text()

        return self.currentText()

    def setCurrentText(self, text: str) -> None:
        """Set the current text display of the combo box."""
        super().setCurrentText(text)

    def currentText(self) -> str:
        """Get the current text display of the combo box."""
        return super().currentText()

    def populate_from_metadata_groups(self, groups: dict, auto_select_first: bool = False) -> None:
        """Populate the combo box from grouped metadata data.

        Args:
            groups: mapping category -> list of (display, data)
            auto_select_first: when True select and emit the first item (keeps previous behaviour when desired)

        """
        self.model.clear()
        self._categories.clear()

        logger.debug("Populating combo box with groups: %s", list(groups.keys()))

        first_item = None
        non_empty_groups = [(g, items) for g, items in groups.items() if items]

        # Detect single-group case to flatten items directly under root
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
                if items:
                    group_item = QStandardItem(group_name)
                    group_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
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

        # Expand first category, collapse others
        group_names = list(groups.keys())
        for i, group_name in enumerate(group_names):
            if groups[group_name]:
                for row in range(self.model.rowCount()):
                    item = self.model.item(row)
                    if item and item.text() == group_name:
                        category_index = self.model.indexFromItem(item)
                        self.tree_view.setExpanded(category_index, i == 0)
                        break

        # Select first item if available and requested
        if first_item and auto_select_first:
            from oncutf.utils.timer_manager import TimerType, get_timer_manager

            index = self.model.indexFromItem(first_item)
            self.tree_view.setCurrentIndex(index)
            self.setCurrentText(first_item.text())
            self._last_selected_data = first_item.data(Qt.ItemDataRole.UserRole)
            self._selected_item_data = first_item.data(Qt.ItemDataRole.UserRole)
            # Emit immediate item_selected and schedule confirmed emission after popup actions
            self.item_selected.emit(first_item.text(), first_item.data(Qt.ItemDataRole.UserRole))
            get_timer_manager().schedule(
                lambda: self.selection_confirmed.emit(
                    first_item.text(), first_item.data(Qt.ItemDataRole.UserRole)
                ),
                delay=0,
                timer_type=TimerType.UI_UPDATE,
                timer_id="hierarchical_combo_first_select",
            )
            logger.debug(
                "Selected first item: %s with data: %s",
                first_item.text(),
                first_item.data(Qt.ItemDataRole.UserRole),
            )
        else:
            logger.debug("No items to auto-select in hierarchical combo box")

    def select_item_by_data(self, data: Any) -> None:
        """Select an item by its data value."""
        for row in range(self.model.rowCount()):
            item = self.model.item(row)
            if item:
                for child_row in range(item.rowCount()):
                    child_item = item.child(child_row)
                    if child_item and child_item.data(Qt.ItemDataRole.UserRole) == data:
                        index = self.model.indexFromItem(child_item)
                        self.tree_view.setCurrentIndex(index)
                        self.setCurrentText(child_item.text())

                        # Update internal state
                        self._current_selected_data = data

                        self.item_selected.emit(child_item.text(), data)

                        logger.debug(
                            "Selected item by data: %s with data: %s",
                            child_item.text(),
                            data,
                        )
                        return

        logger.warning("select_item_by_data: No item found with data: %s", data)

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
