"""Module: view.py - FileTableView widget (thin shell).

Author: Michael Economou
Date: 2025-05-21 (Refactored: 2026-01-04)

Custom QTableView with Windows Explorer-like behavior:
- Full-row selection with anchor handling
- Intelligent column width management with automatic viewport fitting
- Drag & drop support with custom MIME types
- Hover highlighting and visual feedback
- Automatic vertical scrollbar detection and filename column adjustment

Architecture:
    Uses composition pattern with handler classes:
    - SelectionBehavior: Selection logic
    - DragDropBehavior: Drag & drop support
    - ColumnManagementBehavior: Column width/visibility
    - EventHandler: Qt event handling
    - HoverHandler: Hover highlighting
    - TooltipHandler: Custom tooltips
    - ViewportHandler: Scrollbar/viewport management
"""

from contextlib import suppress

from oncutf.core.pyqt_imports import (
    QAbstractItemView,
    QEvent,
    QHeaderView,
    QModelIndex,
    QMouseEvent,
    QPoint,
    Qt,
    QTableView,
    pyqtSignal,
)
from oncutf.core.theme_manager import get_theme_manager
from oncutf.ui.behaviors import (
    ColumnManagementBehavior,
    DragDropBehavior,
    SelectionBehavior,
)
from oncutf.ui.widgets.file_table.event_handler import EventHandler
from oncutf.ui.widgets.file_table.hover_handler import HoverHandler
from oncutf.ui.widgets.file_table.tooltip_handler import TooltipHandler
from oncutf.ui.widgets.file_table.utils import (
    clear_preview_and_metadata,
    emergency_cursor_cleanup,
    force_cursor_cleanup,
    get_main_window,
    get_metadata_tree,
)
from oncutf.ui.widgets.file_table.viewport_handler import ViewportHandler
from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.shared.timer_manager import schedule_ui_update
from oncutf.utils.ui.placeholder_helper import create_placeholder_helper

logger = get_cached_logger(__name__)

# Constants
SCROLLBAR_MARGIN = 40


