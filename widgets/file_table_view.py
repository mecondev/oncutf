"""
Module: file_table_view.py

Author: Michael Economou
Date: 2025-05-31


Custom QTableView with Windows Explorer-like behavior:
- Full-row selection with anchor handling
- Intelligent column width management with automatic viewport fitting
- Drag & drop support with custom MIME types
- Hover highlighting and visual feedback
- Automatic vertical scrollbar detection and filename column adjustment
"""

# from config import FILE_TABLE_COLUMN_CONFIG  # deprecated: using UnifiedColumnService
from core.application_context import get_app_context
from core.pyqt_imports import (
    QAbstractItemView,
    QApplication,
    QCursor,
    QDropEvent,
    QEvent,
    QHeaderView,
    QItemSelection,
    QItemSelectionModel,
    QKeySequence,
    QModelIndex,
    QMouseEvent,
    QPoint,
    Qt,
    QTableView,
    QTimer,
    pyqtSignal,
)
from core.unified_column_service import get_column_service
from utils.file_drop_helper import extract_file_paths
from utils.logger_factory import get_cached_logger
from utils.placeholder_helper import create_placeholder_helper
from utils.timer_manager import (
    schedule_ui_update,
)
from widgets.mixins import ColumnManagementMixin, DragDropMixin, SelectionMixin


logger = get_cached_logger(__name__)

# Constants for better maintainability
SCROLLBAR_MARGIN = 40


