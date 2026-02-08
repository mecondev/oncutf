"""Module: view.py.

Author: Michael Economou
Date: 2025-05-31 (Refactored: 2026-01-02)

Filesystem tree view for folder navigation.

This is the main view widget that serves as a thin shell,
delegating to specialized handlers for specific functionality:
- FilesystemHandler: Monitor setup and directory change callbacks
- StateHandler: Save/restore expanded state and selection
- DragHandler: Custom drag & drop implementation
- EventHandler: Keyboard, scroll, and wheel events

Features:
- Custom drag implementation (manual, not Qt built-in)
- Single item selection
- Filesystem monitoring for auto-refresh
- Drive mount/unmount detection
"""

from pathlib import Path

from PyQt5.QtCore import QEvent, Qt, pyqtSignal
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTreeView,
)

from oncutf.ui.delegates.ui_delegates import TreeViewItemDelegate
from oncutf.ui.widgets.file_tree.drag_handler import DragHandler
from oncutf.ui.widgets.file_tree.event_handler import EventHandler
from oncutf.ui.widgets.file_tree.filesystem_handler import FilesystemHandler
from oncutf.ui.widgets.file_tree.state_handler import StateHandler
from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.shared.timer_manager import schedule_scroll_adjust

logger = get_cached_logger(__name__)