class FileTableView(QTableView):
    """Custom QTableView with Windows Explorer-like behavior.

    Features:
    - Full-row selection with anchor handling (via SelectionBehavior)
    - Drag & drop support with custom MIME types (via DragDropBehavior)
    - Column width/visibility management (via ColumnManagementBehavior)
    - Event handling (via EventHandler)
    - Hover highlighting (via HoverHandler)
    - Custom tooltips (via TooltipHandler)
    - Scrollbar management (via ViewportHandler)
    """

    selection_changed = pyqtSignal(list)  # Emitted with list[int] of selected rows
    files_dropped = pyqtSignal(list, object)  # Emitted with dropped paths and modifiers
    refresh_requested = pyqtSignal()  # Emitted when F5 pressed for full refresh

    def __init__(self, parent=None):
        """Initialize the file table view with all configurations."""
        super().__init__(parent)

        # Core state
        self._manual_anchor_index: QModelIndex | None = None
        self._drag_start_pos: QPoint | None = None
        self._active_drag = None
        self._programmatic_resize: bool = False
        self._clicked_index = None
        self._drag_data = None
        self._drag_feedback_timer = None

        # Selection state
        self.selected_rows: set[int] = set()
        self.anchor_row: int | None = None
        self.context_focused_row: int | None = None

        # Protection flags
        self._selection_change_count = 0
        self._last_selection_change_time = 0
        self._max_selection_changes_per_second = 20
        self._ensuring_selection = False
        self._processing_selection_change = False

        # Column configuration
        self._config_save_timer = None
        self._pending_column_changes = {}
        self._visible_columns = {}
        self._has_manual_preference = False
        self._user_preferred_width = None

        # Initialize Qt properties
        self._setup_qt_properties()

        # Setup placeholder
        self.placeholder_helper = create_placeholder_helper(
            self, "file_table", text="No files loaded", icon_size=160
        )

        # Setup hover delegate
        from oncutf.ui.delegates.ui_delegates import FileTableHoverDelegate

        self.hover_delegate = FileTableHoverDelegate(self)
        self.setItemDelegate(self.hover_delegate)

        # Setup viewport event overrides
        self.viewport()._original_leave_event = self.viewport().leaveEvent
        self.viewport()._original_enter_event = self.viewport().enterEvent
        self.viewport().leaveEvent = self._viewport_leave_event
        self.viewport().enterEvent = self._viewport_enter_event

        # Initialize handlers (composition)
        self._hover_handler = HoverHandler(self)
        self._tooltip_handler = TooltipHandler(self)
        self._viewport_handler = ViewportHandler(self)
        self._event_handler = EventHandler(self)

        # Initialize behaviors (existing composition)
        self._selection_behavior = SelectionBehavior(self)
        self._drag_drop_behavior = DragDropBehavior(self)
        self._column_mgmt_behavior = ColumnManagementBehavior(self)

        # Load column config after behavior exists
        self._visible_columns = self._load_column_visibility_config()

        # Register shutdown hook
        self._column_mgmt_behavior.register_shutdown_hook()

        # Install event filter for tooltips
        self.viewport().installEventFilter(self)

        # Schedule header visibility update
        schedule_ui_update(self._column_mgmt_behavior._update_header_visibility, delay=100)

    def _setup_qt_properties(self) -> None:
        """Setup Qt widget properties."""
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setDefaultDropAction(Qt.CopyAction)
        self.setDragDropOverwriteMode(False)
        self.setDropIndicatorShown(True)
        self.setAlternatingRowColors(False)
        self.setShowGrid(False)
        self.setWordWrap(False)
        self.setCornerButtonEnabled(False)
        self.setSortingEnabled(False)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self.setTextElideMode(Qt.ElideRight)

        # Row height from theme
        theme = get_theme_manager()
        self.verticalHeader().setDefaultSectionSize(theme.get_constant("table_row_height"))

        # Scrollbar policies
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

        # Custom drag settings
        self.setDragEnabled(False)
        self.setDragDropMode(QAbstractItemView.DropOnly)
        self.viewport().setAcceptDrops(True)

        self.setSizeAdjustPolicy(QAbstractItemView.AdjustIgnored)

    # =====================================
    # Qt Event Overrides (delegate to handlers)
    # =====================================

    def eventFilter(self, obj, event):
        """Event filter for custom tooltips on table cells."""
        if obj == self.viewport():
            index = self.indexAt(event.pos()) if event.type() == QEvent.MouseMove else None
            if self._tooltip_handler.handle_event(event.type(), index):
                return True
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press events."""
        if not self._event_handler.handle_mouse_press(event):
            super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        """Handle double-click events."""
        if not self._event_handler.handle_mouse_double_click(event):
            super().mouseDoubleClickEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle mouse release events."""
        if not self._event_handler.handle_mouse_release(event):
            super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event) -> None:
        """Handle mouse move events."""
        if not self._event_handler.handle_mouse_move(event):
            super().mouseMoveEvent(event)

    def keyPressEvent(self, event) -> None:
        """Handle keyboard navigation."""
        if self._event_handler.handle_key_press(event):
            event.accept()
            return
        super().keyPressEvent(event)
        if self._event_handler.should_sync_selection_after_key(event):
            self._selection_behavior.sync_selection_safely()

    def keyReleaseEvent(self, event) -> None:
        """Handle key release events."""
        if not self._event_handler.handle_key_release(event):
            super().keyReleaseEvent(event)

    def focusOutEvent(self, event) -> None:
        """Handle focus out events."""
        super().focusOutEvent(event)
        self._event_handler.handle_focus_out(event)

    def focusInEvent(self, event) -> None:
        """Handle focus in events."""
        super().focusInEvent(event)
        self._event_handler.handle_focus_in(event)

    def leaveEvent(self, event) -> None:
        """Handle mouse leave events."""
        self._event_handler.handle_leave(event)
        super().leaveEvent(event)

    def enterEvent(self, event) -> None:
        """Handle mouse enter events."""
        self._event_handler.handle_enter(event)
        super().enterEvent(event)

    def _viewport_leave_event(self, event) -> None:
        """Handle viewport leave events."""
        self._event_handler.handle_viewport_leave(event)

    def _viewport_enter_event(self, event) -> None:
        """Handle viewport enter events."""
        self._event_handler.handle_viewport_enter(event)

    def wheelEvent(self, event) -> None:
        """Handle wheel events for scrolling."""
        if not self._event_handler.handle_wheel(event):
            super().wheelEvent(event)

    def showEvent(self, event) -> None:
        """Handle show events."""
        super().showEvent(event)
        self._viewport_handler.force_scrollbar_update()
        self._column_mgmt_behavior._update_header_visibility()

    def paintEvent(self, event) -> None:
        """Handle paint events."""
        super().paintEvent(event)

    def resizeEvent(self, event) -> None:
        """Handle resize events."""
        super().resizeEvent(event)
        if hasattr(self, "placeholder_helper"):
            self.placeholder_helper.update_position()
        self._viewport_handler.force_scrollbar_update()
        self._ensure_no_word_wrap()

    def scrollTo(self, index, hint=None) -> None:
        """Scroll to make an index visible with reduced horizontal scrolling."""
        if hint is None:
            hint = QAbstractItemView.EnsureVisible

        if not index.isValid():
            return

        # Use minimal scrolling hint when possible
        if hint == QAbstractItemView.EnsureVisible:
            current_rect = self.visualRect(index)
            viewport_rect = self.viewport().rect()
            if viewport_rect.contains(current_rect):
                return
            super().scrollTo(index, QAbstractItemView.PositionAtCenter)
        else:
            super().scrollTo(index, hint)

    def enable_selection_store_mode(self):
        """Enable SelectionStore integration mode.

        Called during initialization to sync Qt selection with SelectionStore.
        """
        logger.debug(
            "enable_selection_store_mode called - syncing selection to store",
            extra={"dev_only": True},
        )

        # Sync current Qt selection to store
        selection_store = self._get_selection_store()
        if selection_store is not None:
            current_selection = self._selection_behavior.get_current_selection_safe()
            selection_store.set_selected_rows(current_selection, emit_signal=True)

    # =====================================
    # Table State & Utility Methods
    # =====================================

    def is_empty(self) -> bool:
        """Check if the table is empty."""
        if not self.model():
            return True
        files = getattr(self.model(), "files", [])
        return not files or len(files) == 0

    def _force_cursor_cleanup(self):
        """Force cleanup of any stuck cursor states."""
        force_cursor_cleanup(self)

    def _emergency_cursor_cleanup(self):
        """Emergency cursor cleanup with aggressive reset."""
        emergency_cursor_cleanup(self)

    def _get_metadata_tree(self):
        """Get the metadata tree widget from parent hierarchy."""
        return get_metadata_tree(self)

    def _get_main_window(self):
        """Get the main window from parent hierarchy."""
        return get_main_window(self)

    def _clear_preview_and_metadata(self) -> None:
        """Clear preview and metadata displays."""
        clear_preview_and_metadata(self)

    # =====================================
    # Model & Table Setup
    # =====================================

    def setModel(self, model) -> None:
        """Set the model for the table view."""
        logger.debug("FileTableView setModel called", extra={"dev_only": True})

        if model is self.model():
            return

        super().setModel(model)
        if model:
            self._ensure_no_word_wrap()
            model._table_view_ref = self

            if hasattr(model, "columnsInserted"):
                model.columnsInserted.connect(self._column_mgmt_behavior.configure_columns)
            if hasattr(model, "columnsRemoved"):
                model.columnsRemoved.connect(self._column_mgmt_behavior.configure_columns)
            if hasattr(model, "modelReset"):
                model.modelReset.connect(self._column_mgmt_behavior.configure_columns)

            if model.columnCount() > 0:
                schedule_ui_update(self._column_mgmt_behavior.check_and_fix_column_widths, delay=50)
                self._column_mgmt_behavior.configure_columns()
            else:
                schedule_ui_update(self._column_mgmt_behavior.configure_columns, delay=50)

        self.update_placeholder_visibility()

    def prepare_table(self, file_items: list, *, preserve_selection: bool = False) -> None:
        """Prepare the table for display with file items."""
        logger.debug(
            "prepare_table called with %d items", len(file_items), extra={"dev_only": True}
        )
        self._has_manual_preference = False
        self._user_preferred_width = None

        for file_item in file_items:
            file_item.checked = False

        if not preserve_selection:
            self.clearSelection()
            self.selected_rows.clear()
            selection_store = self._get_selection_store()
            if selection_store:
                selection_store.clear_selection(emit_signal=False)
                selection_store.set_anchor_row(None, emit_signal=False)

        if self.model() and hasattr(self.model(), "set_files"):
            self.model().set_files(file_items)

        self.show()
        self._column_mgmt_behavior.configure_columns()
        self._ensure_no_word_wrap()
        self._setup_column_delegates()

        if hasattr(self, "hover_delegate"):
            self.setItemDelegate(self.hover_delegate)
            self.hover_delegate.hovered_row = -1

        self.viewport().update()
        self.update_placeholder_visibility()
        self.refresh_view_state()

    def _setup_column_delegates(self) -> None:
        """Setup column-specific delegates (e.g., color column)."""
        if not self.model():
            return

        from oncutf.core.ui_managers import get_column_service

        visible_columns_list = get_column_service().get_visible_columns()

        try:
            color_column_logical_index = visible_columns_list.index("color")
            color_column_view_index = color_column_logical_index + 1

            from oncutf.ui.delegates.color_column_delegate import ColorColumnDelegate

            color_delegate = ColorColumnDelegate(self)
            self.setItemDelegateForColumn(color_column_view_index, color_delegate)
            logger.debug("Set ColorColumnDelegate for column %d", color_column_view_index)
        except (ValueError, AttributeError):
            pass

    def _ensure_no_word_wrap(self) -> None:
        """Ensure word wrap is disabled and text is properly elided."""
        self.setWordWrap(False)

        if hasattr(self.horizontalHeader(), "setWordWrap"):
            self.horizontalHeader().setWordWrap(False)

        theme = get_theme_manager()
        row_height = theme.get_constant("table_row_height")
        self.verticalHeader().setDefaultSectionSize(row_height)
        self.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.setTextElideMode(Qt.ElideRight)

        if self.model():
            for row in range(self.model().rowCount()):
                self.setRowHeight(row, row_height)
            self._column_mgmt_behavior.ensure_all_columns_proper_width()
            self.model().layoutChanged.emit()

        self.viewport().update()
        schedule_ui_update(self._viewport_handler.refresh_text_display, delay=50)
        schedule_ui_update(lambda: self.setWordWrap(False), delay=100)

    # =====================================
    # Viewport & Scrollbar Management
    # =====================================

    def _force_scrollbar_update(self) -> None:
        """Force immediate scrollbar and viewport update."""
        self._viewport_handler.force_scrollbar_update()

    def _delayed_refresh(self) -> None:
        """Delayed refresh for proper scrollbar and content updates."""
        self._viewport_handler._delayed_refresh()

    def _update_scrollbar_visibility(self) -> None:
        """Update scrollbar visibility based on content."""
        self._viewport_handler.update_scrollbar_visibility()

    def _smart_scrollbar_adjustment(self, column_added: bool = False) -> None:
        """Smart scrollbar position adjustment (currently disabled)."""

    def ensure_scrollbar_visibility(self) -> None:
        """Public wrapper to ensure scrollbar visibility."""
        self._viewport_handler.ensure_scrollbar_visibility()

    def _refresh_text_display(self) -> None:
        """Refresh text display in visible cells."""
        self._viewport_handler.refresh_text_display()

    # =====================================
    # Header & View State
    # =====================================

    def set_header_enabled(self, enabled: bool) -> None:
        """Enable/disable header widgets."""
        with suppress(Exception):
            header = self.horizontalHeader()
            if header is not None:
                header.setEnabled(enabled)

        with suppress(Exception):
            parent = self.parent()
            while parent is not None:
                if hasattr(parent, "header"):
                    with suppress(Exception):
                        parent.header.setEnabled(enabled)
                    break
                parent = parent.parent()

        with suppress(Exception):
            self._column_mgmt_behavior._update_header_visibility()

    def refresh_view_state(self) -> None:
        """Refresh complete view state (scrollbar + header visibility)."""
        with suppress(Exception):
            self._viewport_handler.update_scrollbar_visibility()
        with suppress(Exception):
            self._column_mgmt_behavior._update_header_visibility()

    def on_horizontal_splitter_moved(self, pos: int, index: int) -> None:
        """Handle horizontal splitter movement."""

    def on_vertical_splitter_moved(self, pos: int, index: int) -> None:
        """Handle vertical splitter movement."""

    # =====================================
    # Placeholder Management
    # =====================================

    def set_placeholder_visible(self, visible: bool) -> None:
        """Show or hide the placeholder."""
        if hasattr(self, "placeholder_helper"):
            if visible:
                self.placeholder_helper.show()
            else:
                self.placeholder_helper.hide()
        self.refresh_view_state()

    def update_placeholder_visibility(self):
        """Update placeholder visibility based on table content."""
        if hasattr(self, "placeholder_helper"):
            self.placeholder_helper.update_position()

    # =====================================
    # Qt Event Overrides (required for proper delegation)
    # =====================================

    def _load_column_visibility_config(self) -> dict:
        """Load column visibility config (called during __init__ before behavior exists)."""
        if hasattr(self, "_column_mgmt_behavior"):
            return self._column_mgmt_behavior.load_column_visibility_config()
        return {}

    def dragEnterEvent(self, event) -> None:
        """Delegate to DragDropBehavior."""
        if not self._drag_drop_behavior.handle_drag_enter(event):
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        """Delegate to DragDropBehavior."""
        if not self._drag_drop_behavior.handle_drag_move(event):
            super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:
        """Delegate to DragDropBehavior."""
        import time

        from oncutf.utils.logging.logger_factory import get_cached_logger
        logger = get_cached_logger(__name__)

        t0 = time.time()
        logger.debug("[DROP-TIMING] dropEvent START at %.3f", t0, extra={"dev_only": True})

        # Set wait cursor IMMEDIATELY for user feedback
        from oncutf.core.pyqt_imports import QApplication, Qt
        t1 = time.time()
        logger.debug("[DROP-TIMING] Before setOverrideCursor at +%.3fms", (t1-t0)*1000, extra={"dev_only": True})

        QApplication.setOverrideCursor(Qt.WaitCursor)
        t2 = time.time()
        logger.debug("[DROP-TIMING] After setOverrideCursor at +%.3fms", (t2-t0)*1000, extra={"dev_only": True})

        # Force cursor update before any processing
        QApplication.processEvents()
        t3 = time.time()
        logger.debug("[DROP-TIMING] After processEvents at +%.3fms", (t3-t0)*1000, extra={"dev_only": True})

        QApplication.flush()
        t4 = time.time()
        logger.debug("[DROP-TIMING] After flush at +%.3fms", (t4-t0)*1000, extra={"dev_only": True})

        try:
            result = self._drag_drop_behavior.handle_drop(event)
            t5 = time.time()
            logger.debug("[DROP-TIMING] After handle_drop at +%.3fms, result=%s", (t5-t0)*1000, bool(result), extra={"dev_only": True})

            if result:
                dropped_paths, modifiers = result
                logger.debug("[DROP-TIMING] Emitting files_dropped with %d paths at +%.3fms", len(dropped_paths), (time.time()-t0)*1000, extra={"dev_only": True})
                self.files_dropped.emit(dropped_paths, modifiers)
                t6 = time.time()
                logger.debug("[DROP-TIMING] After emit at +%.3fms", (t6-t0)*1000, extra={"dev_only": True})
            else:
                # Restore cursor if no valid drop
                QApplication.restoreOverrideCursor()
                logger.debug("[DROP-TIMING] No valid drop, cursor restored at +%.3fms", (time.time()-t0)*1000, extra={"dev_only": True})
        except Exception as e:
            QApplication.restoreOverrideCursor()
            logger.error("[DROP-TIMING] Exception at +%.3fms: %s", (time.time()-t0)*1000, e)
            raise

    def selectionChanged(self, selected, deselected) -> None:
        """Override to delegate to SelectionBehavior."""
        self._selection_behavior.handle_selection_changed(selected, deselected)

    # =====================================
    # Selection Delegation (for DragDropBehavior Protocol)
    # =====================================

    def _get_current_selection(self) -> set[int]:
        """Delegate to SelectionBehavior."""
        return self._selection_behavior.get_current_selection()

    def _get_current_selection_safe(self) -> set[int]:
        """Delegate to SelectionBehavior."""
        return self._selection_behavior.get_current_selection_safe()

    def _set_anchor_row(self, row: int | None, emit_signal: bool = True) -> None:
        """Delegate to SelectionBehavior."""
        self._selection_behavior.set_anchor_row(row)

    def _get_anchor_row(self) -> int | None:
        """Delegate to SelectionBehavior."""
        return self._selection_behavior.get_anchor_row()

    def _get_selection_store(self):
        """Get SelectionStore instance."""
        return self._selection_behavior.selection_store
