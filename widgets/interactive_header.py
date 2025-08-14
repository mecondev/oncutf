"""
Module: interactive_header.py

Author: Michael Economou
Date: 2025-05-31

interactive_header.py
This module defines InteractiveHeader, a subclass of QHeaderView that
adds interactive behavior to table headers in the oncutf application.
Features:
- Toggles selection of all rows when clicking on column 0
- Performs manual sort handling for sortable columns (excluding column 0)
- Prevents accidental sort when resizing (Explorer-like behavior)
"""

from core.pyqt_imports import QAction, QHeaderView, QMenu, QPoint, Qt

# ApplicationContext integration
try:
    from core.application_context import get_app_context
except ImportError:
    get_app_context = None


class InteractiveHeader(QHeaderView):
    """
    A custom QHeaderView that toggles selection on column 0 click,
    and performs manual sorting for other columns. Prevents accidental sort
    when user clicks near the edge to resize.
    """

    def __init__(self, orientation, parent=None, parent_window=None):
        super().__init__(orientation, parent)
        self.parent_window = parent_window  # Keep for backward compatibility
        self.setSectionsClickable(True)
        self.setHighlightSections(True)
        self.setSortIndicatorShown(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.contextMenuEvent)

        self.header_enabled = True

        self._press_pos: QPoint = QPoint()
        self._pressed_index: int = -1

    def _get_app_context(self):
        """Get ApplicationContext with fallback to None."""
        if get_app_context is None:
            return None
        try:
            return get_app_context()
        except RuntimeError:
            # ApplicationContext not ready yet
            return None

    def _get_main_window_via_context(self):
        """Get main window via ApplicationContext with fallback to parent traversal."""
        # Try ApplicationContext first
        context = self._get_app_context()
        if context and hasattr(context, "_main_window"):
            return context._main_window

        # Fallback to legacy parent_window approach
        if self.parent_window:
            return self.parent_window

        # Last resort: traverse parents to find main window
        from utils.path_utils import find_parent_with_attribute

        return find_parent_with_attribute(self, "handle_header_toggle")

    def mousePressEvent(self, event) -> None:
        self._press_pos = event.pos()
        self._pressed_index = self.logicalIndexAt(event.pos())
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        released_index = self.logicalIndexAt(event.pos())

        if released_index != self._pressed_index:
            super().mouseReleaseEvent(event)
            return

        if (event.pos() - self._press_pos).manhattanLength() > 4:
            super().mouseReleaseEvent(event)
            return

        # Section was clicked without drag or resize intent
        main_window = self._get_main_window_via_context()

        if released_index == 0:
            if main_window and hasattr(main_window, "handle_header_toggle"):
                # Qt.Checked may not always exist as attribute
                checked = getattr(Qt, "Checked", 2)
                main_window.handle_header_toggle(checked)
        else:
            if main_window and hasattr(main_window, "sort_by_column"):
                main_window.sort_by_column(released_index)

        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, position):
        """
        Show unified right-click context menu for header with sorting and column visibility options.
        """
        logical_index = self.logicalIndexAt(position)

        menu = QMenu(self)

        # Apply consistent styling with Inter fonts
        menu.setStyleSheet(
            """
            QMenu {
                background-color: #232323;
                color: #f0ebd8;
                border: none;
                border-radius: 8px;
                font-family: "Inter", "Segoe UI", Arial, sans-serif;
                font-size: 9pt;
                padding: 6px 4px;
            }
            QMenu::item {
                background-color: transparent;
                padding: 3px 16px 3px 8px;
                margin: 1px 2px;
                border-radius: 4px;
                min-height: 16px;
                icon-size: 16px;
            }
            QMenu::item:selected {
                background-color: #748cab;
                color: #0d1321;
            }
            QMenu::item:disabled {
                color: #888888;
            }
            QMenu::icon {
                padding-left: 6px;
                padding-right: 6px;
            }
            QMenu::separator {
                background-color: #5a5a5a;
                height: 1px;
                margin: 4px 8px;
            }
        """
        )

        # Add sorting options for columns > 0
        if logical_index > 0:
            try:
                from utils.icons_loader import get_menu_icon

                sort_asc = QAction("Sort Ascending", self)
                sort_asc.setIcon(get_menu_icon("chevron-up"))
                sort_desc = QAction("Sort Descending", self)
                sort_desc.setIcon(get_menu_icon("chevron-down"))
            except ImportError:
                sort_asc = QAction("Sort Ascending", self)
                sort_desc = QAction("Sort Descending", self)

            asc = getattr(Qt, "AscendingOrder", 0)
            desc = getattr(Qt, "DescendingOrder", 1)
            sort_asc.triggered.connect(lambda: self._sort(logical_index, asc))
            sort_desc.triggered.connect(lambda: self._sort(logical_index, desc))

            menu.addAction(sort_asc)
            menu.addAction(sort_desc)
            menu.addSeparator()

        # Add column visibility options
        self._add_column_visibility_menu(menu)

        menu.exec_(self.mapToGlobal(position))

    def _sort(self, column: int, order: Qt.SortOrder) -> None:
        """
        Calls MainWindow.sort_by_column() with forced order from context menu.
        """
        main_window = self._get_main_window_via_context()
        if main_window and hasattr(main_window, "sort_by_column"):
            main_window.sort_by_column(column, force_order=order)

    def _add_column_visibility_menu(self, menu):
        """Add column visibility toggle options to the menu."""
        try:
            # Get the file table view to access column configuration
            file_table_view = self._get_file_table_view()
            if not file_table_view:
                return

            from config import FILE_TABLE_COLUMN_CONFIG
            from utils.icons_loader import get_menu_icon

            # Add submenu title
            columns_menu = QMenu("Show Columns", menu)
            columns_menu.setIcon(get_menu_icon("columns"))

            # Add column toggle actions (sorted alphabetically by title)
            column_items = []
            for column_key, column_config in FILE_TABLE_COLUMN_CONFIG.items():
                if not column_config.get("removable", True):
                    continue  # Skip non-removable columns like filename
                column_items.append((column_key, column_config))

            # Sort by title alphabetically
            column_items.sort(key=lambda x: x[1]["title"])

            for column_key, column_config in column_items:
                action = QAction(column_config["title"], columns_menu)

                # Get visibility state from file table view
                is_visible = True
                if hasattr(file_table_view, "_visible_columns"):
                    is_visible = file_table_view._visible_columns.get(
                        column_key, column_config.get("default_visible", True)
                    )

                # Set icon based on visibility (toggle-left for hidden, toggle-right for visible)
                if is_visible:
                    action.setIcon(get_menu_icon("toggle-right"))
                else:
                    action.setIcon(get_menu_icon("toggle-left"))

                # Use triggered signal (menu will close, but it's simpler)
                action.triggered.connect(
                    lambda _checked=False, key=column_key: self._toggle_column_visibility(key)
                )
                columns_menu.addAction(action)

            menu.addMenu(columns_menu)

        except Exception as e:
            # Fallback: just add a simple label if configuration fails
            from utils.logger_factory import get_cached_logger

            logger = get_cached_logger(__name__)
            logger.warning(f"Failed to add column visibility menu: {e}")

    def _get_file_table_view(self):
        """Get the file table view that this header belongs to."""
        # The header's parent should be the table view
        return self.parent() if hasattr(self.parent(), "_visible_columns") else None

    def _toggle_column_visibility(self, column_key: str):
        """Toggle visibility of a specific column via the file table view."""
        file_table_view = self._get_file_table_view()
        if file_table_view and hasattr(file_table_view, "_toggle_column_visibility"):
            file_table_view._toggle_column_visibility(column_key)
