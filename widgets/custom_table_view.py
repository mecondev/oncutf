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
from PyQt5.QtCore import QMimeData, QUrl, QItemSelectionModel, QItemSelection, Qt, QPoint, QModelIndex, QTimer
from PyQt5.QtGui import QKeySequence, QDrag, QMouseEvent, QCursor, QPixmap, QPainter, QFont, QColor

# Fix import to use relative import instead of absolute
try:
    # When imported normally from main application
    from .hover_delegate import HoverItemDelegate
except ImportError:
    # When run directly (for testing/debugging)
    import sys, os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    try:
        from widgets.hover_delegate import HoverItemDelegate
    except ImportError:
        # Fallback when run directly from the widgets directory
        from hover_delegate import HoverItemDelegate

from PyQt5.QtCore import pyqtSignal
from utils.logger_helper import get_logger
from utils.file_drop_helper import analyze_drop, filter_allowed_files, ask_recursive_dialog, show_rejected_dialog

logger = get_logger(__name__)

# Add a guard for direct execution
if __name__ == "__main__":
    logger.info("This module is not meant to be run directly. Please run main.py instead.")

class CustomTableView(QTableView):
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

        self.placeholder_label = QLabel(self)
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.placeholder_label.setWordWrap(True)
        self.placeholder_label.setStyleSheet("color: #777; font-size: 14px;")
        self.placeholder_label.setPixmap(QPixmap(":/assets/File_Folder_Drag_Drop.png").scaled(160, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.placeholder_label.setText("\nDrag & Drop\nfiles or folder\nhere to start")
        self.placeholder_label.setTextInteractionFlags(Qt.NoTextInteraction)
        self.placeholder_label.setVisible(False)

        # Selection state (custom selection model)
        self.selected_rows: set[int] = set()  # Keeps track of currently selected rows
        self.anchor_row: int | None = None    # Used for shift-click range selection

        # Enable hover visuals via delegate
        self.hover_delegate = HoverItemDelegate(self, hover_color="#3e5c76")
        self.setItemDelegate(self.hover_delegate)

        # Used for right-click visual indication
        self.context_focused_row: int | None = None

        self.placeholder_message = ""
        self.placeholder_icon = QPixmap("assets/File_Folder_Drag_Drop.png")
        if self.placeholder_icon.isNull():
            logger.warning("Placeholder icon could not be loaded. Displaying text only.")
            self.placeholder_message = "Drag & Drop files or folder here to start"

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.placeholder_label:
            self.placeholder_label.resize(self.viewport().size())
            self.placeholder_label.move(0, 0)

    def set_placeholder_visible(self, visible: bool, text: str = None) -> None:
        if visible:
            if text:
                self.placeholder_label.setText(text)
            self.placeholder_label.show()
        else:
            self.placeholder_label.hide()

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
        from widgets.custom_tree_view import _drag_cancel_filter

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
        from widgets.custom_tree_view import _drag_cancel_filter
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

    def paintEvent(self, event):
        super().paintEvent(event)
        model = self.model()
        # Display placeholder if there are no files or the model is empty
        show_placeholder = False
        if model is None:
            show_placeholder = True
        elif hasattr(model, "files"):
            # FileTableModel
            show_placeholder = not getattr(model, "files", None)
        elif model.rowCount() == 0:
            show_placeholder = True
        elif model.rowCount() == 1 and all(model.data(model.index(0, c)) in (None, "", "No files loaded", "No folder selected") for c in range(model.columnCount())):
            show_placeholder = True

        if show_placeholder:
            painter = QPainter(self.viewport())
            rect = self.viewport().rect()
            center_x = rect.width() // 2
            center_y = rect.height() // 2

            # Icon
            icon_size = 160
            if not self.placeholder_icon.isNull():
                icon = self.placeholder_icon.scaled(icon_size, icon_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                icon_x = center_x - icon.width() // 2
                icon_y = center_y - icon.height() // 2
                painter.drawPixmap(icon_x, icon_y, icon)

            # Message
            font = QFont(self.font())
            font.setPointSize(14)
            painter.setFont(font)
            painter.setPen(QColor("#888888"))
            metrics = painter.fontMetrics()
            text = self.placeholder_message
            text_width = metrics.horizontalAdvance(text)
            text_x = center_x - text_width // 2
            text_y = center_y + icon_size // 2 - 80
            painter.drawText(text_x, text_y, text)
            painter.end()

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

    def dropEvent(self, event):
        """
        Handles drag & drop events for the file table using modular logic from file_drop_helper.
        Only allowed files are loaded, and custom dialogs are shown for recursive and rejected cases.
        """
        logger.debug("[DragDrop] dropEvent called!")

        paths = []
        if event.mimeData().hasUrls():
            paths = [url.toLocalFile() for url in event.mimeData().urls()]
        elif event.mimeData().hasFormat("application/x-oncutf-internal"):
            path_data = event.mimeData().data("application/x-oncutf-internal")
            try:
                path = bytes(path_data).decode()
                if path:
                    paths = [path]
            except Exception as e:
                logger.error(f"[DragDrop] Error decoding internal path: {e}")
                event.ignore()
                return
        else:
            super().dropEvent(event)
            return

        # Remove empty paths
        valid_paths = [p for p in paths if p]
        if not valid_paths:
            logger.warning("[DragDrop] No valid paths found in drop event")
            event.ignore()
            return

        drop_info = analyze_drop(valid_paths)
        drop_type = drop_info["type"]
        folders = drop_info["folders"]
        files = drop_info["files"]
        rejected = drop_info["rejected"]

        accepted_files = []

        if drop_type == "single_folder":
            # Ask for recursive
            # recursive = ask_recursive_dialog(folders[0])
            recursive = False  # Απενεργοποιήθηκε προσωρινά το dialog για δοκιμή
            # Scan for files
            import glob
            import os
            pattern = "**/*" if recursive else "*"
            all_files = [os.path.join(dp, f) for dp, dn, filenames in os.walk(folders[0]) for f in filenames] if recursive else [os.path.join(folders[0], f) for f in os.listdir(folders[0]) if os.path.isfile(os.path.join(folders[0], f))]
            allowed, rejected_files = filter_allowed_files(all_files)
            accepted_files.extend(allowed)
            # if rejected_files:
            #     show_rejected_dialog(rejected_files)
        elif drop_type == "files":
            allowed, rejected_files = filter_allowed_files(files)
            accepted_files.extend(allowed)
            # if rejected_files:
            #     show_rejected_dialog(rejected_files)
        elif drop_type in ("multiple_folders", "mixed"):
            # show_rejected_dialog(folders + files)
            pass
        else:
            logger.warning(f"[DragDrop] Unknown or unsupported drop type: {drop_type}")
            event.ignore()
            return

        if not accepted_files:
            logger.info("[DragDrop] No accepted files to load after filtering.")
            event.ignore()
            return

        # Accept the event BEFORE emitting the signal
        event.accept()
        self.setFocus()
        # Emit signal with accepted files and modifiers
        modifiers = QApplication.keyboardModifiers()
        self.files_dropped.emit(accepted_files, modifiers)
