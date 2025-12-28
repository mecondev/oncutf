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

from typing import TYPE_CHECKING, Protocol

from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.core.pyqt_imports import QItemSelection
    from oncutf.core.selection.selection_store import SelectionStore

logger = get_cached_logger(__name__)


class SelectableWidget(Protocol):
    """Protocol defining requirements for widgets that can use SelectionBehavior."""

    def selectionModel(self):
        """Return the selection model."""
        ...

    def model(self):
        """Return the data model."""
        ...

    def blockSignals(self, block: bool) -> bool:
        """Block/unblock signals."""
        ...

    def viewport(self):
        """Return the viewport widget."""
        ...


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

    def _setup(self) -> None:
        """Set up behavior-specific initialization."""
        # Connect to Qt selection model if available
        if hasattr(self.widget, "selectionModel") and callable(self._widget.selectionModel):
            selection_model = self._widget.selectionModel()
            if selection_model:
                # Note: Using pyqtSignal directly; this would need proper disconnect in cleanup
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
                # ApplicationContext not ready
                logger.debug(
                    "[SelectionBehavior] ApplicationContext not ready for SelectionStore",
                    extra={"dev_only": True},
                )
        return self._selection_store

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
            # Get current Qt selection
            selection_model = self._widget.selectionModel()
            if selection_model:
                selected_indexes = selection_model.selectedRows()
                selected_rows = {idx.row() for idx in selected_indexes}

                # Update SelectionStore if available
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
        # Update SelectionStore
        if self.selection_store:
            self.selection_store.set_selected_rows(selected_rows, emit_signal=emit_signal)

        # Synchronize Qt selection model
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

        # Temporarily block signals to avoid recursion
        self._processing_selection_change = True
        try:
            # Clear existing selection
            selection_model.clearSelection()

            if not selected_rows:
                return

            # Build Qt selection
            selection = QItemSelection()
            for row in sorted(selected_rows):
                if 0 <= row < model.rowCount():
                    index = model.index(row, 0)
                    # Select entire row
                    last_col = model.columnCount() - 1
                    last_index = model.index(row, last_col)
                    selection.select(index, last_index)

            # Apply selection
            selection_model.select(selection, QItemSelectionModel.Select | QItemSelectionModel.Rows)

        finally:
            self._processing_selection_change = False

    def set_anchor_row(self, row: int | None) -> None:
        """Set the anchor row for range selections.

        Args:
            row: Row index to use as anchor, or None to clear

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
        # Try SelectionStore first
        if self.selection_store:
            return self.selection_store.get_selected_rows()

        # Fallback to Qt selection model
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

        # Get current selection
        current_selection = set()
        if self.selection_store:
            current_selection = self.selection_store.get_selected_rows()

        # Compute inverted selection
        all_rows = set(range(model.rowCount()))
        inverted = all_rows - current_selection

        self.update_selection_store(inverted, emit_signal=True)

    def cleanup(self) -> None:
        """Clean up behavior resources.

        Disconnects signals and clears references.
        Should be called when the widget is destroyed.
        """
        # Disconnect from Qt selection model
        if hasattr(self.widget, "selectionModel") and callable(self._widget.selectionModel):
            selection_model = self._widget.selectionModel()
            if selection_model:
                from contextlib import suppress

                with suppress(TypeError):
                    # Signal might not be connected
                    selection_model.selectionChanged.disconnect(self._on_qt_selection_changed)

        logger.debug(
            "[SelectionBehavior] Cleaned up for widget %s",
            self._widget.__class__.__name__,
            extra={"dev_only": True},
        )


__all__ = ["SelectionBehavior"]
