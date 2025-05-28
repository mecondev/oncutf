'''
custom_table_view.py

Author: Michael Economou
Date: 2025-05-25

This module defines the CustomTableView class, a subclass of QTableView,
that emulates the interactive behavior of the Windows File Explorer.

Key features:
- Full-row selection on click/keyboard/drag
- Manual anchor index handling for Shift+Click/Shift+DoubleClick/Shift+RightClick
- Hover highlight per row (including column 0)
- Drag & drop export of file paths
- Seamless integration with parent MainWindow for preview/metadata sync
- Proper visual updates on hover/selection using manual viewport repaint
'''

from PyQt5.QtWidgets import QAbstractItemView, QTableView, QApplication
from PyQt5.QtCore import QMimeData, QUrl, QItemSelectionModel, QItemSelection, Qt, QPoint, QModelIndex
from PyQt5.QtGui import QKeySequence, QDrag, QMouseEvent, QCursor
from widgets.hover_delegate import HoverItemDelegate
from PyQt5.QtCore import pyqtSignal
from utils.logger_helper import get_logger

logger = get_logger(__name__)

class CustomTableView(QTableView):
    selection_changed = pyqtSignal(list)  # Emitted with list[int] of selected rows
    def __init__(self, parent=None) -> None:
        """
        Initializes the custom table view with full-row interaction logic.
        Enables drag operations, QSS-based hover, and anchor-aware selection.
        """
        super().__init__(parent)
        self._manual_anchor_index: QModelIndex | None = None
        self._drag_start_pos: QPoint = QPoint()
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragOnly)
        self.setMouseTracking(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)

        # Selection state (custom selection model)
        self.selected_rows: set[int] = set()  # Keeps track of currently selected rows
        self.anchor_row: int | None = None    # Used for shift-click range selection

        # Enable hover visuals via delegate
        self.hover_delegate = HoverItemDelegate(self, hover_color="#2e3b4e")
        self.setItemDelegate(self.hover_delegate)
        self.setItemDelegateForColumn(0, self.hover_delegate)

        # Used for right-click visual indication
        self.context_focused_row: int | None = None

    def ensure_anchor_or_select(self, index: QModelIndex, modifiers: Qt.KeyboardModifiers) -> None:
        """
        Handles custom selection logic with anchor and modifier support.

        Supports:
        - Shift + Click: Selects a range from anchor to index
        - Ctrl + Click: Toggles selection manually (Qt-safe)
        - Plain Click: Selects only the clicked row

        Args:
            index (QModelIndex): Clicked index.
            modifiers (Qt.KeyboardModifiers): Active keyboard modifiers.
        """
        sm = self.selectionModel()
        model = self.model()
        if sm is None or model is None:
            return

        if hasattr(Qt, 'ShiftModifier') and modifiers & Qt.ShiftModifier:
            if self._manual_anchor_index is None:
                self._manual_anchor_index = index
                logger.debug(f"[Anchor] Initialized at row {index.row()} (no previous anchor)")
            else:
                if hasattr(QItemSelectionModel, 'ClearAndSelect') and hasattr(QItemSelectionModel, 'Rows'):
                    selection = QItemSelection(self._manual_anchor_index, index)
                    sm.select(selection, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)
                    if hasattr(QItemSelectionModel, 'NoUpdate'):
                        sm.setCurrentIndex(index, QItemSelectionModel.NoUpdate)
                    logger.debug(f"[Anchor] Shift-select from {self._manual_anchor_index.row()} to {index.row()}")

        elif hasattr(Qt, 'ControlModifier') and modifiers & Qt.ControlModifier:
            self._manual_anchor_index = index
            row = index.row()
            selection = QItemSelection(index, index)

            if hasattr(sm, 'blockSignals'):
                sm.blockSignals(True)

            if hasattr(sm, 'isSelected') and sm.isSelected(index):
                if hasattr(QItemSelectionModel, 'Deselect') and hasattr(QItemSelectionModel, 'Rows'):
                    sm.select(selection, QItemSelectionModel.Deselect | QItemSelectionModel.Rows)
                    logger.debug(f"[Anchor] Ctrl-toggle OFF at row {row}")
            else:
                if hasattr(QItemSelectionModel, 'Select') and hasattr(QItemSelectionModel, 'Rows'):
                    sm.select(selection, QItemSelectionModel.Select | QItemSelectionModel.Rows)
                    logger.debug(f"[Anchor] Ctrl-toggle ON at row {row}")

            if hasattr(sm, 'blockSignals'):
                sm.blockSignals(False)

            if hasattr(QItemSelectionModel, 'NoUpdate'):
                sm.setCurrentIndex(index, QItemSelectionModel.NoUpdate)

            # Επιβάλε ανανέωση γραμμής.
            if hasattr(model, 'index') and hasattr(model, 'columnCount') and hasattr(self, 'viewport') and callable(getattr(self.viewport(), 'update', None)):
                left = model.index(row, 0)
                right = model.index(row, model.columnCount() - 1)
                self.viewport().update(self.visualRect(left).united(self.visualRect(right)))

        else:
            self._manual_anchor_index = index
            if hasattr(QItemSelectionModel, 'ClearAndSelect') and hasattr(QItemSelectionModel, 'Rows'):
                sm.select(index, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)
                if hasattr(QItemSelectionModel, 'NoUpdate'):
                    sm.setCurrentIndex(index, QItemSelectionModel.NoUpdate)
                logger.debug(f"[Anchor] Single click select at row {index.row()}")

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        Custom mouse press handler for row selection.
        Implements Ctrl, Shift, and Ctrl+Shift logic for reliable selection.
        Implements explorer-style: single click always selects only the row, Ctrl+click toggles selection.
        """
        index: QModelIndex = self.indexAt(event.pos())
        if not index.isValid() or self.is_empty():
            super().mousePressEvent(event)
            return

        row: int = index.row()
        modifiers = event.modifiers()
        ctrl = modifiers & Qt.ControlModifier
        shift = modifiers & Qt.ShiftModifier

        # Right click inside selection: do nothing, just repaint
        if event.button() == Qt.RightButton:
            super().mousePressEvent(event)
            return

        # Left click logic (range, ctrl, shift, κλπ)
        super().mousePressEvent(event)

        # Clear context_focused_row if not right click
        if event.button() != Qt.RightButton and self.context_focused_row is not None:
            self.context_focused_row = None
            self.viewport().update()

    def mouseDoubleClickEvent(self, event) -> None:
        """
        Handles double-click with optional Shift modifier.
        For Shift+DoubleClick, cancels range selection and loads extended metadata for one row only.
        """
        if self.is_empty():
            event.ignore()
            return

        index = self.indexAt(event.pos())
        if not index.isValid():
            super().mouseDoubleClickEvent(event)
            return

        selection_model = self.selectionModel()

        if event.modifiers() & Qt.ShiftModifier:
            # SHIFT + DoubleClick → cancel any previous range selection
            selection_model.clearSelection()
            selection_model.select(index, QItemSelectionModel.Clear | QItemSelectionModel.Select | QItemSelectionModel.Rows)
            selection_model.setCurrentIndex(index, QItemSelectionModel.NoUpdate)

            self._manual_anchor_index = index  # new anchor
            logger.debug(f"[DoubleClick] SHIFT override: only row {index.row()} selected for extended metadata")
        else:
            # Normal double-click → allow anchor-based selection
            self.ensure_anchor_or_select(index, event.modifiers())

        # In all valid cases, trigger metadata load
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

                # Repaint selected rows
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

        # If dragging from already selected row, do not change selection (ignore modifiers)
        if event.buttons() & Qt.LeftButton and hovered_row in self.selected_rows:
            if (event.pos() - self._drag_start_pos).manhattanLength() >= QApplication.startDragDistance():
                self.startDrag(Qt.CopyAction)
                return

        if hasattr(self, "hover_delegate") and hovered_row != self.hover_delegate.hovered_row:
            old_row = self.hover_delegate.hovered_row
            self.hover_delegate.update_hover_row(hovered_row)

            for r in (old_row, hovered_row):
                if r >= 0:
                    left = self.model().index(r, 0)
                    right = self.model().index(r, self.model().columnCount() - 1)
                    row_rect = self.visualRect(left).united(self.visualRect(right))
                    logger.debug(f"[Hover] Repainting full row {r}", extra={"dev_only": True})
                    self.viewport().update(row_rect)

    def keyPressEvent(self, event) -> None:
        """
        Handles keyboard navigation and ensures selection is synchronized.
        """
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
            logger.debug(f"[DEBUG] _sync_selection_safely → selected_rows: {selected_rows}")
            parent.sync_selection_to_checked(selection, QItemSelection())

    def startDrag(self, supportedActions: Qt.DropActions) -> None:
        """
        Initiates a drag operation for selected file paths.
        """
        rows = sorted(self.selected_rows)
        if not rows:
            return

        file_items = [self.model().files[r] for r in rows if 0 <= r < len(self.model().files)]
        file_paths = [f.full_path for f in file_items if f.full_path]

        if not file_paths:
            return

        mime_data = QMimeData()
        urls = [QUrl.fromLocalFile(p) for p in file_paths]
        mime_data.setUrls(urls)

        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec_(Qt.CopyAction)

    def selectionChanged(self, selected, deselected) -> None:
        super().selectionChanged(selected, deselected)
        # Sync custom selected_rows with the actual selection model
        selection_model = self.selectionModel()
        if selection_model is not None:
            self.selected_rows = set(index.row() for index in selection_model.selectedRows())
            self.selection_changed.emit(list(self.selected_rows))
        # Always clear context_focused_row on selection change to avoid stale focus highlight
        if self.context_focused_row is not None:
            self.context_focused_row = None
        if hasattr(self, 'viewport') and callable(getattr(self.viewport(), 'update', None)):
            self.viewport().update()

    def is_empty(self) -> bool:
        return not getattr(self.model(), "files", [])

    def focusOutEvent(self, event) -> None:
        super().focusOutEvent(event)
        # Clear context_focused_row when table loses focus (e.g. after context menu closes)
        if self.context_focused_row is not None:
            self.context_focused_row = None
            self.viewport().update()

    def contextMenuEvent(self, event) -> None:
        """
        Clear context_focused_row after context menu closes
        to avoid stale highlight.
        """
        super().contextMenuEvent(event)
        if self.context_focused_row is not None:
            self.context_focused_row = None
            self.viewport().update()

    def focusInEvent(self, event) -> None:
        super().focusInEvent(event)
        # Sync custom selected_rows with the actual selection model on focus in
        self.selected_rows = set(index.row() for index in self.selectionModel().selectedRows())
        self.viewport().update()

    def wheelEvent(self, event) -> None:
        super().wheelEvent(event)
        # Update hover row after scroll to follow mouse position
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

    def select_rows_range(self, start_row: int, end_row: int) -> None:
        """Selects a range of rows efficiently (block selection). Does NOT clear previous selection."""
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
        if hasattr(self, 'viewport') and callable(getattr(self.viewport(), 'update', None)):
            self.viewport().update()
        # Update custom selected_rows and emit selection_changed for preview sync
        if model is not None:
            self.selected_rows = set(range(start_row, end_row + 1))
            self.selection_changed.emit(list(self.selected_rows))
