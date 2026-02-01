"""Module: event_handler.py.

Author: Michael Economou
Date: 2026-01-02

Event handler for file tree view.

Handles keyboard events, scroll events, wheel events,
and other UI interactions for the tree view.
"""

from __future__ import annotations

import os
import platform
from typing import TYPE_CHECKING

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QApplication

from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.shared.timer_manager import schedule_scroll_adjust

if TYPE_CHECKING:
    from PyQt5.QtGui import QKeyEvent

    from oncutf.ui.widgets.file_tree.view import FileTreeView

logger = get_cached_logger(__name__)


class EventHandler:
    """Handles various events for the file tree view.

    Manages keyboard input, scroll behavior, wheel events,
    and other UI interactions.
    """

    def __init__(self, view: FileTreeView) -> None:
        """Initialize event handler.

        Args:
            view: The file tree view widget to handle events for

        """
        self._view = view

    def handle_key_press(self, event: QKeyEvent) -> bool:
        """Handle key press events.

        Args:
            event: Key press event

        Returns:
            True if event was handled, False otherwise

        """
        # Update drag feedback if dragging
        if self._view.drag_handler.is_dragging:
            self._view.drag_handler._update_drag_feedback()

        # Handle F5 refresh
        if event.key() == Qt.Key_F5:
            self._refresh_tree_view()
            return True

        # Handle Return/Enter key
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._view.folder_selected.emit()
            return True

        return False

    def handle_key_release(self, event: QKeyEvent) -> bool:
        """Handle key release events.

        Args:
            event: Key release event

        Returns:
            True if event was handled, False otherwise

        """
        if self._view.drag_handler.is_dragging:
            self._view.drag_handler._update_drag_feedback()

        return False

    def _refresh_tree_view(self) -> None:
        """Refresh the tree view by refreshing the underlying model."""
        from oncutf.ui.helpers.cursor_helper import wait_cursor

        logger.info("[EventHandler] F5 pressed - refreshing tree view")

        with wait_cursor():
            model = self._view.model()
            if model and hasattr(model, "refresh"):
                try:
                    current_path = self._view.get_selected_path()
                    expanded_paths = self._view.state_handler.save_expanded_state()

                    if len(expanded_paths) > 100:
                        logger.info(
                            "[EventHandler] Limiting expanded paths from %d to 100",
                            len(expanded_paths),
                        )
                        expanded_paths = sorted(expanded_paths, key=lambda p: p.count(os.sep))[:100]

                    model.refresh()

                    root = "" if platform.system() == "Windows" else "/"
                    self._view.setRootIndex(model.index(root))

                    self._view.state_handler.start_incremental_restore(expanded_paths, current_path)

                    logger.info("[EventHandler] Tree view refreshed successfully")

                    # Show status message if available
                    if hasattr(self._view, "parent") and callable(self._view.parent):
                        parent = self._view.parent()
                        if parent and hasattr(parent, "status_manager"):
                            parent.status_manager.set_file_operation_status(
                                "File tree refreshed", success=True, auto_reset=True
                            )

                except Exception:
                    logger.exception("[EventHandler] Error refreshing tree view")
            else:
                logger.debug(
                    "[EventHandler] No model or model does not support refresh",
                    extra={"dev_only": True},
                )

    def handle_wheel_event(self) -> None:
        """Update hover state after scroll to track cursor position smoothly."""
        delegate = getattr(self._view, "_delegate", None)
        if delegate and hasattr(delegate, "hovered_index"):
            pos = self._view.viewport().mapFromGlobal(QCursor.pos())
            new_index = self._view.indexAt(pos)
            old_index = delegate.hovered_index

            if new_index != old_index:
                delegate.hovered_index = new_index if new_index.isValid() else None
                if old_index and old_index.isValid():
                    self._view.viewport().update(self._view.visualRect(old_index))
                if new_index.isValid():
                    self._view.viewport().update(self._view.visualRect(new_index))

    def handle_splitter_moved(self) -> None:
        """Handle horizontal splitter movement to adjust column width."""
        schedule_scroll_adjust(self._view._adjust_column_width, 50)

    def handle_item_expanded(self) -> None:
        """Handle item expansion with wait cursor for better UX."""
        from oncutf.ui.helpers.cursor_helper import wait_cursor
        from oncutf.utils.shared.timer_manager import schedule_ui_update

        def show_wait_cursor() -> None:
            with wait_cursor():
                QApplication.processEvents()
                schedule_ui_update(lambda: None, delay=100)

        schedule_ui_update(show_wait_cursor, delay=1)
        logger.debug("[EventHandler] Item expanded with wait cursor", extra={"dev_only": True})

        self._view.state_handler.save_to_config()

    def handle_item_collapsed(self) -> None:
        """Handle item collapse - no wait cursor needed as it's instant."""
        logger.debug("[EventHandler] Item collapsed", extra={"dev_only": True})
        self._view.state_handler.save_to_config()
