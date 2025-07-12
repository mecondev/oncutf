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

from typing import Optional

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
    QLabel,
    QModelIndex,
    QMouseEvent,
    QPixmap,
    QPoint,
    Qt,
    QTableView,
    pyqtSignal,
    QTimer,
)
from utils.file_drop_helper import extract_file_paths
from utils.logger_factory import get_cached_logger
from utils.timer_manager import (
    schedule_resize_adjust,
    schedule_ui_update,
)

from .hover_delegate import HoverItemDelegate

logger = get_cached_logger(__name__)

# Constants for better maintainability
PLACEHOLDER_ICON_SIZE = 160
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
    - Automatic placeholder management (no scrollbar in placeholder mode)
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

    def __init__(self, parent=None) -> None:
        """Initialize the custom table view with Explorer-like behavior."""
        super().__init__(parent)
        logger.debug("FileTableView __init__ called")
        self._manual_anchor_index: Optional[QModelIndex] = None
        self._drag_start_pos: Optional[QPoint] = None  # Initialize as None instead of empty QPoint
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

        # Check and fix column widths if needed
        self._check_and_fix_column_widths()

        # Initialize selection tracking
        self._manual_anchor_index = None
        self._legacy_selection_mode = False

        # Note: Vertical scrollbar handling is now integrated into _calculate_filename_width

        # Custom drag state tracking (needed by existing drag implementation)
        self._is_dragging = False
        self._drag_data = None
        self._drag_feedback_timer = None

        # Selection preservation for drag operations
        self._preserve_selection_for_drag = False
        self._clicked_on_selected = False
        self._clicked_index = None

        # Column configuration delayed save
        self._config_save_timer = None
        self._pending_column_changes = {}

        # Setup placeholder icon
        self.placeholder_label = QLabel(self.viewport())
        self.placeholder_label.setAlignment(Qt.AlignCenter)  # type: ignore
        self.placeholder_label.setVisible(False)
        # Set background color to match table background (needed even with transparent PNG)
        self.placeholder_label.setStyleSheet("background-color: #181818;")

        from utils.path_utils import get_images_dir

        icon_path = get_images_dir() / "File_table_placeholder_fixed.png"
        self.placeholder_icon = QPixmap(str(icon_path))

        if not self.placeholder_icon.isNull():
            scaled = self.placeholder_icon.scaled(
                PLACEHOLDER_ICON_SIZE,
                PLACEHOLDER_ICON_SIZE,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,  # type: ignore
            )
            self.placeholder_label.setPixmap(scaled)
        else:
            logger.warning("Placeholder icon could not be loaded.")

        # Selection and interaction state
        self.selected_rows: set[int] = set()
        self.anchor_row: Optional[int] = None
        self.context_focused_row: Optional[int] = None

        # Enable hover visuals
        from widgets.hover_delegate import HoverItemDelegate
        self.hover_delegate = HoverItemDelegate(self)
        self.setItemDelegate(self.hover_delegate)

        # Selection store integration (with fallback to legacy selection handling)
        self._legacy_selection_mode = True  # Start in legacy mode for compatibility

    def showEvent(self, event) -> None:
        """Handle show events and update scrollbar visibility."""
        super().showEvent(event)

        # Force complete refresh when widget becomes visible
        self._force_scrollbar_update()

        # Ensure proper text display
        self._ensure_no_word_wrap()

    def paintEvent(self, event):
        logger.debug("FileTableView paintEvent called")
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
        """Update SelectionStore with current selection and ensure Qt model is synchronized."""
        selection_store = self._get_selection_store()
        if selection_store and not self._legacy_selection_mode:
            selection_store.set_selected_rows(selected_rows, emit_signal=emit_signal)

        # Always update legacy state for compatibility
        self.selected_rows = selected_rows

        # CRITICAL: Ensure Qt selection model is synchronized with our selection
        # This prevents blue highlighting desync issues
        if emit_signal:  # Only sync Qt model when we're not in a batch operation
            self._sync_qt_selection_model(selected_rows)
            # Emit selection change signal immediately
            self.selection_changed.emit(list(selected_rows))

    def _sync_qt_selection_model(self, selected_rows: set) -> None:
        """Ensure Qt selection model matches our internal selection state."""
        selection_model = self.selectionModel()
        if not selection_model or not self.model():
            return

        # Prevent recursive calls during Qt model synchronization
        if hasattr(self, "_syncing_qt_model") and self._syncing_qt_model:
            return

        # Get current Qt selection
        current_qt_selection = set(index.row() for index in selection_model.selectedRows())

        # Only update if there's a significant difference (avoid unnecessary updates)
        if current_qt_selection != selected_rows:
            # Set flag to prevent recursive calls
            self._syncing_qt_model = True

            # Block signals to prevent recursive calls
            self.blockSignals(True)
            try:
                # Clear current selection
                selection_model.clearSelection()

                # Select the new rows
                if selected_rows:
                    from core.pyqt_imports import QItemSelection

                    full_selection = QItemSelection()

                    for row in selected_rows:
                        if 0 <= row < self.model().rowCount():  # type: ignore
                            left_index = self.model().index(row, 0)  # type: ignore
                            right_index = self.model().index(row, self.model().columnCount() - 1)  # type: ignore
                            if left_index.isValid() and right_index.isValid():
                                row_selection = QItemSelection(left_index, right_index)
                                full_selection.merge(row_selection, selection_model.Select)  # type: ignore

                    if not full_selection.isEmpty():
                        selection_model.select(full_selection, selection_model.Select)  # type: ignore

                # Force visual update
                self.viewport().update()  # type: ignore

            finally:
                self.blockSignals(False)
                # Clear the flag
                self._syncing_qt_model = False

    def _get_current_selection(self) -> set:
        """Get current selection from SelectionStore or fallback to Qt model."""
        selection_store = self._get_selection_store()
        if selection_store and not self._legacy_selection_mode:
            return selection_store.get_selected_rows()
        else:
            # Fallback: get from Qt selection model (more reliable than legacy)
            selection_model = self.selectionModel()
            if selection_model:
                qt_selection = set(index.row() for index in selection_model.selectedRows())
                # Update legacy state to match Qt
                self.selected_rows = qt_selection
                return qt_selection
            else:
                return self.selected_rows

    def _get_current_selection_safe(self) -> set:
        """Get current selection safely - SIMPLIFIED VERSION."""
        selection_model = self.selectionModel()
        if selection_model:
            return set(index.row() for index in selection_model.selectedRows())
        else:
            return set()

    def _set_anchor_row(self, row: Optional[int]) -> None:
        """Set anchor row in SelectionStore or fallback to legacy."""
        selection_store = self._get_selection_store()
        if selection_store and not self._legacy_selection_mode:
            selection_store.set_anchor_row(row)

        # Always update legacy state for compatibility
        self.anchor_row = row

    def _get_anchor_row(self) -> Optional[int]:
        """Get anchor row from SelectionStore or fallback to legacy."""
        selection_store = self._get_selection_store()
        if selection_store and not self._legacy_selection_mode:
            return selection_store.get_anchor_row()
        else:
            return self.anchor_row

    def resizeEvent(self, event) -> None:
        """Handle window resize events and update scrollbar visibility."""
        super().resizeEvent(event)

        # Update placeholder position if visible
        if self.placeholder_label.isVisible():
            self.placeholder_label.resize(self.viewport().size())

        # Force scrollbar update after resize
        self._force_scrollbar_update()

        # Ensure word wrap is disabled after resize
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

        # Force complete model refresh to update text display
        if self.model():
            self.model().layoutChanged.emit()

        # Force viewport update
        self.viewport().update()

        # Schedule delayed update to ensure proper text rendering
        schedule_ui_update(lambda: self._refresh_text_display(), delay=50)

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
            bottom_right = self.model().index(self.model().rowCount() - 1, self.model().columnCount() - 1)
            self.dataChanged(top_left, bottom_right)

    def setModel(self, model) -> None:
        logger.debug(f"FileTableView setModel called with model: {type(model)}")

        # Log column widths BEFORE calling super().setModel()
        if self.model():
            logger.debug("Column widths BEFORE super().setModel():")
            for i in range(min(5, self.model().columnCount())):
                width = self.columnWidth(i)
                logger.debug(f"  Column {i}: {width}px")

        super().setModel(model)

        # Don't configure columns here - let refresh_columns_after_model_change() handle it
        # This avoids double configuration
        logger.debug("setModel: Column configuration will be handled by refresh_columns_after_model_change()")

        # Auto-update placeholder visibility after model is set
        self._auto_update_placeholder_visibility()

    # =====================================
    # Table Preparation & Management
    # =====================================

    def prepare_table(self, file_items: list) -> None:
        logger.debug(f"prepare_table called with {len(file_items)} items")
        # Reset manual column preferences when loading new files
        self._has_manual_preference = False
        self._user_preferred_width = None

        # Clear selection and reset checked state
        for file_item in file_items:
            file_item.checked = False

        self.clearSelection()
        self.selected_rows.clear()

        # Clear selection in SelectionStore as well
        selection_store = self._get_selection_store()
        if selection_store:
            selection_store.clear_selection(emit_signal=False)
            selection_store.set_anchor_row(None, emit_signal=False)

        # Set files in model (this triggers beginResetModel/endResetModel)
        if self.model() and hasattr(self.model(), "set_files"):
            self.model().set_files(file_items)

        # Reconfigure columns after model reset
        # self._configure_columns()  # Αφαιρείται, το κάνει το μοντέλο πλέον

        # Ensure no word wrap after setting files
        self._ensure_no_word_wrap()

        # Reset hover delegate state
        if hasattr(self, "hover_delegate"):
            self.setItemDelegate(self.hover_delegate)
            self.hover_delegate.hovered_row = -1

        # Update UI
        self.viewport().update()
        self._update_scrollbar_visibility()

        # Note: Vertical scrollbar handling is now integrated into _calculate_filename_width

        logger.debug("prepare_table finished")

    # =====================================
    # Column Management & Scrollbar Optimization
    # =====================================

    def _configure_columns(self) -> None:
        """Configure columns with values from config.py."""
        if not self.model():
            return

        logger.debug("_configure_columns: Starting configuration")

        header = self.horizontalHeader()
        if not header:
            return

        # Show header first
        header.show()

        # Configure status column (column 0) - always fixed
        self.setColumnWidth(0, 45)
        header.setSectionResizeMode(0, header.Fixed)

        # Load column configuration from config.py (already imported at top)

        # Get visible columns from model or use defaults
        visible_columns = ['filename', 'file_size', 'type', 'modified']
        if hasattr(self.model(), 'get_visible_columns'):
            visible_columns = self.model().get_visible_columns()
            logger.debug(f"Got visible columns from model: {visible_columns}")
        else:
            logger.debug(f"Model doesn't have get_visible_columns, using defaults: {visible_columns}")

                # Configure each visible column with delay to avoid timing issues
        def configure_columns_delayed():
            logger.debug("Configuring columns with delay...")
            for column_index, column_key in enumerate(visible_columns):
                actual_column_index = column_index + 1  # +1 because column 0 is status

                if actual_column_index < self.model().columnCount():
                    # Get width from saved config or use defaults from config.py
                    width = self._load_column_width(column_key)

                    logger.debug(f"Setting column {actual_column_index} ({column_key}) to {width}px")

                    # Set resize mode first, then width
                    header.setSectionResizeMode(actual_column_index, header.Interactive)

                    # Set the width
                    self.setColumnWidth(actual_column_index, width)

                    # Verify the width was set correctly
                    actual_width = self.columnWidth(actual_column_index)
                    logger.debug(f"Verified column {actual_column_index} width: {actual_width}px")

        # Configure columns with a small delay to avoid timing issues
        QTimer.singleShot(10, configure_columns_delayed)

        # Update header visibility
        if hasattr(self.model(), 'files') and len(self.model().files) > 0:
            header.show()
            logger.debug("Header shown")
        else:
            header.hide()
            logger.debug("Header hidden")

        # Check if header has any automatic resize settings that might interfere
        logger.debug(f"Header stretch last section: {header.stretchLastSection()}")
        logger.debug(f"Header cascade section resizes: {header.cascadingSectionResizes()}")

        # Ensure these don't interfere with our column widths
        header.setStretchLastSection(False)
        header.setCascadingSectionResizes(False)
        logger.debug("Disabled header auto-resize features")

        logger.debug("_configure_columns: Configuration finished")

    def _update_header_visibility(self) -> None:
        """Update header visibility based on whether there are files in the model."""
        # This method is now handled in _configure_columns - do nothing
        pass

    def _ensure_header_visibility(self) -> None:
        """Ensure header visibility is correct after column configuration."""
        # This method is now handled in _configure_columns - do nothing
        pass

    def _set_column_alignment(self, column_index: int, alignment: str) -> None:
        """Set text alignment for a specific column."""
        if not self.model():
            return

        # Map alignment strings to Qt constants
        alignment_map = {
            'left': Qt.AlignLeft | Qt.AlignVCenter,
            'right': Qt.AlignRight | Qt.AlignVCenter,
            'center': Qt.AlignCenter,
        }

        qt_alignment = alignment_map.get(alignment, Qt.AlignLeft | Qt.AlignVCenter)

        # Store alignment for use in delegates or model
        if not hasattr(self, '_column_alignments'):
            self._column_alignments = {}
        self._column_alignments[column_index] = qt_alignment

    def _load_column_width(self, column_key: str) -> int:
        """Load column width from main config system with fallback to defaults."""
        try:
            # First, get the default width from config.py
            from config import FILE_TABLE_COLUMN_CONFIG
            default_width = FILE_TABLE_COLUMN_CONFIG.get(column_key, {}).get("width", 100)

            # Try main config system first
            main_window = self._get_main_window()
            if main_window and hasattr(main_window, 'window_config_manager'):
                config_manager = main_window.window_config_manager.config_manager
                window_config = config_manager.get_category('window')
                column_widths = window_config.get('file_table_column_widths', {})

                if column_key in column_widths:
                    saved_width = column_widths[column_key]
                    # Check if saved width is reasonable (not the default Qt 100px for all columns)
                    # If all columns are 100px, it means they were saved incorrectly
                    if saved_width == 100 and default_width != 100:
                        logger.debug(f"Column '{column_key}' has suspicious saved width (100px), using default {default_width}px")
                        return default_width
                    return saved_width

            # Fallback to old method
            from utils.json_config_manager import load_config
            config = load_config()
            column_widths = config.get("file_table_column_widths", {})
            if column_key in column_widths:
                saved_width = column_widths[column_key]
                # Same check for old config format
                if saved_width == 100 and default_width != 100:
                    logger.debug(f"Column '{column_key}' has suspicious saved width (100px), using default {default_width}px")
                    return default_width
                return saved_width

            # Return default width from config.py
            return default_width

        except Exception as e:
            logger.warning(f"Failed to load column width for {column_key}: {e}")
            # Emergency fallback to config.py defaults
            from config import FILE_TABLE_COLUMN_CONFIG
            column_config = FILE_TABLE_COLUMN_CONFIG.get(column_key, {})
            return column_config.get("width", 100)

    def _reset_column_widths_to_defaults(self) -> None:
        """Reset all column widths to their default values from config.py."""
        try:
            from config import FILE_TABLE_COLUMN_CONFIG

            logger.info("Resetting column widths to defaults from config.py")

            # Clear saved column widths
            main_window = self._get_main_window()
            if main_window and hasattr(main_window, 'window_config_manager'):
                config_manager = main_window.window_config_manager.config_manager
                window_config = config_manager.get_category('window')
                window_config.set('file_table_column_widths', {})
                config_manager.save()

            # Also clear from old format
            from utils.json_config_manager import load_config, save_config
            config = load_config()
            config["file_table_column_widths"] = {}
            save_config(config)

            # Reconfigure columns with defaults
            self._configure_columns()

            logger.info("Column widths reset to defaults successfully")

        except Exception as e:
            logger.error(f"Failed to reset column widths to defaults: {e}")

    def _save_column_width(self, column_key: str, width: int) -> None:
        """Save column width to main config system."""
        try:
            # Get the main window and its config manager
            main_window = self._get_main_window()
            if main_window and hasattr(main_window, 'window_config_manager'):
                config_manager = main_window.window_config_manager.config_manager
                window_config = config_manager.get_category('window')

                # Get current column widths
                column_widths = window_config.get('file_table_column_widths', {})
                column_widths[column_key] = width
                window_config.set('file_table_column_widths', column_widths)

                # Save immediately for individual changes
                config_manager.save()
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

        logger.debug(f"Scheduled delayed save for column '{column_key}' width {width}px (will save in 7 seconds)")

    def _save_pending_column_changes(self) -> None:
        """Save all pending column width changes to config.json."""
        if not self._pending_column_changes:
            return

        try:
            from utils.json_config_manager import load_config, save_config
            config = load_config()
            if "file_table_column_widths" not in config:
                config["file_table_column_widths"] = {}

            # Apply all pending changes
            for column_key, width in self._pending_column_changes.items():
                config["file_table_column_widths"][column_key] = width

            save_config(config)

            logger.info(f"Saved {len(self._pending_column_changes)} column width changes to config")

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

        # Update scrollbar visibility immediately and force viewport update
        self._force_scrollbar_update()

        # Force repaint and layout update so elidedText is recalculated
        if self.model():
            self.model().layoutChanged.emit()
        self.viewport().update()

        logger.debug(f"Column '{column_key}' resized from {old_size}px to {new_size}px")

    def _force_scrollbar_update(self) -> None:
        """Force immediate scrollbar and viewport update."""
        # Update scrollbar visibility
        self._update_scrollbar_visibility()

        # Use column manager's improved horizontal scrollbar handling
        try:
            from core.application_context import get_app_context
            context = get_app_context()
            if context and hasattr(context, 'column_manager'):
                context.column_manager.ensure_horizontal_scrollbar_state(self)
        except (RuntimeError, AttributeError):
            # Fallback to basic scrollbar handling
            self.updateGeometries()
            hbar = self.horizontalScrollBar()
            if hbar and hbar.maximum() > 0:
                hbar.setValue(0)

        # Force immediate viewport refresh
        self.viewport().update()

        # Force geometry update
        self.updateGeometry()

        # Force model data refresh to update word wrap
        if self.model():
            self.model().layoutChanged.emit()

        # Schedule a delayed update to ensure everything is properly refreshed
        schedule_ui_update(lambda: self._delayed_refresh(), delay=100)

    def _delayed_refresh(self) -> None:
        """Delayed refresh to ensure proper scrollbar and content updates."""
        self._update_scrollbar_visibility()

        # Use column manager's improved horizontal scrollbar handling
        try:
            from core.application_context import get_app_context
            context = get_app_context()
            if context and hasattr(context, 'column_manager'):
                context.column_manager.ensure_horizontal_scrollbar_state(self)
        except (RuntimeError, AttributeError):
            # Fallback to basic scrollbar handling
            self.updateGeometries()
            hbar = self.horizontalScrollBar()
            if hbar and hbar.maximum() > 0:
                hbar.setValue(0)

        self.viewport().update()

        # Force text refresh in all visible cells
        if self.model():
            visible_rect = self.viewport().rect()
            top_left = self.indexAt(visible_rect.topLeft())
            bottom_right = self.indexAt(visible_rect.bottomRight())

            if top_left.isValid() and bottom_right.isValid():
                self.dataChanged(top_left, bottom_right)

    def _on_column_moved(self, logical_index: int, old_visual_index: int, new_visual_index: int) -> None:
        """Handle column reordering and save order to config."""
        if logical_index == 0:  # Don't allow moving status column
            # Revert the move by moving it back to position 0
            header = self.horizontalHeader()
            if header and new_visual_index != 0:
                header.moveSection(new_visual_index, 0)
            return

        # Save new column order to config
        try:
            from utils.json_config_manager import load_config, save_config
            config = load_config()
            # TODO: Implement column order saving
            logger.debug(f"Column moved from position {old_visual_index} to {new_visual_index}")
        except Exception as e:
            logger.warning(f"Failed to save column order: {e}")

    def _get_column_key_from_index(self, logical_index: int) -> str:
        """Get column key from logical index."""
        if logical_index == 0:
            return "status"

        # Get visible columns from model
        visible_columns = []
        if hasattr(self.model(), 'get_visible_columns'):
            visible_columns = self.model().get_visible_columns()
        else:
            visible_columns = ['filename', 'file_size', 'type', 'modified']

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

    def on_horizontal_splitter_moved(self, pos: int, index: int) -> None:
        """Handle horizontal splitter movement - no longer adjusts filename column."""
        # No longer needed - columns maintain their fixed widths
        # Horizontal scrollbar will appear when needed
        pass

    def on_vertical_splitter_moved(self, pos: int, index: int) -> None:
        """Handle vertical splitter movement."""
        # No special handling needed
        pass

    # =====================================
    # UI Methods
    # =====================================

    def set_placeholder_visible(self, visible: bool) -> None:
        """Show or hide the placeholder icon and configure table state."""
        if visible and not self.placeholder_icon.isNull():
            self.placeholder_label.raise_()
            self.placeholder_label.show()

            # Force hide horizontal scrollbar when showing placeholder
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

            # Disable interactions when showing placeholder but keep drag & drop
            header = self.horizontalHeader()
            if header:
                header.setEnabled(False)
                header.setSectionsClickable(False)
                header.setSortIndicatorShown(False)

            self.setSelectionMode(QAbstractItemView.NoSelection)
            self.setContextMenuPolicy(Qt.NoContextMenu)

            # Set placeholder property for styling
            self.setProperty("placeholder", True)

        else:
            # Use batch updates to prevent flickering when re-enabling content
            self.setUpdatesEnabled(False)

            try:
                self.placeholder_label.hide()

                # Re-enable scrollbar policy based on content
                self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

                # Re-enable interactions when hiding placeholder
                header = self.horizontalHeader()
                if header:
                    header.show()  # CRITICAL: Show the header
                    header.setEnabled(True)
                    header.setSectionsClickable(True)
                    header.setSortIndicatorShown(True)
                    header.repaint()  # Force repaint

                self.setSelectionMode(QAbstractItemView.ExtendedSelection)
                self.setContextMenuPolicy(Qt.CustomContextMenu)

                # Clear placeholder property
                self.setProperty("placeholder", False)

            finally:
                # Re-enable updates and force a single refresh
                self.setUpdatesEnabled(True)
                self.viewport().update()

    def _auto_update_placeholder_visibility(self) -> None:
        """Automatically update placeholder visibility based on model state."""
        should_show_placeholder = self.is_empty()
        self.set_placeholder_visible(should_show_placeholder)

    def ensure_anchor_or_select(self, index: QModelIndex, modifiers: Qt.KeyboardModifiers) -> None:
        """Handle selection logic with anchor and modifier support."""
        sm = self.selectionModel()
        model = self.model()
        if sm is None or model is None:
            return

        if modifiers & Qt.ShiftModifier:
            # Check if we're clicking on an already selected item
            current_selection = set(idx.row() for idx in sm.selectedRows())
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
                # Use ClearAndSelect to replace existing selection with the range
                sm.select(selection, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)
                sm.setCurrentIndex(index, QItemSelectionModel.NoUpdate)

            # Update SelectionStore to match Qt selection model
            selection_store = self._get_selection_store()
            if selection_store and not self._legacy_selection_mode:
                current_qt_selection = set(idx.row() for idx in sm.selectedRows())
                selection_store.set_selected_rows(current_qt_selection, emit_signal=True)
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
                current_qt_selection = set(idx.row() for idx in sm.selectedRows())
                selection_store.set_selected_rows(current_qt_selection, emit_signal=True)
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
                current_qt_selection = set(idx.row() for idx in sm.selectedRows())
                selection_store.set_selected_rows(current_qt_selection, emit_signal=True)
                selection_store.set_anchor_row(index.row(), emit_signal=False)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        Handle mouse press events for selection and drag initiation.
        """
        # Get the index under the mouse
        index = self.indexAt(event.pos())
        modifiers = event.modifiers()

        # Store clicked index for potential drag
        self._clicked_index = index

        # Check if we clicked on a selected item
        if index.isValid():
            self._clicked_on_selected = index.row() in self._get_current_selection()
        else:
            self._clicked_on_selected = False

        # Handle left button press
        if event.button() == Qt.LeftButton:
            # Store drag start position
            self._drag_start_pos = event.pos()

            # Store current selection for potential drag operation
            current_sel = self._get_current_selection()
            self._drag_start_selection = current_sel.copy()

            # If clicking on empty space, clear selection
            if not index.isValid():
                if modifiers == Qt.NoModifier:
                    self.clearSelection()
                    self._set_anchor_row(None)
                    self._update_selection_store(set(), emit_signal=True)
                # Don't call super() for empty space clicks to avoid Qt's default behavior
                return

            # Handle selection based on modifiers
            if modifiers == Qt.NoModifier:
                # Check if we're clicking on an already selected item for potential drag
                current_selection = self._get_current_selection()
                if index.row() in current_selection and len(current_selection) > 1:
                    # Multi-selection: Preserve current selection for drag, but allow deselection on release
                    self._drag_start_selection = current_selection.copy()
                    self._preserve_selection_for_drag = True
                    self._clicked_on_selected = True
                    self._skip_selection_changed = True
                    schedule_ui_update(self._clear_skip_flag, 50)
                    return  # Don't change selection - preserve for drag

                else:
                    # Single click - select single row
                    self._set_anchor_row(index.row())
                    self._update_selection_store({index.row()})
            elif modifiers == Qt.ControlModifier:
                # Check if we're on a selected item for potential drag
                current_selection = self._get_current_selection()
                if index.row() in current_selection:
                    # Ctrl+click on selected item - prepare for toggle (remove) on mouse release
                    self._preserve_selection_for_drag = True
                    self._clicked_on_selected = True
                    self._clicked_index = index
                    self._drag_start_selection = current_selection.copy()
                    return  # Don't call super() - we'll handle in mouseReleaseEvent
                else:
                    # Ctrl+click on unselected - add to selection (toggle)
                    current_selection = (
                        current_selection.copy()
                    )  # Make a copy to avoid modifying the original
                    current_selection.add(index.row())
                    self._set_anchor_row(index.row())  # Set anchor for future range selections
                    self._update_selection_store(current_selection)
                    # Don't call super() - we handled the selection ourselves
                    return
            elif modifiers == Qt.ShiftModifier:
                # Check if we're clicking on a selected item for potential drag
                current_selection = self._get_current_selection()
                if index.row() in current_selection:
                    # Clicking on already selected item with Shift - preserve selection for drag
                    # This prevents Shift+drag from changing selection
                    self._drag_start_selection = current_selection.copy()
                    self._skip_selection_changed = True
                    schedule_ui_update(self._clear_skip_flag, 50)
                    return  # Let Qt handle Shift+click
                else:
                    # Shift+click on unselected item - select range
                    anchor = self._get_anchor_row()
                    if anchor is not None:
                        self.select_rows_range(anchor, index.row())
                    else:
                        self._set_anchor_row(index.row())
                        self._update_selection_store({index.row()})
                    # Don't call super() - we handled the selection ourselves
                    return

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
            # Handle preserved selection case (clicked on selected item but didn't drag)
            if (
                getattr(self, "_preserve_selection_for_drag", False)
                and not self._is_dragging
                and hasattr(self, "_clicked_on_selected")
                and self._clicked_on_selected
            ):
                modifiers = QApplication.keyboardModifiers()
                if modifiers == Qt.ControlModifier:
                    # Ctrl+click on selected item without drag - toggle selection (remove)
                    if (
                        hasattr(self, "_clicked_index")
                        and self._clicked_index
                        and self._clicked_index.isValid()
                    ):
                        current_selection = self._get_current_selection().copy()
                        row = self._clicked_index.row()
                        if row in current_selection:
                            current_selection.remove(row)
                            # Update anchor to another selected item if available
                            if current_selection:
                                self._set_anchor_row(
                                    max(current_selection)
                                )  # Use highest row as new anchor
                            else:
                                self._set_anchor_row(None)  # No selection left
                            self._update_selection_store(current_selection)
                elif modifiers == Qt.ShiftModifier:
                    # Shift+click on selected item without drag - preserve current selection
                    # Don't change selection when Shift is held and we clicked on a selected item
                    pass
                elif modifiers == Qt.NoModifier:
                    # Regular click on selected item without drag - clear selection and select only this
                    if (
                        hasattr(self, "_clicked_index")
                        and self._clicked_index
                        and self._clicked_index.isValid()
                    ):
                        row = self._clicked_index.row()
                        # Clear selection and select only the clicked item
                        self._set_anchor_row(row)
                        self._update_selection_store({row})

            # Clean up flags
            self._preserve_selection_for_drag = False
            self._clicked_on_selected = False
            if hasattr(self, "_clicked_index"):
                self._clicked_index = None

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
                            logger.debug(
                                f"[FileTableView] Final status update after drag: {len(current_selection)} files",
                                extra={"dev_only": True},
                            )

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
        # Handle column management shortcuts
        from config import COLUMN_SHORTCUTS

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
            current_qt_selection = set(idx.row() for idx in self.selectionModel().selectedRows())
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
        """SIMPLIFIED selection handling with protection against post-drag empty selections"""
        super().selectionChanged(selected, deselected)

        selection_model = self.selectionModel()
        if selection_model is not None:
            selected_rows = set(index.row() for index in selection_model.selectedRows())

            # PROTECTION: Ignore empty selections that come immediately after SUCCESSFUL metadata drops
            # This prevents Qt's automatic clearSelection() from clearing our metadata display
            if (
                not selected_rows
                and hasattr(self, "_successful_metadata_drop")
                and self._successful_metadata_drop
            ):
                logger.debug(
                    "[FileTableView] Ignoring empty selection after successful metadata drop",
                    extra={"dev_only": True},
                )
                # Clear the flag and restore the selection
                self._successful_metadata_drop = False
                # Try to restore the selection from SelectionStore
                selection_store = self._get_selection_store()
                if selection_store and not self._legacy_selection_mode:
                    stored_selection = selection_store.get_selected_rows()
                    if stored_selection:
                        logger.debug(
                            f"[FileTableView] Restoring {len(stored_selection)} files from SelectionStore",
                            extra={"dev_only": True},
                        )
                        self._sync_qt_selection_model(stored_selection)
                        self.viewport().update()
                return

            # Also ignore empty selections during active drag operations
            if not selected_rows and hasattr(self, "_is_dragging") and self._is_dragging:
                logger.debug(
                    "[FileTableView] Ignoring empty selection during drag operation",
                    extra={"dev_only": True},
                )
                return

            self._update_selection_store(selected_rows, emit_signal=True)

        if self.context_focused_row is not None:
            self.context_focused_row = None

        if hasattr(self, "viewport"):
            self.viewport().update()

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

    def select_dropped_files(self, file_paths: Optional[list[str]] = None) -> None:
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
        return not getattr(self.model(), "files", [])

    def focusOutEvent(self, event) -> None:
        super().focusOutEvent(event)
        if self.context_focused_row is not None:
            self.context_focused_row = None
            self.viewport().update()

    def focusInEvent(self, event) -> None:
        """SIMPLIFIED focus handling - just sync selection, no special cases"""
        super().focusInEvent(event)

        # Simple sync: update SelectionStore with current Qt selection
        selection_model = self.selectionModel()
        if selection_model is not None:
            selected_rows = set(index.row() for index in selection_model.selectedRows())
            self._update_selection_store(selected_rows, emit_signal=False)  # Don't emit signal on focus

        self.viewport().update()

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
            current_selection = set(index.row() for index in self.selectionModel().selectedRows())  # type: ignore
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

    def _clear_skip_flag(self):
        """Clear the skip flag after a delay."""
        self._skip_selection_changed = False

    # =====================================
    # Column Management Methods
    # =====================================

    def _load_column_visibility_config(self) -> dict:
        """Load column visibility configuration from config.json."""
        try:
            from utils.json_config_manager import load_config
            config = load_config()
            return config.get("file_table_columns", {})
        except Exception:
            # Return default configuration
            from config import FILE_TABLE_COLUMN_CONFIG
            return {key: cfg["default_visible"] for key, cfg in FILE_TABLE_COLUMN_CONFIG.items()}

    def _save_column_visibility_config(self) -> None:
        """Save column visibility configuration to main config system."""
        try:
            # Get the main window and its config manager
            main_window = self._get_main_window()
            if main_window and hasattr(main_window, 'window_config_manager'):
                config_manager = main_window.window_config_manager.config_manager
                window_config = config_manager.get_category('window')

                # Get current column visibility
                current_visibility = self._load_column_visibility_config()
                window_config.set('file_table_columns', current_visibility)

                # Save immediately
                config_manager.save()
            else:
                # Fallback to old method
                from utils.json_config_manager import load_config, save_config
                config = load_config()
                config["file_table_columns"] = self._load_column_visibility_config()
                save_config(config)
        except Exception as e:
            logger.warning(f"Failed to save column visibility config: {e}")

    def _toggle_column_visibility(self, column_key: str) -> None:
        """Toggle visibility of a specific column and refresh the table."""
        from config import FILE_TABLE_COLUMN_CONFIG

        if column_key not in FILE_TABLE_COLUMN_CONFIG:
            logger.warning(f"Unknown column key: {column_key}")
            return

        column_config = FILE_TABLE_COLUMN_CONFIG[column_key]
        if not column_config.get("removable", True):
            logger.warning(f"Cannot toggle non-removable column: {column_key}")
            return  # Can't toggle non-removable columns

        # Toggle visibility
        current_visibility = self._visible_columns.get(column_key, column_config["default_visible"])
        self._visible_columns[column_key] = not current_visibility

        # Save configuration
        self._save_column_visibility_config()

        # Update table display with gentle refresh (preserves selection)
        self._update_table_columns()

        logger.info(f"Toggled column '{column_key}' visibility to {not current_visibility}")

    def _update_table_columns(self) -> None:
        """Update table columns based on visibility configuration while preserving selection."""
        model = self.model()
        if not model:
            logger.warning("No model available for column update")
            return

        try:
            # Store current selection before any changes
            selected_rows = self._get_current_selection()

            # Update the model with new visible columns
            if hasattr(model, 'update_visible_columns'):
                model.update_visible_columns(self._visible_columns)

                # Reconfigure columns with new layout - this will set proper widths and scrollbar policy
                self._configure_columns()

                # Force gentle refresh of the view
                self.updateGeometry()
                self.viewport().update()

                # Restore selection immediately if it existed
                if selected_rows:
                    # Use the existing sync method which is designed for this
                    self._sync_qt_selection_model(selected_rows)

                    # Update metadata tree directly without clearing - this preserves existing metadata
                    metadata_tree = self._get_metadata_tree()
                    if metadata_tree and hasattr(metadata_tree, 'update_from_parent_selection'):
                        # Use direct call to preserve metadata state during column updates
                        metadata_tree.update_from_parent_selection()
                    else:
                        # Fallback to signal emission if direct method unavailable
                        QTimer.singleShot(50, lambda: self.selection_changed.emit(list(selected_rows)))

                # Count visible columns for logging
                visible_count = sum(1 for visible in self._visible_columns.values() if visible)
                logger.info(f"Table columns updated - {visible_count} columns visible, selection restored: {len(selected_rows)} rows")

            else:
                logger.warning("Model does not support dynamic columns")

        except Exception as e:
            logger.error(f"Error updating table columns: {e}")

        # No longer need to trigger column adjustment - columns maintain fixed widths

    def _get_metadata_tree(self):
        """Get the metadata tree widget from the parent hierarchy."""
        parent = self.parent()
        while parent:
            if hasattr(parent, 'metadata_tree'):
                return parent.metadata_tree
            parent = parent.parent()
        return None

    def _get_main_window(self):
        """Get the main window from the parent hierarchy."""
        parent = self.parent()
        while parent:
            if hasattr(parent, 'window_config_manager'):
                return parent
            parent = parent.parent()
        return None

    def _clear_preview_and_metadata(self) -> None:
        """Clear preview and metadata displays when no selection exists."""
        try:
            # Get the parent window to access preview and metadata components
            parent_window = self.parent()
            while parent_window and not hasattr(parent_window, 'metadata_tree_view'):
                parent_window = parent_window.parent()

            if parent_window:
                # Clear metadata display
                if hasattr(parent_window, 'metadata_tree_view'):
                    metadata_tree = parent_window.metadata_tree_view
                    if hasattr(metadata_tree, 'show_empty_state'):
                        metadata_tree.show_empty_state("No file selected")

                # Clear preview display
                if hasattr(parent_window, 'preview_tables_view'):
                    preview_view = parent_window.preview_tables_view
                    if hasattr(preview_view, 'clear_view'):
                        preview_view.clear_view()

                logger.debug("Cleared preview and metadata displays after column update")

        except Exception as e:
            logger.warning(f"Error clearing preview/metadata displays: {e}")

    # =====================================
    # Column Management Shortcuts
    # =====================================

    def _reset_columns_to_default(self) -> None:
        """Reset all column widths to their default values (Ctrl+T)."""
        try:
            from config import FILE_TABLE_COLUMN_CONFIG

            # Get visible columns from model
            visible_columns = []
            if hasattr(self.model(), 'get_visible_columns'):
                visible_columns = self.model().get_visible_columns()
            else:
                visible_columns = ['filename', 'file_size', 'type', 'modified']

            # Reset each column to its default width
            for i, column_key in enumerate(visible_columns):
                column_index = i + 1  # +1 because column 0 is status column
                column_config = FILE_TABLE_COLUMN_CONFIG.get(column_key, {})
                default_width = column_config.get('width', 100)

                self.setColumnWidth(column_index, default_width)

                # Schedule save for delayed updates
                self._schedule_column_save(column_key, default_width)

            logger.info(f"Reset {len(visible_columns)} columns to default widths")

        except Exception as e:
            logger.error(f"Error resetting columns to default: {e}")

    def _auto_fit_columns_to_content(self) -> None:
        """Auto-fit all column widths to their content (Ctrl+Shift+T)."""
        try:
            from config import FILE_TABLE_COLUMN_CONFIG, GLOBAL_MIN_COLUMN_WIDTH

            if not self.model() or self.model().rowCount() == 0:
                logger.warning("Cannot auto-fit columns: no data available")
                return

            # Get visible columns from model
            visible_columns = []
            if hasattr(self.model(), 'get_visible_columns'):
                visible_columns = self.model().get_visible_columns()
            else:
                visible_columns = ['filename', 'file_size', 'type', 'modified']

            header = self.horizontalHeader()
            if not header:
                return

            # Auto-fit each column to its content
            for i, column_key in enumerate(visible_columns):
                column_index = i + 1  # +1 because column 0 is status column
                column_config = FILE_TABLE_COLUMN_CONFIG.get(column_key, {})

                # Use Qt's built-in resize to contents
                header.resizeSection(column_index, header.sectionSizeHint(column_index))

                # Apply minimum width constraint
                min_width = max(column_config.get('min_width', GLOBAL_MIN_COLUMN_WIDTH), GLOBAL_MIN_COLUMN_WIDTH)
                current_width = self.columnWidth(column_index)
                final_width = max(current_width, min_width)

                if final_width != current_width:
                    self.setColumnWidth(column_index, final_width)

                # Schedule save for delayed updates
                self._schedule_column_save(column_key, final_width)

            logger.info(f"Auto-fitted {len(visible_columns)} columns to content")

        except Exception as e:
            logger.error(f"Error auto-fitting columns to content: {e}")

    def refresh_columns_after_model_change(self) -> None:
        """
        Public slot to reconfigure columns after the model's data changes (e.g. after set_files).
        This ensures that columns, headers, and resize modes are always correct.
        """
        logger.debug("refresh_columns_after_model_change: Starting column reconfiguration")

        # Add a small delay to ensure model is fully ready
        def delayed_configure():
            logger.debug("refresh_columns_after_model_change: Delayed column configuration")
            self._configure_columns()
            logger.debug("refresh_columns_after_model_change: Column reconfiguration finished")

            # Auto-update placeholder visibility after column configuration
            self._auto_update_placeholder_visibility()

            self.viewport().update()

        # Use a timer to delay the configuration
        QTimer.singleShot(50, delayed_configure)

    def _check_and_fix_column_widths(self) -> None:
        """Check if column widths need to be reset due to incorrect saved values."""
        try:
            from config import FILE_TABLE_COLUMN_CONFIG

            # Get current saved widths
            main_window = self._get_main_window()
            saved_widths = {}

            if main_window and hasattr(main_window, 'window_config_manager'):
                config_manager = main_window.window_config_manager.config_manager
                window_config = config_manager.get_category('window')
                saved_widths = window_config.get('file_table_column_widths', {})

            if not saved_widths:
                # Try fallback method
                from utils.json_config_manager import load_config
                config = load_config()
                saved_widths = config.get("file_table_column_widths", {})

            # Check if most columns are set to 100px (suspicious)
            suspicious_count = 0
            total_count = 0

            for column_key, column_config in FILE_TABLE_COLUMN_CONFIG.items():
                if column_config.get("default_visible", False):  # Only check visible columns
                    total_count += 1
                    default_width = column_config.get("width", 100)
                    saved_width = saved_widths.get(column_key, default_width)

                    # If saved width is 100px but default is different, it's suspicious
                    if saved_width == 100 and default_width != 100:
                        suspicious_count += 1

            # If most visible columns have suspicious widths, reset them
            if total_count > 0 and suspicious_count >= (total_count * 0.5):  # 50% threshold
                logger.info(f"Found {suspicious_count}/{total_count} columns with suspicious widths, resetting to defaults")
                self._reset_column_widths_to_defaults()

        except Exception as e:
            logger.error(f"Failed to check column widths: {e}")
