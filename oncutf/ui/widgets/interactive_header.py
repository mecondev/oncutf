"""Module: interactive_header.py

Author: Michael Economou
Date: 2025-05-22

interactive_header.py
This module defines InteractiveHeader, a subclass of QHeaderView that
adds interactive behavior to table headers in the oncutf application.
Features:
- Toggles selection of all rows when clicking on column 0
- Performs manual sort handling for sortable columns (excluding column 0)
- Prevents accidental sort when resizing (Explorer-like behavior)
"""

from contextlib import suppress

from oncutf.core.pyqt_imports import (
    QAction,
    QHeaderView,
    QLabel,
    QMenu,
    QPoint,
    Qt,
    QWidget,
)
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


# ApplicationContext integration
try:
    from oncutf.core.application_context import get_app_context
except ImportError:
    get_app_context = None


class InteractiveHeader(QHeaderView):
    """A custom QHeaderView that toggles selection on column 0 click,
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

        # When False, header clicks won't trigger app actions (sort/toggle).
        self._click_actions_enabled: bool = True

        self._press_pos: QPoint = QPoint()
        self._pressed_index: int = -1
        self._drag_active: bool = False
        self._drag_grab_offset: int = 0
        self._interaction_qss_applied: bool = False

        # Floating overlay widget for drag feedback
        self._drag_overlay: QWidget | None = None

        self._ensure_interaction_qss()
        self._set_interaction_state(locked=not self.sectionsMovable())

    def setSectionsMovable(self, movable: bool) -> None:  # type: ignore[override]
        """Override to keep UI interaction feedback consistent with lock state."""
        super().setSectionsMovable(movable)
        if not movable:
            self._drag_active = False
            self._hide_drag_overlay()
        self._set_interaction_state(locked=not movable)

    def _create_drag_overlay(self, width: int, title: str) -> None:
        """Create a floating overlay widget for drag feedback."""
        if self._drag_overlay:
            self._drag_overlay.deleteLater()

        try:
            from oncutf.core.theme_manager import get_theme_manager
            theme = get_theme_manager()
            bg_color = theme.get_color("table_selection_bg")
            # text_color = theme.get_color("table_selection_text")
            text_color = theme.get_color("table_header_text")

            logger.debug("[INTERACTIVE_HEADER] Drag overlay colors from theme: bg=%s, text=%s", bg_color, text_color)
        except Exception as e:
            # Fallback colors should never be used
            logger.error("[INTERACTIVE_HEADER] Failed to get theme colors for drag overlay: %s", e)

        self._drag_overlay = QLabel(title, self)
        self._drag_overlay.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._drag_overlay.setFixedSize(width, self.height())
        self._drag_overlay.setStyleSheet(
            f"QLabel {{"
            f"  background-color: {bg_color};"
            f"  color: {text_color};"
            f"  padding-left: 6px;"
            # f"  border: 2px dotted {text_color};"
            # f"  font-weight: 600;"
            f"}}"
        )
        self._drag_overlay.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._drag_overlay.show()
        self._drag_overlay.raise_()

    def _update_drag_overlay_position(self, mouse_x: int) -> None:
        """Update the position of the drag overlay."""
        if not self._drag_overlay:
            return

        left = mouse_x - self._drag_grab_offset
        # Clamp to header bounds
        max_left = self.width() - self._drag_overlay.width()
        left = max(0, min(left, max_left))

        self._drag_overlay.move(left, 0)

    def _hide_drag_overlay(self) -> None:
        """Hide and destroy the drag overlay."""
        if self._drag_overlay:
            self._drag_overlay.hide()
            self._drag_overlay.deleteLater()
            self._drag_overlay = None

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
        from oncutf.utils.filesystem.path_utils import find_parent_with_attribute

        return find_parent_with_attribute(self, "handle_header_toggle")

    def mousePressEvent(self, event) -> None:
        self._press_pos = event.pos()
        self._pressed_index = self.logicalIndexAt(event.pos())
        self._drag_active = False

        # Store grab offset for drag overlay positioning
        if self._pressed_index >= 0:
            section_left = self.sectionViewportPosition(self._pressed_index)
            self._drag_grab_offset = event.pos().x() - section_left

        super().mousePressEvent(event)

    def enterEvent(self, event) -> None:
        """Clear table hover when mouse enters header."""
        # Get file table view to clear its hover state
        file_table_view = self._get_file_table_view()
        if file_table_view and hasattr(file_table_view, '_hover_handler'):
            file_table_view._hover_handler.clear_hover()
        super().enterEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if not self.sectionsMovable():
            super().mouseMoveEvent(event)
            return

        if (event.buttons() & Qt.LeftButton) and self._pressed_index >= 0:
            if not self._drag_active:
                if (event.pos() - self._press_pos).manhattanLength() > 4:
                    self._drag_active = True
                    # Get column title and width
                    width = self.sectionSize(self._pressed_index)
                    title = ""
                    model = self.model()
                    if model and 0 <= self._pressed_index < model.columnCount():
                        title = str(model.headerData(self._pressed_index, Qt.Horizontal, Qt.DisplayRole) or "")
                    self._create_drag_overlay(width, title)

            if self._drag_active:
                self._update_drag_overlay_position(event.pos().x())

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._drag_active:
            self._drag_active = False
            self._hide_drag_overlay()

        super().mouseReleaseEvent(event)

        if not self._click_actions_enabled:
            return

        # Check for drag
        if (event.pos() - self._press_pos).manhattanLength() > 4:
            return

        released_index = self.logicalIndexAt(event.pos())
        if released_index != self._pressed_index or released_index == -1:
            return

        main_window = self._get_main_window_via_context()
        if not main_window:
            return

        if released_index == 0:
            if hasattr(main_window, "handle_header_toggle"):
                checked = getattr(Qt, "Checked", 2)
                main_window.handle_header_toggle(checked)
        elif hasattr(main_window, "sort_by_column"):
            main_window.sort_by_column(released_index)


    def set_click_actions_enabled(self, enabled: bool) -> None:
        """Enable/disable click-triggered actions (sort/toggle).

        Note: This does not change Qt's sectionsClickable, which is needed
        for pressed/drag visual feedback.
        """
        self._click_actions_enabled = enabled

    def _ensure_interaction_qss(self) -> None:
        if self._interaction_qss_applied:
            return

        try:
            from oncutf.core.theme_manager import get_theme_manager

            theme = get_theme_manager()
            header_bg = theme.get_color("table_header_bg")
            header_text = theme.get_color("table_header_text")

            # While locked: neutralize hover.
            qss = (
                "\nQHeaderView[oncutf_locked=\"true\"]::section:hover {"
                f"background-color: {header_bg};"
                f"color: {header_text};"
                "}"
            )

            self.setStyleSheet((self.styleSheet() or "") + qss)
            self._interaction_qss_applied = True
        except Exception:
            self._interaction_qss_applied = False

    def _set_interaction_state(self, *, locked: bool | None = None) -> None:
        if locked is not None:
            self.setProperty("oncutf_locked", locked)

        with suppress(Exception):
            self.style().unpolish(self)
            self.style().polish(self)
        self.update()



    def contextMenuEvent(self, position):
        """Show unified right-click context menu for header."""
        logical_index = self.logicalIndexAt(position)

        menu = QMenu(self)

        # Apply theme styling
        from oncutf.core.theme_manager import get_theme_manager

        theme = get_theme_manager()
        menu.setStyleSheet(theme.get_context_menu_stylesheet())

        # Add sorting options for columns > 0
        if logical_index > 0:
            try:
                from oncutf.utils.ui.icons_loader import get_menu_icon

                sort_asc = QAction("Sort Ascending", self)
                sort_asc.setIcon(get_menu_icon("chevron-down"))
                sort_desc = QAction("Sort Descending", self)
                sort_desc.setIcon(get_menu_icon("chevron-up"))
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
        """Calls MainWindow.sort_by_column() with forced order from context menu."""
        main_window = self._get_main_window_via_context()
        if main_window and hasattr(main_window, "sort_by_column"):
            main_window.sort_by_column(column, force_order=order)

    def _add_column_visibility_menu(self, menu):
        """Add column visibility toggle options to the menu with grouped sections."""
        try:
            # Get the file table view to access column configuration
            file_table_view = self._get_file_table_view()
            if not file_table_view:
                return

            # Use canonical column management behavior API
            if not hasattr(file_table_view, "_column_mgmt_behavior"):
                return

            from oncutf.config import FILE_TABLE_COLUMN_CONFIG
            from oncutf.utils.ui.icons_loader import get_menu_icon

            # Add submenu title
            columns_menu = QMenu("Show Columns", menu)
            columns_menu.setIcon(get_menu_icon("columns"))

            # Get current visible columns via canonical API
            visible_columns_list = file_table_view._column_mgmt_behavior.get_visible_columns_list()

            # Group columns by category
            column_groups = {
                "File": [],
                "Image": [],
                "Video": [],
                "Audio": [],
                "Metadata": [],
                "Device": [],
                "Other": [],
            }

            for column_key, column_config in FILE_TABLE_COLUMN_CONFIG.items():
                if not column_config.get("removable", True):
                    continue  # Skip non-removable columns like filename

                # Categorize columns
                if column_key in ["color", "type", "file_size", "modified", "file_hash", "duration"]:
                    column_groups["File"].append((column_key, column_config))
                elif column_key in ["image_size", "rotation", "iso", "aperture", "shutter_speed",
                                   "white_balance", "compression", "color_space"]:
                    column_groups["Image"].append((column_key, column_config))
                elif column_key in ["video_fps", "video_avg_bitrate", "video_codec", "video_format"]:
                    column_groups["Video"].append((column_key, column_config))
                elif column_key in ["audio_channels", "audio_format"]:
                    column_groups["Audio"].append((column_key, column_config))
                elif column_key in ["artist", "copyright", "owner_name"]:
                    column_groups["Metadata"].append((column_key, column_config))
                elif column_key in ["device_manufacturer", "device_model", "device_serial_no", "target_umid"]:
                    column_groups["Device"].append((column_key, column_config))
                else:
                    column_groups["Other"].append((column_key, column_config))

            # Add grouped columns to menu
            first_group = True
            for group_name in ["File", "Image", "Video", "Audio", "Metadata", "Device", "Other"]:
                group_columns = column_groups[group_name]
                if not group_columns:
                    continue

                # Add separator between groups (except before first group)
                if not first_group:
                    columns_menu.addSeparator()
                first_group = False

                # Sort columns within group alphabetically
                from typing import cast
                group_columns.sort(key=lambda x: cast("str", x[1]["title"]))

                # Add group columns
                for column_key, column_config in group_columns:
                    action = QAction(column_config["title"], columns_menu)

                    # Get visibility state via canonical API
                    is_visible = column_key in visible_columns_list

                    # Set icon based on visibility
                    if is_visible:
                        action.setIcon(get_menu_icon("toggle-right"))
                    else:
                        action.setIcon(get_menu_icon("toggle-left"))

                    # Connect toggle action
                    action.triggered.connect(
                        lambda _checked=False, key=column_key: self._toggle_column_visibility(key)
                    )
                    columns_menu.addAction(action)

            menu.addMenu(columns_menu)

            # Add separator before lock toggle
            menu.addSeparator()

            # Add lock columns toggle
            self._add_lock_columns_toggle(menu, file_table_view)

            # Add reset column order option
            self._add_reset_column_order(menu, file_table_view)

        except Exception as e:
            # Fallback: just add a simple label if configuration fails
            from oncutf.utils.logging.logger_factory import get_cached_logger

            logger = get_cached_logger(__name__)
            logger.warning("Failed to add column visibility menu: %s", e)

    def _get_file_table_view(self):
        """Get the file table view that this header belongs to."""
        # The header's parent should be the table view
        parent = self.parent()
        if parent and hasattr(parent, "_column_mgmt_behavior"):
            return parent
        return None

    def _add_lock_columns_toggle(self, menu, file_table_view):
        """Add lock/unlock columns toggle to menu."""
        try:
            from oncutf.utils.ui.icons_loader import get_menu_icon

            # Check current lock state
            is_locked = self._is_columns_locked()

            # Use toggle switch icons: toggle-left (off/locked), toggle-right (on/unlocked)
            if is_locked:
                lock_action = QAction("Unlock Columns", menu)
                lock_action.setIcon(get_menu_icon("toggle-left"))  # Off = Locked
            else:
                lock_action = QAction("Lock Columns", menu)
                lock_action.setIcon(get_menu_icon("toggle-right"))  # On = Unlocked

            lock_action.triggered.connect(self._toggle_columns_lock)
            menu.addAction(lock_action)

        except Exception as e:
            from oncutf.utils.logging.logger_factory import get_cached_logger

            logger = get_cached_logger(__name__)
            logger.warning("Failed to add lock columns toggle: %s", e)

    def _is_columns_locked(self) -> bool:
        """Check if columns are currently locked (not movable)."""
        # Try to load from config first
        try:
            main_window = self._get_main_window_via_context()
            if main_window and hasattr(main_window, "window_config_manager"):
                config_manager = main_window.window_config_manager.config_manager
                window_config = config_manager.get_category("window")
                return window_config.get("columns_locked", False)
        except Exception:
            pass

        # Fallback: check current header state
        return not self.sectionsMovable()

    def _toggle_columns_lock(self):
        """Toggle lock state of columns (enable/disable reordering)."""
        current_state = self.sectionsMovable()
        new_state = not current_state

        # Update header
        self.setSectionsMovable(new_state)

        # Save to config
        try:
            main_window = self._get_main_window_via_context()
            if main_window and hasattr(main_window, "window_config_manager"):
                config_manager = main_window.window_config_manager.config_manager
                window_config = config_manager.get_category("window")
                window_config.set("columns_locked", not new_state)
                config_manager.mark_dirty()

                from oncutf.utils.logging.logger_factory import get_cached_logger

                logger = get_cached_logger(__name__)
                logger.info(
                    "Columns %s", "locked" if not new_state else "unlocked"
                )
        except Exception as e:
            from oncutf.utils.logging.logger_factory import get_cached_logger

            logger = get_cached_logger(__name__)
            logger.warning("Failed to save columns lock state: %s", e)

    def _add_reset_column_order(self, menu, file_table_view):
        """Add reset column order option to menu."""
        try:
            from oncutf.utils.ui.icons_loader import get_menu_icon

            reset_action = QAction("Reset Column Order", menu)
            reset_action.setIcon(get_menu_icon("refresh"))
            reset_action.triggered.connect(self._reset_column_order)

            # Disable if columns are locked
            if self._is_columns_locked():
                reset_action.setEnabled(False)

            menu.addAction(reset_action)

        except Exception as e:
            from oncutf.utils.logging.logger_factory import get_cached_logger

            logger = get_cached_logger(__name__)
            logger.warning("Failed to add reset column order option: %s", e)

    def _reset_column_order(self):
        """Reset column order to default."""
        try:
            # Clear saved order from config
            main_window = self._get_main_window_via_context()
            if main_window and hasattr(main_window, "window_config_manager"):
                config_manager = main_window.window_config_manager.config_manager
                window_config = config_manager.get_category("window")
                window_config.set("column_order", None)
                config_manager.mark_dirty()

            # Reset visual order immediately
            header = self.parent().horizontalHeader() if self.parent() else None
            if header:
                # Move sections back to their logical order
                for logical_index in range(1, header.count()):  # Skip status column (0)
                    current_visual = header.visualIndex(logical_index)
                    if current_visual != logical_index:
                        header.moveSection(current_visual, logical_index)

                from oncutf.utils.logging.logger_factory import get_cached_logger

                logger = get_cached_logger(__name__)
                logger.info("Reset column order to default")

        except Exception as e:
            from oncutf.utils.logging.logger_factory import get_cached_logger

            logger = get_cached_logger(__name__)
            logger.warning("Failed to reset column order: %s", e)

    def _toggle_column_visibility(self, column_key: str):
        """Toggle visibility of a specific column via canonical column management API."""
        file_table_view = self._get_file_table_view()
        if file_table_view and hasattr(file_table_view, "_column_mgmt_behavior"):
            file_table_view._column_mgmt_behavior.toggle_column_visibility(column_key)
