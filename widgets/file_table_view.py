'''
file_table_view.py

Author: Michael Economou
Date: 2025-05-25

This module defines the FileTableView class, a subclass of QTableView,
that emulates the interactive behavior of the Windows File Explorer.

Key features:
- Full-row selection on click/keyboard/drag
- Manual anchor index handling for Shift+Click/Shift+DoubleClick/Shift+RightClick
- Hover highlight per row (including column 0)
- Drag & drop export of file paths
- Seamless integration with parent MainWindow for preview/metadata sync
- Proper visual updates on hover/selection using manual viewport repaint
'''
import sys, os
from pathlib import Path
from PyQt5.QtWidgets import QAbstractItemView, QTableView, QApplication, QLabel
from PyQt5.QtCore import (
      QMimeData, QUrl, QItemSelectionModel, QItemSelection,
      Qt, QPoint, QModelIndex, QTimer, pyqtSignal
)
from PyQt5.QtGui import QKeySequence, QDrag, QMouseEvent, QCursor, QPixmap, QPainter, QFont, QColor, QDropEvent
from utils.file_drop_helper import (
      analyze_drop, filter_allowed_files, ask_recursive_dialog, show_rejected_dialog, extract_file_paths
)
from .hover_delegate import HoverItemDelegate


from utils.logger_helper import get_logger

logger = get_logger(__name__)


