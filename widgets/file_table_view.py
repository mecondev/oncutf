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
    QEvent,
    QItemSelection,
    QItemSelectionModel,
    QModelIndex,
    QPoint,
    Qt,
    pyqtSignal,
)
from PyQt5.QtGui import (
    QCursor,
    QDropEvent,
    QKeySequence,
    QMouseEvent,
    QPixmap,
)
from PyQt5.QtWidgets import QAbstractItemView, QApplication, QHeaderView, QLabel, QTableView

from config import FILE_TABLE_COLUMN_WIDTHS
from core.application_context import get_app_context
from core.drag_manager import DragManager
from core.drag_visual_manager import (
    DragType,
    DragVisualManager,
    end_drag_visual,
    start_drag_visual,
    update_drag_feedback_for_widget,
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

        # Custom drag state tracking (needed by existing drag implementation)
        self._is_dragging = False
        self._drag_data = None
        self._drag_feedback_timer = None

        # Selection preservation for drag operations
        self._preserve_selection_for_drag = False
        self._clicked_on_selected = False
        self._clicked_index = None

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
            # Emit selection change signal immediately
            self.selection_changed.emit(list(selected_rows))

    def _sync_qt_selection_model(self, selected_rows: set) -> None:
        """Ensure Qt selection model matches our internal selection state."""
        selection_model = self.selectionModel()
        if not selection_model or not self.model():
            return

        # Prevent recursive calls during Qt model synchronization
        if hasattr(self, '_syncing_qt_model') and self._syncing_qt_model:
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
        # Always use the current Qt selection for consistency
        # This is more reliable than trying to preserve drag selections
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
        """Handle resize events and update placeholder position."""
        super().resizeEvent(event)
        if self.placeholder_label:
            self.placeholder_label.resize(self.viewport().size())
            self.placeholder_label.move(0, 0)

        # Check if vertical scrollbar visibility changed after resize
        # Use a small delay to ensure scrollbar state is updated
        schedule_resize_adjust(self._check_vertical_scrollbar_visibility, 10)

    def showEvent(self, event) -> None:
        """Handle show events to ensure proper display after visibility changes."""
        super().showEvent(event)
        # Force viewport refresh when table becomes visible (e.g., after maximize/restore)
        schedule_resize_adjust(lambda: self.viewport().update(), 5)

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

        # Filename column - Interactive with minimum width protection and dynamic sizing
        filename_min = font_metrics.horizontalAdvance("Long_Filename_Example_2024.jpeg") + 30

                # Determine filename width based on user preference or use config default
        if hasattr(self, '_has_manual_preference') and self._has_manual_preference:
            # User has manually resized - use their preference but ensure minimum
            filename_width = max(self._user_preferred_width, filename_min)
        else:
            # Use config default as baseline for auto-sizing
            config_default = FILE_TABLE_COLUMN_WIDTHS["FILENAME_COLUMN"]
            filename_width = max(config_default, filename_min, 250)

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

        # Initialize user preference tracking
        if not hasattr(self, '_has_manual_preference'):
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
                self._recent_manual_resize = True

                # Clear the flag after some time to allow auto-sizing on window changes
                from utils.timer_manager import schedule_resize_adjust
                schedule_resize_adjust(lambda: setattr(self, '_recent_manual_resize', False), 5000)

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
        else:
            # Scrollbar not needed - restore filename column to base width
            if self._filename_base_width > 0:
                new_width = max(self._filename_base_width, self._filename_min_width)

                if new_width != current_width:
                    self._programmatic_resize = True
                    self.setColumnWidth(1, new_width)
                    self._programmatic_resize = False

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
                    # Multi-selection: Preserve current selection for drag
                    self._drag_start_selection = current_selection.copy()
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
                    current_selection = current_selection.copy()  # Make a copy to avoid modifying the original
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
                elif modifiers == Qt.ShiftModifier:
                    # Shift+click on selected item without drag - preserve current selection
                    # Don't change selection when Shift is held and we clicked on a selected item
                    pass
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

                # Final status update after drag ends to ensure UI consistency
                def final_status_update():
                    current_selection = self._get_current_selection()
                    if current_selection:
                        selection_store = self._get_selection_store()
                        if selection_store and not self._legacy_selection_mode:
                            selection_store.selection_changed.emit(list(current_selection))
                            logger.debug(f"[FileTableView] Final status update after drag: {len(current_selection)} files", extra={"dev_only": True})

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
        # Don't handle ESC at all - let it pass through to dialogs and other components
        # Cursor cleanup is handled automatically by other mechanisms

        # Skip key handling during drag (using Qt built-in drag now)
        if self._is_dragging:
            return

        super().keyPressEvent(event)
        if event.matches(QKeySequence.SelectAll) or event.key() in (
            Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter,
            Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right
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

        # Stop any existing drag feedback timer
        if hasattr(self, '_drag_feedback_timer_id') and self._drag_feedback_timer_id:
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

        logger.debug(f"[FileTableView] Custom drag started with visual feedback: {len(file_paths)} files (type: {drag_type.value})", extra={"dev_only": True})

    def _start_drag_feedback_loop(self):
        """Start repeated drag feedback updates using timer_manager"""
        from utils.timer_manager import schedule_ui_update
        if self._is_dragging:
            self._update_drag_feedback()
            # Schedule next update
            self._drag_feedback_timer_id = schedule_ui_update(self._start_drag_feedback_loop, delay=50)

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

        logger.debug("[FileTableView] Ending custom drag operation", extra={"dev_only": True})

        # Stop and cleanup drag feedback timer
        if hasattr(self, '_drag_feedback_timer_id') and self._drag_feedback_timer_id:
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
                if parent.__class__.__name__ == 'MetadataTreeView':
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

        logger.debug("[FileTableView] Custom drag operation completed", extra={"dev_only": True})

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
        """Handle drop on metadata tree - SIMPLIFIED direct communication"""
        if not self._drag_data:
            logger.debug("[FileTableView] No drag data available for metadata tree drop", extra={"dev_only": True})
            return False

        # Get current selection - this is what the user sees and expects
        selected_rows = self._get_current_selection()
        logger.debug(f"[FileTableView] Using current selection for metadata drop: {len(selected_rows)} files", extra={"dev_only": True})

        if not selected_rows:
            logger.warning("[FileTableView] No valid selection found for metadata tree drop")
            return False

        # Convert to FileItem objects
        try:
            file_items = [self.model().files[r] for r in selected_rows if 0 <= r < len(self.model().files)]
            if not file_items:
                logger.warning("[FileTableView] No valid file items found for metadata tree drop")
                return False
        except (AttributeError, IndexError) as e:
            logger.error(f"[FileTableView] Error converting selection to file items: {e}")
            return False

        # Get modifiers for metadata loading decision
        modifiers = QApplication.keyboardModifiers()
        use_extended = bool(modifiers & Qt.ShiftModifier) # type: ignore

        # Find parent window and call MetadataManager directly
        parent_window = self._get_parent_with_metadata_tree()
        if not parent_window or not hasattr(parent_window, 'metadata_manager'):
            logger.warning("[FileTableView] Could not find parent window or metadata manager")
            return False

        logger.debug(f"[FileTableView] Calling MetadataManager directly with {len(file_items)} files (extended={use_extended})", extra={"dev_only": True})

        # SIMPLIFIED: Call MetadataManager directly - no complex signal chain
        try:
            parent_window.metadata_manager.load_metadata_for_items(
                file_items,
                use_extended=use_extended,
                source="drag_drop_direct"
            )

            # Set flag to indicate successful metadata drop
            self._successful_metadata_drop = True
            logger.debug("[FileTableView] Metadata loading initiated successfully", extra={"dev_only": True})

            # Force cursor cleanup after successful operation
            self._force_cursor_cleanup()

            # Schedule final status update
            def final_status_update():
                current_selection = self._get_current_selection()
                if current_selection:
                    selection_store = self._get_selection_store()
                    if selection_store and not self._legacy_selection_mode:
                        selection_store.selection_changed.emit(list(current_selection))
                        logger.debug(f"[FileTableView] Final status update: {len(current_selection)} files", extra={"dev_only": True})

            schedule_ui_update(final_status_update, delay=100)
            return True

        except Exception as e:
            logger.error(f"[FileTableView] Error calling MetadataManager: {e}")
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
    # Drag & Drop Event Handlers
    # =====================================

    def dragEnterEvent(self, event):
        """Accept drag events with URLs or internal format."""
        if event.mimeData().hasUrls() or event.mimeData().hasFormat("application/x-oncutf-internal"):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        """Accept drag move events with URLs or internal format."""
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
        """SIMPLIFIED selection handling with protection against post-drag empty selections"""
        super().selectionChanged(selected, deselected)

        selection_model = self.selectionModel()
        if selection_model is not None:
            selected_rows = set(index.row() for index in selection_model.selectedRows())

            # PROTECTION: Ignore empty selections that come immediately after SUCCESSFUL metadata drops
            # This prevents Qt's automatic clearSelection() from clearing our metadata display
            if not selected_rows and hasattr(self, '_successful_metadata_drop') and self._successful_metadata_drop:
                logger.debug("[FileTableView] Ignoring empty selection after successful metadata drop", extra={"dev_only": True})
                # Clear the flag and restore the selection
                self._successful_metadata_drop = False
                # Try to restore the selection from SelectionStore
                selection_store = self._get_selection_store()
                if selection_store and not self._legacy_selection_mode:
                    stored_selection = selection_store.get_selected_rows()
                    if stored_selection:
                        logger.debug(f"[FileTableView] Restoring {len(stored_selection)} files from SelectionStore", extra={"dev_only": True})
                        self._sync_qt_selection_model(stored_selection)
                        self.viewport().update()
                return

            # Also ignore empty selections during active drag operations
            if not selected_rows and hasattr(self, '_is_dragging') and self._is_dragging:
                logger.debug("[FileTableView] Ignoring empty selection during drag operation", extra={"dev_only": True})
                return

            logger.debug(f"[FileTableView] Selection changed to: {len(selected_rows)} files", extra={"dev_only": True})
            self._update_selection_store(selected_rows, emit_signal=True)

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
        logger.debug(f"[FileTableView] Selecting dropped files: {len(file_paths) if file_paths else 0} paths", extra={"dev_only": True})

        model = self.model()
        if not model or not hasattr(model, 'files'):
            logger.error("[FileTableView] No model or model has no files attribute")
            return

        if not file_paths:
            # Fallback: select all files if no specific paths provided
            row_count = len(model.files)
            if row_count == 0:
                logger.debug("[FileTableView] No files in model - returning early", extra={"dev_only": True})
                return
            logger.debug(f"[FileTableView] Fallback: selecting all {row_count} files", extra={"dev_only": True})
            self.select_rows_range(0, row_count - 1)
            return

        # Select specific files based on their paths
        rows_to_select = []
        for i, file_item in enumerate(model.files):
            if file_item.full_path in file_paths:
                rows_to_select.append(i)

        logger.debug(f"[FileTableView] Found {len(rows_to_select)} matching files to select", extra={"dev_only": True})

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
        from PyQt5.QtCore import QItemSelection
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
        if hasattr(self, 'viewport'):
            self.viewport().update()

        # Final verification
        final_selection = set(index.row() for index in self.selectionModel().selectedRows()) if self.selectionModel() else set()
        logger.debug(f"[FileTableView] Selection completed: {len(final_selection)} rows selected", extra={"dev_only": True})

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

    def _clear_skip_flag(self):
        """Clear the skip selection changed flag."""
        self._skip_selection_changed = False
