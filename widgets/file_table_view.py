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
    Qt,
    QTimer,
    QUrl,
    pyqtSignal,
)
from PyQt5.QtGui import QCursor, QDrag, QDropEvent, QKeySequence, QMouseEvent, QPixmap
from PyQt5.QtWidgets import QAbstractItemView, QApplication, QHeaderView, QLabel, QTableView

from config import FILE_TABLE_COLUMN_WIDTHS
from utils.file_drop_helper import extract_file_paths
from utils.logger_helper import get_logger

from .hover_delegate import HoverItemDelegate

logger = get_logger(__name__)

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
        self._drag_start_pos: QPoint = QPoint()
        self._filename_min_width: int = 250  # Will be updated in _configure_columns
        self._user_preferred_width: Optional[int] = None  # User's preferred filename column width

        # Configure table behavior
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setMouseTracking(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)

        # Setup placeholder icon
        self.placeholder_label = QLabel(self.viewport())
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.placeholder_label.setVisible(False)

        icon_path = Path(__file__).parent.parent / "assets/File_Folder_Drag_Drop.png"
        self.placeholder_icon = QPixmap(str(icon_path))

        if not self.placeholder_icon.isNull():
            scaled = self.placeholder_icon.scaled(
                PLACEHOLDER_ICON_SIZE, PLACEHOLDER_ICON_SIZE,
                Qt.KeepAspectRatio, Qt.SmoothTransformation
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

    def resizeEvent(self, event) -> None:
        """Handle resize events and update placeholder position."""
        super().resizeEvent(event)
        if self.placeholder_label:
            self.placeholder_label.resize(self.viewport().size())
            self.placeholder_label.move(0, 0)

    def setModel(self, model) -> None:
        """Configure columns when model is set."""
        super().setModel(model)
        if model:
            QTimer.singleShot(10, self._configure_columns)

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
        # Clear selection and reset checked state
        for file_item in file_items:
            file_item.checked = False

        self.clearSelection()
        self.selected_rows.clear()

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

        # Find parent window with fontMetrics
        parent_window = self.parent()
        while parent_window and not hasattr(parent_window, 'fontMetrics'):
            parent_window = parent_window.parent()

        if not parent_window:
            logger.warning("[FileTableView] Cannot find parent window with fontMetrics")
            return

        # Configure each column with config values and calculated minimums
        status_width = FILE_TABLE_COLUMN_WIDTHS["STATUS_COLUMN"]
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.setColumnWidth(0, status_width)

        # Filename column - Interactive with minimum width protection
        filename_min = parent_window.fontMetrics().horizontalAdvance("Long_Filename_Example_2024.jpeg") + 30
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

                # Store minimum width for filename column enforcement (use same as initial width)
        self._filename_min_width = filename_width

        # Initialize user preferred width to the initial width
        self._user_preferred_width = filename_width

        # Connect signal to enforce filename column minimum width
        header.sectionResized.connect(self._on_filename_resized)

    def _on_filename_resized(self, logical_index: int, old_size: int, new_size: int) -> None:
        """Enforce minimum width and remember user preference for filename column (column 1)."""
        if logical_index == 1 and hasattr(self, '_filename_min_width'):
            if new_size < self._filename_min_width:
                self.setColumnWidth(1, self._filename_min_width)
                self._user_preferred_width = self._filename_min_width
            else:
                # Remember user's preferred width
                self._user_preferred_width = new_size

    def _update_scrollbar_visibility(self) -> None:
        """Update scrollbar visibility based on table content."""
        if not self.model():
            return

        is_empty = (self.model() is None or self.model().rowCount() == 0)

        if is_empty:
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        else:
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    def on_horizontal_splitter_moved(self, pos: int, index: int) -> None:
        """Handle horizontal splitter movement - use user preference as base, expand if more space available."""
        parent_window = self.parent()
        while parent_window and not hasattr(parent_window, 'horizontal_splitter'):
            parent_window = parent_window.parent()

        if not parent_window:
            return

        sizes = parent_window.horizontal_splitter.sizes()
        center_panel_width = sizes[1]

        if center_panel_width > 0 and hasattr(self, '_filename_min_width'):
            # Calculate available width for filename column
            other_columns_width = (self.columnWidth(0) + self.columnWidth(2) +
                                  self.columnWidth(3) + self.columnWidth(4))
            available_width = center_panel_width - other_columns_width - SCROLLBAR_MARGIN

            current_filename_width = self.columnWidth(1)

            # Use available space, but respect minimum width
            new_filename_width = max(self._filename_min_width, available_width)

            # Only resize if the difference is significant (avoid micro-adjustments)
            size_difference = abs(new_filename_width - current_filename_width)

            # Only adjust if:
            # 1. We need to expand significantly (>20px more space available)
            # 2. We need to shrink below current size due to space constraints
            should_resize = False

            if new_filename_width > current_filename_width and size_difference > 20:
                # Expand only if we have significantly more space
                should_resize = True
            elif new_filename_width < current_filename_width:
                # Always shrink when space is constrained
                should_resize = True

            if should_resize:
                # Temporarily disconnect signal to avoid updating user preference during auto-resize
                header = self.horizontalHeader()
                if header:
                    header.sectionResized.disconnect(self._on_filename_resized)

                self.setColumnWidth(1, new_filename_width)

                # Reconnect signal
                if header:
                    header.sectionResized.connect(self._on_filename_resized)

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

            self.viewport().update()

    def ensure_anchor_or_select(self, index: QModelIndex, modifiers: Qt.KeyboardModifiers) -> None:
        """Handle selection logic with anchor and modifier support."""
        sm = self.selectionModel()
        model = self.model()
        if sm is None or model is None:
            return

        if modifiers & Qt.ShiftModifier:
            if self._manual_anchor_index is None:
                self._manual_anchor_index = index
            else:
                selection = QItemSelection(self._manual_anchor_index, index)
                sm.select(selection, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)
                sm.setCurrentIndex(index, QItemSelectionModel.NoUpdate)

        elif modifiers & Qt.ControlModifier:
            self._manual_anchor_index = index
            row = index.row()
            selection = QItemSelection(index, index)
            sm.blockSignals(True)
            if sm.isSelected(index):
                sm.select(selection, QItemSelectionModel.Deselect | QItemSelectionModel.Rows)
            else:
                sm.select(selection, QItemSelectionModel.Select | QItemSelectionModel.Rows)
            sm.blockSignals(False)
            sm.setCurrentIndex(index, QItemSelectionModel.NoUpdate)

            # Update visual feedback
            left = model.index(row, 0)
            right = model.index(row, model.columnCount() - 1)
            self.viewport().update(self.visualRect(left).united(self.visualRect(right)))

        else:
            self._manual_anchor_index = index
            sm.select(index, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)
            sm.setCurrentIndex(index, QItemSelectionModel.NoUpdate)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press with custom selection logic."""
        index: QModelIndex = self.indexAt(event.pos())
        if not index.isValid() or self.is_empty():
            super().mousePressEvent(event)
            return

        # Handle right-click separately
        if event.button() == Qt.RightButton:
            super().mousePressEvent(event)
            return

        super().mousePressEvent(event)

        # Clear context focus on left click
        if event.button() != Qt.RightButton and self.context_focused_row is not None:
            self.context_focused_row = None
            self.viewport().update()

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
        if hasattr(self, "parent_window"):
            self.parent_window.handle_file_double_click(index, event.modifiers())

        self._sync_selection_safely()

    def mouseReleaseEvent(self, event) -> None:
        if self.is_empty():
            return

        if event.button() == Qt.RightButton:
            index = self.indexAt(event.pos())
            if index.isValid() and event.modifiers() & Qt.ShiftModifier:
                self.ensure_anchor_or_select(index, event.modifiers())

                # Update visual range
                top = min(self._manual_anchor_index.row(), index.row())
                bottom = max(self._manual_anchor_index.row(), index.row())
                for row in range(top, bottom + 1):
                    left = self.model().index(row, 0)
                    right = self.model().index(row, self.model().columnCount() - 1)
                    self.viewport().update(self.visualRect(left).united(self.visualRect(right)))

                self._sync_selection_safely()
                return

        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self.is_empty():
            return

        index = self.indexAt(event.pos())
        hovered_row = index.row() if index.isValid() else -1

        # Handle drag initiation
        if event.buttons() & Qt.LeftButton and hovered_row in self.selected_rows:
            if (event.pos() - self._drag_start_pos).manhattanLength() >= QApplication.startDragDistance():
                self.startDrag(Qt.CopyAction)
                return

        # Update hover highlighting
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
        """Handle keyboard navigation and sync selection."""
        super().keyPressEvent(event)
        if event.matches(QKeySequence.SelectAll) or event.key() in (
            Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter,
            Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right
        ):
            self._sync_selection_safely()

    def _sync_selection_safely(self) -> None:
        parent = self.window()
        if hasattr(parent, "sync_selection_to_checked"):
            selection = self.selectionModel().selection()
            selected_rows = set(idx.row() for idx in self.selectionModel().selectedRows())
            parent.sync_selection_to_checked(selection, QItemSelection())

    # =====================================
    # Drag & Drop Methods
    # =====================================

    def startDrag(self, supportedActions: Qt.DropActions) -> None:
        """Initiate drag operation for selected files."""
        rows = sorted(self.selected_rows)
        if not rows:
            return

        file_items = [self.model().files[r] for r in rows if 0 <= r < len(self.model().files)]
        file_paths = [f.full_path for f in file_items if f.full_path]

        if not file_paths:
            return

        # Setup drag cancel filter
        from widgets.file_tree_view import _drag_cancel_filter
        _drag_cancel_filter.activate()

        # Create MIME data
        mime_data = QMimeData()
        mime_data.setData("application/x-oncutf-filetable", b"1")
        urls = [QUrl.fromLocalFile(p) for p in file_paths]
        mime_data.setUrls(urls)

        # Execute drag
        drag = QDrag(self)
        drag.setMimeData(mime_data)

        try:
            result = drag.exec(Qt.CopyAction | Qt.MoveAction | Qt.LinkAction)
        except Exception as e:
            logger.error(f"Drag operation failed: {e}")
        finally:
            self._cleanup_drag_state()

        QTimer.singleShot(0, self._complete_drag_cleanup)

    def _cleanup_drag_state(self):
        """Clean up drag operation state."""
        while QApplication.overrideCursor():
            QApplication.restoreOverrideCursor()

        from widgets.file_tree_view import _drag_cancel_filter
        _drag_cancel_filter.deactivate()

        if hasattr(self, 'viewport'):
            self.viewport().update()
        QApplication.processEvents()

    def _complete_drag_cleanup(self):
        """Complete drag cleanup after event loop."""
        from widgets.file_tree_view import _drag_cancel_filter
        _drag_cancel_filter.deactivate()

        while QApplication.overrideCursor():
            QApplication.restoreOverrideCursor()

        if hasattr(self, 'viewport'):
            self.viewport().update()
        QApplication.processEvents()

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
        selection_model = self.selectionModel()
        if selection_model is not None:
            self.selected_rows = set(index.row() for index in selection_model.selectedRows())
            self.selection_changed.emit(list(self.selected_rows))

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
            top_left = model.index(start_row, 0)
            bottom_right = model.index(end_row, model.columnCount() - 1)
            selection = QItemSelection(top_left, bottom_right)
            selection_model.select(selection, QItemSelectionModel.Select | QItemSelectionModel.Rows)

        self.blockSignals(False)

        if hasattr(self, 'viewport'):
            self.viewport().update()

        if model is not None:
            self.selected_rows = set(range(start_row, end_row + 1))
            self.selection_changed.emit(list(self.selected_rows))

    def is_empty(self) -> bool:
        return not getattr(self.model(), "files", [])

    def focusOutEvent(self, event) -> None:
        super().focusOutEvent(event)
        if self.context_focused_row is not None:
            self.context_focused_row = None
            self.viewport().update()

    def focusInEvent(self, event) -> None:
        super().focusInEvent(event)
        self.selected_rows = set(index.row() for index in self.selectionModel().selectedRows())
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
                        left = self.model().index(r, 0)
                        right = self.model().index(r, self.model().columnCount() - 1)
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
        viewport_rect = self.viewport().rect()
        item_rect = self.visualRect(index)

        # Only scroll if item is completely outside the viewport
        if not viewport_rect.intersects(item_rect):
            super().scrollTo(index, hint)
        # Otherwise, do nothing - prevent automatic centering