class FileTableView(QTableView):
    selection_changed = pyqtSignal(list)  # Emitted with list[int] of selected rows
    files_dropped = pyqtSignal(list, object)  # Emitted with list of dropped paths and keyboard modifiers

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
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setMouseTracking(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)  # Very important for drop functionality!

        self.placeholder_label = QLabel(self.viewport())
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.placeholder_label.setVisible(False)

        # Load the placeholder icon
        icon_path = Path(__file__).parent.parent / "assets/File_Folder_Drag_Drop.png"
        self.placeholder_icon = QPixmap(str(icon_path))

        # Safe usage only if it's OK
        if not self.placeholder_icon.isNull():
            scaled = self.placeholder_icon.scaled(160, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.placeholder_label.setPixmap(scaled)
            logger.debug(f"Successfully loaded placeholder icon from {icon_path}")
        else:
            logger.warning("Placeholder icon could not be loaded.")

        # Selection state (custom selection model)
        self.selected_rows: set[int] = set()  # Keeps track of currently selected rows
        self.anchor_row: int | None = None    # Used for shift-click range selection

        # Enable hover visuals via delegate
        self.hover_delegate = HoverItemDelegate(self, hover_color="#3e5c76")
        self.setItemDelegate(self.hover_delegate)

        # Used for right-click visual indication
        self.context_focused_row: int | None = None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.placeholder_label:
            self.placeholder_label.resize(self.viewport().size())
            self.placeholder_label.move(0, 0)

    def set_placeholder_visible(self, visible: bool) -> None:
        """
        Shows or hides the placeholder icon over the table (only image, no text).
        """
        assert self.model() is not None, "Cannot show placeholder: model has not been set on FileTableView"

        if visible and not self.placeholder_icon.isNull():
            self.placeholder_label.raise_()
            self.placeholder_label.show()
        else:
            self.placeholder_label.hide()
            self.viewport().update()

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

        if modifiers & Qt.ShiftModifier:  # type: ignore
            if self._manual_anchor_index is None:
                self._manual_anchor_index = index
                logger.debug(f"[Anchor] Initialized at row {index.row()} (no previous anchor)")
            else:
                selection = QItemSelection(self._manual_anchor_index, index)
                sm.select(selection, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)  # type: ignore
                sm.setCurrentIndex(index, QItemSelectionModel.NoUpdate)  # type: ignore
                logger.debug(f"[Anchor] Shift-select from {self._manual_anchor_index.row()} to {index.row()}")

        elif modifiers & Qt.ControlModifier:  # type: ignore
            self._manual_anchor_index = index
            row = index.row()
            selection = QItemSelection(index, index)
            sm.blockSignals(True)
            if sm.isSelected(index):
                sm.select(selection, QItemSelectionModel.Deselect | QItemSelectionModel.Rows)  # type: ignore
                logger.debug(f"[Anchor] Ctrl-toggle OFF at row {row}")
            else:
                sm.select(selection, QItemSelectionModel.Select | QItemSelectionModel.Rows)  # type: ignore
                logger.debug(f"[Anchor] Ctrl-toggle ON at row {row}")
            sm.blockSignals(False)
            sm.setCurrentIndex(index, QItemSelectionModel.NoUpdate)  # type: ignore
            # Force row update
            left = model.index(row, 0)
            right = model.index(row, model.columnCount() - 1)
            self.viewport().update(self.visualRect(left).united(self.visualRect(right)))

        else:
            self._manual_anchor_index = index
            sm.select(index, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)  # type: ignore
            sm.setCurrentIndex(index, QItemSelectionModel.NoUpdate)  # type: ignore
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

        # Left click logic (range, ctrl, shift, etc.)
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
        Adds custom MIME type marker to identify drags originating from our file table.
        """
        rows = sorted(self.selected_rows)
        if not rows:
            return

        file_items = [self.model().files[r] for r in rows if 0 <= r < len(self.model().files)]
        file_paths = [f.full_path for f in file_items if f.full_path]

        if not file_paths:
            return

        # Get the global drag cancel filter
        from widgets.file_tree_view import _drag_cancel_filter

        # Activate the filter to catch events that should terminate drag
        _drag_cancel_filter.activate()

        # Create MIME data with custom marker
        mime_data = QMimeData()

        # Add our custom MIME type to identify this drag as coming from the file table
        # This is used by the metadata tree view to only accept drags from our application
        mime_data.setData("application/x-oncutf-filetable", b"1")

        # Add standard URL format for file paths
        urls = [QUrl.fromLocalFile(p) for p in file_paths]
        mime_data.setUrls(urls)

        # Create and execute the drag operation
        drag = QDrag(self)
        drag.setMimeData(mime_data)

        try:
            # Use exec() instead of exec_ (which is Python 2 compatible name)
            # Execute drag with all possible actions to ensure proper termination
            result = drag.exec(Qt.CopyAction | Qt.MoveAction | Qt.LinkAction)
            logger.debug(f"Drag completed with result: {result}")
        except Exception as e:
            logger.error(f"Drag operation failed: {e}")
        finally:
            # Force complete cleanup of any lingering drag state
            while QApplication.overrideCursor():
                QApplication.restoreOverrideCursor()

            # Deactivate the filter
            _drag_cancel_filter.deactivate()

            # Force repaint to clear any visual artifacts
            if hasattr(self, 'viewport') and callable(getattr(self.viewport(), 'update', None)):
                self.viewport().update()
            # Force immediate processing of all pending events
            QApplication.processEvents()

        # Create a zero-delay timer to ensure complete cleanup after event loop returns
        QTimer.singleShot(0, self._complete_drag_cleanup)

    def _complete_drag_cleanup(self):
        """
        Additional cleanup method called after drag operation to ensure
        all drag state is completely reset.
        """
        # Get the global drag cancel filter to ensure it's deactivated
        from widgets.file_tree_view import _drag_cancel_filter
        _drag_cancel_filter.deactivate()

        # Restore cursor if needed
        while QApplication.overrideCursor():
            QApplication.restoreOverrideCursor()

        if hasattr(self, 'viewport') and callable(getattr(self.viewport(), 'update', None)):
            self.viewport().update()
        QApplication.processEvents()

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

    def dragEnterEvent(self, event):
        logger.debug(f"[DragDrop] dragEnterEvent! formats={event.mimeData().formats()}")
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
        """
        Handles drop events for files/folders into the file table.

        - Ignores internal drags (from this same QTableView).
        - Filters out files that are already present in the model.
        - Emits signal with unique new files to be loaded.
        """
        mime_data = event.mimeData()

        # 1. Ignore internal drag-drop from this same view
        if mime_data.hasFormat("application/x-oncutf-filetable"):
            logger.debug("[Drop] Ignoring internal drag-drop from file table")
            return

        # 2. Extract paths from mime data (uses helper)
        modifiers = event.keyboardModifiers()
        dropped_paths = extract_file_paths(mime_data)

        if not dropped_paths:
            logger.debug("[Drop] No valid file paths extracted")
            return

        logger.info(f"[Drop] {len(dropped_paths)} file(s)/folder(s) dropped in table view")

        # 3. Remove duplicates (already loaded files)
        if self.model() and hasattr(self.model(), "files"):
            existing_paths = {f.full_path for f in self.model().files}
            new_paths = [p for p in dropped_paths if p not in existing_paths]
            if not new_paths:
                logger.debug("[Drop] All dropped files already exist in table. Ignored.")
                return
        else:
            new_paths = dropped_paths

        # 4. Emit signal with unique new files
        self.files_dropped.emit(new_paths, modifiers)

        # 5. Finalize
        event.acceptProposedAction()
        logger.debug("Drag completed with result: %s", event.dropAction())
