'''
file_table_view.py

Author: Michael Economou
Date: 2025-05-25

Custom QTableView with Windows Explorer-like behavior:
- Full-row selection with anchor handling
- Intelligent column width management
- Drag & drop support with custom MIME types
- Hover highlighting and visual feedback
'''
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import (
    QItemSelection,
    QItemSelectionModel,
    QMimeData,
    QModelIndex,
    QPoint,
    QRect,
    Qt,
    QTimer,
    QUrl,
    pyqtSignal,
    QEvent,
)
from PyQt5.QtGui import QCursor, QDrag, QDropEvent, QKeySequence, QMouseEvent, QPixmap, QPainter, QPen, QBrush, QColor
from PyQt5.QtWidgets import QAbstractItemView, QApplication, QHeaderView, QLabel, QTableView

from config import FILE_TABLE_COLUMN_WIDTHS
from core.application_context import get_app_context
from core.drag_manager import DragManager
from core.drag_visual_manager import (
    DragVisualManager, DragType, DropZoneState, ModifierState,
    start_drag_visual, end_drag_visual, update_drop_zone_state,
    update_modifier_state, is_valid_drop_target
)
from utils.file_drop_helper import extract_file_paths
from utils.logger_factory import get_cached_logger
from utils.timer_manager import schedule_resize_adjust, schedule_drag_cleanup, schedule_selection_update

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
    - Intelligent column width management
    - Drag & drop support with custom MIME types
    - Hover highlighting and visual feedback
    - Automatic placeholder management
    """

    selection_changed = pyqtSignal(list)  # Emitted with list[int] of selected rows
    files_dropped = pyqtSignal(list, object)  # Emitted with list of dropped paths and keyboard modifiers

    def __init__(self, parent=None) -> None:
        """Initialize the custom table view with Explorer-like behavior."""
        super().__init__(parent)
        self._manual_anchor_index: Optional[QModelIndex] = None
        self._drag_start_pos: Optional[QPoint] = None  # Initialize as None instead of empty QPoint
        self._active_drag = None  # Store active QDrag object for cleanup
        self._filename_min_width: int = 250  # Will be updated in _configure_columns
        self._user_preferred_width: Optional[int] = None  # User's preferred filename column width
        self._programmatic_resize: bool = False  # Flag to indicate programmatic resize in progress

        # Vertical scrollbar tracking for filename column adjustment
        self._vertical_scrollbar_visible: bool = False
        self._filename_base_width: int = 0  # Store the base width before scrollbar adjustment
        self._scrollbar_adjustment: int = 12  # How much to reduce filename column when scrollbar appears

        # Configure table behavior
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setDragEnabled(False)  # Disable Qt's built-in drag for custom implementation
        self.setDragDropMode(QAbstractItemView.DropOnly)  # Only accept drops, no built-in drags
        self.setMouseTracking(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True) # type: ignore

        # Note: QTableView in PyQt5 doesn't have setRubberBandSelectionMode
        # We'll implement custom lasso selection with Ctrl+drag

        # Custom drag state tracking
        self._is_dragging = False
        self._drag_data = None  # Store selected file data for drag

        # Selection preservation for drag operations
        self._preserve_selection_for_drag = False
        self._clicked_on_selected = False
        self._clicked_index = None
        self._ignore_selection_changes = False  # Flag to ignore selection changes during drag/drop

        # Setup placeholder icon
        self.placeholder_label = QLabel(self.viewport())
        self.placeholder_label.setAlignment(Qt.AlignCenter) # type: ignore
        self.placeholder_label.setVisible(False)

        icon_path = Path(__file__).parent.parent / "resources/images/File_table_placeholder.png"
        self.placeholder_icon = QPixmap(str(icon_path))

        if not self.placeholder_icon.isNull():
            scaled = self.placeholder_icon.scaled(
                PLACEHOLDER_ICON_SIZE, PLACEHOLDER_ICON_SIZE,
                Qt.KeepAspectRatio, Qt.SmoothTransformation # type: ignore
            )
            self.placeholder_label.setPixmap(scaled)
        else:
            logger.warning("Placeholder icon could not be loaded.")

        # Selection and interaction state
        self.selected_rows: set[int] = set()
        self.anchor_row: Optional[int] = None
        self.context_focused_row: Optional[int] = None

        # Enable hover visuals
        self.hover_delegate = HoverItemDelegate(self)
        self.setItemDelegate(self.hover_delegate)

        # Selection store integration (with fallback to legacy selection handling)
        self._legacy_selection_mode = True  # Start in legacy mode for compatibility

    def paintEvent(self, event):
        """Paint the table."""
        # Paint the normal table
        super().paintEvent(event)

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
            # Use a small delay to batch multiple rapid selection changes
            if not hasattr(self, '_selection_emit_timer'):
                self._selection_emit_timer = QTimer()
                self._selection_emit_timer.setSingleShot(True)
                self._selection_emit_timer.timeout.connect(lambda: self.selection_changed.emit(list(self.selected_rows)))
            self._selection_emit_timer.stop()
            self._selection_emit_timer.start(10)  # 10ms delay to batch rapid changes

    def _sync_qt_selection_model(self, selected_rows: set) -> None:
        """Ensure Qt selection model matches our internal selection state."""
        selection_model = self.selectionModel()
        if not selection_model or not self.model():
            return

        # Get current Qt selection
        current_qt_selection = set(index.row() for index in selection_model.selectedRows())

        # Only update if there's a significant difference (avoid unnecessary updates)
        if current_qt_selection != selected_rows:
            logger.debug(f"[FileTableView] Syncing Qt selection: {len(current_qt_selection)} -> {len(selected_rows)} files", extra={"dev_only": True})

            # Block signals to prevent recursive calls
            self.blockSignals(True)
            try:
                # Clear current selection
                selection_model.clearSelection()

                # Select the new rows
                if selected_rows:
                    from PyQt5.QtCore import QItemSelection
                    full_selection = QItemSelection()

                    for row in selected_rows:
                        if 0 <= row < self.model().rowCount(): # type: ignore
                            left_index = self.model().index(row, 0) # type: ignore
                            right_index = self.model().index(row, self.model().columnCount() - 1) # type: ignore
                            if left_index.isValid() and right_index.isValid():
                                row_selection = QItemSelection(left_index, right_index)
                                full_selection.merge(row_selection, selection_model.Select) # type: ignore

                    if not full_selection.isEmpty():
                        selection_model.select(full_selection, selection_model.Select) # type: ignore

                # Force visual update
                self.viewport().update() # type: ignore

            finally:
                self.blockSignals(False)

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
        """Get current selection safely without triggering updates during drag operations."""
        # During drag operations, use preserved selection if available
        if hasattr(self, '_drag_start_selection') and isinstance(self._drag_start_selection, set):
            return self._drag_start_selection
        else:
            return self._get_current_selection()

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
        """Handle resize events and update placeholder position."""
        super().resizeEvent(event)
        if self.placeholder_label:
            self.placeholder_label.resize(self.viewport().size())
            self.placeholder_label.move(0, 0)

        # Check if vertical scrollbar visibility changed after resize
        # Use a small delay to ensure scrollbar state is updated
        schedule_resize_adjust(self._check_vertical_scrollbar_visibility, 10)

    def setModel(self, model) -> None:
        """Configure columns when model is set."""
        super().setModel(model)
        if model:
            schedule_resize_adjust(self._configure_columns, 10)

    # =====================================
    # Table Preparation & Management
    # =====================================

    def prepare_table(self, file_items: list) -> None:
        """
        Prepare the table view with the given file items.

        This method handles:
        - Clearing selection and resetting state
        - Setting files in the model
        - Reconfiguring columns after model reset
        - Updating delegates and UI elements
        - Managing scrollbar visibility

        Args:
            file_items: List of FileItem objects to display in the table
        """
        # Reset manual column preferences when loading new files
        self._has_manual_preference = False
        self._user_preferred_width = FILE_TABLE_COLUMN_WIDTHS["FILENAME_COLUMN"]

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
        if self.model() and hasattr(self.model(), 'set_files'):
            self.model().set_files(file_items)

        # Reconfigure columns after model reset
        self._configure_columns()

        # Reset hover delegate state
        if hasattr(self, 'hover_delegate'):
            self.setItemDelegate(self.hover_delegate)
            self.hover_delegate.hovered_row = -1

        # Update UI
        self.viewport().update()
        self._update_scrollbar_visibility()

        # Check vertical scrollbar visibility and adjust filename column if needed
        # Use a timer to ensure the scrollbar visibility is properly updated after model reset
        schedule_resize_adjust(self._check_vertical_scrollbar_visibility, 50)

    # =====================================
    # Column Management & Scrollbar Optimization
    # =====================================

    def _configure_columns(self) -> None:
        """Configure column settings and initial widths from config."""
        if not self.model():
            return

        header = self.horizontalHeader()
        if not header:
            return

        # Try to get fontMetrics from ApplicationContext, fallback to parent traversal
        font_metrics = None
        try:
            get_app_context()
            # Try to get main window through context for font metrics
            # This is a transitional approach until we fully migrate font handling
            parent_window = self.parent()
            while parent_window and not hasattr(parent_window, 'fontMetrics'):
                parent_window = parent_window.parent()

            if parent_window:
                font_metrics = parent_window.fontMetrics()
            else:
                logger.warning("[FileTableView] Cannot find parent window with fontMetrics", extra={"dev_only": True})
                return
        except RuntimeError:
            # ApplicationContext not ready yet, use legacy approach
            parent_window = self.parent()
            while parent_window and not hasattr(parent_window, 'fontMetrics'):
                parent_window = parent_window.parent()

            if not parent_window:
                logger.warning("[FileTableView] Cannot find parent window with fontMetrics", extra={"dev_only": True})
                return

            font_metrics = parent_window.fontMetrics()

        # Configure each column with config values and calculated minimums
        status_width = FILE_TABLE_COLUMN_WIDTHS["STATUS_COLUMN"]
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.setColumnWidth(0, status_width)

        # Filename column - Interactive with minimum width protection
        filename_min = font_metrics.horizontalAdvance("Long_Filename_Example_2024.jpeg") + 30
        filename_width = max(FILE_TABLE_COLUMN_WIDTHS["FILENAME_COLUMN"], filename_min, 250)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        self.setColumnWidth(1, filename_width)

        # File size column - Fixed width, cannot be resized
        filesize_width = FILE_TABLE_COLUMN_WIDTHS["FILESIZE_COLUMN"]
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        self.setColumnWidth(2, filesize_width)

        # Extension column - Fixed width, cannot be resized
        extension_width = FILE_TABLE_COLUMN_WIDTHS["EXTENSION_COLUMN"]
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        self.setColumnWidth(3, extension_width)

        # Date column - Fixed width, cannot be resized
        datetime_width = FILE_TABLE_COLUMN_WIDTHS["DATE_COLUMN"]
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        self.setColumnWidth(4, datetime_width)

        # Apply general minimum size to header (for all columns)
        header.setMinimumSectionSize(20)

        # Store minimum width for filename column enforcement (allow reduction for scrollbar)
        # Set minimum to be smaller than initial width to allow scrollbar adjustment
        self._filename_min_width = max(filename_min, 333)  # Use calculated minimum or 333px, whichever is larger

        # Initialize user preferred width to the initial width
        self._user_preferred_width = filename_width
        self._has_manual_preference = False  # Track if user has manually resized

        # Connect signal to enforce filename column minimum width
        header.sectionResized.connect(self._on_filename_resized)

    def _on_filename_resized(self, logical_index: int, old_size: int, new_size: int) -> None:
        """Enforce minimum width and track manual user preferences for filename column (column 1)."""
        if logical_index == 1 and hasattr(self, '_filename_min_width'):
            # Always enforce minimum width
            if new_size < self._filename_min_width:
                self.setColumnWidth(1, self._filename_min_width)
                return

            # Track manual user preference only if this is NOT a programmatic resize
            if not getattr(self, '_programmatic_resize', False):
                self._user_preferred_width = new_size
                self._has_manual_preference = True

    def _update_scrollbar_visibility(self) -> None:
        """Update scrollbar visibility based on table content with anti-flickering."""
        model = self.model()
        if not model:
            return

        is_empty = (model.rowCount() == 0)
        current_policy = self.horizontalScrollBarPolicy()

        # Only change policy if different to prevent unnecessary updates
        if is_empty and current_policy != Qt.ScrollBarAlwaysOff:
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        elif not is_empty and current_policy != Qt.ScrollBarAsNeeded:
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    def _check_vertical_scrollbar_visibility(self) -> None:
        """Check if vertical scrollbar is needed and adjust filename column accordingly."""
        if not self.model():
            return

        # Check if vertical scrollbar is needed by comparing content height with viewport height
        model = self.model()
        row_count = model.rowCount()

        if row_count == 0:
            return

        # Calculate if scrollbar is needed
        viewport_height = self.viewport().height()
        row_height = self.rowHeight(0) if row_count > 0 else 25  # fallback height
        total_content_height = row_count * row_height
        header_height = self.horizontalHeader().height() if self.horizontalHeader() else 0

        # Add some margin for safety
        is_scrollbar_needed = (total_content_height + header_height) > viewport_height

        # Also check the actual scrollbar visibility as backup
        vertical_scrollbar = self.verticalScrollBar()
        is_actually_visible = vertical_scrollbar.isVisible()

        # Use the calculated need or actual visibility (whichever indicates scrollbar is needed)
        is_visible = is_scrollbar_needed or is_actually_visible

        # Only proceed if visibility state has changed
        if is_visible == self._vertical_scrollbar_visible:
            return

        self._vertical_scrollbar_visible = is_visible

        # Get current filename column width
        current_width = self.columnWidth(1)

        if is_visible:
            # Scrollbar needed - reduce filename column by adjustment amount
            if self._filename_base_width == 0:
                # Store the current width as base width
                self._filename_base_width = current_width

            new_width = max(self._filename_base_width - self._scrollbar_adjustment, self._filename_min_width)

            if new_width != current_width:
                self._programmatic_resize = True
                self.setColumnWidth(1, new_width)
                self._programmatic_resize = False
                logger.debug(f"[FileTableView] Vertical scrollbar appeared - reduced filename column: {current_width}px → {new_width}px", extra={"dev_only": True})
        else:
            # Scrollbar not needed - restore filename column to base width
            if self._filename_base_width > 0:
                new_width = max(self._filename_base_width, self._filename_min_width)

                if new_width != current_width:
                    self._programmatic_resize = True
                    self.setColumnWidth(1, new_width)
                    self._programmatic_resize = False
                    logger.debug(f"[FileTableView] Vertical scrollbar disappeared - restored filename column: {current_width}px → {new_width}px", extra={"dev_only": True})

                # Reset base width for next cycle
                self._filename_base_width = 0

    def on_horizontal_splitter_moved(self, pos: int, index: int) -> None:
        """Handle horizontal splitter movement - use user preference as base, expand if more space available."""
        # Try to get splitter from ApplicationContext, fallback to parent traversal
        horizontal_splitter = None
        try:
            get_app_context()
            # Try to get main window through context for splitter access
            # This is a transitional approach until we fully migrate splitter handling
            parent_window = self.parent()
            while parent_window and not hasattr(parent_window, 'horizontal_splitter'):
                parent_window = parent_window.parent()

            if parent_window:
                horizontal_splitter = parent_window.horizontal_splitter
            else:
                return
        except RuntimeError:
            # ApplicationContext not ready yet, use legacy approach
            parent_window = self.parent()
            while parent_window and not hasattr(parent_window, 'horizontal_splitter'):
                parent_window = parent_window.parent()

            if not parent_window:
                return

            horizontal_splitter = parent_window.horizontal_splitter

        sizes = horizontal_splitter.sizes()
        center_panel_width = sizes[1]

        if center_panel_width > 0 and hasattr(self, '_filename_min_width'):
            # Calculate available width for filename column
            other_columns_width = (self.columnWidth(0) + self.columnWidth(2) +
                                  self.columnWidth(3) + self.columnWidth(4))
            available_width = center_panel_width - other_columns_width - SCROLLBAR_MARGIN

            current_filename_width = self.columnWidth(1)

            # Simple logic: Check if user has manually resized the column
            if getattr(self, '_has_manual_preference', False):
                # User has manually resized - use their preferred width, but expand to fill space if needed
                target_width = max(self._user_preferred_width, self._filename_min_width)
                if available_width > target_width:
                    # Expand to fill available space
                    new_filename_width = available_width
                else:
                    # Use their preferred width (or minimum if space is constrained)
                    new_filename_width = max(target_width, self._filename_min_width)
            else:
                # No manual preference - just fill available space
                new_filename_width = max(self._filename_min_width, available_width)

            # Only resize if there's a meaningful difference (avoid micro-adjustments)
            size_difference = abs(new_filename_width - current_filename_width)
            should_resize = size_difference > 5  # Much smaller threshold for smoother behavior

            if should_resize:
                # Use batch updates to prevent scrollbar flickering during column resize
                self.setUpdatesEnabled(False)

                try:
                    # Set flag to indicate this is a programmatic resize
                    self._programmatic_resize = True
                    self.setColumnWidth(1, new_filename_width)
                    self._programmatic_resize = False

                    # Update scrollbar visibility intelligently after column resize
                    self._update_scrollbar_visibility()

                    logger.debug(f"[FileTableView] Column resized with anti-flickering: {current_filename_width}px → {new_filename_width}px", extra={"dev_only": True})

                finally:
                    # Re-enable updates and force a single refresh
                    self.setUpdatesEnabled(True)
                    self.viewport().update()

                    # Check if vertical scrollbar visibility changed after column resize
                    schedule_resize_adjust(self._check_vertical_scrollbar_visibility, 10)

    def on_vertical_splitter_moved(self, pos: int, index: int) -> None:
        """Handle vertical splitter movement."""
        pass  # Reserved for future use

    # =====================================
    # UI Methods
    # =====================================

    def set_placeholder_visible(self, visible: bool) -> None:
        """Show or hide the placeholder icon and configure table state."""
        assert self.model() is not None, "Model must be set before showing placeholder"

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

        else:
            # Use batch updates to prevent flickering when re-enabling content
            self.setUpdatesEnabled(False)

            try:
                self.placeholder_label.hide()

                # Re-enable scrollbar policy based on content
                self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                logger.debug("[FileTableView] Placeholder hidden - content mode restored with anti-flickering", extra={"dev_only": True})

                # Re-enable interactions when hiding placeholder
                header = self.horizontalHeader()
                if header:
                    header.setEnabled(True)
                    header.setSectionsClickable(True)
                    header.setSortIndicatorShown(True)

                self.setSelectionMode(QAbstractItemView.ExtendedSelection)
                self.setContextMenuPolicy(Qt.CustomContextMenu)

            finally:
                # Re-enable updates and force a single refresh
                self.setUpdatesEnabled(True)
                self.viewport().update()

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
                    selection_store.set_anchor_row(self._manual_anchor_index.row(), emit_signal=False)

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

            # CRITICAL: Store current selection BEFORE any changes for potential drag
            # This ensures we have the correct selection even if Qt changes it
            self._drag_start_selection = self._get_current_selection().copy()
            logger.debug(f"[FileTableView] Preserved selection for potential drag: {len(self._drag_start_selection)} files", extra={"dev_only": True})

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
                    # Don't change selection yet - might be starting a drag
                    self._preserve_selection_for_drag = True
                    self._clicked_on_selected = True
                    logger.debug(f"[FileTableView] Preserving multi-selection for potential drag: {len(current_selection)} files", extra={"dev_only": True})
                    # IMPORTANT: Still call super() to allow Qt to process the event
                    super().mousePressEvent(event)
                    return
                else:
                    # Single click - select single row
                    self._set_anchor_row(index.row())
                    self._update_selection_store({index.row()})
                    logger.debug(f"[FileTableView] Single selection: row {index.row()}", extra={"dev_only": True})
            elif modifiers == Qt.ControlModifier:
                # Check if we're on a selected item for potential drag
                current_selection = self._get_current_selection()
                if index.row() in current_selection:
                    # Don't change selection yet - might be starting a drag
                    self._preserve_selection_for_drag = True
                    self._clicked_on_selected = True
                    logger.debug(f"[FileTableView] Preserving Ctrl-selection for potential drag: {len(current_selection)} files", extra={"dev_only": True})
                    # CRITICAL: Call super() to allow Qt to process the event
                    super().mousePressEvent(event)
                    return
                else:
                    # Ctrl+click on unselected - add to selection (toggle)
                    current_selection = current_selection.copy()  # Make a copy to avoid modifying the original
                    current_selection.add(index.row())
                    self._set_anchor_row(index.row())  # Set anchor for future range selections
                    self._update_selection_store(current_selection)
                    logger.debug(f"[FileTableView] Ctrl+click toggle: added row {index.row()}, total: {len(current_selection)}", extra={"dev_only": True})
                    # Don't call super() - we handled the selection ourselves
                    return
            elif modifiers == Qt.ShiftModifier:
                # Check if we're clicking on a selected item for potential drag
                current_selection = self._get_current_selection()
                if index.row() in current_selection:
                    # Clicking on already selected item with Shift - preserve selection for drag
                    # This prevents Shift+drag from changing selection
                    self._preserve_selection_for_drag = True
                    self._clicked_on_selected = True
                    logger.debug(f"[FileTableView] Preserving Shift-selection for potential drag: {len(current_selection)} files", extra={"dev_only": True})
                    # IMPORTANT: Don't call super() and don't change selection
                    # This prevents Shift+Click from changing selection when starting a drag
                    return
                else:
                    # Shift+click on unselected item - select range
                    anchor = self._get_anchor_row()
                    if anchor is not None:
                        self.select_rows_range(anchor, index.row())
                        logger.debug(f"[FileTableView] Shift+click range: {anchor} to {index.row()}", extra={"dev_only": True})
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
            selection_model.select(index, QItemSelectionModel.Clear | QItemSelectionModel.Select | QItemSelectionModel.Rows)
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
            while parent_window and not hasattr(parent_window, 'handle_file_double_click'):
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
            if (getattr(self, '_preserve_selection_for_drag', False) and
                    not self._is_dragging and
                    hasattr(self, '_clicked_on_selected') and self._clicked_on_selected):

                modifiers = QApplication.keyboardModifiers()
                if modifiers == Qt.ControlModifier:
                    # Ctrl+click on selected item without drag - toggle selection (remove)
                    if hasattr(self, '_clicked_index') and self._clicked_index and self._clicked_index.isValid():
                        current_selection = self._get_current_selection().copy()
                        row = self._clicked_index.row()
                        if row in current_selection:
                            current_selection.remove(row)
                            # Update anchor to another selected item if available
                            if current_selection:
                                self._set_anchor_row(max(current_selection))  # Use highest row as new anchor
                            else:
                                self._set_anchor_row(None)  # No selection left
                            self._update_selection_store(current_selection)
                            logger.debug(f"[FileTableView] Ctrl+click toggle: removed row {row}, remaining: {len(current_selection)}", extra={"dev_only": True})
                elif modifiers == Qt.ShiftModifier:
                    # Shift+click on selected item without drag - preserve current selection
                    # Don't change selection when Shift is held and we clicked on a selected item
                    logger.debug(f"[FileTableView] Shift+click on selected item without drag - preserving selection", extra={"dev_only": True})
                elif modifiers == Qt.NoModifier:
                    # Regular click on selected item without drag - clear selection and select only this
                    if hasattr(self, '_clicked_index') and self._clicked_index and self._clicked_index.isValid():
                        row = self._clicked_index.row()
                        # Clear selection and select only the clicked item
                        self._set_anchor_row(row)
                        self._update_selection_store({row})

            # Clean up flags
            self._preserve_selection_for_drag = False
            self._clicked_on_selected = False
            if hasattr(self, '_clicked_index'):
                self._clicked_index = None

            # Reset drag start position
            self._drag_start_pos = None

            # If we were dragging, clean up
            if self._is_dragging:
                self._end_custom_drag()

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
        if (event.buttons() & Qt.LeftButton and self._drag_start_pos is not None):
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

        # Handle real-time drag feedback if dragging
        if self._is_dragging:
            self._update_drag_feedback()
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
        # Don't handle ESC at all - let it pass through to dialogs and other components
        # Cursor cleanup is handled automatically by other mechanisms

        # Update drag feedback if we're currently dragging
        if self._is_dragging:
            self._update_drag_feedback()

        super().keyPressEvent(event)
        if event.matches(QKeySequence.SelectAll) or event.key() in (
            Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter,
            Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right
        ):
            self._sync_selection_safely()

    def keyReleaseEvent(self, event) -> None:
        """Handle key release events, including modifier changes during drag."""
        # Update drag feedback if we're currently dragging
        if self._is_dragging:
            self._update_drag_feedback()

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
        self._ignore_selection_changes = False  # Ensure flag is clear at drag start

        # Get selected file data using safe method
        selected_rows = self._get_current_selection_safe()
        logger.debug(f"[FileTableView] Using selection for drag: {len(selected_rows)} files", extra={"dev_only": True})

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
        if hasattr(self, 'hover_delegate'):
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

        logger.debug(f"[FileTableView] Custom drag started with visual feedback: {len(file_paths)} files (type: {drag_type.value})", extra={"dev_only": True})

    def _update_drag_feedback(self):
        """Update visual feedback based on current cursor position during drag"""
        if not self._is_dragging:
            return

        # Update modifier state first (for Ctrl/Shift changes during drag)
        update_modifier_state()

        # Get widget under cursor
        widget_under_cursor = QApplication.widgetAt(QCursor.pos())
        if not widget_under_cursor:
            # Cursor is outside application window - terminate drag
            logger.debug("[FileTableView] Cursor outside application - terminating drag", extra={"dev_only": True})
            self._end_custom_drag()
            return

        # Use the improved drop target detection from DragVisualManager
        visual_manager = DragVisualManager.get_instance()

        # Check if current position is a valid drop target (walks up parent hierarchy automatically)
        if visual_manager.is_valid_drop_target(widget_under_cursor, "file_table"):
            update_drop_zone_state(DropZoneState.VALID)
            logger.debug(f"[FileTableView] Valid drop zone detected: {widget_under_cursor.__class__.__name__}", extra={"dev_only": True})
        else:
            # Check for explicit invalid targets (policy violations)
            current_widget = widget_under_cursor
            invalid_found = False

            while current_widget and not invalid_found:
                widget_class = current_widget.__class__.__name__
                if widget_class in ['FileTreeView', 'FileTableView']:
                    update_drop_zone_state(DropZoneState.INVALID)
                    invalid_found = True
                    logger.debug(f"[FileTableView] Invalid drop zone: {widget_class}", extra={"dev_only": True})
                    break
                current_widget = current_widget.parent()

            # If no specific invalid target found, neutral state
            if not invalid_found:
                update_drop_zone_state(DropZoneState.NEUTRAL)

    def _end_custom_drag(self):
        """End our custom drag operation with enhanced visual feedback"""
        if not self._is_dragging:
            return

        # CRITICAL: Store current selection IMMEDIATELY before any cleanup
        # This must be the FIRST thing we do to avoid race conditions
        preserved_selection = None
        if hasattr(self, '_drag_start_selection') and isinstance(self._drag_start_selection, set):
            preserved_selection = self._drag_start_selection.copy()
            logger.debug(f"[FileTableView] Preserving drag start selection: {len(preserved_selection)} files", extra={"dev_only": True})
        else:
            # Fallback: try current selection (might be empty due to timing)
            current_selection = self._get_current_selection()
            if current_selection:
                preserved_selection = current_selection.copy()
                logger.debug(f"[FileTableView] Preserving current selection: {len(preserved_selection)} files", extra={"dev_only": True})

        # Force immediate cursor cleanup
        self._force_cursor_cleanup()

        # Check if drag has been cancelled by external force cleanup
        drag_manager = DragManager.get_instance()
        if not drag_manager.is_drag_active():
            logger.debug("[FileTableView] Drag was cancelled, skipping drop", extra={"dev_only": True})
            # Clean up drag state without performing drop
            self._is_dragging = False
            self._drag_data = None

            # Clear the preserved drag selection
            if hasattr(self, '_drag_start_selection'):
                self._drag_start_selection = None

            # Cleanup visual feedback
            end_drag_visual()
            drag_manager.end_drag("file_table")

            # Restore selection that was preserved IMMEDIATELY
            if preserved_selection:
                logger.debug(f"[FileTableView] Restoring selection after cancelled drag: {len(preserved_selection)} files", extra={"dev_only": True})
                self._restore_selection_immediately(preserved_selection)

            return

        logger.debug("[FileTableView] Ending custom drag operation", extra={"dev_only": True})

        # Get widget under cursor for drop detection
        cursor_pos = QCursor.pos()
        widget_under_cursor = QApplication.widgetAt(cursor_pos)

        dropped_successfully = False

        if widget_under_cursor:
            # Walk up parent hierarchy to find drop targets
            parent = widget_under_cursor
            while parent and not dropped_successfully:
                if parent.__class__.__name__ == 'MetadataTreeView':
                    dropped_successfully = self._handle_drop_on_metadata_tree()
                    break
                parent = parent.parent()

        # Clean up drag state
        self._is_dragging = False
        self._drag_data = None

        # Clear the preserved drag selection
        if hasattr(self, '_drag_start_selection'):
            self._drag_start_selection = None

        # Cleanup visual feedback
        end_drag_visual()

        # Notify DragManager
        drag_manager.end_drag("file_table")

        # CRITICAL: Restore selection after all cleanup is done
        if preserved_selection:
            # Use immediate restoration instead of timer to avoid race conditions
            self._restore_selection_immediately(preserved_selection)

        # Force cleanup any remaining visual artifacts
        schedule_drag_cleanup(self._restore_hover_after_drag, 10)

        logger.debug("[FileTableView] Custom drag operation completed", extra={"dev_only": True})

    def _restore_selection_immediately(self, preserved_selection: set):
        """Restore selection immediately without timers to avoid race conditions"""
        if not preserved_selection:
            logger.debug("[FileTableView] No selection to restore", extra={"dev_only": True})
            return

        logger.debug(f"[FileTableView] Immediate selection restore: {len(preserved_selection)} files", extra={"dev_only": True})

        # Update our internal state first
        self.selected_rows = preserved_selection.copy()

        # Update SelectionStore
        selection_store = self._get_selection_store()
        if selection_store and not self._legacy_selection_mode:
            selection_store.set_selected_rows(preserved_selection, emit_signal=False)  # Don't emit to avoid loops

        # Update Qt selection model immediately
        self._restore_qt_selection(preserved_selection)

        # Emit our signal after everything is synchronized
        self.selection_changed.emit(list(preserved_selection))

        # Force viewport update to show selection
        self.viewport().update()

        logger.debug(f"[FileTableView] Selection restored immediately: {len(preserved_selection)} files", extra={"dev_only": True})

        # Clear the ignore flag after restoration is complete
        self._ignore_selection_changes = False
        logger.debug("[FileTableView] Cleared ignore_selection_changes flag after restoration", extra={"dev_only": True})

    def _restore_qt_selection(self, preserved_selection: set):
        """Restore Qt selection model to match preserved selection"""
        selection_model = self.selectionModel()
        if not selection_model or not self.model():
            return

        # Block signals to prevent recursive calls during restoration
        self.blockSignals(True)
        try:
            # Clear current selection first
            selection_model.clearSelection()

            # Select each preserved row
            if preserved_selection:
                from PyQt5.QtCore import QItemSelection
                full_selection = QItemSelection()

                for row in preserved_selection:
                    if 0 <= row < self.model().rowCount():
                        left_index = self.model().index(row, 0)
                        right_index = self.model().index(row, self.model().columnCount() - 1)
                        if left_index.isValid() and right_index.isValid():
                            row_selection = QItemSelection(left_index, right_index)
                            full_selection.merge(row_selection, selection_model.Select)

                if not full_selection.isEmpty():
                    selection_model.select(full_selection, selection_model.Select)

            logger.debug(f"[FileTableView] Qt selection model updated with {len(preserved_selection)} rows", extra={"dev_only": True})
        finally:
            self.blockSignals(False)

    def _restore_hover_after_drag(self):
        """Restore hover state after drag ends by sending a fake mouse move event"""
        if not hasattr(self, 'hover_delegate'):
            return

        # Get current cursor position relative to this widget
        global_pos = QCursor.pos()
        local_pos = self.mapFromGlobal(global_pos)

        # Only restore hover if cursor is still over this widget
        if self.rect().contains(local_pos):
            # Create and post a fake mouse move event
            fake_move_event = QMouseEvent(
                QEvent.MouseMove,
                local_pos,
                Qt.NoButton,
                Qt.NoButton,
                Qt.NoModifier
            )
            QApplication.postEvent(self, fake_move_event)

    def _handle_drop_on_metadata_tree(self):
        """Handle drop on metadata tree - send ALL SELECTED files, not just dragged files"""
        if not self._drag_data:
            logger.debug("[FileTableView] No drag data available for metadata tree drop", extra={"dev_only": True})
            return False

        # Enable flag to ignore selection changes during drop
        self._ignore_selection_changes = True
        logger.debug("[FileTableView] Enabled ignore_selection_changes flag for metadata drop", extra={"dev_only": True})

        # CRITICAL: Use preserved selection from drag start IMMEDIATELY
        # This must happen BEFORE any cleanup that might affect selection
        selected_file_paths = []

        if hasattr(self, '_drag_start_selection') and isinstance(self._drag_start_selection, set):
            selected_rows = self._drag_start_selection
            logger.debug(f"[FileTableView] Using preserved selection for metadata drop: {len(selected_rows)} files", extra={"dev_only": True})

            # Convert to file paths IMMEDIATELY before any cleanup
            try:
                file_items = [self.model().files[r] for r in selected_rows if 0 <= r < len(self.model().files)]
                selected_file_paths = [f.full_path for f in file_items if f.full_path]
                logger.debug(f"[FileTableView] Converted to {len(selected_file_paths)} file paths", extra={"dev_only": True})
            except (AttributeError, IndexError) as e:
                logger.error(f"[FileTableView] Error converting selection to paths: {e}")
                return False
        else:
            # Fallback: try to get current selection (though it might be lost)
            selected_rows = self._get_current_selection()
            logger.debug(f"[FileTableView] Fallback to current selection: {len(selected_rows)} files", extra={"dev_only": True})

            if selected_rows:
                try:
                    file_items = [self.model().files[r] for r in selected_rows if 0 <= r < len(self.model().files)]
                    selected_file_paths = [f.full_path for f in file_items if f.full_path]
                except (AttributeError, IndexError) as e:
                    logger.error(f"[FileTableView] Error converting fallback selection to paths: {e}")
                    return False

        if not selected_file_paths:
            logger.warning("[FileTableView] No valid file paths found for metadata tree drop")
            return False

        logger.debug(f"[FileTableView] Ready to emit signal with {len(selected_file_paths)} files", extra={"dev_only": True})

        # Store file paths for signal emission (before any cleanup)
        paths_to_emit = selected_file_paths.copy()

        # Get modifiers BEFORE cleanup (they might change)
        modifiers = QApplication.keyboardModifiers()

        # Force cursor cleanup AFTER we have everything we need
        self._force_cursor_cleanup()

        # Find metadata tree view and emit signal
        parent_window = self._get_parent_with_metadata_tree()
        if parent_window and hasattr(parent_window, 'metadata_tree_view'):
            metadata_tree = parent_window.metadata_tree_view

            logger.debug(f"[FileTableView] Emitting files_dropped signal with {len(paths_to_emit)} files", extra={"dev_only": True})
            # Emit the signal with the preserved file paths
            metadata_tree.files_dropped.emit(paths_to_emit, modifiers)

            # Force additional cleanup after signal emission
            QApplication.processEvents()  # Allow signal to be processed
            self._force_cursor_cleanup()  # Clean up any remaining cursor issues

            logger.debug("[FileTableView] Metadata tree drop completed successfully", extra={"dev_only": True})
            return True
        else:
            logger.warning("[FileTableView] Could not find metadata tree view for drop", extra={"dev_only": True})
            return False

    def _get_parent_with_metadata_tree(self):
        """Find parent window that has metadata_tree_view attribute"""
        parent = self.parent()
        while parent:
            if hasattr(parent, 'metadata_tree_view'):
                return parent
            parent = parent.parent()
        return None

    # =====================================
    # Drag & Drop Methods (Legacy - may remove)
    # =====================================

    def startDrag(self, supportedActions: Qt.DropActions) -> None:
        """Initiate drag operation for selected files."""
        selected_rows = self._get_current_selection()
        rows = sorted(selected_rows)
        if not rows:
            return

        file_items = [self.model().files[r] for r in rows if 0 <= r < len(self.model().files)]
        file_paths = [f.full_path for f in file_items if f.full_path]

        if not file_paths:
            return

        # Start drag operation with DragManager
        drag_manager = DragManager.get_instance()
        drag_manager.start_drag("file_table")

        # Setup drag cancel filter and PRESERVE CURRENT SELECTION
        from widgets.file_tree_view import _drag_cancel_filter
        _drag_cancel_filter.activate()
        # THIS IS THE KEY FIX: Preserve selection BEFORE drag starts
        _drag_cancel_filter.preserve_selection(selected_rows)

        logger.debug(f"[FileTableView] Starting drag with {len(selected_rows)} files selected", extra={"dev_only": True})

        # Create MIME data
        mime_data = QMimeData()
        mime_data.setData("application/x-oncutf-filetable", b"1")
        urls = [QUrl.fromLocalFile(p) for p in file_paths]
        mime_data.setUrls(urls)

        # Execute drag - store reference for cleanup
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        self._active_drag = drag

        try:
            result = drag.exec(Qt.CopyAction | Qt.MoveAction | Qt.LinkAction)
            logger.debug(f"[FileTable] Drag completed with result: {result}")
        except Exception as e:
            logger.error(f"Drag operation failed: {e}")
            result = Qt.IgnoreAction
        finally:
            # Immediate cleanup
            self._active_drag = None

            # End drag operation with DragManager
            drag_manager.end_drag("file_table")

            # Deactivate filter
            _drag_cancel_filter.deactivate()

            # Force cursor restoration
            while QApplication.overrideCursor():
                QApplication.restoreOverrideCursor()

            # Update UI immediately
            self.viewport().update()
            QApplication.processEvents()

        # Schedule aggressive cleanup with reasonable delay
        schedule_drag_cleanup(self._aggressive_drag_cleanup, 100)

    def _aggressive_drag_cleanup(self):
        """Aggressive post-drag cleanup to prevent ghost effects"""
        # Force DragManager cleanup
        drag_manager = DragManager.get_instance()
        if drag_manager.is_drag_active():
            logger.debug("[FileTable] Forcing DragManager cleanup in post-drag", extra={"dev_only": True})
            drag_manager.force_cleanup()

        # Reset drag state
        self._drag_start_pos = None
        if hasattr(self, '_active_drag'):
            self._active_drag = None

        # Force cursor cleanup again
        while QApplication.overrideCursor():
            QApplication.restoreOverrideCursor()

        # Deactivate filter if still active
        from widgets.file_tree_view import _drag_cancel_filter
        if _drag_cancel_filter._active:
            _drag_cancel_filter.deactivate()

        # Force UI update
        self.viewport().update()
        self.update()

        # Process events to clear any pending drag events
        QApplication.processEvents()

        # Send fake mouse release to self
        fake_event = QMouseEvent(
            QEvent.MouseButtonRelease,
            QPoint(0, 0),
            Qt.LeftButton,
            Qt.NoButton,
            Qt.NoModifier
        )
        QApplication.postEvent(self.viewport(), fake_event)

    def _final_drag_cleanup(self):
        """Final drag cleanup after event loop."""
        from widgets.file_tree_view import _drag_cancel_filter
        _drag_cancel_filter.deactivate()

        while QApplication.overrideCursor():
            QApplication.restoreOverrideCursor()

        if hasattr(self, 'viewport'):
            self.viewport().update()
        QApplication.processEvents()

        # Schedule more aggressive cleanup
        schedule_drag_cleanup(self._aggressive_drag_cleanup, 50)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasFormat("application/x-oncutf-internal"):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasFormat("application/x-oncutf-internal"):
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
        super().selectionChanged(selected, deselected)

        # Ignore selection changes during drag operations
        if self._ignore_selection_changes:
            logger.debug("[FileTableView] Ignoring selection change during drag/drop operation", extra={"dev_only": True})
            return

        selection_model = self.selectionModel()
        if selection_model is not None:
            selected_rows = set(index.row() for index in selection_model.selectedRows())

            # Avoid unnecessary updates if selection hasn't actually changed
            current_selection = self._get_current_selection()
            if selected_rows != current_selection:
                logger.debug(f"[FileTableView] Selection changed: {len(current_selection)} -> {len(selected_rows)}", extra={"dev_only": True})
                self._update_selection_store(selected_rows, emit_signal=True)
            else:
                logger.debug(f"[FileTableView] Selection unchanged: {len(selected_rows)} files", extra={"dev_only": True})

        if self.context_focused_row is not None:
            self.context_focused_row = None

        if hasattr(self, 'viewport'):
            self.viewport().update()

    def select_rows_range(self, start_row: int, end_row: int) -> None:
        """Select a range of rows efficiently."""
        self.blockSignals(True)
        selection_model = self.selectionModel()
        model = self.model()

        if selection_model is None or model is None:
            self.blockSignals(False)
            return

        if hasattr(model, 'index') and hasattr(model, 'columnCount'):
            # Ensure we always select from lower to higher row number
            min_row = min(start_row, end_row)
            max_row = max(start_row, end_row)
            top_left = model.index(min_row, 0)
            bottom_right = model.index(max_row, model.columnCount() - 1)
            selection = QItemSelection(top_left, bottom_right)
            selection_model.select(selection, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)  # type: ignore

        self.blockSignals(False)

        if hasattr(self, 'viewport'):
            self.viewport().update()  # type: ignore

        if model is not None:
            # Ensure we always create range from lower to higher
            min_row = min(start_row, end_row)
            max_row = max(start_row, end_row)
            selected_rows = set(range(min_row, max_row + 1))
            self._update_selection_store(selected_rows, emit_signal=True)

    def select_dropped_files(self, file_paths: Optional[list[str]] = None) -> None:
        """Select specific files that were just dropped/loaded in the table."""
        logger.warning(f"[FileTableView] *** SELECT_DROPPED_FILES CALLED with {len(file_paths) if file_paths else 0} paths ***")

        model = self.model()
        if not model or not hasattr(model, 'files'):
            logger.warning(f"[FileTableView] *** NO MODEL or model has no files attribute ***")
            return

        logger.warning(f"[FileTableView] *** MODEL OK, has {len(model.files)} files ***")

        if not file_paths:
            # Fallback: select all files if no specific paths provided
            row_count = len(model.files)
            if row_count == 0:
                logger.warning(f"[FileTableView] *** NO FILES IN MODEL - returning early ***")
                return
            logger.warning(f"[FileTableView] *** FALLBACK: Selecting all {row_count} files ***")
            self.select_rows_range(0, row_count - 1)
            return

        # Select specific files based on their paths
        rows_to_select = []
        logger.warning(f"[FileTableView] *** MATCHING {len(file_paths)} paths against {len(model.files)} files ***")

        for i, file_item in enumerate(model.files):
            if file_item.full_path in file_paths:
                logger.warning(f"[FileTableView] *** MATCH found at row {i}: {file_item.full_path} ***")
                rows_to_select.append(i)

        logger.warning(f"[FileTableView] *** FOUND {len(rows_to_select)} matching files: {rows_to_select} ***")

        if not rows_to_select:
            logger.warning(f"[FileTableView] *** NO MATCHING FILES FOUND - returning early ***")
            return

        logger.warning(f"[FileTableView] *** STARTING SELECTION PROCESS ***")

        # Clear existing selection first
        logger.warning(f"[FileTableView] *** CLEARING EXISTING SELECTION ***")
        self.clearSelection()

        # Select the specific rows ALL AT ONCE using range selection
        selection_model = self.selectionModel()
        if not selection_model:
            logger.warning(f"[FileTableView] *** NO SELECTION MODEL - returning early ***")
            return

        logger.warning(f"[FileTableView] *** BLOCKING SIGNALS ***")
        self.blockSignals(True)

        # Create a single selection for all rows
        from PyQt5.QtCore import QItemSelection
        full_selection = QItemSelection()
        logger.warning(f"[FileTableView] *** CREATED EMPTY SELECTION OBJECT ***")

        for row in rows_to_select:
            logger.warning(f"[FileTableView] *** PROCESSING ROW {row} ***")
            if 0 <= row < len(model.files):
                left_index = model.index(row, 0)
                right_index = model.index(row, model.columnCount() - 1)
                logger.warning(f"[FileTableView] *** ROW {row}: left_valid={left_index.isValid()}, right_valid={right_index.isValid()} ***")
                if left_index.isValid() and right_index.isValid():
                    logger.warning(f"[FileTableView] *** CREATING ROW SELECTION FOR ROW {row} ***")
                    row_selection = QItemSelection(left_index, right_index)
                    full_selection.merge(row_selection, selection_model.Select)
                    logger.warning(f"[FileTableView] *** MERGED ROW {row} INTO FULL SELECTION ***")

        # Apply the entire selection at once
        logger.warning(f"[FileTableView] *** SELECTION EMPTY? {full_selection.isEmpty()} ***")
        if not full_selection.isEmpty():
            logger.warning(f"[FileTableView] *** APPLYING FULL SELECTION ***")
            selection_model.select(full_selection, selection_model.Select)
            logger.warning(f"[FileTableView] *** SELECTION APPLIED SUCCESSFULLY ***")

        logger.warning(f"[FileTableView] *** UNBLOCKING SIGNALS ***")
        self.blockSignals(False)

        # Update selection store
        selected_rows = set(rows_to_select)
        self._update_selection_store(selected_rows, emit_signal=True)

        # Update UI
        if hasattr(self, 'viewport'):
            self.viewport().update()

        # Final verification
        final_selection = set(index.row() for index in self.selectionModel().selectedRows()) if self.selectionModel() else set()
        logger.warning(f"[FileTableView] *** FINAL VERIFICATION: {len(final_selection)} rows selected: {final_selection} ***")

    def is_empty(self) -> bool:
        return not getattr(self.model(), "files", [])

    def focusOutEvent(self, event) -> None:
        super().focusOutEvent(event)
        if self.context_focused_row is not None:
            self.context_focused_row = None
            self.viewport().update()

    def focusInEvent(self, event) -> None:
        super().focusInEvent(event)
        selected_rows = set(index.row() for index in self.selectionModel().selectedRows())
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
                        left = self.model().index(r, 0) # type: ignore
                        right = self.model().index(r, self.model().columnCount() - 1) # type: ignore
                        row_rect = self.visualRect(left).united(self.visualRect(right))
                        self.viewport().update(row_rect) # type: ignore

        # Check if vertical scrollbar visibility changed after wheel scroll
        # Use a small delay to ensure scrollbar state is updated
        schedule_resize_adjust(self._check_vertical_scrollbar_visibility, 10)

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
        viewport_rect = self.viewport().rect() # type: ignore
        item_rect = self.visualRect(index) # type: ignore

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
            current_selection = set(index.row() for index in self.selectionModel().selectedRows()) # type: ignore
            selection_store.set_selected_rows(current_selection, emit_signal=False)
            if hasattr(self, 'anchor_row') and self.anchor_row is not None:
                selection_store.set_anchor_row(self.anchor_row, emit_signal=False)
            logger.debug("[FileTableView] SelectionStore mode enabled", extra={"dev_only": True})
        else:
            logger.warning("[FileTableView] Cannot enable SelectionStore mode - store not available")

    def disable_selection_store_mode(self):
        """Disable selection store synchronization mode."""
        if self._get_selection_store():
            self._get_selection_store().set_active(False) # type: ignore
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
            logger.debug(f"[FileTableView] Force cleaned {cursor_count} stuck cursors during drag", extra={"dev_only": True})

        # Process events immediately
        QApplication.processEvents()

    def _emergency_cursor_cleanup(self):
        """Emergency cursor cleanup method."""
        # Use the force cleanup method first
        self._force_cursor_cleanup()

        # Additional cleanup for drag manager
        drag_manager = DragManager.get_instance()
        if drag_manager.is_drag_active():
            logger.debug("[FileTableView] Emergency: Forcing DragManager cleanup", extra={"dev_only": True})
            drag_manager.force_cleanup()

        # Force viewport update
        if hasattr(self, 'viewport'):
            self.viewport().update() # type: ignore
        QApplication.processEvents()