class FileTableView(SelectionMixin, DragDropMixin, ColumnManagementMixin, QTableView):
    """
    Custom QTableView with Windows Explorer-like behavior.

    Features:
    - Full-row selection with anchor handling (via SelectionMixin)
    - Drag & drop support with custom MIME types (via DragDropMixin)
    - Fixed-width column management with delayed save (7 seconds)
    - Horizontal scrollbar appears when columns exceed viewport width
    - Hover highlighting and visual feedback
    - Unified placeholder management using PlaceholderHelper
    - Keyboard shortcuts for column management (Ctrl+T, Ctrl+Shift+T)

    Column Configuration:
    - Columns maintain their configured widths when adding/removing columns
    - Column width changes are batched and saved with a 7-second delay
    - Multiple rapid changes are consolidated into a single save operation
    - On application shutdown, pending changes are force-saved immediately
    - This prevents excessive I/O while maintaining user preference persistence
    - Horizontal scrollbar appears automatically when total column width exceeds viewport
    """

    selection_changed = pyqtSignal(list)  # Emitted with list[int] of selected rows
    files_dropped = pyqtSignal(
        list, object
    )  # Emitted with list of dropped paths and keyboard modifiers

    def __init__(self, parent=None):
        """Initialize the file table view with all configurations."""
        super().__init__(parent)
        self._manual_anchor_index: QModelIndex | None = None
        self._drag_start_pos: QPoint | None = None  # Initialize as None instead of empty QPoint
        self._active_drag = None  # Store active QDrag object for cleanup
        self._programmatic_resize: bool = False  # Flag to indicate programmatic resize in progress

        # Initialize table properties
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setDefaultDropAction(Qt.CopyAction)
        self.setDragDropOverwriteMode(False)
        self.setDropIndicatorShown(True)
        self.setAlternatingRowColors(False)
        self.setShowGrid(False)
        self.setWordWrap(False)  # Disable word wrap
        self.setCornerButtonEnabled(False)
        self.setSortingEnabled(False)  # Disable by default, enable after configuration
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)

        # Additional settings to prevent text wrapping
        self.setTextElideMode(Qt.ElideRight)  # Elide text with ... instead of wrapping
        # Row height from theme engine
        from utils.theme_engine import ThemeEngine
        theme = ThemeEngine()
        self.verticalHeader().setDefaultSectionSize(theme.get_constant("table_row_height"))

        # Force single-line text display
        self.setWordWrap(False)  # Ensure word wrap is disabled
        self.setSizeAdjustPolicy(QAbstractItemView.AdjustIgnored)  # Keep control over widths

        # Ensure scrollbar updates properly
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Custom drag settings for existing implementation
        self.setDragEnabled(False)  # Disable Qt's built-in drag for custom implementation
        self.setDragDropMode(QAbstractItemView.DropOnly)  # Only accept drops, no built-in drags
        self.viewport().setAcceptDrops(True)

        # Load column visibility configuration
        self._visible_columns = self._load_column_visibility_config()

        # Initialize selection tracking
        self._manual_anchor_index = None
        self._legacy_selection_mode = False

        # Note: Vertical scrollbar handling is now integrated into _calculate_filename_width

        # Custom drag state tracking (needed by existing drag implementation)
        self._is_dragging = False
        self._drag_data = None
        self._drag_feedback_timer = None

        # Click tracking for drag operations
        self._clicked_index = None

        # Column configuration delayed save
        self._config_save_timer = None
        self._pending_column_changes = {}

        # Setup placeholder using unified helper
        self.placeholder_helper = create_placeholder_helper(
            self, "file_table", text="No files loaded", icon_size=160
        )

        # Selection and interaction state
        self.selected_rows: set[int] = set()
        self.anchor_row: int | None = None
        self.context_focused_row: int | None = None

        # Enable hover visuals
        from widgets.ui_delegates import FileTableHoverDelegate

        self.hover_delegate = FileTableHoverDelegate(self)
        self.setItemDelegate(self.hover_delegate)

        # Setup viewport events to hide tooltips when mouse leaves viewport
        self.viewport()._original_leave_event = self.viewport().leaveEvent
        self.viewport()._original_enter_event = self.viewport().enterEvent
        self.viewport().leaveEvent = self._viewport_leave_event
        self.viewport().enterEvent = self._viewport_enter_event

        # Selection store integration (with fallback to legacy selection handling)
        self._legacy_selection_mode = True  # Start in legacy mode for compatibility

        # Ensure header visibility is set correctly from the start
        # This will be called again after model is set, but ensures initial state
        from utils.timer_manager import schedule_ui_update

        schedule_ui_update(self._update_header_visibility, delay=100)

        # Selection loop protection
        self._selection_change_count = 0
        self._last_selection_change_time = 0
        self._max_selection_changes_per_second = 20  # Increased to 20 for better performance

        # Protection against infinite loops in ensure_anchor_or_select
        self._ensuring_selection = False

        # Protection against infinite loops in selectionChanged
        self._processing_selection_change = False

    def showEvent(self, event) -> None:
        """Handle show events and update scrollbar visibility."""
        super().showEvent(event)

        # Force complete refresh when widget becomes visible
        self._force_scrollbar_update()

        # Update header visibility when widget becomes visible
        self._update_header_visibility()

    def paintEvent(self, event):
        # Remove this debug log as it's too verbose
        # logger.debug("FileTableView paintEvent called")
        super().paintEvent(event)

        # Note: Removed scrollbar update from paintEvent to prevent recursion

    def _get_selection_store(self):
        """Get SelectionStore from ApplicationContext with fallback to None."""
        try:
            context = get_app_context()
            return context.selection_store
        except RuntimeError:
            # ApplicationContext not ready yet
            return None

    def resizeEvent(self, event) -> None:
        """Handle resize events and update scrollbar visibility."""
        super().resizeEvent(event)
        if hasattr(self, "placeholder_helper"):
            self.placeholder_helper.update_position()
        self._force_scrollbar_update()
        self._ensure_no_word_wrap()

    def _ensure_no_word_wrap(self) -> None:
        """Ensure word wrap is disabled and text is properly elided."""
        # Force word wrap to be disabled multiple times to ensure it sticks
        self.setWordWrap(False)

        # Also try to disable word wrap on the horizontal header
        if hasattr(self.horizontalHeader(), "setWordWrap"):
            self.horizontalHeader().setWordWrap(False)

        # Set fixed row height to prevent expansion (from theme engine)
        from utils.theme_engine import ThemeEngine
        theme = ThemeEngine()
        row_height = theme.get_constant("table_row_height")
        self.verticalHeader().setDefaultSectionSize(row_height)
        self.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)

        # Ensure text eliding is enabled
        self.setTextElideMode(Qt.ElideRight)

        # Force uniform row heights for all existing rows
        if self.model():
            for row in range(self.model().rowCount()):
                self.setRowHeight(row, row_height)

        # Ensure all columns have proper width to minimize text elision
        self._ensure_all_columns_proper_width()

        # Force complete model refresh to update text display
        if self.model():
            self.model().layoutChanged.emit()

        # Force viewport update
        self.viewport().update()

        # Schedule delayed update to ensure proper text rendering
        schedule_ui_update(lambda: self._refresh_text_display(), delay=50)

        # Schedule another word wrap check to ensure it stays disabled
        schedule_ui_update(lambda: self.setWordWrap(False), delay=100)

        model = self.model()
        if not model:
            return

        # For empty table, always hide horizontal scrollbar
        if model.rowCount() == 0:
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            return

        # Calculate total column width
        total_width = 0
        for i in range(model.columnCount()):
            total_width += self.columnWidth(i)

        # Get viewport width
        viewport_width = self.viewport().width()

        # Simple logic: show scrollbar if content is wider than viewport
        if total_width > viewport_width:
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        else:
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def _smart_scrollbar_adjustment(self, column_added: bool = False) -> None:
        """Smart scrollbar position adjustment when columns are added/removed."""
        # This method is currently disabled to prevent issues with table content
        # The scrollbar position is now handled by ensure_horizontal_scrollbar_state

    def on_horizontal_splitter_moved(self, pos: int, index: int) -> None:
        """Handle horizontal splitter movement - no longer adjusts filename column."""
        # No longer needed - columns maintain their fixed widths
        # Horizontal scrollbar will appear when needed

    def on_vertical_splitter_moved(self, pos: int, index: int) -> None:
        """Handle vertical splitter movement."""
        # No special handling needed

    # =====================================
    # UI Methods
    # =====================================

    def set_placeholder_visible(self, visible: bool) -> None:
        """Show or hide the placeholder using the unified helper."""
        if hasattr(self, "placeholder_helper"):
            if visible:
                self.placeholder_helper.show()
            else:
                self.placeholder_helper.hide()
        # Update header visibility when placeholder state changes
        self._update_header_visibility()

    def update_placeholder_visibility(self):
        """Update placeholder visibility based on table content."""
        is_empty = self.is_empty() if hasattr(self, "is_empty") else False
        self.set_placeholder_visible(is_empty)
        # Update header visibility when placeholder visibility changes
        self._update_header_visibility()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        Handle mouse press events for selection and drag initiation.
        """
        # Get the index under the mouse
        index = self.indexAt(event.pos())
        modifiers = event.modifiers()

        # Store clicked index for potential drag
        self._clicked_index = index

        # Handle left button press
        if event.button() == Qt.LeftButton:
            # Store drag start position
            self._drag_start_pos = event.pos()

            # If clicking on empty space, clear selection
            if not index.isValid():
                if modifiers == Qt.NoModifier:
                    self._set_anchor_row(None, emit_signal=False)
                    self.clearSelection()
                return

            # Handle selection based on modifiers
            if modifiers == Qt.NoModifier:
                # Simple click - clear all selections and select only this item
                self._set_anchor_row(index.row(), emit_signal=False)
                # Let Qt handle the selection change
            elif modifiers == Qt.ControlModifier:
                # Ctrl+click - toggle selection (add/remove from current selection)
                # Set anchor and let Qt handle the selection in selectionChanged
                self._set_anchor_row(index.row(), emit_signal=False)
            elif modifiers == Qt.ShiftModifier:
                # Shift+click - select range
                anchor = self._get_anchor_row()
                if anchor is not None:
                    self.select_rows_range(anchor, index.row())
                    return
                else:
                    self._set_anchor_row(index.row(), emit_signal=False)

        # Call parent implementation
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        """Handle double-click with Shift modifier support."""
        if self.is_empty():
            event.ignore()
            return

        index = self.indexAt(event.pos())
        if not index.isValid():
            super().mouseDoubleClickEvent(event)
            return

        selection_model = self.selectionModel()

        if event.modifiers() & Qt.ShiftModifier:
            # Cancel range selection for extended metadata on single file
            selection_model.clearSelection()
            selection_model.select(
                index,
                QItemSelectionModel.Clear | QItemSelectionModel.Select | QItemSelectionModel.Rows,
            )
            selection_model.setCurrentIndex(index, QItemSelectionModel.NoUpdate)
            self._manual_anchor_index = index
        else:
            self.ensure_anchor_or_select(index, event.modifiers())

        # Trigger metadata load
        try:
            get_app_context()
            # Try to get main window through context for file double click handling
            # This is a transitional approach until we fully migrate event handling
            parent_window = self.parent()
            while parent_window and not hasattr(parent_window, "handle_file_double_click"):
                parent_window = parent_window.parent()

            if parent_window:
                parent_window.handle_file_double_click(index, event.modifiers())
        except RuntimeError:
            # ApplicationContext not ready yet, use legacy approach
            if hasattr(self, "parent_window"):
                self.parent_window.handle_file_double_click(index, event.modifiers())

        self._sync_selection_safely()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """
        Handle mouse release events.
        """
        if event.button() == Qt.LeftButton:
            # Reset drag start position
            self._drag_start_pos = None

            # If we were dragging, clean up
            if self._is_dragging:
                self._end_custom_drag()

                # Final status update after drag ends to ensure UI consistency
                def final_status_update():
                    current_selection = self._get_current_selection()
                    if current_selection:
                        selection_store = self._get_selection_store()
                        if selection_store and not self._legacy_selection_mode:
                            selection_store.selection_changed.emit(list(current_selection))

                # Schedule final status update after everything is settled
                schedule_ui_update(final_status_update, delay=50)

        # Call parent implementation
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event) -> None:
        """
        Handle mouse move events for drag initiation.
        """
        if self.is_empty():
            return

        # Get current mouse position and check what's under it
        index = self.indexAt(event.pos())
        hovered_row = index.row() if index.isValid() else -1

        # Handle drag operations
        if event.buttons() & Qt.LeftButton and self._drag_start_pos is not None:
            distance = (event.pos() - self._drag_start_pos).manhattanLength()

            if distance >= QApplication.startDragDistance():
                # Check if we're dragging from a selected item
                start_index = self.indexAt(self._drag_start_pos)
                if start_index.isValid():
                    start_row = start_index.row()
                    if start_row in self._get_current_selection_safe():
                        # Start drag from selected item
                        self._start_custom_drag()
                        return

        # Skip hover updates if dragging (using Qt built-in drag now)
        if self._is_dragging:
            return

        # Update hover highlighting (only when not dragging)
        if hasattr(self, "hover_delegate") and hovered_row != self.hover_delegate.hovered_row:
            old_row = self.hover_delegate.hovered_row
            self.hover_delegate.update_hover_row(hovered_row)

            for r in (old_row, hovered_row):
                if r >= 0:
                    left = self.model().index(r, 0)
                    right = self.model().index(r, self.model().columnCount() - 1)
                    row_rect = self.visualRect(left).united(self.visualRect(right))
                    self.viewport().update(row_rect)

    def keyPressEvent(self, event) -> None:
        """Handle keyboard navigation, sync selection, and modifier changes during drag."""
        # SIMPLIFIED: No longer needed - selection is cleared during column updates

        # Handle column management shortcuts

        # Ctrl+T: Auto-fit columns to content
        if event.key() == Qt.Key_T and event.modifiers() == Qt.ControlModifier:
            self._auto_fit_columns_to_content()
            event.accept()
            return

        # Ctrl+Shift+T: Reset column widths to default
        if event.key() == Qt.Key_T and event.modifiers() == (Qt.ControlModifier | Qt.ShiftModifier):
            self._reset_columns_to_default()
            event.accept()
            return

        # Don't handle ESC at all - let it pass through to dialogs and other components
        # Cursor cleanup is handled automatically by other mechanisms

        # Skip key handling during drag (using Qt built-in drag now)
        if self._is_dragging:
            return

        super().keyPressEvent(event)
        if event.matches(QKeySequence.SelectAll) or event.key() in (
            Qt.Key_Space,
            Qt.Key_Return,
            Qt.Key_Enter,
            Qt.Key_Up,
            Qt.Key_Down,
            Qt.Key_Left,
            Qt.Key_Right,
        ):
            self._sync_selection_safely()

    def keyReleaseEvent(self, event) -> None:
        """Handle key release events, including modifier changes during drag."""
        # Skip key handling during drag (using Qt built-in drag now)
        if self._is_dragging:
            return

        super().keyReleaseEvent(event)

    # =====================================
    # Table State & Utility Methods
    # =====================================


    def is_empty(self) -> bool:
        """Check if the table is empty (no files or no model)."""
        if not self.model():
            return True
        files = getattr(self.model(), "files", [])
        return not files or len(files) == 0

    def focusOutEvent(self, event) -> None:
        super().focusOutEvent(event)
        if self.context_focused_row is not None:
            self.context_focused_row = None

        # Clear hover state and hide tooltips when focus is lost
        if hasattr(self, "hover_delegate"):
            old_row = self.hover_delegate.hovered_row
            self.hover_delegate.update_hover_row(-1)
            if old_row >= 0:
                left = self.model().index(old_row, 0)
                right = self.model().index(old_row, self.model().columnCount() - 1)
                row_rect = self.visualRect(left).united(self.visualRect(right))
                self.viewport().update(row_rect)

        # Hide any active tooltips
        from utils.tooltip_helper import TooltipHelper

        TooltipHelper.clear_tooltips_for_widget(self)

        self.viewport().update()

    def focusInEvent(self, event) -> None:
        """SIMPLIFIED focus handling - just sync selection, no special cases"""
        super().focusInEvent(event)

        # Simple sync: update SelectionStore with current Qt selection
        selection_model = self.selectionModel()
        if selection_model is not None:
            selected_rows = {index.row() for index in selection_model.selectedRows()}
            self._update_selection_store(
                selected_rows, emit_signal=False
            )  # Don't emit signal on focus

        self.viewport().update()

    def leaveEvent(self, event) -> None:
        """Handle mouse leave events to hide tooltips and clear hover state."""
        # Clear hover state when mouse leaves the table
        if hasattr(self, "hover_delegate"):
            old_row = self.hover_delegate.hovered_row
            self.hover_delegate.update_hover_row(-1)
            if old_row >= 0:
                left = self.model().index(old_row, 0)
                right = self.model().index(old_row, self.model().columnCount() - 1)
                row_rect = self.visualRect(left).united(self.visualRect(right))
                self.viewport().update(row_rect)

        # Hide any active tooltips
        from utils.tooltip_helper import TooltipHelper

        TooltipHelper.clear_tooltips_for_widget(self)

        super().leaveEvent(event)

    def _viewport_leave_event(self, event) -> None:
        """Handle viewport leave events to hide tooltips and clear hover state."""
        # Clear hover state when mouse leaves the viewport
        if hasattr(self, "hover_delegate"):
            old_row = self.hover_delegate.hovered_row
            self.hover_delegate.update_hover_row(-1)
            if old_row >= 0:
                left = self.model().index(old_row, 0)
                right = self.model().index(old_row, self.model().columnCount() - 1)
                row_rect = self.visualRect(left).united(self.visualRect(right))
                self.viewport().update(row_rect)

        # Hide any active tooltips
        from utils.tooltip_helper import TooltipHelper

        TooltipHelper.clear_tooltips_for_widget(self)

        # Call original viewport leaveEvent if it exists
        original_leave_event = getattr(self.viewport(), "_original_leave_event", None)
        if original_leave_event:
            original_leave_event(event)

    def _viewport_enter_event(self, event) -> None:
        """Handle viewport enter events to restore hover state."""
        # Update hover state when mouse enters the viewport
        pos = self.viewport().mapFromGlobal(QCursor.pos())
        index = self.indexAt(pos)
        hovered_row = index.row() if index.isValid() else -1

        if hasattr(self, "hover_delegate"):
            self.hover_delegate.update_hover_row(hovered_row)
            if hovered_row >= 0:
                left = self.model().index(hovered_row, 0)
                right = self.model().index(hovered_row, self.model().columnCount() - 1)
                row_rect = self.visualRect(left).united(self.visualRect(right))
                self.viewport().update(row_rect)

        # Call original viewport enterEvent if it exists
        original_enter_event = getattr(self.viewport(), "_original_enter_event", None)
        if original_enter_event:
            original_enter_event(event)

    def enterEvent(self, event) -> None:
        """Handle mouse enter events to restore hover state."""
        # Update hover state when mouse enters the table
        pos = self.viewport().mapFromGlobal(QCursor.pos())
        index = self.indexAt(pos)
        hovered_row = index.row() if index.isValid() else -1

        if hasattr(self, "hover_delegate"):
            self.hover_delegate.update_hover_row(hovered_row)
            if hovered_row >= 0:
                left = self.model().index(hovered_row, 0)
                right = self.model().index(hovered_row, self.model().columnCount() - 1)
                row_rect = self.visualRect(left).united(self.visualRect(right))
                self.viewport().update(row_rect)

        super().enterEvent(event)

    def wheelEvent(self, event) -> None:
        """Update hover state after scroll to track cursor position smoothly."""
        super().wheelEvent(event)

        # Update hover after scroll completes to reflect current cursor position
        pos = self.viewport().mapFromGlobal(QCursor.pos())
        index = self.indexAt(pos)
        hovered_row = index.row() if index.isValid() else -1

        if hasattr(self, "hover_delegate"):
            old_row = self.hover_delegate.hovered_row
            if old_row != hovered_row:
                self.hover_delegate.update_hover_row(hovered_row)
                # Update both old and new rows
                for r in (old_row, hovered_row):
                    if r >= 0:
                        left = self.model().index(r, 0)  # type: ignore
                        right = self.model().index(r, self.model().columnCount() - 1)  # type: ignore
                        row_rect = self.visualRect(left).united(self.visualRect(right))
                        self.viewport().update(row_rect)

    def scrollTo(self, index, hint=None) -> None:
        """
        Override scrollTo to prevent automatic scrolling when selections change.
        This prevents the table from moving when selecting rows.
        """
        # Check if table is empty or in placeholder mode
        if self.is_empty():
            # In empty/placeholder mode, allow normal scrolling
            super().scrollTo(index, hint)
            return

        # Allow minimal scrolling only if the selected item is completely out of view
        viewport_rect = self.viewport().rect()  # type: ignore
        item_rect = self.visualRect(index)  # type: ignore

        # Only scroll if item is completely outside the viewport
        if not viewport_rect.intersects(item_rect):
            super().scrollTo(index, hint)
        # Otherwise, do nothing - prevent automatic centering

    def enable_selection_store_mode(self):
        """Enable SelectionStore mode (disable legacy selection handling)."""
        selection_store = self._get_selection_store()
        if selection_store:
            self._legacy_selection_mode = False
            # Sync current selection to SelectionStore
            current_selection = {index.row() for index in self.selectionModel().selectedRows()}  # type: ignore
            selection_store.set_selected_rows(current_selection, emit_signal=False)
            if hasattr(self, "anchor_row") and self.anchor_row is not None:
                selection_store.set_anchor_row(self.anchor_row, emit_signal=False)
            logger.debug("[FileTableView] SelectionStore mode enabled", extra={"dev_only": True})
        else:
            logger.warning(
                "[FileTableView] Cannot enable SelectionStore mode - store not available"
            )

    def disable_selection_store_mode(self):
        """Disable selection store synchronization mode."""
        if self._get_selection_store():
            self._get_selection_store().set_active(False)  # type: ignore
            logger.debug("[FileTable] Selection store mode disabled")

    def _force_cursor_cleanup(self):
        """Force immediate cursor cleanup during drag operations."""
        # Immediate and aggressive cursor cleanup
        cursor_count = 0
        while QApplication.overrideCursor():
            QApplication.restoreOverrideCursor()
            cursor_count += 1
            if cursor_count > 15:  # Higher limit for stuck cursors
                break

        if cursor_count > 0:
            logger.debug(
                f"[FileTableView] Force cleaned {cursor_count} stuck cursors during drag",
                extra={"dev_only": True},
            )

        # Process events immediately
        QApplication.processEvents()

    def _emergency_cursor_cleanup(self):
        """Emergency cursor cleanup method."""
        # Use the force cleanup method first
        self._force_cursor_cleanup()

        # Additional cleanup for drag manager
        drag_manager = DragManager.get_instance()
        if drag_manager.is_drag_active():
            logger.debug(
                "[FileTableView] Emergency: Forcing DragManager cleanup", extra={"dev_only": True}
            )
            drag_manager.force_cleanup()

        # Force viewport update
        if hasattr(self, "viewport"):
            self.viewport().update()  # type: ignore
        QApplication.processEvents()

    # =====================================
    # Column Management Methods
    # =====================================

    def _load_column_visibility_config(self) -> dict:
        """Load column visibility configuration from config.json."""
        try:
            # Try main config system first
            main_window = self._get_main_window()
            if main_window and hasattr(main_window, "window_config_manager"):
                config_manager = main_window.window_config_manager.config_manager
                window_config = config_manager.get_category("window")
                saved_visibility = window_config.get("file_table_columns", {})

                if saved_visibility:
                    logger.debug(f"[ColumnVisibility] Loaded from main config: {saved_visibility}")
                    # Ensure we have all columns from config, not just saved ones
                    from core.unified_column_service import get_column_service

                    service = get_column_service()

                    complete_visibility = {}
                    for key, cfg in service.get_all_columns().items():
                        # Use saved value if available, otherwise use default
                        complete_visibility[key] = saved_visibility.get(key, cfg.default_visible)
                    logger.debug(
                        f"[ColumnVisibility] Complete visibility state: {complete_visibility}"
                    )
                    return complete_visibility

            # Fallback to old method
            from utils.json_config_manager import load_config

            config = load_config()
            saved_visibility = config.get("file_table_columns", {})

            if saved_visibility:
                logger.debug(f"[ColumnVisibility] Loaded from fallback config: {saved_visibility}")
                # Ensure we have all columns from config, not just saved ones
                from core.unified_column_service import get_column_service

                service = get_column_service()

                complete_visibility = {}
                for key, cfg in service.get_all_columns().items():
                    # Use saved value if available, otherwise use default
                    complete_visibility[key] = saved_visibility.get(key, cfg.default_visible)
                logger.debug(f"[ColumnVisibility] Complete visibility state: {complete_visibility}")
                return complete_visibility

        except Exception as e:
            logger.warning(f"[ColumnVisibility] Error loading config: {e}")

        # Return default configuration
        from core.unified_column_service import get_column_service

        service = get_column_service()

        default_visibility = {
            key: cfg.default_visible for key, cfg in service.get_all_columns().items()
        }
        return default_visibility

    def _save_column_visibility_config(self) -> None:
        """Save column visibility configuration to main config system."""
        try:
            # Get the main window and its config manager
            main_window = self._get_main_window()
            if main_window and hasattr(main_window, "window_config_manager"):
                config_manager = main_window.window_config_manager.config_manager
                window_config = config_manager.get_category("window")

                # Save current visibility state
                window_config.set("file_table_columns", self._visible_columns)
                logger.debug(f"[ColumnVisibility] Saved to main config: {self._visible_columns}")

                # Mark dirty for debounced save
                config_manager.mark_dirty()
            else:
                # Fallback to old method
                from utils.json_config_manager import load_config, save_config

                config = load_config()
                config["file_table_columns"] = self._visible_columns
                save_config(config)
                logger.debug(
                    f"[ColumnVisibility] Saved to fallback config: {self._visible_columns}"
                )
        except Exception as e:
            logger.warning(f"Failed to save column visibility config: {e}")

    def _sync_view_model_columns(self) -> None:
        """Ensure view and model have synchronized column visibility."""
        model = self.model()
        if not model or not hasattr(model, "get_visible_columns"):
            logger.debug("[ColumnSync] No model or model doesn't support get_visible_columns")
            return

        try:
            # Ensure we have complete visibility state
            if not hasattr(self, "_visible_columns") or not self._visible_columns:
                logger.warning("[ColumnSync] _visible_columns not initialized, reloading")
                self._visible_columns = self._load_column_visibility_config()

            # Get current state from both view and model
            view_visible = [key for key, visible in self._visible_columns.items() if visible]
            model_visible = model.get_visible_columns()

            logger.debug(f"[ColumnSync] View visible: {view_visible}")
            logger.debug(f"[ColumnSync] Model visible: {model_visible}")

            # Sort both lists to ensure consistent comparison
            view_visible_sorted = sorted(view_visible)
            model_visible_sorted = sorted(model_visible)

            # If they don't match, update model to match view (view is authoritative)
            if view_visible_sorted != model_visible_sorted:
                logger.warning("[ColumnSync] Columns out of sync! Updating model to match view")
                logger.debug(f"[ColumnSync] View wants: {view_visible_sorted}")
                logger.debug(f"[ColumnSync] Model has: {model_visible_sorted}")

                if hasattr(model, "update_visible_columns"):
                    model.update_visible_columns(view_visible)

                    # Verify the update worked
                    updated_model_visible = model.get_visible_columns()
                    logger.debug(f"[ColumnSync] Model updated to: {sorted(updated_model_visible)}")

                    if sorted(updated_model_visible) != view_visible_sorted:
                        logger.error("[ColumnSync] CRITICAL: Model update failed!")
                        logger.error(f"[ColumnSync] Expected: {view_visible_sorted}")
                        logger.error(f"[ColumnSync] Got: {sorted(updated_model_visible)}")
                else:
                    logger.error("[ColumnSync] Model doesn't support update_visible_columns")
            else:
                logger.debug("[ColumnSync] View and model are already synchronized")

        except Exception as e:
            logger.error(f"[ColumnSync] Error syncing columns: {e}", exc_info=True)

    def _toggle_column_visibility(self, column_key: str) -> None:
        """Toggle visibility of a specific column and refresh the table."""

        from core.unified_column_service import get_column_service

        all_columns = get_column_service().get_all_columns()
        if column_key not in all_columns:
            logger.warning(f"Unknown column key: {column_key}")
            return

        column_config = all_columns[column_key]
        if not getattr(column_config, "removable", True):
            logger.warning(f"Cannot toggle non-removable column: {column_key}")
            return  # Can't toggle non-removable columns

        # Ensure we have complete visibility state
        if not hasattr(self, "_visible_columns") or not self._visible_columns:
            logger.warning("[ColumnToggle] _visible_columns not initialized, reloading config")
            self._visible_columns = self._load_column_visibility_config()

        # Toggle visibility
        current_visibility = self._visible_columns.get(column_key, column_config.default_visible)
        new_visibility = not current_visibility
        self._visible_columns[column_key] = new_visibility

        logger.info(f"Toggled column '{column_key}' visibility to {new_visibility}")
        logger.debug(f"[ColumnToggle] Current visibility state: {self._visible_columns}")

        # Verify we have all columns in visibility state
        from core.unified_column_service import get_column_service

        for key, cfg in get_column_service().get_all_columns().items():
            if key not in self._visible_columns:
                self._visible_columns[key] = cfg.default_visible
                logger.debug(
                    f"[ColumnToggle] Added missing column '{key}' with default visibility {cfg.default_visible}"
                )

        # Save configuration immediately
        self._save_column_visibility_config()

        # Ensure view and model are synchronized before updating
        self._sync_view_model_columns()

        # Update table display (clears selection)
        self._update_table_columns()

        logger.info(f"Column '{column_key}' visibility toggle completed")

        # Debug: Show current visible columns
        visible_cols = [key for key, visible in self._visible_columns.items() if visible]
        logger.debug(f"[ColumnToggle] Currently visible columns: {visible_cols}")

    def add_column(self, column_key: str) -> None:
        """Add a column to the table (make it visible)."""

        from core.unified_column_service import get_column_service

        if column_key not in get_column_service().get_all_columns():
            logger.warning(f"Cannot add unknown column: {column_key}")
            return

        # Ensure we have complete visibility state
        if not hasattr(self, "_visible_columns") or not self._visible_columns:
            self._visible_columns = self._load_column_visibility_config()

        # Make column visible
        if not self._visible_columns.get(column_key, False):
            self._visible_columns[column_key] = True
            logger.info(f"Added column '{column_key}' to table")

            # Save and update
            self._save_column_visibility_config()
            self._sync_view_model_columns()
            self._update_table_columns()

            # Force configure columns after model update to ensure new column gets proper width
            from utils.timer_manager import schedule_ui_update

            schedule_ui_update(
                self._configure_columns_delayed,
                delay=50,
                timer_id=f"configure_new_column_{column_key}",
            )

            # Ensure proper width for the newly added column
            schedule_ui_update(
                self._ensure_new_column_proper_width,
                delay=100,
                timer_id=f"ensure_column_width_{column_key}",
            )

            # Debug
            visible_cols = [key for key, visible in self._visible_columns.items() if visible]
            logger.debug(f"[AddColumn] Currently visible columns: {visible_cols}")
        else:
            logger.debug(f"Column '{column_key}' is already visible")

    def _ensure_new_column_proper_width(self) -> None:
        """Ensure newly added column has proper width."""
        try:
            if not self.model():
                return

            # Get visible columns from model
            visible_columns = (
                self.model().get_visible_columns()
                if hasattr(self.model(), "get_visible_columns")
                else []
            )

            # Check all visible columns for proper width
            for column_key in visible_columns:
                column_index = visible_columns.index(column_key) + 1  # +1 for status column

                if column_index >= self.model().columnCount():
                    continue

                # Get current width
                current_width = self.columnWidth(column_index)

                # Get recommended width
                recommended_width = self._ensure_column_proper_width(column_key, current_width)

                # Apply if different
                if recommended_width != current_width:
                    logger.debug(
                        f"[ColumnWidth] Adjusting column '{column_key}' width from {current_width}px to {recommended_width}px"
                    )
                    self.setColumnWidth(column_index, recommended_width)
                    self._schedule_column_save(column_key, recommended_width)

        except Exception as e:
            logger.warning(f"Error ensuring new column proper width: {e}")

    def remove_column(self, column_key: str) -> None:
        """Remove a column from the table (make it invisible)."""

        from core.unified_column_service import get_column_service

        all_columns = get_column_service().get_all_columns()
        if column_key not in all_columns:
            logger.warning(f"Cannot remove unknown column: {column_key}")
            return

        column_config = all_columns[column_key]
        if not getattr(column_config, "removable", True):
            logger.warning(f"Cannot remove non-removable column: {column_key}")
            return

        # Ensure we have complete visibility state
        if not hasattr(self, "_visible_columns") or not self._visible_columns:
            self._visible_columns = self._load_column_visibility_config()

        # Make column invisible
        if self._visible_columns.get(column_key, False):
            self._visible_columns[column_key] = False
            logger.info(f"Removed column '{column_key}' from table")

            # Save and update
            self._save_column_visibility_config()
            self._sync_view_model_columns()
            self._update_table_columns()

            # Debug
            visible_cols = [key for key, visible in self._visible_columns.items() if visible]
            logger.debug(f"[RemoveColumn] Currently visible columns: {visible_cols}")
        else:
            logger.debug(f"Column '{column_key}' is already invisible")

    def get_visible_columns_list(self) -> list:
        """Get list of currently visible column keys."""
        if not hasattr(self, "_visible_columns") or not self._visible_columns:
            self._visible_columns = self._load_column_visibility_config()
        return [key for key, visible in self._visible_columns.items() if visible]

    def debug_column_state(self) -> None:
        """Debug method to print current column state."""
        logger.debug("[ColumnDebug] === FileTableView Column State ===")
        logger.debug(f"[ColumnDebug] _visible_columns: {self._visible_columns}")
        visible_cols = self.get_visible_columns_list()
        logger.debug(f"[ColumnDebug] Visible columns list: {visible_cols}")

        model = self.model()
        if model and hasattr(model, "get_visible_columns"):
            model_visible = model.get_visible_columns()
            logger.debug(f"[ColumnDebug] Model visible columns: {model_visible}")
            logger.debug(f"[ColumnDebug] Model column count: {model.columnCount()}")

            if hasattr(model, "debug_column_state"):
                model.debug_column_state()
        else:
            logger.debug("[ColumnDebug] No model or model doesn't support get_visible_columns")

        logger.debug("[ColumnDebug] =========================================")

    def _clear_selection_for_column_update(self, force_emit_signal: bool = False) -> None:
        """Clear selection during column updates."""
        self.clearSelection()

        selection_store = self._get_selection_store()
        if selection_store and not self._legacy_selection_mode:
            selection_store.set_selected_rows(set(), emit_signal=force_emit_signal)

    def _handle_column_update_lifecycle(self, update_function: callable) -> None:
        """Handle the complete lifecycle of a column update operation."""
        try:
            self._updating_columns = True
            self._clear_selection_for_column_update(force_emit_signal=False)
            update_function()
        except Exception as e:
            logger.error(f"[ColumnUpdate] Error during column update: {e}")
            raise
        finally:
            self._updating_columns = False
            self._clear_selection_for_column_update(force_emit_signal=True)

    def _update_table_columns(self) -> None:
        """Update table columns based on visibility configuration."""
        model = self.model()
        if not model:
            return

        def perform_column_update():
            visible_columns = self.get_visible_columns_list()

            if hasattr(model, "update_visible_columns"):
                model.update_visible_columns(visible_columns)

            self._configure_columns()
            self._update_header_visibility()
            self._force_scrollbar_update()

        self._handle_column_update_lifecycle(perform_column_update)

    def _restore_pending_selection(self) -> None:
        """Restore pending selection if it exists."""
        # SIMPLIFIED: No longer needed - selection is cleared during column updates

    def _get_metadata_tree(self):
        """Get the metadata tree widget from the parent hierarchy."""
        parent = self.parent()
        while parent:
            if hasattr(parent, "metadata_tree"):
                return parent.metadata_tree
            elif hasattr(parent, "metadata_tree_view"):
                return parent.metadata_tree_view
            parent = parent.parent()
        return None

    def _get_main_window(self):
        """Get the main window from the parent hierarchy."""
        parent = self.parent()
        while parent:
            if hasattr(parent, "window_config_manager"):
                return parent
            parent = parent.parent()
        return None

    def _clear_preview_and_metadata(self) -> None:
        """Clear preview and metadata displays when no selection exists."""
        try:
            parent_window = self.parent()
            while parent_window and not hasattr(parent_window, "metadata_tree_view"):
                parent_window = parent_window.parent()

            if parent_window:
                if hasattr(parent_window, "metadata_tree_view"):
                    metadata_tree = parent_window.metadata_tree_view
                    if hasattr(metadata_tree, "show_empty_state"):
                        metadata_tree.show_empty_state("No file selected")

                if hasattr(parent_window, "preview_tables_view"):
                    preview_view = parent_window.preview_tables_view
                    if hasattr(preview_view, "clear_view"):
                        preview_view.clear_view()

        except Exception as e:
            logger.warning(f"Error clearing preview/metadata displays: {e}")

    # =====================================
    # Column Management Shortcuts
    # =====================================

    def _reset_columns_to_default(self) -> None:
        """Reset all column widths to their default values (Ctrl+Shift+T).

        Restores all columns to config defaults with Interactive resize mode.
        """
        try:
            from core.unified_column_service import get_column_service

            visible_columns = []
            if hasattr(self.model(), "get_visible_columns"):
                visible_columns = self.model().get_visible_columns()
            else:
                visible_columns = ["filename", "file_size", "type", "modified"]

            header = self.horizontalHeader()
            if not header:
                return

            for i, column_key in enumerate(visible_columns):
                column_index = i + 1  # +1 because column 0 is status column
                cfg = get_column_service().get_column_config(column_key)
                default_width = cfg.width if cfg else 100

                # Reset to Interactive mode for all columns
                header.setSectionResizeMode(column_index, QHeaderView.Interactive)

                # Apply intelligent width validation for all columns
                final_width = self._ensure_column_proper_width(column_key, default_width)

                self.setColumnWidth(column_index, final_width)
                self._schedule_column_save(column_key, final_width)

            self._update_header_visibility()

        except Exception as e:
            logger.error(f"Error resetting columns to default: {e}")

    def _auto_fit_columns_to_content(self) -> None:
        """Auto-fit all column widths to their content (Ctrl+T).

        Special handling:
        - Filename column: stretches to fill available space (last stretch)
        - Other columns: resize to fit content with min/max constraints
        """
        try:
            from config import GLOBAL_MIN_COLUMN_WIDTH

            if not self.model() or self.model().rowCount() == 0:
                return

            visible_columns = []
            if hasattr(self.model(), "get_visible_columns"):
                visible_columns = self.model().get_visible_columns()
            else:
                visible_columns = ["filename", "file_size", "type", "modified"]

            header = self.horizontalHeader()
            if not header:
                return

            for i, column_key in enumerate(visible_columns):
                column_index = i + 1  # +1 because column 0 is status column
                from core.unified_column_service import get_column_service

                cfg = get_column_service().get_column_config(column_key)

                # Special handling for filename column: set to stretch
                if column_key == "filename":
                    header.setSectionResizeMode(column_index, QHeaderView.Stretch)
                    continue

                # For other columns: resize to contents with constraints
                self.resizeColumnToContents(column_index)

                # Apply minimum width constraint
                min_width = max(
                    (cfg.min_width if cfg else GLOBAL_MIN_COLUMN_WIDTH), GLOBAL_MIN_COLUMN_WIDTH
                )
                current_width = self.columnWidth(column_index)
                final_width = max(current_width, min_width)

                # Apply intelligent width validation for all columns
                final_width = self._ensure_column_proper_width(column_key, final_width)

                if final_width != current_width:
                    self.setColumnWidth(column_index, final_width)

                self._schedule_column_save(column_key, final_width)

            self._update_header_visibility()

        except Exception as e:
            logger.error(f"Error auto-fitting columns to content: {e}")

    def refresh_columns_after_model_change(self) -> None:
        self._configure_columns()
        self.update_placeholder_visibility()
        self._update_header_visibility()
        self.viewport().update()

        # Ensure word wrap is disabled after column changes
        self._ensure_no_word_wrap()

    def _check_and_fix_column_widths(self) -> None:
        """Check if column widths need to be reset due to incorrect saved values."""
        try:
            # Get current saved widths
            main_window = self._get_main_window()
            saved_widths = {}

            if main_window and hasattr(main_window, "window_config_manager"):
                try:
                    config_manager = main_window.window_config_manager.config_manager
                    window_config = config_manager.get_category("window")
                    saved_widths = window_config.get("file_table_column_widths", {})
                except Exception:
                    # Try fallback method
                    from utils.json_config_manager import load_config

                    config = load_config()
                    saved_widths = config.get("file_table_column_widths", {})

            # Check if most columns are set to 100px (suspicious)
            suspicious_count = 0
            total_count = 0

            from core.unified_column_service import get_column_service

            for column_key, column_config in get_column_service().get_all_columns().items():
                if getattr(column_config, "default_visible", False):
                    total_count += 1
                    default_width = getattr(column_config, "width", 100)
                    saved_width = saved_widths.get(column_key, default_width)

                    if saved_width == 100 and default_width > 120:
                        suspicious_count += 1

            # If most visible columns have suspicious widths, reset them
            if total_count > 0 and suspicious_count >= (total_count * 0.5):
                self._reset_column_widths_to_defaults()
                if self.model() and self.model().columnCount() > 0:
                    from utils.timer_manager import schedule_ui_update

                    schedule_ui_update(self._configure_columns, delay=10)

        except Exception as e:
            logger.error(f"Failed to check column widths: {e}")
