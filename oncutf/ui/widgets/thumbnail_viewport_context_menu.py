"""Thumbnail Viewport Context Menu Builder.

Author: Michael Economou
Date: 2026-02-06

Builds context menu for thumbnail viewport operations.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING

from PyQt5.QtWidgets import QAction, QMenu

from oncutf.ui.services.icon_service import get_menu_icon
from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from PyQt5.QtCore import QPoint
    from PyQt5.QtWidgets import QWidget

logger = get_cached_logger(__name__)


class ThumbnailViewportContextMenuBuilder:
    """Builds context menu for thumbnail viewport."""

    def __init__(self, parent_widget: "QWidget"):
        """Initialize context menu builder.

        Args:
            parent_widget: Parent widget for menu

        """
        self._parent = parent_widget

    def build_fallback_menu(
        self,
        order_mode: str,
        selected_files: list[str],
        sort_callback: Callable[[str, bool], None],
        return_to_manual_callback: Callable[[], None],
        zoom_in_callback: Callable[[], None],
        zoom_out_callback: Callable[[], None],
        reset_zoom_callback: Callable[[], None],
        open_file_callback: Callable[[], None],
        reveal_callback: Callable[[], None],
        open_location_callback: Callable[[], None],
        refresh_callback: Callable[[], None],
    ) -> QMenu:
        """Build fallback context menu.

        Args:
            order_mode: Current order mode ("manual" or "sorted")
            selected_files: List of selected file paths
            sort_callback: Callback for sorting (key, reverse)
            return_to_manual_callback: Callback to return to manual order
            zoom_in_callback: Callback for zoom in
            zoom_out_callback: Callback for zoom out
            reset_zoom_callback: Callback for reset zoom
            open_file_callback: Callback to open selected file
            reveal_callback: Callback to reveal in file manager
            open_location_callback: Callback to open file location
            refresh_callback: Callback to refresh viewport

        Returns:
            Configured QMenu

        """
        menu = QMenu(self._parent)

        # View submenu
        view_menu = menu.addMenu("View")
        view_menu.setIcon(get_menu_icon("table_view"))

        zoom_in_action = QAction(get_menu_icon("zoom_in"), "Zoom In", view_menu)
        zoom_in_action.triggered.connect(zoom_in_callback)
        view_menu.addAction(zoom_in_action)

        zoom_out_action = QAction(get_menu_icon("zoom_out"), "Zoom Out", view_menu)
        zoom_out_action.triggered.connect(zoom_out_callback)
        view_menu.addAction(zoom_out_action)

        reset_zoom_action = QAction(get_menu_icon("zoom_out_map"), "Reset Zoom", view_menu)
        reset_zoom_action.triggered.connect(reset_zoom_callback)
        view_menu.addAction(reset_zoom_action)

        # Sort submenu
        sort_menu = menu.addMenu("Sort")
        sort_menu.setIcon(get_menu_icon("sort_by_alpha"))

        sort_asc_action = QAction(
            get_menu_icon("keyboard_arrow_down"), "Ascending (A-Z)", sort_menu
        )
        sort_asc_action.triggered.connect(lambda: sort_callback("filename", False))
        sort_menu.addAction(sort_asc_action)

        sort_desc_action = QAction(
            get_menu_icon("keyboard_arrow_up"), "Descending (Z-A)", sort_menu
        )
        sort_desc_action.triggered.connect(lambda: sort_callback("filename", True))
        sort_menu.addAction(sort_desc_action)

        sort_color_action = QAction(get_menu_icon("palette"), "By Color Flag", sort_menu)
        sort_color_action.triggered.connect(lambda: sort_callback("color", False))
        sort_menu.addAction(sort_color_action)

        sort_menu.addSeparator()

        return_manual_action = QAction(
            get_menu_icon("pinch_zoom_out"), "Return to Manual Mode", sort_menu
        )
        return_manual_action.triggered.connect(return_to_manual_callback)
        return_manual_action.setEnabled(order_mode == "sorted")
        sort_menu.addAction(return_manual_action)

        menu.addSeparator()

        # File operations
        if selected_files:
            if len(selected_files) == 1:
                menu.addAction("Open File", open_file_callback)
                menu.addAction("Reveal in File Manager", reveal_callback)
            menu.addAction(
                f"Open Folder ({len(selected_files)} file(s) selected)",
                open_location_callback,
            )
        else:
            action = menu.addAction("No files selected")
            action.setEnabled(False)

        menu.addSeparator()
        menu.addAction("Refresh", refresh_callback)

        return menu

    def show_menu(
        self,
        position: "QPoint",
        viewport_widget: "QWidget",
        order_mode: str,
        selected_files: list[str],
        sort_callback: Callable[[str, bool], None],
        return_to_manual_callback: Callable[[], None],
        zoom_in_callback: Callable[[], None],
        zoom_out_callback: Callable[[], None],
        reset_zoom_callback: Callable[[], None],
        open_file_callback: Callable[[], None],
        reveal_callback: Callable[[], None],
        open_location_callback: Callable[[], None],
        refresh_callback: Callable[[], None],
    ) -> None:
        """Build and show context menu.

        Args:
            position: Click position in widget coordinates
            viewport_widget: Viewport widget to map position
            order_mode: Current order mode ("manual" or "sorted")
            selected_files: List of selected file paths
            sort_callback: Callback for sorting (key, reverse)
            return_to_manual_callback: Callback to return to manual order
            zoom_in_callback: Callback for zoom in
            zoom_out_callback: Callback for zoom out
            reset_zoom_callback: Callback for reset zoom
            open_file_callback: Callback to open selected file
            reveal_callback: Callback to reveal in file manager
            open_location_callback: Callback to open file location
            refresh_callback: Callback to refresh viewport

        """
        menu = self.build_fallback_menu(
            order_mode=order_mode,
            selected_files=selected_files,
            sort_callback=sort_callback,
            return_to_manual_callback=return_to_manual_callback,
            zoom_in_callback=zoom_in_callback,
            zoom_out_callback=zoom_out_callback,
            reset_zoom_callback=reset_zoom_callback,
            open_file_callback=open_file_callback,
            reveal_callback=reveal_callback,
            open_location_callback=open_location_callback,
            refresh_callback=refresh_callback,
        )

        # Show menu at global position
        menu.exec_(viewport_widget.mapToGlobal(position))
