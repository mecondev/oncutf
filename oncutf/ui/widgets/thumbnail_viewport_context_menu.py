"""Thumbnail Viewport Context Menu Builder.

Author: Michael Economou
Date: 2026-02-06

Builds context menu for thumbnail viewport operations.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING

from PyQt5.QtWidgets import QMenu

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

        # Sort submenu
        sort_menu = menu.addMenu("Sort")
        sort_menu.addAction("Ascending (A-Z)", lambda: sort_callback("filename", False))
        sort_menu.addAction("Descending (Z-A)", lambda: sort_callback("filename", True))
        sort_menu.addAction("By Color Flag", lambda: sort_callback("color", False))

        menu.addSeparator()

        # Order mode toggle
        if order_mode == "sorted":
            menu.addAction("Return to Manual Order", return_to_manual_callback)
        else:
            action = menu.addAction("Manual Order Active")
            action.setEnabled(False)

        menu.addSeparator()

        # Zoom controls
        menu.addAction("Zoom In", zoom_in_callback)
        menu.addAction("Zoom Out", zoom_out_callback)
        menu.addAction("Reset Zoom", reset_zoom_callback)

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
