"""Module: file_table_view.py

Author: Michael Economou
Date: 2025-05-21


Custom QTableView with Windows Explorer-like behavior:
- Full-row selection with anchor handling
- Intelligent column width management with automatic viewport fitting
- Drag & drop support with custom MIME types
- Hover highlighting and visual feedback
- Automatic vertical scrollbar detection and filename column adjustment
"""

from contextlib import suppress

from oncutf.core.application_context import get_app_context
from oncutf.core.drag.drag_manager import DragManager
from oncutf.core.pyqt_imports import (
    QAbstractItemView,
    QApplication,
    QCursor,
    QEvent,
    QHeaderView,
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
from oncutf.core.theme_manager import get_theme_manager

# Mixins imported for backwards compatibility during migration
# from oncutf.ui.mixins import ColumnManagementMixin, DragDropMixin, SelectionMixin
from oncutf.ui.behaviors import (
    ColumnManagementBehavior,
    DragDropBehavior,
    SelectionBehavior,
)
from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.shared.timer_manager import (
    schedule_ui_update,
)
from oncutf.utils.ui.placeholder_helper import create_placeholder_helper
from oncutf.utils.ui.tooltip_helper import TooltipHelper, TooltipType

logger = get_cached_logger(__name__)

# Constants for better maintainability
SCROLLBAR_MARGIN = 40


class FileTableView(QTableView):
    """Custom QTableView with Windows Explorer-like behavior.

    Features:
    - Full-row selection with anchor handling (via SelectionBehavior)
    - Drag & drop support with custom MIME types (via DragDropBehavior)
    - Column width/visibility management (via ColumnManagementBehavior)
    - Fixed-width column management with delayed save (7 seconds)
    - Horizontal scrollbar appears when columns exceed viewport width
    - Hover highlighting and visual feedback
    - Unified placeholder management using PlaceholderHelper
    - Keyboard shortcuts for column management (Ctrl+T, Ctrl+Shift+T)

    Architecture:
    - Uses composition pattern with behavior classes (NEW)
    - No longer inherits from mixins (MIGRATION COMPLETE)
    - Behaviors: SelectionBehavior, DragDropBehavior, ColumnManagementBehavior

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
    refresh_requested = pyqtSignal()  # Emitted when F5 pressed for full refresh

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
        # Row height from theme manager
        theme = get_theme_manager()
        self.verticalHeader().setDefaultSectionSize(theme.get_constant("table_row_height"))

        # Force single-line text display
        self.setWordWrap(False)  # Ensure word wrap is disabled
        self.setSizeAdjustPolicy(QAbstractItemView.AdjustIgnored)  # Keep control over widths

        # Ensure scrollbar updates properly
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Enable smooth pixel-based scrolling instead of per-column jumps
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

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
        # Note: _is_dragging is now delegated to DragDropBehavior
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
        from oncutf.ui.delegates.ui_delegates import FileTableHoverDelegate

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
        from oncutf.utils.shared.timer_manager import schedule_ui_update

        schedule_ui_update(self._update_header_visibility, delay=100)

        # Selection loop protection
        self._selection_change_count = 0
        self._last_selection_change_time = 0
        self._max_selection_changes_per_second = 20  # Increased to 20 for better performance

        # Protection against infinite loops in ensure_anchor_or_select
        self._ensuring_selection = False

        # Protection against infinite loops in selectionChanged
        self._processing_selection_change = False

        # Setup custom tooltip event filter
        self._tooltip_timer = QTimer()
        self._tooltip_timer.setSingleShot(True)
        self._tooltip_timer.timeout.connect(self._show_custom_tooltip)
        self._current_tooltip_index = QModelIndex()
        self.viewport().installEventFilter(self)

        # Initialize behaviors (composition pattern)
        self._selection_behavior = SelectionBehavior(self)
        self._drag_drop_behavior = DragDropBehavior(self)
        self._column_mgmt_behavior = ColumnManagementBehavior(self)

        # Register shutdown hook for column save
        self._column_mgmt_behavior.register_shutdown_hook()

    def eventFilter(self, obj, event):
        """Event filter for custom tooltips on table cells"""
        if obj == self.viewport():
            if event.type() == QEvent.ToolTip:
                # Suppress default Qt tooltips
                return True
            elif event.type() == QEvent.MouseMove:
                # Get index under mouse
                index = self.indexAt(event.pos())
                if index != self._current_tooltip_index:
                    # Index changed, hide current tooltip and start timer for new one (local only)
                    TooltipHelper.clear_tooltips_for_widget(self.viewport())
                    self._tooltip_timer.stop()
                    self._current_tooltip_index = index
                    if index.isValid():
                        # Start timer to show tooltip after hover delay
                        self._tooltip_timer.start(600)  # 600ms delay
                if not index.isValid():
                    TooltipHelper.clear_tooltips_for_widget(self.viewport())
                    self._tooltip_timer.stop()
                return False
            elif event.type() in (QEvent.MouseButtonPress, QEvent.MouseButtonRelease):
                # Mouse clicked - hide tooltip immediately
                TooltipHelper.clear_tooltips_for_widget(self.viewport())
                self._tooltip_timer.stop()
            elif event.type() in (QEvent.Leave, QEvent.HoverLeave):
                # Mouse left viewport, hide tooltip (local only)
                TooltipHelper.clear_tooltips_for_widget(self.viewport())
                self._tooltip_timer.stop()
                self._current_tooltip_index = QModelIndex()
        return super().eventFilter(obj, event)

    def _show_custom_tooltip(self):
        """Show custom tooltip for current cell"""
        if not self._current_tooltip_index.isValid():
            return

        # Get tooltip text from model
        tooltip_text = self.model().data(self._current_tooltip_index, Qt.ToolTipRole)
        if not tooltip_text:
            return

        # Convert QVariant to string if necessary
        tooltip_text = str(tooltip_text) if tooltip_text else ""
        if not tooltip_text:
            return

        # Determine tooltip type based on content
        tooltip_type = TooltipType.INFO
        if "no metadata" in tooltip_text.lower() or "no hash" in tooltip_text.lower():
            tooltip_type = TooltipType.WARNING
        elif "error" in tooltip_text.lower() or "invalid" in tooltip_text.lower():
            tooltip_type = TooltipType.ERROR
        elif "metadata" in tooltip_text.lower() or "hash" in tooltip_text.lower():
            tooltip_type = TooltipType.INFO

        # Show custom tooltip as temporary (cell hover should not register persistent filters)
        from oncutf.config import TOOLTIP_DURATION

        TooltipHelper.show_tooltip(
            self.viewport(),
            tooltip_text,
            tooltip_type,
            duration=TOOLTIP_DURATION,  # Auto-hide after configured duration, hides immediately on mouse leave via eventFilter
            persistent=False,
        )

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

        # Set fixed row height to prevent expansion (from theme manager)
        theme = get_theme_manager()
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

    def _refresh_text_display(self) -> None:
        """Refresh text display in all visible cells."""
        if not self.model():
            return

        # Get visible area
        visible_rect = self.viewport().rect()
        top_left = self.indexAt(visible_rect.topLeft())
        bottom_right = self.indexAt(visible_rect.bottomRight())

        if top_left.isValid() and bottom_right.isValid():
            # Emit dataChanged for visible area to force text refresh
            self.dataChanged(top_left, bottom_right)
        else:
            # Fallback: refresh all data
            top_left = self.model().index(0, 0)
            bottom_right = self.model().index(
                self.model().rowCount() - 1, self.model().columnCount() - 1
            )
            self.dataChanged(top_left, bottom_right)

    def setModel(self, model) -> None:
        """Set the model for the table view."""
        logger.debug(
            "FileTableView setModel called with model: %s",
            type(model),
            extra={"dev_only": True},
        )

        if model is self.model():
            logger.debug("FileTableView setModel: Same model, skipping", extra={"dev_only": True})
            return

        super().setModel(model)
        if model:
            # Ensure word wrap is disabled when model is set
            self._ensure_no_word_wrap()
            # Store reference to table view in model for callbacks
            model._table_view_ref = self
            # Connect column change signals for dynamic table
            if hasattr(model, "columnsInserted"):
                model.columnsInserted.connect(self._configure_columns)
            if hasattr(model, "columnsRemoved"):
                model.columnsRemoved.connect(self._configure_columns)
            if hasattr(model, "modelReset"):
                model.modelReset.connect(self._configure_columns)
            # If model has columns, setup immediately, otherwise with small delay
            if model.columnCount() > 0:
                # Check and fix column widths if needed (only when model is set)
                # Delay this check to ensure model is fully initialized
                from oncutf.utils.shared.timer_manager import schedule_ui_update

                schedule_ui_update(self._check_and_fix_column_widths, delay=50)
                self._configure_columns()
            else:
                from oncutf.utils.shared.timer_manager import schedule_ui_update

                schedule_ui_update(self._configure_columns, delay=50)
        self.update_placeholder_visibility()
        # Don't call _update_header_visibility() here as it will be called from _configure_columns_delayed()

    # =====================================
    # Table Preparation & Management
    # =====================================

    def prepare_table(self, file_items: list, *, preserve_selection: bool = False) -> None:
        """Prepare the table for display with file items.

        Args:
            file_items: List of FileItem objects to display
            preserve_selection: If True, don't clear selections (used during rename restore)
        """
        logger.debug(
            "prepare_table called with %d items (preserve_selection=%s)",
            len(file_items),
            preserve_selection,
            extra={"dev_only": True},
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
        self.show()  # Ensure table is visible for column setup
        self._configure_columns()
        logger.debug("prepare_table finished", extra={"dev_only": True})
        self._ensure_no_word_wrap()

        # Setup column-specific delegates
        self._setup_column_delegates()

        if hasattr(self, "hover_delegate"):
            self.setItemDelegate(self.hover_delegate)
            self.hover_delegate.hovered_row = -1
        self.viewport().update()
        self.update_placeholder_visibility()
        self.refresh_view_state()

    # =====================================
    # Column Management & Scrollbar Optimization
    # =====================================

    def _setup_column_delegates(self) -> None:
        """Setup column-specific delegates (e.g., color column)."""
        logger.info("[FileTableView] _setup_column_delegates() called")

        if not self.model():
            logger.warning("[FileTableView] No model set, skipping delegates")
            return

        # Get visible columns list from column service
        from oncutf.core.ui_managers import get_column_service

        visible_columns_list = get_column_service().get_visible_columns()
        logger.info("[FileTableView] Visible columns list: %s", visible_columns_list)
        logger.info("[FileTableView] Model column count: %d", self.model().columnCount())

        try:
            color_column_logical_index = visible_columns_list.index("color")
            logger.info(
                "[FileTableView] Color column logical index: %d", color_column_logical_index
            )

            # +1 because column 0 is status column
            color_column_view_index = color_column_logical_index + 1
            logger.info(
                "[FileTableView] Color column view index (after +1): %d", color_column_view_index
            )

            # Set color column delegate
            from oncutf.ui.delegates.color_column_delegate import ColorColumnDelegate

            color_delegate = ColorColumnDelegate(self)
            logger.info("[FileTableView] ColorColumnDelegate created: %s", color_delegate)

            self.setItemDelegateForColumn(color_column_view_index, color_delegate)
            logger.info(
                "[FileTableView] setItemDelegateForColumn(%d) called", color_column_view_index
            )

            # Verify installation
            installed_delegate = self.itemDelegateForColumn(color_column_view_index)
            logger.info(
                "[FileTableView] Verification - delegate for column %d: %s",
                color_column_view_index,
                installed_delegate,
            )

            logger.debug(
                "[FileTableView] Set ColorColumnDelegate for column %d", color_column_view_index
            )
        except (ValueError, AttributeError) as e:
            # Color column not visible or not in list
            logger.warning("[FileTableView] Color column not visible, delegate not set: %s", e)

    def _force_scrollbar_update(self) -> None:
        """Force immediate scrollbar and viewport update."""
        # Update scrollbar visibility
        self._update_scrollbar_visibility()

        # Use column manager's improved horizontal scrollbar handling
        try:
            from oncutf.core.application_context import get_app_context

            context = get_app_context()
            if context and hasattr(context, "column_manager"):
                context.column_manager.ensure_horizontal_scrollbar_state(self)
        except (RuntimeError, AttributeError):
            # Fallback to basic scrollbar handling - preserve scroll position
            hbar = self.horizontalScrollBar()
            current_position = hbar.value() if hbar else 0

            self.updateGeometries()

            # Restore scroll position if still valid
            if hbar and hbar.maximum() > 0:
                if current_position <= hbar.maximum():
                    hbar.setValue(current_position)
                else:
                    hbar.setValue(hbar.maximum())

        # Force immediate viewport refresh
        self.viewport().update()

        # Force geometry update
        self.updateGeometry()

        # Force model data refresh to update word wrap
        if self.model():
            self.model().layoutChanged.emit()

        # Schedule a delayed update to ensure everything is properly refreshed
        schedule_ui_update(lambda: self._delayed_refresh(), delay=100)

        # Update both scrollbar and header visibility after update
        self.refresh_view_state()

    def _delayed_refresh(self) -> None:
        """Delayed refresh to ensure proper scrollbar and content updates."""
        # Update scrollbar visibility first
        self._update_scrollbar_visibility()

        # Use column manager's improved horizontal scrollbar handling
        try:
            from oncutf.core.application_context import get_app_context

            context = get_app_context()
            if context and hasattr(context, "column_manager"):
                context.column_manager.ensure_horizontal_scrollbar_state(self)
        except (RuntimeError, AttributeError):
            # Fallback to basic scrollbar handling - preserve scroll position
            hbar = self.horizontalScrollBar()
            current_position = hbar.value() if hbar else 0

            self.updateGeometries()

            # Restore scroll position if still valid
            if hbar and hbar.maximum() > 0:
                if current_position <= hbar.maximum():
                    hbar.setValue(current_position)
                else:
                    hbar.setValue(hbar.maximum())

        self.viewport().update()

        # Force text refresh in all visible cells
        if self.model():
            visible_rect = self.viewport().rect()
            top_left = self.indexAt(visible_rect.topLeft())
            bottom_right = self.indexAt(visible_rect.bottomRight())

            if top_left.isValid() and bottom_right.isValid():
                self.dataChanged(top_left, bottom_right)

        # Update header visibility after delayed refresh (call directly, not via refresh_view_state to avoid duplicate scrollbar update)
        self._update_header_visibility()

    def _update_scrollbar_visibility(self) -> None:
        """Update scrollbar visibility based on table content and column widths."""
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

    # Public wrappers (safe, stable APIs for TableManager)
    def ensure_scrollbar_visibility(self) -> None:
        """Public wrapper to ensure scrollbar visibility is correct.

        Use this from other components (e.g. `TableManager`) instead of
        calling the internal `_update_scrollbar_visibility` directly.
        """
        self._update_scrollbar_visibility()

    def set_header_enabled(self, enabled: bool) -> None:
        """Public wrapper to enable/disable header widgets.

        This sets the table's horizontal header enabled state and, when
        available, propagates the change to a containing main window
        header (stored as `header` on the main window). Call this from
        external managers instead of manipulating other windows' header
        widgets directly.
        """
        with suppress(Exception):
            header = self.horizontalHeader()
            if header is not None:
                header.setEnabled(enabled)

        # Propagate to parent window header if present (best-effort)
        with suppress(Exception):
            parent = self.parent()
            while parent is not None:
                if hasattr(parent, "header"):
                    with suppress(Exception):
                        parent.header.setEnabled(enabled)
                    break
                parent = parent.parent()

        # Ensure header visibility/state is consistent after change
        with suppress(Exception):
            self._update_header_visibility()

    def refresh_view_state(self) -> None:
        """Refresh complete view state (scrollbar + header visibility).

        Use this public API when you need to update both scrollbar and
        header visibility in one call. This is commonly needed after
        loading files, clearing the table, or changing visible columns.

        For finer-grained control, use ensure_scrollbar_visibility()
        or set_header_enabled() individually.
        """
        with suppress(Exception):
            self._update_scrollbar_visibility()
        with suppress(Exception):
            self._update_header_visibility()

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
        # Update both scrollbar and header visibility when placeholder state changes
        self.refresh_view_state()

    def update_placeholder_visibility(self):
        """Update placeholder visibility based on table content."""
        is_empty = self.is_empty() if hasattr(self, "is_empty") else False
        # Set placeholder visibility (which will call refresh_view_state internally)
        self.set_placeholder_visible(is_empty)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press events for selection and drag initiation.
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

        # NOTE: Double-click metadata loading removed (2025-12-21)
        # This event is now reserved for future functionality
        # Metadata loading is available via keyboard shortcuts (Ctrl+M, etc.)

        self._sync_selection_safely()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle mouse release events.
        """
        was_dragging = False
        if event.button() == Qt.LeftButton:
            # Reset drag start position
            self._drag_start_pos = None

            # If we were dragging, clean up
            if self._drag_drop_behavior.is_dragging:
                was_dragging = True
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

        # Call parent implementation only if we weren't dragging
        # This prevents the release event from clearing selection or triggering click actions
        if not was_dragging:
            super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event) -> None:
        """Handle mouse move events for drag initiation.
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
                        # Clear drag start position before starting drag
                        self._drag_start_pos = None
                        # Start drag from selected item
                        self._start_custom_drag()
                        return

        # Skip hover updates if dragging (using Qt built-in drag now)
        if self._drag_drop_behavior.is_dragging:
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
        # Handle F5 refresh (like FileTreeView does)
        if event.key() == Qt.Key_F5:
            self.refresh_requested.emit()
            event.accept()
            return

        # Handle column management shortcuts (delegate to behavior)
        if hasattr(self, "_column_mgmt_behavior"):
            if self._column_mgmt_behavior.handle_keyboard_shortcut(event.key(), event.modifiers()):
                event.accept()
                return

        # Note: Escape for drag cancel is now handled globally in ui_manager.py

        # Skip key handling during drag (using Qt built-in drag now)
        if self._drag_drop_behavior.is_dragging:
            self._update_drag_feedback()
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
        if self._drag_drop_behavior.is_dragging:
            self._update_drag_feedback()
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
        from oncutf.utils.ui.tooltip_helper import TooltipHelper

        TooltipHelper.clear_tooltips_for_widget(self)

        self.viewport().update()

    def focusInEvent(self, event) -> None:
        """SIMPLIFIED focus handling - just sync selection, no special cases"""
        super().focusInEvent(event)

        # Simple sync: update SelectionStore with current Qt selection
        selection_model = self.selectionModel()
        if selection_model is not None:
            from oncutf.utils.ui.selection_provider import get_selected_row_set

            selected_rows = get_selected_row_set(selection_model)
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
        from oncutf.utils.ui.tooltip_helper import TooltipHelper

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
        from oncutf.utils.ui.tooltip_helper import TooltipHelper

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
                        left = self.model().index(r, 0)  # type: ignore[union-attr]
                        right = self.model().index(r, self.model().columnCount() - 1)  # type: ignore[union-attr]
                        row_rect = self.visualRect(left).united(self.visualRect(right))
                        self.viewport().update(row_rect)

    def scrollTo(self, index, hint=None) -> None:
        """Override scrollTo to prevent automatic scrolling when selections change.
        This prevents the table from moving when selecting rows.
        """
        # Check if table is empty or in placeholder mode
        if self.is_empty():
            # In empty/placeholder mode, allow normal scrolling
            super().scrollTo(index, hint)
            return

        # Allow minimal scrolling only if the selected item is completely out of view
        viewport_rect = self.viewport().rect()  # type: ignore[union-attr]
        item_rect = self.visualRect(index)  # type: ignore[arg-type]

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
            from oncutf.utils.ui.selection_provider import get_selected_row_set

            current_selection = get_selected_row_set(self.selectionModel())  # type: ignore[arg-type]
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
            self._get_selection_store().set_active(False)  # type: ignore[union-attr]
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
                "[FileTableView] Force cleaned %d stuck cursors during drag",
                cursor_count,
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
            self.viewport().update()  # type: ignore[union-attr]
        QApplication.processEvents()

    # =====================================
    # Behavior Delegation Methods
    # =====================================

    # Column Management Behavior delegation
    def _configure_columns(self) -> None:
        """Delegate to ColumnManagementBehavior."""
        self._column_mgmt_behavior.configure_columns()

    def _ensure_all_columns_proper_width(self) -> None:
        """Delegate to ColumnManagementBehavior."""
        self._column_mgmt_behavior.ensure_all_columns_proper_width()

    def _reset_columns_to_default(self) -> None:
        """Delegate to ColumnManagementBehavior."""
        self._column_mgmt_behavior.reset_column_widths_to_defaults()

    def _check_and_fix_column_widths(self) -> None:
        """Delegate to ColumnManagementBehavior."""
        self._column_mgmt_behavior.check_and_fix_column_widths()

    def _auto_fit_columns_to_content(self) -> None:
        """Delegate to ColumnManagementBehavior."""
        self._column_mgmt_behavior.auto_fit_columns_to_content()

    def add_column(self, column_key: str) -> None:
        """Delegate to ColumnManagementBehavior."""
        self._column_mgmt_behavior.add_column(column_key)

    def remove_column(self, column_key: str) -> None:
        """Delegate to ColumnManagementBehavior."""
        self._column_mgmt_behavior.remove_column(column_key)

    def _load_column_visibility_config(self) -> dict:
        """Delegate to ColumnManagementBehavior (legacy compatibility)."""
        # This is called during __init__ before behaviors exist
        # Return empty dict and let behavior handle it after initialization
        if hasattr(self, "_column_mgmt_behavior"):
            return self._column_mgmt_behavior.load_column_visibility_config()
        return {}

    def _set_column_alignment(self, column_index: int, alignment: str) -> None:
        """Delegate to ColumnManagementBehavior."""
        if hasattr(self, "_column_mgmt_behavior"):
            self._column_mgmt_behavior._set_column_alignment(column_index, alignment)

    def _sync_view_model_columns(self) -> None:
        """Delegate to ColumnManagementBehavior."""
        if hasattr(self, "_column_mgmt_behavior"):
            self._column_mgmt_behavior.sync_view_model_columns()

    def _toggle_column_visibility(self, column_key: str) -> None:
        """Delegate to ColumnManagementBehavior."""
        if hasattr(self, "_column_mgmt_behavior"):
            self._column_mgmt_behavior.toggle_column_visibility(column_key)

    def _update_header_visibility(self) -> None:
        """Delegate to ColumnManagementBehavior."""
        if hasattr(self, "_column_mgmt_behavior"):
            self._column_mgmt_behavior._update_header_visibility()

    def refresh_columns_after_model_change(self) -> None:
        """Delegate to ColumnManagementBehavior."""
        self._column_mgmt_behavior.refresh_columns_after_model_change()

    def _force_save_column_changes(self) -> None:
        """Delegate to ColumnManagementBehavior."""
        if hasattr(self, "_column_mgmt_behavior"):
            self._column_mgmt_behavior.force_save_column_changes()

    # Drag & Drop Behavior delegation
    def _start_custom_drag(self) -> None:
        """Delegate to DragDropBehavior."""
        self._drag_drop_behavior.start_drag()

    def _end_custom_drag(self) -> None:
        """Delegate to DragDropBehavior."""
        self._drag_drop_behavior.end_drag()

    def _update_drag_feedback(self) -> None:
        """Delegate to DragDropBehavior."""
        self._drag_drop_behavior._update_drag_feedback()

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
        result = self._drag_drop_behavior.handle_drop(event)
        if result:
            dropped_paths, modifiers = result
            self.files_dropped.emit(dropped_paths, modifiers)

    # Selection Behavior delegation
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

    def _sync_selection_safely(self) -> None:
        """Delegate to SelectionBehavior."""
        self._selection_behavior.sync_selection_safely()

    def _update_selection_store(self, selected_rows: set[int], emit_signal: bool = True) -> None:
        """Delegate to SelectionBehavior."""
        self._selection_behavior.update_selection_store(selected_rows, emit_signal=emit_signal)

    def select_rows_range(self, start_row: int, end_row: int) -> None:
        """Delegate to SelectionBehavior."""
        self._selection_behavior.select_rows_range(start_row, end_row)

    def select_dropped_files(self, file_paths: list[str] | None = None) -> None:
        """Delegate to SelectionBehavior."""
        self._selection_behavior.select_dropped_files(file_paths)

    def ensure_anchor_or_select(self, index: QModelIndex, modifiers: Qt.KeyboardModifiers) -> None:
        """Delegate to SelectionBehavior."""
        self._selection_behavior.ensure_anchor_or_select(index, modifiers)

    def selectionChanged(self, selected, deselected) -> None:
        """Override to delegate to SelectionBehavior."""
        self._selection_behavior.handle_selection_changed(selected, deselected)

    # =====================================
    # Cleanup & Lifecycle
    # =====================================

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
            logger.warning("Error clearing preview/metadata displays: %s", e)
