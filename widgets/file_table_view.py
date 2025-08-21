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

from config import FILE_TABLE_COLUMN_CONFIG
from core.application_context import get_app_context
from core.drag_manager import DragManager
from core.drag_visual_manager import (
    DragType,
    DragVisualManager,
    end_drag_visual,
    start_drag_visual,
    update_drag_feedback_for_widget,
)
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
from utils.file_drop_helper import extract_file_paths
from utils.logger_factory import get_cached_logger
from utils.placeholder_helper import create_placeholder_helper
from utils.timer_manager import (
    schedule_ui_update,
)

logger = get_cached_logger(__name__)

# Constants for better maintainability
SCROLLBAR_MARGIN = 40


class FileTableView(QTableView):
    """
    Custom QTableView with Windows Explorer-like behavior.

    Features:
    - Full-row selection with anchor handling
    - Fixed-width column management with delayed save (7 seconds)
    - Horizontal scrollbar appears when columns exceed viewport width
    - Drag & drop support with custom MIME types
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
        self.verticalHeader().setDefaultSectionSize(22)  # Fixed row height to prevent expansion

        # Force single-line text display
        self.setWordWrap(False)  # Ensure word wrap is disabled
        self.setSizeAdjustPolicy(QAbstractItemView.AdjustToContents)  # Adjust to content size

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

        # Ensure proper text display
        self._ensure_no_word_wrap()

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

    def _update_selection_store(self, selected_rows: set, emit_signal: bool = True) -> None:
        selection_store = self._get_selection_store()
        if selection_store and not self._legacy_selection_mode:
            selection_store.set_selected_rows(selected_rows, emit_signal=emit_signal)

        # Always update legacy state for compatibility
        self.selected_rows = selected_rows

        # CRITICAL: Ensure Qt selection model is synchronized with our selection
        # This prevents blue highlighting desync issues
        if emit_signal:  # Only sync Qt model when we're not in a batch operation
            self._sync_qt_selection_model(selected_rows)

    def _sync_qt_selection_model(self, selected_rows: set) -> None:
        """Optimized batch synchronization of Qt's selection model."""
        try:
            selection_model = self.selectionModel()
            if not selection_model or not self.model():
                return

            # Block signals during sync to prevent loops
            self.blockSignals(True)
            try:
                # Clear current selection
                selection_model.clearSelection()

                if selected_rows:
                    # OPTIMIZED: Create single batch selection instead of row-by-row
                    from core.pyqt_imports import QItemSelection

                    batch_selection = QItemSelection()

                    for row in selected_rows:
                        if 0 <= row < self.model().rowCount():
                            start_index = self.model().index(row, 0)
                            end_index = self.model().index(row, self.model().columnCount() - 1)
                            if start_index.isValid() and end_index.isValid():
                                row_selection = QItemSelection(start_index, end_index)
                                batch_selection.merge(row_selection, selection_model.Select)

                    # Apply entire batch at once - much faster than individual selections
                    if not batch_selection.isEmpty():
                        selection_model.select(batch_selection, selection_model.Select)
            finally:
                self.blockSignals(False)

        except Exception as e:
            logger.error(f"[SyncQt] Error syncing selection: {e}")

    def _get_current_selection(self) -> set:
        """Get current selection from SelectionStore or fallback to Qt model."""
        selection_store = self._get_selection_store()
        if selection_store and not self._legacy_selection_mode:
            return selection_store.get_selected_rows()
        else:
            # Fallback: get from Qt selection model (more reliable than legacy)
            selection_model = self.selectionModel()
            if selection_model:
                qt_selection = {index.row() for index in selection_model.selectedRows()}
                # Update legacy state to match Qt
                self.selected_rows = qt_selection
                return qt_selection
            else:
                return self.selected_rows

    def _get_current_selection_safe(self) -> set:
        """Get current selection safely - SIMPLIFIED VERSION."""
        selection_model = self.selectionModel()
        if selection_model:
            return {index.row() for index in selection_model.selectedRows()}
        else:
            return set()

    def _set_anchor_row(self, row: int | None, emit_signal: bool = True) -> None:
        """Set anchor row in SelectionStore or fallback to legacy."""
        selection_store = self._get_selection_store()
        if selection_store and not self._legacy_selection_mode:
            selection_store.set_anchor_row(row, emit_signal=emit_signal)

        # Always update legacy state for compatibility
        self.anchor_row = row

    def _get_anchor_row(self) -> int | None:
        """Get anchor row from SelectionStore or fallback to legacy."""
        selection_store = self._get_selection_store()
        if selection_store and not self._legacy_selection_mode:
            return selection_store.get_anchor_row()
        else:
            return self.anchor_row

    def resizeEvent(self, event) -> None:
        """Handle resize events and update scrollbar visibility."""
        super().resizeEvent(event)
        if hasattr(self, "placeholder_helper"):
            self.placeholder_helper.update_position()
        self._force_scrollbar_update()
        self._ensure_no_word_wrap()

    def _ensure_no_word_wrap(self) -> None:
        """Ensure word wrap is disabled and text is properly elided."""
        # Force word wrap to be disabled
        self.setWordWrap(False)

        # Set fixed row height to prevent expansion
        self.verticalHeader().setDefaultSectionSize(22)
        self.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)

        # Ensure text eliding is enabled
        self.setTextElideMode(Qt.ElideRight)

        # Force uniform row heights for all existing rows
        if self.model():
            for row in range(self.model().rowCount()):
                self.setRowHeight(row, 22)

        # Ensure all columns have proper width to minimize text elision
        self._ensure_all_columns_proper_width()

        # Force complete model refresh to update text display
        if self.model():
            self.model().layoutChanged.emit()

        # Force viewport update
        self.viewport().update()

        # Schedule delayed update to ensure proper text rendering
        schedule_ui_update(lambda: self._refresh_text_display(), delay=50)

    def _ensure_all_columns_proper_width(self) -> None:
        """Ensure all visible columns have proper width to minimize text elision."""
        try:
            if not self.model():
                return

            # Get visible columns from model
            visible_columns = (
                self.model().get_visible_columns()
                if hasattr(self.model(), "get_visible_columns")
                else []
            )

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
                        f"[ColumnWidth] Adjusting column '{column_key}' width from {current_width}px to {recommended_width}px to reduce elision"
                    )
                    self.setColumnWidth(column_index, recommended_width)
                    self._schedule_column_save(column_key, recommended_width)

        except Exception as e:
            logger.warning(f"Error ensuring all columns proper width: {e}")

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
            f"FileTableView setModel called with model: {type(model)}", extra={"dev_only": True}
        )

        if model is self.model():
            logger.debug("FileTableView setModel: Same model, skipping", extra={"dev_only": True})
            return

        super().setModel(model)
        if model:
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
                from utils.timer_manager import schedule_ui_update

                schedule_ui_update(self._check_and_fix_column_widths, delay=50)
                self._configure_columns()
            else:
                from utils.timer_manager import schedule_ui_update

                schedule_ui_update(self._configure_columns, delay=50)
        self.update_placeholder_visibility()
        # Don't call _update_header_visibility() here as it will be called from _configure_columns_delayed()

    # =====================================
    # Table Preparation & Management
    # =====================================

    def prepare_table(self, file_items: list) -> None:
        """Prepare the table for display with file items."""
        logger.debug(f"prepare_table called with {len(file_items)} items", extra={"dev_only": True})
        self._has_manual_preference = False
        self._user_preferred_width = None
        for file_item in file_items:
            file_item.checked = False
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
        if hasattr(self, "hover_delegate"):
            self.setItemDelegate(self.hover_delegate)
            self.hover_delegate.hovered_row = -1
        self.viewport().update()
        self._update_scrollbar_visibility()
        self.update_placeholder_visibility()
        self._update_header_visibility()

    # =====================================
    # Column Management & Scrollbar Optimization
    # =====================================

    def _configure_columns(self) -> None:
        """Configure columns with values from config.py."""

        if not self.model() or self.model().columnCount() == 0:
            return
        header = self.horizontalHeader()
        if not header:
            return

        # Prevent recursive calls during column configuration
        if hasattr(self, "_configuring_columns") and self._configuring_columns:
            return

        self._configuring_columns = True

        try:
            # Small delay to ensure model synchronization using global timer manager
            from utils.timer_manager import schedule_ui_update

            schedule_ui_update(
                self._configure_columns_delayed, delay=10, timer_id=f"column_config_{id(self)}"
            )
        except Exception as e:
            logger.error(f"[ColumnConfig] Error during column configuration: {e}")
            self._configuring_columns = False

    def _configure_columns_delayed(self) -> None:
        """Delayed column configuration to ensure model synchronization."""
        try:
            header = self.horizontalHeader()
            if not header or not self.model():
                return

            header.show()
            # Configure status column (always column 0)
            self.setColumnWidth(0, 45)
            header.setSectionResizeMode(0, header.Fixed)

            # Get visible columns from model (this is the authoritative source)
            visible_columns = []
            if hasattr(self.model(), "get_visible_columns"):
                visible_columns = self.model().get_visible_columns()
            else:
                # Emergency fallback - load from config
                from config import FILE_TABLE_COLUMN_CONFIG

                visible_columns = [
                    key
                    for key, cfg in FILE_TABLE_COLUMN_CONFIG.items()
                    if cfg.get("default_visible", False)
                ]
                logger.warning(
                    f"[ColumnConfig] Model doesn't have get_visible_columns, using fallback: {visible_columns}"
                )

            # Configure each visible column
            for column_index, column_key in enumerate(visible_columns):
                actual_column_index = column_index + 1  # +1 because column 0 is status
                if actual_column_index < self.model().columnCount():
                    width = self._load_column_width(column_key)

                    # Apply intelligent width validation for all columns
                    width = self._ensure_column_proper_width(column_key, width)

                    header.setSectionResizeMode(actual_column_index, header.Interactive)
                    self.setColumnWidth(actual_column_index, width)

                else:
                    logger.error(
                        f"[ColumnConfig] CRITICAL: Column {actual_column_index} ({column_key}) exceeds model columnCount {self.model().columnCount()}"
                    )
                    logger.error(
                        "[ColumnConfig] This indicates a sync issue between view and model visible columns"
                    )

            # Connect header resize signal if not already connected
            if not hasattr(self, "_header_resize_connected"):
                header.sectionResized.connect(self._on_column_resized)
                self._header_resize_connected = True

            # Force a viewport update to ensure visual refresh
            self.viewport().update()
            self.updateGeometry()

            # Update header visibility after column configuration is complete
            self._update_header_visibility()

        except Exception as e:
            logger.error(f"[ColumnConfig] Error during delayed column configuration: {e}")
        finally:
            self._configuring_columns = False

    def _ensure_column_proper_width(self, column_key: str, current_width: int) -> int:
        """Ensure column has proper width based on its content type and configuration."""
        from config import FILE_TABLE_COLUMN_CONFIG

        column_config = FILE_TABLE_COLUMN_CONFIG.get(column_key, {})
        default_width = column_config.get("width", 100)
        min_width = column_config.get("min_width", 50)

        # Analyze column content type to determine appropriate width
        content_type = self._analyze_column_content_type(column_key)
        recommended_width = self._get_recommended_width_for_content_type(
            content_type, default_width, min_width
        )

        # If current width is suspiciously small (likely from saved config), use recommended width
        if current_width < min_width:
            logger.debug(
                f"[ColumnWidth] Column '{column_key}' width {current_width}px is below minimum {min_width}px, using recommended {recommended_width}px"
            )
            return recommended_width

        # If current width is reasonable, use it but ensure it's not below minimum
        return max(current_width, min_width)

    def _analyze_column_content_type(self, column_key: str) -> str:
        """Analyze the content type of a column to determine appropriate width."""
        # Define content types based on column keys
        content_types = {
            # Short content (names, types, codes)
            "type": "short",
            "iso": "short",
            "rotation": "short",
            "duration": "short",
            "video_fps": "short",
            "audio_channels": "short",
            # Medium content (formats, models, sizes)
            "audio_format": "medium",
            "video_codec": "medium",
            "video_format": "medium",
            "white_balance": "medium",
            "compression": "medium",
            "device_model": "medium",
            "device_manufacturer": "medium",
            "image_size": "medium",
            "video_avg_bitrate": "medium",
            "aperture": "medium",
            "shutter_speed": "medium",
            # Long content (filenames, hashes, UMIDs)
            "filename": "long",
            "file_hash": "long",
            "target_umid": "long",
            "device_serial_no": "long",
            # Very long content (dates, file paths)
            "modified": "very_long",
            "file_size": "very_long",
        }

        return content_types.get(column_key, "medium")

    def _get_recommended_width_for_content_type(
        self, content_type: str, default_width: int, min_width: int
    ) -> int:
        """Get recommended width based on content type."""
        # Define width recommendations for different content types
        width_recommendations = {
            "short": max(80, min_width),  # Short codes, numbers
            "medium": max(120, min_width),  # Formats, models, sizes
            "long": max(200, min_width),  # Filenames, hashes, UMIDs
            "very_long": max(300, min_width),  # Dates, file paths
        }

        # Use the larger of default_width, min_width, or content_type recommendation
        recommended = width_recommendations.get(content_type, default_width)
        return max(recommended, default_width, min_width)

    def _update_header_visibility(self) -> None:
        """Update header visibility based on whether there are files in the model."""
        if not self.model():
            logger.debug("[FileTableView] No model - header hidden", extra={"dev_only": True})
            return

        header = self.horizontalHeader()
        if not header:
            logger.debug(
                "[FileTableView] No header - cannot update visibility", extra={"dev_only": True}
            )
            return

        # Hide header when table is empty, show when it has content
        is_empty = self.is_empty()
        header.setVisible(not is_empty)

        logger.debug(
            f"[FileTableView] Header visibility: {'hidden' if is_empty else 'visible'} (empty: {is_empty})",
            extra={"dev_only": True},
        )

    def _ensure_header_visibility(self) -> None:
        """Ensure header visibility is correct after column configuration."""
        self._update_header_visibility()

    def _set_column_alignment(self, column_index: int, alignment: str) -> None:
        """Set text alignment for a specific column."""
        if not self.model():
            return

        # Map alignment strings to Qt constants
        alignment_map = {
            "left": Qt.AlignLeft | Qt.AlignVCenter,
            "right": Qt.AlignRight | Qt.AlignVCenter,
            "center": Qt.AlignCenter,
        }

        qt_alignment = alignment_map.get(alignment, Qt.AlignLeft | Qt.AlignVCenter)

        # Store alignment for use in delegates or model
        if not hasattr(self, "_column_alignments"):
            self._column_alignments = {}
        self._column_alignments[column_index] = qt_alignment

    def _load_column_width(self, column_key: str) -> int:
        """Load column width from main config system with fallback to defaults."""
        logger.debug(
            f"[ColumnWidth] Loading width for column '{column_key}'", extra={"dev_only": True}
        )
        try:
            # First, get the default width from config.py
            from config import FILE_TABLE_COLUMN_CONFIG

            default_width = FILE_TABLE_COLUMN_CONFIG.get(column_key, {}).get("width", 100)
            logger.debug(
                f"[ColumnWidth] Default width for '{column_key}': {default_width}px",
                extra={"dev_only": True},
            )

            # Try main config system first
            main_window = self._get_main_window()
            if main_window and hasattr(main_window, "window_config_manager"):
                try:
                    config_manager = main_window.window_config_manager.config_manager
                    window_config = config_manager.get_category("window")
                    column_widths = window_config.get("file_table_column_widths", {})

                    if column_key in column_widths:
                        saved_width = column_widths[column_key]
                        logger.debug(
                            f"[ColumnWidth] Found saved width for '{column_key}': {saved_width}px",
                            extra={"dev_only": True},
                        )
                        # Only check for suspicious 100px width if the default is significantly different
                        # This prevents false positives when the default width is actually close to 100px
                        if saved_width == 100 and default_width > 120:
                            logger.debug(
                                f"[ColumnWidth] Column '{column_key}' has suspicious saved width (100px), using default {default_width}px"
                            )
                            return default_width
                        logger.debug(
                            f"[ColumnWidth] Using saved width for '{column_key}': {saved_width}px",
                            extra={"dev_only": True},
                        )
                        return saved_width
                    else:
                        logger.debug(
                            f"[ColumnWidth] No saved width found for '{column_key}' in main config",
                            extra={"dev_only": True},
                        )
                except Exception as e:
                    logger.warning(
                        f"[ColumnWidth] Error accessing main config for '{column_key}': {e}"
                    )
                    # Continue to fallback method

            # Fallback to old method
            from utils.json_config_manager import load_config

            config = load_config()
            column_widths = config.get("file_table_column_widths", {})
            if column_key in column_widths:
                saved_width = column_widths[column_key]
                logger.debug(
                    f"[ColumnWidth] Found saved width in fallback for '{column_key}': {saved_width}px"
                )
                # Same check for old config format
                if saved_width == 100 and default_width > 120:
                    logger.debug(
                        f"[ColumnWidth] Column '{column_key}' has suspicious saved width (100px), using default {default_width}px"
                    )
                    return default_width
                logger.debug(
                    f"[ColumnWidth] Using fallback saved width for '{column_key}': {saved_width}px"
                )
                return saved_width
            else:
                logger.debug(
                    f"[ColumnWidth] No saved width found for '{column_key}' in fallback config"
                )

            # Return default width from config.py
            logger.debug(f"[ColumnWidth] Using default width for '{column_key}': {default_width}px")
            return default_width

        except Exception as e:
            logger.warning(f"[ColumnWidth] Failed to load column width for {column_key}: {e}")
            # Emergency fallback to config.py defaults
            from config import FILE_TABLE_COLUMN_CONFIG

            column_config = FILE_TABLE_COLUMN_CONFIG.get(column_key, {})
            fallback_width = column_config.get("width", 100)
            logger.debug(
                f"[ColumnWidth] Using emergency fallback width for '{column_key}': {fallback_width}px"
            )
            return fallback_width

    def _reset_column_widths_to_defaults(self) -> None:
        """Reset all column widths to their default values from config.py."""
        try:
            logger.info("Resetting column widths to defaults from config.py")

            # Clear saved column widths
            main_window = self._get_main_window()
            if main_window and hasattr(main_window, "window_config_manager"):
                try:
                    config_manager = main_window.window_config_manager.config_manager
                    window_config = config_manager.get_category("window")
                    window_config.set("file_table_column_widths", {})
                    config_manager.save()
                except Exception as e:
                    logger.warning(f"[ColumnWidth] Error clearing main config: {e}")
                    # Continue to old format

            # Also clear from old format
            from utils.json_config_manager import load_config, save_config

            config = load_config()
            config["file_table_column_widths"] = {}
            save_config(config)

            # Reconfigure columns with defaults (only if model is available)
            if self.model() and self.model().columnCount() > 0:
                self._configure_columns()

            logger.info("Column widths reset to defaults successfully")

        except Exception as e:
            logger.error(f"Failed to reset column widths to defaults: {e}")

    def _save_column_width(self, column_key: str, width: int) -> None:
        """Save column width to main config system."""
        try:
            # Get the main window and its config manager
            main_window = self._get_main_window()
            if main_window and hasattr(main_window, "window_config_manager"):
                try:
                    config_manager = main_window.window_config_manager.config_manager
                    window_config = config_manager.get_category("window")

                    # Get current column widths
                    column_widths = window_config.get("file_table_column_widths", {})
                    column_widths[column_key] = width
                    window_config.set("file_table_column_widths", column_widths)

                    # Save immediately for individual changes
                    config_manager.save()
                except Exception as e:
                    logger.warning(f"[ColumnWidth] Error saving to main config: {e}")
                    # Continue to fallback method
            else:
                # Fallback to old method if main window not available
                from utils.json_config_manager import load_config, save_config

                config = load_config()
                if "file_table_column_widths" not in config:
                    config["file_table_column_widths"] = {}
                config["file_table_column_widths"][column_key] = width
                save_config(config)
        except Exception as e:
            logger.warning(f"Failed to save column width for {column_key}: {e}")

    def _schedule_column_save(self, column_key: str, width: int) -> None:
        """Schedule delayed save of column width changes."""
        from config import COLUMN_RESIZE_BEHAVIOR

        if not COLUMN_RESIZE_BEHAVIOR.get("PRESERVE_USER_WIDTHS", True):
            return

        # Store the pending change
        self._pending_column_changes[column_key] = width

        # Cancel existing timer if any
        if self._config_save_timer:
            self._config_save_timer.stop()
            self._config_save_timer = None

        # Start new timer for delayed save (7 seconds)
        self._config_save_timer = QTimer()
        self._config_save_timer.setSingleShot(True)
        self._config_save_timer.timeout.connect(self._save_pending_column_changes)
        self._config_save_timer.start(7000)  # 7 seconds delay

        logger.debug(
            f"Scheduled delayed save for column '{column_key}' width {width}px (will save in 7 seconds)"
        )

    def _save_pending_column_changes(self) -> None:
        """Save all pending column width changes to config.json."""
        if not self._pending_column_changes:
            return

        try:
            # Try main config system first
            main_window = self._get_main_window()
            if main_window and hasattr(main_window, "window_config_manager"):
                try:
                    config_manager = main_window.window_config_manager.config_manager
                    window_config = config_manager.get_category("window")
                    column_widths = window_config.get("file_table_column_widths", {})

                    # Apply all pending changes
                    for column_key, width in self._pending_column_changes.items():
                        column_widths[column_key] = width

                    window_config.set("file_table_column_widths", column_widths)
                    config_manager.save()

                    logger.info(
                        f"Saved {len(self._pending_column_changes)} column width changes to main config"
                    )

                    # Clear pending changes
                    self._pending_column_changes.clear()
                    return

                except Exception as e:
                    logger.warning(f"Failed to save to main config: {e}, trying fallback")

            # Fallback to old method
            from utils.json_config_manager import load_config, save_config

            config = load_config()
            if "file_table_column_widths" not in config:
                config["file_table_column_widths"] = {}

            # Apply all pending changes
            for column_key, width in self._pending_column_changes.items():
                config["file_table_column_widths"][column_key] = width

            save_config(config)

            logger.info(
                f"Saved {len(self._pending_column_changes)} column width changes to fallback config"
            )

            # Clear pending changes
            self._pending_column_changes.clear()

        except Exception as e:
            logger.error(f"Failed to save pending column changes: {e}")
        finally:
            # Clean up timer
            if self._config_save_timer:
                self._config_save_timer = None

    def _force_save_column_changes(self) -> None:
        """Force immediate save of any pending column changes (called on shutdown)."""
        if self._pending_column_changes:
            logger.debug("Force saving pending column changes on shutdown")
            self._save_pending_column_changes()

        # Cancel any pending timer
        if self._config_save_timer:
            self._config_save_timer.stop()
            self._config_save_timer = None

    def _on_column_resized(self, logical_index: int, old_size: int, new_size: int) -> None:
        """Handle column resize events and save user preferences."""
        if self._programmatic_resize:
            return  # Skip saving during programmatic resize

        # Get column key from logical index
        column_key = self._get_column_key_from_index(logical_index)
        if not column_key:
            return

        # Schedule delayed save of column width
        self._schedule_column_save(column_key, new_size)

        # Ensure word wrap is disabled when user resizes columns
        self._ensure_no_word_wrap()

        # Update scrollbar visibility immediately and force viewport update
        self._force_scrollbar_update()

        # Force repaint and layout update so elidedText is recalculated
        if self.model():
            self.model().layoutChanged.emit()
        self.viewport().update()

        # Update header visibility after column resize
        self._update_header_visibility()

        logger.debug(f"Column '{column_key}' resized from {old_size}px to {new_size}px")

    def _force_scrollbar_update(self) -> None:
        """Force immediate scrollbar and viewport update."""
        # Update scrollbar visibility
        self._update_scrollbar_visibility()

        # Use column manager's improved horizontal scrollbar handling
        try:
            from core.application_context import get_app_context

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

        # Update header visibility after scrollbar update
        self._update_header_visibility()

    def _delayed_refresh(self) -> None:
        """Delayed refresh to ensure proper scrollbar and content updates."""
        self._update_scrollbar_visibility()

        # Use column manager's improved horizontal scrollbar handling
        try:
            from core.application_context import get_app_context

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

        # Update header visibility after delayed refresh
        self._update_header_visibility()

    def _on_column_moved(
        self, logical_index: int, old_visual_index: int, new_visual_index: int
    ) -> None:
        """Handle column reordering and save order to config."""
        if logical_index == 0:  # Don't allow moving status column
            # Revert the move by moving it back to position 0
            header = self.horizontalHeader()
            if header and new_visual_index != 0:
                header.moveSection(new_visual_index, 0)
            return

        # Save new column order to config
        try:
            # config = load_config()
            # TODO: Implement column order saving
            logger.debug(f"Column moved from position {old_visual_index} to {new_visual_index}")
        except Exception as e:
            logger.warning(f"Failed to save column order: {e}")

        # Update header visibility after column move
        self._update_header_visibility()

    def _get_column_key_from_index(self, logical_index: int) -> str:
        """Get column key from logical index."""
        if logical_index == 0:
            return "status"

        # Get visible columns from model
        visible_columns = []
        if hasattr(self.model(), "get_visible_columns"):
            visible_columns = self.model().get_visible_columns()
        else:
            visible_columns = ["filename", "file_size", "type", "modified"]

        # Convert logical index to column key
        column_index = logical_index - 1  # -1 because column 0 is status
        if 0 <= column_index < len(visible_columns):
            return visible_columns[column_index]

        return ""

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

    def ensure_anchor_or_select(self, index: QModelIndex, modifiers: Qt.KeyboardModifiers) -> None:
        """Handle selection logic with anchor and modifier support."""
        # Add protection against infinite loops
        if hasattr(self, "_ensuring_selection") and self._ensuring_selection:
            logger.debug("[FileTableView] ensure_anchor_or_select already running, skipping")
            return

        self._ensuring_selection = True
        try:
            sm = self.selectionModel()
            model = self.model()
            if sm is None or model is None:
                return

            if modifiers & Qt.ShiftModifier:
                # Check if we're clicking on an already selected item
                current_selection = {idx.row() for idx in sm.selectedRows()}
                clicked_row = index.row()

                # If clicking on an already selected item, don't change selection
                if clicked_row in current_selection:
                    # Just update the current index without changing selection
                    sm.setCurrentIndex(index, QItemSelectionModel.NoUpdate)
                else:
                    # Normal Shift+Click behavior for unselected items
                    if self._manual_anchor_index is None:
                        # If no anchor exists, use the first selected item as anchor
                        selected_indexes = sm.selectedRows()
                        if selected_indexes:
                            self._manual_anchor_index = selected_indexes[0]
                    else:
                        self._manual_anchor_index = index

                    # Create selection from anchor to current index
                    selection = QItemSelection(self._manual_anchor_index, index)
                    # Block signals to prevent metadata flickering during selection changes
                    self.blockSignals(True)
                    try:
                        # Use ClearAndSelect to replace existing selection with the range
                        sm.select(
                            selection, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows
                        )
                        sm.setCurrentIndex(index, QItemSelectionModel.NoUpdate)
                    finally:
                        self.blockSignals(False)

                # Update SelectionStore to match Qt selection model
                selection_store = self._get_selection_store()
                if selection_store and not self._legacy_selection_mode:
                    current_qt_selection = {idx.row() for idx in sm.selectedRows()}
                    selection_store.set_selected_rows(
                        current_qt_selection, emit_signal=False
                    )  # Don't emit signal to prevent loops
                    if self._manual_anchor_index:
                        selection_store.set_anchor_row(
                            self._manual_anchor_index.row(), emit_signal=False
                        )

                # Force visual update
                left = model.index(index.row(), 0)
                right = model.index(index.row(), model.columnCount() - 1)
                self.viewport().update(self.visualRect(left).united(self.visualRect(right)))

            elif modifiers & Qt.ControlModifier:
                self._manual_anchor_index = index
                row = index.row()

                # Get current selection state before making changes
                was_selected = sm.isSelected(index)

                # Toggle selection in Qt selection model
                if was_selected:
                    sm.select(index, QItemSelectionModel.Deselect | QItemSelectionModel.Rows)
                else:
                    sm.select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows)

                # Set current index without clearing selection
                sm.setCurrentIndex(index, QItemSelectionModel.NoUpdate)

                # Update SelectionStore to match Qt selection model
                selection_store = self._get_selection_store()
                if selection_store and not self._legacy_selection_mode:
                    current_qt_selection = {idx.row() for idx in sm.selectedRows()}
                    selection_store.set_selected_rows(
                        current_qt_selection, emit_signal=False
                    )  # Don't emit signal to prevent loops
                    selection_store.set_anchor_row(row, emit_signal=False)

                # Force visual update
                left = model.index(row, 0)
                right = model.index(row, model.columnCount() - 1)
                self.viewport().update(self.visualRect(left).united(self.visualRect(right)))

            else:
                self._manual_anchor_index = index
                sm.select(index, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)
                sm.setCurrentIndex(index, QItemSelectionModel.NoUpdate)

                # Update SelectionStore to match Qt selection model
                selection_store = self._get_selection_store()
                if selection_store and not self._legacy_selection_mode:
                    current_qt_selection = {idx.row() for idx in sm.selectedRows()}
                    selection_store.set_selected_rows(
                        current_qt_selection, emit_signal=False
                    )  # Don't emit signal to prevent loops
                    selection_store.set_anchor_row(index.row(), emit_signal=False)
        finally:
            self._ensuring_selection = False

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

        # Ctrl+T: Reset column widths to default
        if event.key() == Qt.Key_T and event.modifiers() == Qt.ControlModifier:
            self._reset_columns_to_default()
            event.accept()
            return

        # Ctrl+Shift+T: Auto-fit columns to content
        if event.key() == Qt.Key_T and event.modifiers() == (Qt.ControlModifier | Qt.ShiftModifier):
            self._auto_fit_columns_to_content()
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

    def _sync_selection_safely(self) -> None:
        """Sync selection state with parent window or SelectionStore."""
        # First, try to sync with SelectionStore if available
        selection_store = self._get_selection_store()
        if selection_store and not self._legacy_selection_mode:
            current_qt_selection = {idx.row() for idx in self.selectionModel().selectedRows()}
            selection_store.set_selected_rows(current_qt_selection, emit_signal=True)
            return

        # Fallback: try parent window sync method
        parent = self.window()
        if hasattr(parent, "sync_selection_to_checked"):
            selection = self.selectionModel().selection()
            parent.sync_selection_to_checked(selection, QItemSelection())

    # =====================================
    # Custom Drag Implementation
    # =====================================

    def _start_custom_drag(self):
        """Start our custom drag operation with enhanced visual feedback"""
        if self._is_dragging:
            return

        # Clean up selection preservation flags since we're starting a drag
        self._preserve_selection_for_drag = False
        self._clicked_on_selected = False
        self._clicked_index = None

        # Get selected file data using safe method
        selected_rows = self._get_current_selection_safe()

        if not selected_rows:
            return

        rows = sorted(selected_rows)
        file_items = [self.model().files[r] for r in rows if 0 <= r < len(self.model().files)]
        file_paths = [f.full_path for f in file_items if f.full_path]

        if not file_paths:
            return

        # Activate drag cancel filter to preserve selection (especially for no-modifier drags)
        from widgets.file_tree_view import _drag_cancel_filter

        _drag_cancel_filter.activate()
        _drag_cancel_filter.preserve_selection(selected_rows)

        # Clear hover state before starting drag
        if hasattr(self, "hover_delegate"):
            old_row = self.hover_delegate.hovered_row
            self.hover_delegate.update_hover_row(-1)
            if old_row >= 0:
                left = self.model().index(old_row, 0)
                right = self.model().index(old_row, self.model().columnCount() - 1)
                row_rect = self.visualRect(left).united(self.visualRect(right))
                self.viewport().update(row_rect)

        # Set drag state
        self._is_dragging = True
        self._drag_data = file_paths

        # Stop any existing drag feedback timer
        if hasattr(self, "_drag_feedback_timer_id") and self._drag_feedback_timer_id:
            from utils.timer_manager import cancel_timer

            cancel_timer(self._drag_feedback_timer_id)

        # Notify DragManager
        drag_manager = DragManager.get_instance()
        drag_manager.start_drag("file_table")

        # Start enhanced visual feedback
        visual_manager = DragVisualManager.get_instance()

        # Determine drag type and info string based on selection
        if len(file_paths) == 1:
            drag_type = visual_manager.get_drag_type_from_path(file_paths[0])
            # For single file, show just the filename
            import os

            source_info = os.path.basename(file_paths[0])
        else:
            drag_type = DragType.MULTIPLE
            # For multiple files, show count
            source_info = f"{len(file_paths)} files"

        start_drag_visual(drag_type, source_info, "file_table")

        # Start drag feedback loop for real-time visual updates
        self._start_drag_feedback_loop()

    def _start_drag_feedback_loop(self):
        """Start repeated drag feedback updates using timer_manager"""
        from utils.timer_manager import schedule_ui_update

        if self._is_dragging:
            self._update_drag_feedback()
            # Schedule next update
            self._drag_feedback_timer_id = schedule_ui_update(
                self._start_drag_feedback_loop, delay=50
            )

    def _update_drag_feedback(self):
        """Update visual feedback based on current cursor position during drag"""
        if not self._is_dragging:
            return

        # Use common drag feedback logic
        should_continue = update_drag_feedback_for_widget(self, "file_table")

        # If cursor is outside application, end drag
        if not should_continue:
            self._end_custom_drag()

    def _end_custom_drag(self):
        """End custom drag operation - SIMPLIFIED VERSION"""
        if not self._is_dragging:
            return

        # Stop and cleanup drag feedback timer
        if hasattr(self, "_drag_feedback_timer_id") and self._drag_feedback_timer_id:
            from utils.timer_manager import cancel_timer

            cancel_timer(self._drag_feedback_timer_id)
            self._drag_feedback_timer_id = None

        # Force immediate cursor cleanup
        self._force_cursor_cleanup()

        # Get widget under cursor for drop detection
        cursor_pos = QCursor.pos()
        widget_under_cursor = QApplication.widgetAt(cursor_pos)

        dropped_successfully = False

        if widget_under_cursor:
            # Walk up parent hierarchy to find drop targets
            parent = widget_under_cursor
            while parent and not dropped_successfully:
                if parent.__class__.__name__ == "MetadataTreeView":
                    dropped_successfully = self._handle_drop_on_metadata_tree()
                    break
                parent = parent.parent()

        # Clean up drag state
        self._is_dragging = False
        self._drag_data = None

        # Record drag end time for selection protection
        import time

        self._drag_end_time = time.time() * 1000  # Store in milliseconds

        # Cleanup visual feedback
        end_drag_visual()

        # Notify DragManager
        drag_manager = DragManager.get_instance()
        drag_manager.end_drag("file_table")

        # Always restore hover after drag ends
        self._restore_hover_after_drag()

    def _restore_hover_after_drag(self):
        """Restore hover state after drag ends by sending a fake mouse move event"""
        if not hasattr(self, "hover_delegate"):
            return

        # Get current cursor position relative to this widget
        global_pos = QCursor.pos()
        local_pos = self.mapFromGlobal(global_pos)

        # Only restore hover if cursor is still over this widget
        if self.rect().contains(local_pos):
            # Create and post a fake mouse move event
            fake_move_event = QMouseEvent(
                QEvent.MouseMove, local_pos, Qt.NoButton, Qt.NoButton, Qt.NoModifier
            )
            QApplication.postEvent(self, fake_move_event)

    def _handle_drop_on_metadata_tree(self):
        """Handle drop on metadata tree - SIMPLIFIED direct communication"""
        if not self._drag_data:
            logger.debug(
                "[FileTableView] No drag data available for metadata tree drop",
                extra={"dev_only": True},
            )
            return False

        # Get current selection - this is what the user sees and expects
        selected_rows = self._get_current_selection()

        if not selected_rows:
            logger.warning("[FileTableView] No valid selection found for metadata tree drop")
            return False

        # Convert to FileItem objects using unified selection method
        try:
            parent_window = self._get_parent_with_metadata_tree()
            if not parent_window:
                logger.warning("[FileTableView] Could not find parent window for unified selection")
                return False

            file_items = parent_window.get_selected_files_ordered()
            if not file_items:
                logger.warning("[FileTableView] No valid file items found for metadata tree drop")
                return False
        except (AttributeError, IndexError) as e:
            logger.error(f"[FileTableView] Error getting selected files: {e}")
            return False

        # Get modifiers for metadata loading decision
        modifiers = QApplication.keyboardModifiers()
        use_extended = bool(modifiers & Qt.ShiftModifier)  # type: ignore

        # Find parent window and call MetadataManager directly
        parent_window = self._get_parent_with_metadata_tree()
        if not parent_window or not hasattr(parent_window, "metadata_manager"):
            logger.warning("[FileTableView] Could not find parent window or metadata manager")
            return False

        # SIMPLIFIED: Call MetadataManager directly - no complex signal chain
        try:
            parent_window.metadata_manager.load_metadata_for_items(
                file_items, use_extended=use_extended, source="drag_drop_direct"
            )

            # Set flag to indicate successful metadata drop
            self._successful_metadata_drop = True
            logger.debug(
                "[FileTableView] Metadata loading initiated successfully", extra={"dev_only": True}
            )

            # Force cursor cleanup after successful operation
            self._force_cursor_cleanup()

            # Schedule final status update
            def final_status_update():
                current_selection = self._get_current_selection()
                if current_selection:
                    selection_store = self._get_selection_store()
                    if selection_store and not self._legacy_selection_mode:
                        selection_store.selection_changed.emit(list(current_selection))
                        logger.debug(
                            f"[FileTableView] Final status update: {len(current_selection)} files",
                            extra={"dev_only": True},
                        )

            schedule_ui_update(final_status_update, delay=100)
            return True

        except Exception as e:
            logger.error(f"[FileTableView] Error calling MetadataManager: {e}")
            return False

    def _get_parent_with_metadata_tree(self):
        """Find parent window that has metadata_tree_view attribute"""
        from utils.path_utils import find_parent_with_attribute

        return find_parent_with_attribute(self, "metadata_tree_view")

    # =====================================
    # Drag & Drop Event Handlers
    # =====================================

    def dragEnterEvent(self, event):
        """Accept drag events with URLs or internal format."""
        if event.mimeData().hasUrls() or event.mimeData().hasFormat(
            "application/x-oncutf-internal"
        ):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        """Accept drag move events with URLs or internal format."""
        if event.mimeData().hasUrls() or event.mimeData().hasFormat(
            "application/x-oncutf-internal"
        ):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle file/folder drops into the table."""
        mime_data = event.mimeData()

        # Ignore internal drags from this table
        if mime_data.hasFormat("application/x-oncutf-filetable"):
            return

        # Extract and process dropped paths
        modifiers = event.keyboardModifiers()
        dropped_paths = extract_file_paths(mime_data)

        if not dropped_paths:
            return

        # Filter out duplicates
        if self.model() and hasattr(self.model(), "files"):
            existing_paths = {f.full_path for f in self.model().files}
            new_paths = [p for p in dropped_paths if p not in existing_paths]
            if not new_paths:
                return
        else:
            new_paths = dropped_paths

        # Emit signal for processing
        self.files_dropped.emit(new_paths, modifiers)
        event.acceptProposedAction()

    # =====================================
    # Selection & State Methods
    # =====================================

    def selectionChanged(self, selected, deselected) -> None:
        # SIMPLIFIED: Only essential protection against infinite loops
        if hasattr(self, "_processing_selection_change") and self._processing_selection_change:
            return

        self._processing_selection_change = True
        try:
            super().selectionChanged(selected, deselected)

            selection_model = self.selectionModel()
            if selection_model is not None:
                selected_rows = {index.row() for index in selection_model.selectedRows()}

                # OPTIMIZED: Only check for critical cases that need special handling
                if not selected_rows and hasattr(self, "_is_dragging") and self._is_dragging:
                    return

                # CRITICAL: Update SelectionStore with emit_signal=True to trigger preview update
                self._update_selection_store(selected_rows, emit_signal=True)

            if self.context_focused_row is not None:
                self.context_focused_row = None

            if hasattr(self, "viewport"):
                self.viewport().update()
        finally:
            self._processing_selection_change = False

    def select_rows_range(self, start_row: int, end_row: int) -> None:
        """Select a range of rows efficiently."""
        self.blockSignals(True)
        selection_model = self.selectionModel()
        model = self.model()

        if selection_model is None or model is None:
            self.blockSignals(False)
            return

        if hasattr(model, "index") and hasattr(model, "columnCount"):
            # Ensure we always select from lower to higher row number
            min_row = min(start_row, end_row)
            max_row = max(start_row, end_row)
            top_left = model.index(min_row, 0)
            bottom_right = model.index(max_row, model.columnCount() - 1)
            selection = QItemSelection(top_left, bottom_right)
            selection_model.select(
                selection, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows
            )  # type: ignore

        self.blockSignals(False)

        if hasattr(self, "viewport"):
            self.viewport().update()  # type: ignore

        if model is not None:
            # Ensure we always create range from lower to higher
            min_row = min(start_row, end_row)
            max_row = max(start_row, end_row)
            selected_rows = set(range(min_row, max_row + 1))
            self._update_selection_store(selected_rows, emit_signal=True)

    def select_dropped_files(self, file_paths: list[str] | None = None) -> None:
        """Select specific files that were just dropped/loaded in the table."""

        model = self.model()
        if not model or not hasattr(model, "files"):
            logger.error("[FileTableView] No model or model has no files attribute")
            return

        if not file_paths:
            # Fallback: select all files if no specific paths provided
            row_count = len(model.files)
            if row_count == 0:
                logger.debug(
                    "[FileTableView] No files in model - returning early", extra={"dev_only": True}
                )
                return
            logger.debug(
                f"[FileTableView] Fallback: selecting all {row_count} files",
                extra={"dev_only": True},
            )
            self.select_rows_range(0, row_count - 1)
            return

        # Select specific files based on their paths
        rows_to_select = []
        for i, file_item in enumerate(model.files):
            if file_item.full_path in file_paths:
                rows_to_select.append(i)

        if not rows_to_select:
            logger.debug("[FileTableView] No matching files found", extra={"dev_only": True})
            return

        # Clear existing selection first only if there are modifiers
        if self.keyboardModifiers() != Qt.NoModifier:
            self.clearSelection()

        # Select the specific rows ALL AT ONCE using range selection
        selection_model = self.selectionModel()
        if not selection_model:
            logger.error("[FileTableView] No selection model available")
            return

        self.blockSignals(True)

        # Create a single selection for all rows
        from core.pyqt_imports import QItemSelection

        full_selection = QItemSelection()

        for row in rows_to_select:
            if 0 <= row < len(model.files):
                left_index = model.index(row, 0)
                right_index = model.index(row, model.columnCount() - 1)
                if left_index.isValid() and right_index.isValid():
                    row_selection = QItemSelection(left_index, right_index)
                    full_selection.merge(row_selection, selection_model.Select)

        # Apply the entire selection at once
        if not full_selection.isEmpty():
            selection_model.select(full_selection, selection_model.Select)

        self.blockSignals(False)

        # Update selection store
        selected_rows = set(rows_to_select)
        self._update_selection_store(selected_rows, emit_signal=True)

        # Update UI
        if hasattr(self, "viewport"):
            self.viewport().update()

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
        super().wheelEvent(event)
        # Update hover after scroll
        pos = self.viewport().mapFromGlobal(QCursor.pos())
        index = self.indexAt(pos)
        hovered_row = index.row() if index.isValid() else -1

        if hasattr(self, "hover_delegate"):
            old_row = self.hover_delegate.hovered_row
            self.hover_delegate.update_hover_row(hovered_row)
            if old_row != hovered_row:
                for r in (old_row, hovered_row):
                    if r >= 0:
                        left = self.model().index(r, 0)  # type: ignore
                        right = self.model().index(r, self.model().columnCount() - 1)  # type: ignore
                        row_rect = self.visualRect(left).united(self.visualRect(right))
                        self.viewport().update(row_rect)  # type: ignore

        # Note: Vertical scrollbar handling is now integrated into _calculate_filename_width

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
                    from config import FILE_TABLE_COLUMN_CONFIG

                    complete_visibility = {}
                    for key, cfg in FILE_TABLE_COLUMN_CONFIG.items():
                        # Use saved value if available, otherwise use default
                        complete_visibility[key] = saved_visibility.get(key, cfg["default_visible"])
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
                from config import FILE_TABLE_COLUMN_CONFIG

                complete_visibility = {}
                for key, cfg in FILE_TABLE_COLUMN_CONFIG.items():
                    # Use saved value if available, otherwise use default
                    complete_visibility[key] = saved_visibility.get(key, cfg["default_visible"])
                logger.debug(f"[ColumnVisibility] Complete visibility state: {complete_visibility}")
                return complete_visibility

        except Exception as e:
            logger.warning(f"[ColumnVisibility] Error loading config: {e}")

        # Return default configuration
        from config import FILE_TABLE_COLUMN_CONFIG

        default_visibility = {
            key: cfg["default_visible"] for key, cfg in FILE_TABLE_COLUMN_CONFIG.items()
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

                # Save immediately
                config_manager.save()
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

        if column_key not in FILE_TABLE_COLUMN_CONFIG:
            logger.warning(f"Unknown column key: {column_key}")
            return

        column_config = FILE_TABLE_COLUMN_CONFIG[column_key]
        if not column_config.get("removable", True):
            logger.warning(f"Cannot toggle non-removable column: {column_key}")
            return  # Can't toggle non-removable columns

        # Ensure we have complete visibility state
        if not hasattr(self, "_visible_columns") or not self._visible_columns:
            logger.warning("[ColumnToggle] _visible_columns not initialized, reloading config")
            self._visible_columns = self._load_column_visibility_config()

        # Toggle visibility
        current_visibility = self._visible_columns.get(column_key, column_config["default_visible"])
        new_visibility = not current_visibility
        self._visible_columns[column_key] = new_visibility

        logger.info(f"Toggled column '{column_key}' visibility to {new_visibility}")
        logger.debug(f"[ColumnToggle] Current visibility state: {self._visible_columns}")

        # Verify we have all columns in visibility state
        for key, cfg in FILE_TABLE_COLUMN_CONFIG.items():
            if key not in self._visible_columns:
                self._visible_columns[key] = cfg["default_visible"]
                logger.debug(
                    f"[ColumnToggle] Added missing column '{key}' with default visibility {cfg['default_visible']}"
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

        if column_key not in FILE_TABLE_COLUMN_CONFIG:
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

        if column_key not in FILE_TABLE_COLUMN_CONFIG:
            logger.warning(f"Cannot remove unknown column: {column_key}")
            return

        column_config = FILE_TABLE_COLUMN_CONFIG[column_key]
        if not column_config.get("removable", True):
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
        """Reset all column widths to their default values (Ctrl+T)."""
        try:
            from config import FILE_TABLE_COLUMN_CONFIG

            visible_columns = []
            if hasattr(self.model(), "get_visible_columns"):
                visible_columns = self.model().get_visible_columns()
            else:
                visible_columns = ["filename", "file_size", "type", "modified"]

            for i, column_key in enumerate(visible_columns):
                column_index = i + 1  # +1 because column 0 is status column
                column_config = FILE_TABLE_COLUMN_CONFIG.get(column_key, {})
                default_width = column_config.get("width", 100)

                # Apply intelligent width validation for all columns
                final_width = self._ensure_column_proper_width(column_key, default_width)

                self.setColumnWidth(column_index, final_width)
                self._schedule_column_save(column_key, final_width)

            self._update_header_visibility()

        except Exception as e:
            logger.error(f"Error resetting columns to default: {e}")

    def _auto_fit_columns_to_content(self) -> None:
        """Auto-fit all column widths to their content (Ctrl+Shift+T)."""
        try:
            from config import FILE_TABLE_COLUMN_CONFIG, GLOBAL_MIN_COLUMN_WIDTH

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
                column_config = FILE_TABLE_COLUMN_CONFIG.get(column_key, {})

                # Use Qt's built-in resize to contents
                header.resizeSection(column_index, header.sectionSizeHint(column_index))

                # Apply minimum width constraint
                min_width = max(
                    column_config.get("min_width", GLOBAL_MIN_COLUMN_WIDTH), GLOBAL_MIN_COLUMN_WIDTH
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

    def _check_and_fix_column_widths(self) -> None:
        """Check if column widths need to be reset due to incorrect saved values."""
        try:
            from config import FILE_TABLE_COLUMN_CONFIG

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

            for column_key, column_config in FILE_TABLE_COLUMN_CONFIG.items():
                if column_config.get("default_visible", False):
                    total_count += 1
                    default_width = column_config.get("width", 100)
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
