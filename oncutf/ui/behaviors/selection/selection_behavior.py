"""Selection behavior for table widgets.

Author: Michael Economou
Date: 2025-12-28

Composition-based selection management that can be attached to QTableView widgets.
This is an example of the new behavior pattern as an alternative to mixins.

Usage:
    class MyTableView(QTableView):
        def __init__(self, parent=None):
            super().__init__(parent)
            from oncutf.core.application_context import get_app_context
            self.selection_behavior = SelectionBehavior(
                widget=self,
                selection_store=get_app_context().selection_store
            )
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from oncutf.ui.behaviors.selection.protocols import SelectableWidget
from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.core.pyqt_imports import QItemSelection, QModelIndex, Qt
    from oncutf.core.selection.selection_store import SelectionStore

logger = get_cached_logger(__name__)


class SelectionBehavior:
    """Manages selection state for table view widgets via composition.

    This behavior provides:
    - Integration with SelectionStore for centralized selection state
    - Synchronization between Qt's selection model and application state
    - Anchor row tracking for range selections
    - Modifier key handling (Ctrl for toggle, Shift for range)
    - Bulk selection operations

    This is a composition-based alternative to SelectionMixin for NEW widgets.
    Existing mixins should NOT be replaced unless there's a specific reason.
    """

    def __init__(
        self,
        widget: SelectableWidget,
        selection_store: SelectionStore | None = None,
    ) -> None:
        """Initialize selection behavior.

        Args:
            widget: The widget to manage selection for (must implement SelectableWidget)
            selection_store: Optional SelectionStore instance. If None, will attempt
                to get from ApplicationContext during operation.
        """
        self._widget = widget
        self._selection_store = selection_store
        self._anchor_row: int | None = None
        self._processing_selection_change = False
        self._ensuring_selection = False
        self._manual_anchor_index: QModelIndex | None = None

    def _setup(self) -> None:
        """Set up behavior-specific initialization."""
        # Connect to Qt selection model if available
        if hasattr(self.widget, "selectionModel") and callable(self._widget.selectionModel):
            selection_model = self._widget.selectionModel()
            if selection_model:
                selection_model.selectionChanged.connect(self._on_qt_selection_changed)

    @property
    def selection_store(self) -> SelectionStore | None:
        """Get SelectionStore with lazy initialization fallback."""
        if self._selection_store is None:
            try:
                from oncutf.core.application_context import get_app_context

                context = get_app_context()
                self._selection_store = context.selection_store
            except RuntimeError:
                logger.debug(
                    "[SelectionBehavior] ApplicationContext not ready for SelectionStore",
                    extra={"dev_only": True},
                )
        return self._selection_store

    def get_selection_store(self) -> SelectionStore | None:
        """Get SelectionStore instance (method form for backward compatibility)."""
        return self.selection_store

    def _on_qt_selection_changed(
        self, selected: QItemSelection, deselected: QItemSelection
    ) -> None:
        """Handle Qt selection model changes.

        Args:
            selected: Newly selected items
            deselected: Newly deselected items
        """
        if self._processing_selection_change:
            return

        self._processing_selection_change = True
        try:
            selection_model = self._widget.selectionModel()
            if selection_model:
                selected_indexes = selection_model.selectedRows()
                selected_rows = {idx.row() for idx in selected_indexes}

                if self.selection_store:
                    self.selection_store.set_selected_rows(selected_rows, emit_signal=True)

        finally:
            self._processing_selection_change = False

    def update_selection_store(
        self, selected_rows: set[int], emit_signal: bool = True
    ) -> None:
        """Update SelectionStore and Qt selection model with new selection.

        Args:
            selected_rows: Set of row indices to select
            emit_signal: Whether to emit selection changed signal
        """
        if self.selection_store:
            self.selection_store.set_selected_rows(selected_rows, emit_signal=emit_signal)

        self._sync_qt_selection_model(selected_rows)

    def _sync_qt_selection_model(self, selected_rows: set[int]) -> None:
        """Synchronize Qt selection model with given selection.

        Args:
            selected_rows: Set of row indices to select in Qt model
        """
        from oncutf.core.pyqt_imports import QItemSelection, QItemSelectionModel

        selection_model = self._widget.selectionModel()
        if not selection_model:
            return

        model = self._widget.model()
        if not model:
            return

        self._processing_selection_change = True
        try:
            selection_model.clearSelection()

            if not selected_rows:
                return

            selection = QItemSelection()
            for row in sorted(selected_rows):
                if 0 <= row < model.rowCount():
                    index = model.index(row, 0)
                    last_col = model.columnCount() - 1
                    last_index = model.index(row, last_col)
                    selection.select(index, last_index)

            selection_model.select(
                selection, QItemSelectionModel.Select | QItemSelectionModel.Rows
            )

        finally:
            self._processing_selection_change = False

    def set_anchor_row(self, row: int | None, *, emit_signal: bool = True) -> None:
        """Set the anchor row for range selections.

        Args:
            row: Row index to use as anchor, or None to clear
            emit_signal: Whether to emit the anchor_changed signal (default: True)
        """
        self._anchor_row = row
        logger.debug(
            "[SelectionBehavior] Anchor row set to %s", row, extra={"dev_only": True}
        )

    def get_anchor_row(self) -> int | None:
        """Get the current anchor row.

        Returns:
            Anchor row index or None if not set
        """
        return self._anchor_row

    def get_current_selection(self) -> set[int]:
        """Get current selection from SelectionStore.

        Returns:
            Set of selected row indices
        """
        if self.selection_store:
            return self.selection_store.get_selected_rows()
        return set()

    def get_current_selection_safe(self) -> set[int]:
        """Get current selection safely (fallback to Qt model if store unavailable).

        Returns:
            Set of selected row indices
        """
        if self.selection_store:
            return self.selection_store.get_selected_rows()

        selection_model = self._widget.selectionModel()
        if selection_model:
            selected_indexes = selection_model.selectedRows()
            return {idx.row() for idx in selected_indexes}

        return set()

    def select_all(self) -> None:
        """Select all rows in the widget."""
        model = self._widget.model()
        if not model:
            return

        row_count = model.rowCount()
        all_rows = set(range(row_count))
        self.update_selection_store(all_rows, emit_signal=True)

    def clear_selection(self) -> None:
        """Clear all selection."""
        self.update_selection_store(set(), emit_signal=True)

    def invert_selection(self) -> None:
        """Invert the current selection."""
        model = self._widget.model()
        if not model:
            return

        current_selection = set()
        if self.selection_store:
            current_selection = self.selection_store.get_selected_rows()

        all_rows = set(range(model.rowCount()))
        inverted = all_rows - current_selection

        self.update_selection_store(inverted, emit_signal=True)

    def ensure_anchor_or_select(
        self, index: QModelIndex, modifiers: Qt.KeyboardModifiers
    ) -> None:
        """Handle selection logic with anchor and modifier support.

        Implements Windows Explorer-like selection behavior:
        - No modifier: Clear and select
        - Shift: Range selection from anchor to clicked
        - Ctrl: Toggle selection of clicked item

        Args:
            index: QModelIndex of clicked item
            modifiers: Qt keyboard modifiers (Shift, Ctrl, etc.)
        """
        from oncutf.core.pyqt_imports import Qt

        if self._ensuring_selection:
            logger.debug(
                "[SelectionBehavior] ensure_anchor_or_select already running, skipping"
            )
            return

        self._ensuring_selection = True
        try:
            sm = self._widget.selectionModel()
            model = self._widget.model()
            if sm is None or model is None:
                return

            if modifiers & Qt.ShiftModifier:
                self._handle_shift_selection(sm, model, index)
            elif modifiers & Qt.ControlModifier:
                self._handle_ctrl_selection(sm, model, index)
            else:
                self._handle_simple_selection(sm, model, index)

        finally:
            self._ensuring_selection = False

    def _handle_shift_selection(self, sm, model, index: QModelIndex) -> None:
        """Handle Shift+Click range selection.

        Args:
            sm: Selection model
            model: Data model
            index: Clicked index
        """
        from oncutf.core.pyqt_imports import QItemSelection, QItemSelectionModel

        selected_indexes = sm.selectedRows()
        current_selection = {idx.row() for idx in selected_indexes}
        clicked_row = index.row()

        if clicked_row in current_selection:
            sm.setCurrentIndex(index, QItemSelectionModel.NoUpdate)
        else:
            if self._manual_anchor_index is None:
                if selected_indexes:
                    self._manual_anchor_index = selected_indexes[0]
            else:
                self._manual_anchor_index = index

            selection = QItemSelection(self._manual_anchor_index, index)
            self._widget.blockSignals(True)
            try:
                sm.select(
                    selection,
                    QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows,
                )
                sm.setCurrentIndex(index, QItemSelectionModel.NoUpdate)
            finally:
                self._widget.blockSignals(False)

        if self.selection_store:
            current_qt_selection = {idx.row() for idx in sm.selectedRows()}
            self.selection_store.set_selected_rows(current_qt_selection, emit_signal=False)
            if self._manual_anchor_index:
                self.selection_store.set_anchor_row(
                    self._manual_anchor_index.row(), emit_signal=False
                )

        self._update_row_visual(model, index.row())

    def _handle_ctrl_selection(self, sm, model, index: QModelIndex) -> None:
        """Handle Ctrl+Click toggle selection.

        Args:
            sm: Selection model
            model: Data model
            index: Clicked index
        """
        from oncutf.core.pyqt_imports import QItemSelectionModel

        self._manual_anchor_index = index
        row = index.row()

        was_selected = sm.isSelected(index)

        if was_selected:
            sm.select(index, QItemSelectionModel.Deselect | QItemSelectionModel.Rows)
        else:
            sm.select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows)

        sm.setCurrentIndex(index, QItemSelectionModel.NoUpdate)

        if self.selection_store:
            current_qt_selection = {idx.row() for idx in sm.selectedRows()}
            self.selection_store.set_selected_rows(current_qt_selection, emit_signal=False)
            self.selection_store.set_anchor_row(row, emit_signal=False)

        self._update_row_visual(model, row)

    def _handle_simple_selection(self, sm, model, index: QModelIndex) -> None:
        """Handle simple click selection (no modifiers).

        Args:
            sm: Selection model
            model: Data model
            index: Clicked index
        """
        from oncutf.core.pyqt_imports import QItemSelectionModel

        self._manual_anchor_index = index
        sm.select(index, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)
        sm.setCurrentIndex(index, QItemSelectionModel.NoUpdate)

        if self.selection_store:
            current_qt_selection = {idx.row() for idx in sm.selectedRows()}
            self.selection_store.set_selected_rows(current_qt_selection, emit_signal=False)
            self.selection_store.set_anchor_row(index.row(), emit_signal=False)

        self._update_row_visual(model, index.row())

    def _update_row_visual(self, model, row: int) -> None:
        """Force visual update for a row.

        Args:
            model: Data model
            row: Row index to update
        """
        left = model.index(row, 0)
        right = model.index(row, model.columnCount() - 1)
        self._widget.viewport().update(
            self._widget.visualRect(left).united(self._widget.visualRect(right))
        )

    def select_rows_range(self, start_row: int, end_row: int) -> None:
        """Select a range of rows efficiently using batch selection.

        Args:
            start_row: Starting row index
            end_row: Ending row index (inclusive)
        """
        from oncutf.core.pyqt_imports import QItemSelection, QItemSelectionModel

        self._widget.blockSignals(True)
        selection_model = self._widget.selectionModel()
        model = self._widget.model()

        if selection_model is None or model is None:
            self._widget.blockSignals(False)
            return

        if hasattr(model, "index") and hasattr(model, "columnCount"):
            min_row = min(start_row, end_row)
            max_row = max(start_row, end_row)
            top_left = model.index(min_row, 0)
            bottom_right = model.index(max_row, model.columnCount() - 1)
            selection = QItemSelection(top_left, bottom_right)
            selection_model.select(
                selection, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows
            )

        self._widget.blockSignals(False)

        if hasattr(self._widget, "viewport"):
            self._widget.viewport().update()

        if model is not None:
            min_row = min(start_row, end_row)
            max_row = max(start_row, end_row)
            selected_rows = set(range(min_row, max_row + 1))
            self.update_selection_store(selected_rows, emit_signal=True)

    def select_dropped_files(self, file_paths: list[str] | None = None) -> None:
        """Select specific files that were just dropped/loaded in the table.

        Args:
            file_paths: List of file paths to select (None = select all)
        """
        from oncutf.core.pyqt_imports import QItemSelection, Qt

        model = self._widget.model()
        if not model or not hasattr(model, "files"):
            logger.error("[SelectionBehavior] No model or model has no files attribute")
            return

        if not file_paths:
            row_count = len(model.files)
            if row_count == 0:
                logger.debug(
                    "[SelectionBehavior] No files in model - returning early",
                    extra={"dev_only": True},
                )
                return
            logger.debug(
                "[SelectionBehavior] Fallback: selecting all %d files",
                row_count,
                extra={"dev_only": True},
            )
            self.select_rows_range(0, row_count - 1)
            return

        rows_to_select = []
        for i, file_item in enumerate(model.files):
            if file_item.full_path in file_paths:
                rows_to_select.append(i)

        if not rows_to_select:
            logger.debug(
                "[SelectionBehavior] No matching files found", extra={"dev_only": True}
            )
            return

        if self._widget.keyboardModifiers() != Qt.NoModifier:
            self._widget.clearSelection()

        selection_model = self._widget.selectionModel()
        if not selection_model:
            logger.error("[SelectionBehavior] No selection model available")
            return

        self._widget.blockSignals(True)

        full_selection = QItemSelection()

        for row in rows_to_select:
            if 0 <= row < len(model.files):
                left_index = model.index(row, 0)
                right_index = model.index(row, model.columnCount() - 1)
                if left_index.isValid() and right_index.isValid():
                    row_selection = QItemSelection(left_index, right_index)
                    full_selection.merge(row_selection, selection_model.Select)

        if not full_selection.isEmpty():
            selection_model.select(full_selection, selection_model.Select)

        self._widget.blockSignals(False)

        selected_rows = set(rows_to_select)
        self.update_selection_store(selected_rows, emit_signal=True)

        if hasattr(self._widget, "viewport"):
            self._widget.viewport().update()

    def sync_selection_safely(self) -> None:
        """Sync selection state with SelectionStore."""
        if self.selection_store:
            selected_indexes = self._widget.selectionModel().selectedRows()
            current_qt_selection = {idx.row() for idx in selected_indexes}
            self.selection_store.set_selected_rows(current_qt_selection, emit_signal=True)
            return

        parent = getattr(self._widget, "window", lambda: None)()
        if parent and hasattr(parent, "sync_selection_to_checked"):
            from oncutf.core.pyqt_imports import QItemSelection

            selection = self._widget.selectionModel().selection()
            parent.sync_selection_to_checked(selection, QItemSelection())

    def handle_selection_changed(
        self, selected: QItemSelection, deselected: QItemSelection
    ) -> None:
        """Handle Qt selectionChanged signal.

        Args:
            selected: Newly selected items
            deselected: Newly deselected items
        """
        if self._processing_selection_change:
            return

        self._processing_selection_change = True
        try:
            selection_model = self._widget.selectionModel()
            if selection_model is not None:
                selected_indexes = selection_model.selectedRows()
                selected_rows = {idx.row() for idx in selected_indexes}

                if not selected_rows and hasattr(self._widget, "_is_dragging"):
                    is_dragging = getattr(self._widget, "_is_dragging", False)
                    if is_dragging:
                        return

                self.update_selection_store(selected_rows, emit_signal=True)

            if hasattr(self._widget, "viewport"):
                self._widget.viewport().update()
        finally:
            self._processing_selection_change = False

    def cleanup(self) -> None:
        """Clean up behavior resources."""
        if hasattr(self.widget, "selectionModel") and callable(self._widget.selectionModel):
            selection_model = self._widget.selectionModel()
            if selection_model:
                from contextlib import suppress

                with suppress(TypeError):
                    selection_model.selectionChanged.disconnect(self._on_qt_selection_changed)

        logger.debug(
            "[SelectionBehavior] Cleaned up for widget %s",
            self._widget.__class__.__name__,
            extra={"dev_only": True},
        )


__all__ = ["SelectionBehavior"]
