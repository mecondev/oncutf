"""Module: selection_mixin.py

Author: Michael Economou
Date: 2025-12-04

SelectionMixin - Reusable selection management for QTableView-based widgets.

Provides:
- SelectionStore integration
- Qt selection model synchronization
- Anchor row management
- Range and bulk selection operations
- Modifier key handling (Ctrl, Shift)
"""

from oncutf.core.application_context import get_app_context
from oncutf.core.pyqt_imports import (
    QItemSelection,
    QItemSelectionModel,
    QModelIndex,
    Qt,
)
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class SelectionMixin:
    """Mixin providing selection management functionality for QTableView widgets.

    This mixin handles:
    - Integration with SelectionStore for centralized selection state
    - Synchronization between Qt's selection model and application state
    - Anchor row tracking for range selections
    - Modifier key handling (Ctrl for toggle, Shift for range)
    - Bulk selection operations

    Required attributes on parent class:
    - self.selected_rows: set - Legacy selection state
    - self.anchor_row: int | None - Legacy anchor state
    - self._legacy_selection_mode: bool - Flag for legacy mode
    - self._manual_anchor_index: QModelIndex | None - Manual anchor for Shift selection
    - self._processing_selection_change: bool - Flag to prevent loops
    - self._ensuring_selection: bool - Flag to prevent recursion

    Required methods on parent class:
    - self.selectionModel() - Qt selection model getter
    - self.model() - Qt model getter
    - self.blockSignals() - Signal blocking
    - self.viewport() - Viewport getter
    - self.visualRect() - Visual rect getter
    - self.clearSelection() - Clear selection
    - self.keyboardModifiers() - Get keyboard modifiers
    """

    def _get_selection_store(self):
        """Get SelectionStore from ApplicationContext with fallback to None."""
        try:
            context = get_app_context()
            return context.selection_store
        except RuntimeError:
            # ApplicationContext not ready yet
            return None

    def _update_selection_store(self, selected_rows: set, emit_signal: bool = True) -> None:
        """Update SelectionStore and Qt selection model with new selection.

        Args:
            selected_rows: Set of row indices to select
            emit_signal: Whether to emit selection changed signal

        """
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
        """Optimized batch synchronization of Qt's selection model.

        Uses batch selection instead of row-by-row to improve performance
        with large selections.

        Args:
            selected_rows: Set of row indices to sync

        """
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

        except Exception:
            logger.exception("[SyncQt] Error syncing selection")

    def _get_current_selection(self) -> set:
        """Get current selection from SelectionStore or fallback to Qt model.

        Returns:
            Set of currently selected row indices

        """
        selection_store = self._get_selection_store()
        if selection_store and not self._legacy_selection_mode:
            return selection_store.get_selected_rows()
        else:
            # Fallback: get from Qt selection model (more reliable than legacy)
            from oncutf.utils.ui.selection_provider import get_selected_row_set

            selection_model = self.selectionModel()
            qt_selection = get_selected_row_set(selection_model)
            # Update legacy state to match Qt
            self.selected_rows = qt_selection
            return qt_selection

    def _get_current_selection_safe(self) -> set:
        """Get current selection safely without SelectionStore dependency.

        This is a simplified version that directly queries Qt's selection model.

        Returns:
            Set of currently selected row indices

        """
        from oncutf.utils.ui.selection_provider import get_selected_row_set

        selection_model = self.selectionModel()
        return get_selected_row_set(selection_model)

    def _set_anchor_row(self, row: int | None, emit_signal: bool = True) -> None:
        """Set anchor row in SelectionStore or fallback to legacy.

        Args:
            row: Row index to set as anchor (None to clear)
            emit_signal: Whether to emit anchor changed signal

        """
        selection_store = self._get_selection_store()
        if selection_store and not self._legacy_selection_mode:
            selection_store.set_anchor_row(row, emit_signal=emit_signal)

        # Always update legacy state for compatibility
        self.anchor_row = row

    def _get_anchor_row(self) -> int | None:
        """Get anchor row from SelectionStore or fallback to legacy.

        Returns:
            Anchor row index or None if no anchor set

        """
        selection_store = self._get_selection_store()
        if selection_store and not self._legacy_selection_mode:
            return selection_store.get_anchor_row()
        else:
            return self.anchor_row

    def ensure_anchor_or_select(self, index: QModelIndex, modifiers: Qt.KeyboardModifiers) -> None:
        """Handle selection logic with anchor and modifier support.

        Implements Windows Explorer-like selection behavior:
        - No modifier: Clear and select
        - Shift: Range selection from anchor to clicked
        - Ctrl: Toggle selection of clicked item

        Args:
            index: QModelIndex of clicked item
            modifiers: Qt keyboard modifiers (Shift, Ctrl, etc.)

        """
        # Add protection against infinite loops
        if hasattr(self, "_ensuring_selection") and self._ensuring_selection:
            logger.debug("[SelectionMixin] ensure_anchor_or_select already running, skipping")
            return

        self._ensuring_selection = True
        try:
            sm = self.selectionModel()
            model = self.model()
            if sm is None or model is None:
                return

            if modifiers & Qt.ShiftModifier:
                # Check if we're clicking on an already selected item
                from oncutf.utils.ui.selection_provider import get_selected_row_set

                current_selection = get_selected_row_set(sm)
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
                    from oncutf.utils.ui.selection_provider import get_selected_row_set

                    current_qt_selection = get_selected_row_set(sm)
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
                    from oncutf.utils.ui.selection_provider import get_selected_row_set

                    current_qt_selection = get_selected_row_set(sm)
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
                    from oncutf.utils.ui.selection_provider import get_selected_row_set

                    current_qt_selection = get_selected_row_set(sm)
                    selection_store.set_selected_rows(current_qt_selection, emit_signal=False)
                    selection_store.set_anchor_row(index.row(), emit_signal=False)

                # Force visual update
                left = model.index(index.row(), 0)
                right = model.index(index.row(), model.columnCount() - 1)
                self.viewport().update(self.visualRect(left).united(self.visualRect(right)))

        finally:
            self._ensuring_selection = False

    def selectionChanged(self, selected, deselected) -> None:
        """Override Qt's selectionChanged to update SelectionStore.

        This ensures our application state stays in sync with Qt's selection model.

        Args:
            selected: QItemSelection of newly selected items
            deselected: QItemSelection of newly deselected items

        """
        # SIMPLIFIED: Only essential protection against infinite loops
        if hasattr(self, "_processing_selection_change") and self._processing_selection_change:
            return

        self._processing_selection_change = True
        try:
            super().selectionChanged(selected, deselected)  # type: ignore

            from oncutf.utils.ui.selection_provider import get_selected_row_set

            selection_model = self.selectionModel()
            if selection_model is not None:
                selected_rows = get_selected_row_set(selection_model)

                # OPTIMIZED: Only check for critical cases that need special handling
                if not selected_rows and hasattr(self, "_is_dragging") and self._is_dragging:
                    return

                # CRITICAL: Update SelectionStore with emit_signal=True to trigger preview update
                self._update_selection_store(selected_rows, emit_signal=True)

            if hasattr(self, "context_focused_row") and self.context_focused_row is not None:
                self.context_focused_row = None

            if hasattr(self, "viewport"):
                self.viewport().update()
        finally:
            self._processing_selection_change = False

    def select_rows_range(self, start_row: int, end_row: int) -> None:
        """Select a range of rows efficiently using batch selection.

        Args:
            start_row: Starting row index
            end_row: Ending row index (inclusive)

        """
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
            )

        self.blockSignals(False)

        if hasattr(self, "viewport"):
            self.viewport().update()

        if model is not None:
            # Ensure we always create range from lower to higher
            min_row = min(start_row, end_row)
            max_row = max(start_row, end_row)
            selected_rows = set(range(min_row, max_row + 1))
            self._update_selection_store(selected_rows, emit_signal=True)

    def select_dropped_files(self, file_paths: list[str] | None = None) -> None:
        """Select specific files that were just dropped/loaded in the table.

        Args:
            file_paths: List of file paths to select (None = select all)

        """
        model = self.model()
        if not model or not hasattr(model, "files"):
            logger.error("[SelectionMixin] No model or model has no files attribute")
            return

        if not file_paths:
            # Fallback: select all files if no specific paths provided
            row_count = len(model.files)
            if row_count == 0:
                logger.debug(
                    "[SelectionMixin] No files in model - returning early", extra={"dev_only": True}
                )
                return
            logger.debug(
                "[SelectionMixin] Fallback: selecting all %d files",
                row_count,
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
            logger.debug("[SelectionMixin] No matching files found", extra={"dev_only": True})
            return

        # Clear existing selection first only if there are modifiers
        if self.keyboardModifiers() != Qt.NoModifier:
            self.clearSelection()

        # Select the specific rows ALL AT ONCE using range selection
        selection_model = self.selectionModel()
        if not selection_model:
            logger.error("[SelectionMixin] No selection model available")
            return

        self.blockSignals(True)

        # Create a single selection for all rows
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

    def _sync_selection_safely(self) -> None:
        """Sync selection state with parent window or SelectionStore.

        This is typically called when selection needs to be synchronized
        with external components (e.g., checked files in parent window).
        """
        # First, try to sync with SelectionStore if available
        from oncutf.utils.ui.selection_provider import get_selected_row_set

        selection_store = self._get_selection_store()
        if selection_store and not self._legacy_selection_mode:
            current_qt_selection = get_selected_row_set(self.selectionModel())
            selection_store.set_selected_rows(current_qt_selection, emit_signal=True)
            return

        # Fallback: try parent window sync method
        parent = self.window()
        if hasattr(parent, "sync_selection_to_checked"):
            selection = self.selectionModel().selection()
            parent.sync_selection_to_checked(selection, QItemSelection())