class FileTreeView(QTreeView):
    """Custom tree view with clean single-item drag & drop implementation.

    Features:
    - Manual drag control (no Qt built-in drag system)
    - Intelligent horizontal scrolling
    - Single item selection only (no multi-selection complexity)
    - 4 modifier combinations for drag behavior:
      * Normal: Replace + shallow
      * Ctrl: Replace + recursive
      * Shift: Merge + shallow
      * Ctrl+Shift: Merge + recursive
    - Automatic header configuration for optimal display
    """

    # Signals
    folder_selected = pyqtSignal()  # Signal emitted when Return/Enter is pressed
    selection_changed = pyqtSignal(str)  # Signal emitted when selection changes (single path)

    def __init__(self, parent=None) -> None:
        """Initialize file tree view with drag/drop support."""
        super().__init__(parent)

        # Initialize handlers
        self._filesystem_handler = FilesystemHandler(self)
        self._state_handler = StateHandler(self)
        self._drag_handler = DragHandler(self)
        self._event_handler = EventHandler(self)

        # Enable drag so Qt can call startDrag, but we'll override it
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)

        # Configure scrollbars for optimal horizontal scrolling
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)

        # Configure text display for horizontal scrolling
        self.setTextElideMode(Qt.ElideNone)
        self.setWordWrap(False)

        # Optimize for performance and appearance
        self.setUniformRowHeights(True)
        self.setRootIsDecorated(True)
        self.setAlternatingRowColors(True)

        # Configure SINGLE selection only
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)

        # Setup custom branch icons for Windows compatibility
        self._setup_branch_icons()

        # Defer filesystem monitor setup until context is ready
        self._filesystem_monitor_setup_pending = True

        # Connect expand/collapse signals for wait cursor
        self.expanded.connect(self._on_item_expanded)
        self.collapsed.connect(self._on_item_collapsed)

        # Install custom tree view delegate for consistent hover/selection behavior
        from oncutf.ui.theme_manager import get_theme_manager

        theme = get_theme_manager()
        self._delegate = TreeViewItemDelegate(self, theme=theme)
        self.setItemDelegate(self._delegate)
        self._delegate.install_event_filter(self)

        # Apply tree view QSS for consistent hover/selection colors
        self._apply_tree_styling(theme)

    # =====================================
    # HANDLER PROPERTIES
    # =====================================

    @property
    def state_handler(self) -> StateHandler:
        """Get the state handler."""
        return self._state_handler

    @property
    def drag_handler(self) -> DragHandler:
        """Get the drag handler."""
        return self._drag_handler

    @property
    def filesystem_handler(self) -> FilesystemHandler:
        """Get the filesystem handler."""
        return self._filesystem_handler

    @property
    def event_handler(self) -> EventHandler:
        """Get the event handler."""
        return self._event_handler

    # =====================================
    # BACKWARD COMPATIBILITY PROPERTIES
    # =====================================

    @property
    def _refresh_in_progress(self) -> bool:
        """Backward compatibility: Get refresh in progress flag from filesystem handler."""
        return self._filesystem_handler._refresh_in_progress

    @_refresh_in_progress.setter
    def _refresh_in_progress(self, value: bool) -> None:
        """Backward compatibility: Set refresh in progress flag on filesystem handler."""
        self._filesystem_handler._refresh_in_progress = value

    def _on_directory_changed(self, dir_path: str) -> None:
        """Backward compatibility: Delegate to filesystem handler."""
        self._filesystem_handler._on_directory_changed(dir_path)

    # =====================================
    # STYLING
    # =====================================

    def _apply_tree_styling(self, theme) -> None:
        """Apply consistent hover/selection styling to match file table."""
        text = theme.get_color("text")
        hover_bg = theme.get_color("table_hover_bg")
        selected_bg = theme.get_color("selected")
        selected_text = theme.get_color("selected_text")
        selected_hover_bg = theme.get_color("selected_hover")
        bg_alternate = theme.get_color("background_alternate")

        self.setStyleSheet(f"""
            QTreeView::item:hover:!selected {{
                background-color: {hover_bg};
            }}
            QTreeView::item:selected:!hover {{
                background-color: {selected_bg};
                color: {text};
            }}
            QTreeView::item:selected:hover {{
                background-color: {selected_hover_bg};
                color: {selected_text};
            }}
            QTreeView {{
                alternate-background-color: {bg_alternate};
            }}
        """)

    def _setup_branch_icons(self) -> None:
        """Setup custom branch icons for better cross-platform compatibility."""
        try:
            from oncutf.ui.helpers.icons_loader import get_menu_icon

            try:
                _closed_icon = get_menu_icon("keyboard_arrow_right")
                _open_icon = get_menu_icon("keyboard_arrow_down")
            except Exception:
                logger.debug(
                    "[FileTreeView] Custom branch icons not found, using Qt defaults",
                    extra={"dev_only": True},
                )
                return

            logger.debug(
                "[FileTreeView] Custom branch icons setup attempted",
                extra={"dev_only": True},
            )

        except Exception as e:
            logger.debug(
                "[FileTreeView] Branch icons setup skipped: %s",
                e,
                extra={"dev_only": True},
            )

    # =====================================
    # LIFECYCLE EVENTS
    # =====================================

    def showEvent(self, event) -> None:
        """Handle show event - setup filesystem monitor when widget becomes visible."""
        super().showEvent(event)

        if self._filesystem_monitor_setup_pending:
            self._filesystem_monitor_setup_pending = False
            self._filesystem_handler.setup_monitor()

    def closeEvent(self, event) -> None:
        """Clean up resources before closing."""
        try:
            self._filesystem_handler.cleanup()
            logger.debug("[FileTreeView] Cleanup completed", extra={"dev_only": True})
        except Exception:
            logger.exception("[FileTreeView] Error during cleanup")

        super().closeEvent(event)

    # =====================================
    # MODEL AND HEADER
    # =====================================

    def setModel(self, model) -> None:
        """Override to configure header when model is set."""
        super().setModel(model)
        self._configure_header()

    def resizeEvent(self, event) -> None:
        """Handle resize to adjust column width for optimal horizontal scrolling."""
        super().resizeEvent(event)
        self._adjust_column_width()

    def _configure_header(self) -> None:
        """Configure header for optimal display."""
        header = self.header()
        if header:
            header.setVisible(False)
            header.setStretchLastSection(False)
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)

            for col in range(1, self.model().columnCount() if self.model() else 4):
                self.setColumnHidden(col, True)

            logger.debug(
                "[FileTreeView] Header configured for single column display",
                extra={"dev_only": True},
            )

    def _adjust_column_width(self) -> None:
        """Adjust column width for optimal horizontal scrolling."""
        if not self.model():
            return

        header = self.header()
        if not header:
            return

        viewport_width = self.viewport().width()
        content_width = self.sizeHintForColumn(0)

        if content_width > 0:
            if content_width <= viewport_width:
                header.setSectionResizeMode(0, QHeaderView.Stretch)
                self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            else:
                header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
                self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    def _on_model_changed(self) -> None:
        """Called when model data changes to update column width."""
        schedule_scroll_adjust(self._adjust_column_width, 10)

    # =====================================
    # SELECTION
    # =====================================

    def selectionChanged(self, selected, deselected) -> None:
        """Override to emit custom signal with selected path (single item only)."""
        super().selectionChanged(selected, deselected)

        selected_path = ""
        indexes = self.selectedIndexes()
        if indexes and self.model() and hasattr(self.model(), "filePath"):
            path = self.model().filePath(indexes[0])
            if path:
                selected_path = path

        # Keep filesystem watcher aligned with the active folder
        if selected_path and Path(selected_path).is_dir():
            self._filesystem_handler.update_monitored_folder(selected_path)

        self.selection_changed.emit(selected_path)

    def get_selected_path(self) -> str:
        """Get the single selected file/folder path."""
        selection_model = self.selectionModel()
        if not selection_model:
            return ""

        selected_rows = selection_model.selectedRows()
        if not selected_rows:
            return ""

        index = selected_rows[0]
        if self.model() and hasattr(self.model(), "filePath"):
            path = self.model().filePath(index)
            return path or ""

        return ""

    def select_path(self, path: str) -> None:
        """Select item by its file path."""
        if not self.model() or not hasattr(self.model(), "index"):
            return

        selection_model = self.selectionModel()
        if not selection_model:
            return

        model = self.model()
        if model and hasattr(model, "index_from_path"):
            index = model.index_from_path(path)
        else:
            index = self.model().index(path)
        if index.isValid():
            selection_model.clearSelection()
            selection_model.select(index, selection_model.Select | selection_model.Rows)

    # =====================================
    # MOUSE EVENTS (Delegate to DragHandler)
    # =====================================

    def mousePressEvent(self, event) -> None:
        """Handle mouse press for custom drag detection."""
        self._drag_handler.handle_mouse_press(event)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        """Handle mouse move for custom drag start and real-time drop zone validation."""
        if self._drag_handler.handle_mouse_move(event):
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        """Handle mouse release to end drag."""
        self._drag_handler.handle_mouse_release(event)
        super().mouseReleaseEvent(event)

    # =====================================
    # KEY EVENTS (Delegate to EventHandler)
    # =====================================

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press events, including modifier changes during drag."""
        if self._event_handler.handle_key_press(event):
            event.accept()
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        """Handle key release events, including modifier changes during drag."""
        self._event_handler.handle_key_release(event)
        super().keyReleaseEvent(event)

    # =====================================
    # DROP HANDLING (Reject all drops)
    # =====================================

    def dragEnterEvent(self, event) -> None:
        """Accept internal drops only."""
        event.ignore()

    def dragMoveEvent(self, event) -> None:
        """Handle drag move."""
        event.ignore()

    def dropEvent(self, event) -> None:
        """Handle drop events."""
        event.ignore()

    def dragLeaveEvent(self, event) -> None:
        """Handle drag leave."""
        event.ignore()

    # =====================================
    # SCROLL AND SPLITTER
    # =====================================

    def on_horizontal_splitter_moved(self, _pos: int, _index: int) -> None:
        """Handle horizontal splitter movement to adjust column width."""
        self._event_handler.handle_splitter_moved()

    def on_vertical_splitter_moved(self, pos: int, index: int) -> None:
        """Handle vertical splitter movement (placeholder for future use)."""

    def scrollTo(self, index, hint=None) -> None:
        """Override to ensure optimal scrolling behavior."""
        super().scrollTo(index, hint or QAbstractItemView.EnsureVisible)

    def wheelEvent(self, event) -> None:
        """Update hover state after scroll to track cursor position smoothly."""
        super().wheelEvent(event)
        self._event_handler.handle_wheel_event()

    # =====================================
    # EVENT FILTER
    # =====================================

    def event(self, event) -> bool:
        """Override event handling to block hover events during drag."""
        if (
            self._drag_handler.is_dragging or self._drag_handler.drag_start_pos
        ) and event.type() in (QEvent.HoverEnter, QEvent.HoverMove, QEvent.HoverLeave):
            return True

        return super().event(event)

    def startDrag(self, _supported_actions) -> None:
        """Override Qt's built-in drag to prevent it from interfering with our custom drag."""
        logger.debug(
            "[FileTreeView] Built-in startDrag called but ignored - using custom drag system",
            extra={"dev_only": True},
        )

    # =====================================
    # EXPAND/COLLAPSE
    # =====================================

    def _on_item_expanded(self, _index) -> None:
        """Handle item expansion with wait cursor for better UX."""
        self._event_handler.handle_item_expanded()

    def _on_item_collapsed(self, _index) -> None:
        """Handle item collapse - no wait cursor needed as it's instant."""
        self._event_handler.handle_item_collapsed()
