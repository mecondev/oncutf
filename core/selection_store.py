"""
Module: selection_store.py

Author: Michael Economou
Date: 2025-05-31

Selection Store - Centralized selection state management
This module provides centralized selection and checked state management,
eliminating the need for scattered parent_window traversals and improving performance.
Features:
- Unified selection and checked state tracking
- Event-driven updates via Qt signals
- Performance optimizations for large file sets
- Automatic synchronization between selection and checked states
"""

import time
from typing import Any

from core.pyqt_imports import QObject, QTimer, pyqtSignal
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class SelectionStore(QObject):
    """
    Centralized selection and checked state manager.

    Handles all selection-related logic previously scattered across
    MainWindow and FileTableView, providing better performance and
    maintainability through event-driven architecture.

    Features:
    - Fast selection state access (no parent traversals)
    - Automatic sync between selection and checked states
    - Batch operations for large selections
    - Performance tracking and optimization
    """

    # Signals for state changes
    selection_changed = pyqtSignal(list)  # Emitted when selected rows change
    checked_changed = pyqtSignal(list)  # Emitted when checked rows change
    anchor_changed = pyqtSignal(int)  # Emitted when anchor row changes

    # Combined signals for coordinated updates
    selection_sync_requested = pyqtSignal()  # Request sync from selection to checked
    checked_sync_requested = pyqtSignal()  # Request sync from checked to selection

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)

        # Core selection state
        self._selected_rows: set[int] = set()
        self._checked_rows: set[int] = set()
        self._anchor_row: int | None = None
        self._total_files: int = 0
        self._file_model: Any | None = None  # FileTableModel reference

        # Performance tracking
        self._last_operation_time = time.time()
        self._batch_operations: dict[str, int] = {}

        # Protection against infinite loops
        self._syncing_selection: bool = False

        # Loop protection
        self._syncing_selection: bool = False

        # OPTIMIZED: Faster debouncing timer for better responsiveness
        self._update_timer = QTimer(self)
        self._update_timer.setSingleShot(True)
        self._update_timer.setInterval(5)  # 5ms debounce for faster response
        self._update_timer.timeout.connect(self._emit_deferred_signals)

        # Pending signal emissions (for debouncing)
        self._pending_selection_signal = False
        self._pending_checked_signal = False

        logger.debug("SelectionStore initialized", extra={"dev_only": True})

    # =====================================
    # Selection State Management
    # =====================================

    def get_selected_rows(self) -> set[int]:
        """
        Get currently selected row indices.

        Returns:
            Set of selected row indices
        """
        return self._selected_rows.copy()

    def set_selected_rows(
        self, rows: set[int], *, emit_signal: bool = True, force_emit: bool = False
    ) -> None:
        """
        Set selected row indices with optimized debouncing.

        Args:
            rows: Set of row indices to select
            emit_signal: Whether to emit selection_changed signal
            force_emit: Whether to emit signal even if no change (for delayed updates)
        """
        # Protection against infinite loops during sync operations
        if self._syncing_selection:
            return

        if rows == self._selected_rows and not force_emit:
            return  # No change

        # old_count = len(self._selected_rows)
        self._selected_rows = rows.copy()
        # new_count = len(self._selected_rows)

        self._last_operation_time = time.time()

        # OPTIMIZED: Use debounced signal emission for better performance
        if emit_signal:
            self._schedule_selection_signal()

    def add_selected_rows(self, rows: set[int], *, emit_signal: bool = True) -> None:
        """
        Add rows to current selection.

        Args:
            rows: Set of row indices to add
            emit_signal: Whether to emit selection_changed signal
        """
        if not rows:
            return

        old_count = len(self._selected_rows)
        self._selected_rows.update(rows)
        new_count = len(self._selected_rows)

        if new_count != old_count:
            # OPTIMIZED: Use debounced signal emission
            if emit_signal:
                self._schedule_selection_signal()

    def remove_selected_rows(self, rows: set[int], *, emit_signal: bool = True) -> None:
        """
        Remove rows from current selection.

        Args:
            rows: Set of row indices to remove
            emit_signal: Whether to emit selection_changed signal
        """
        if not rows:
            return

        old_count = len(self._selected_rows)
        self._selected_rows.difference_update(rows)
        new_count = len(self._selected_rows)

        if new_count != old_count:
            # OPTIMIZED: Use debounced signal emission
            if emit_signal:
                self._schedule_selection_signal()

    def clear_selection(self, *, emit_signal: bool = True) -> None:
        """
        Clear all selected rows.

        Args:
            emit_signal: Whether to emit selection_changed signal
        """
        if not self._selected_rows:
            return

        self._selected_rows.clear()
        if emit_signal:
            self._schedule_selection_signal()

    # =====================================
    # Checked State Management
    # =====================================

    def get_checked_rows(self) -> set[int]:
        """
        Get currently checked row indices.

        Returns:
            Set of checked row indices
        """
        return self._checked_rows.copy()

    def set_checked_rows(self, rows: set[int], *, emit_signal: bool = True) -> None:
        """
        Set checked row indices.

        Args:
            rows: Set of row indices to check
            emit_signal: Whether to emit checked_changed signal
        """
        if rows == self._checked_rows:
            return  # No change

        old_count = len(self._checked_rows)
        self._checked_rows = rows.copy()
        new_count = len(self._checked_rows)

        if emit_signal and old_count != new_count:
            logger.debug(
                f"Synced selection->checked: {old_count} -> {new_count} rows",
                extra={"dev_only": True},
            )
            self._schedule_checked_signal()

    def add_checked_rows(self, rows: set[int], *, emit_signal: bool = True) -> None:
        """
        Add rows to checked state.

        Args:
            rows: Set of row indices to check
            emit_signal: Whether to emit checked_changed signal
        """
        if not rows:
            return

        old_count = len(self._checked_rows)
        self._checked_rows.update(rows)
        new_count = len(self._checked_rows)

        if new_count != old_count:
            logger.debug(
                f"Checked state extended: +{new_count - old_count} rows (total: {new_count})",
                extra={"dev_only": True},
            )
            if emit_signal:
                self._schedule_checked_signal()

    def remove_checked_rows(self, rows: set[int], *, emit_signal: bool = True) -> None:
        """
        Remove rows from checked state.

        Args:
            rows: Set of row indices to uncheck
            emit_signal: Whether to emit checked_changed signal
        """
        if not rows:
            return

        old_count = len(self._checked_rows)
        self._checked_rows.difference_update(rows)
        new_count = len(self._checked_rows)

        if new_count != old_count:
            logger.debug(
                f"Checked state reduced: -{old_count - new_count} rows (total: {new_count})",
                extra={"dev_only": True},
            )
            if emit_signal:
                self._schedule_checked_signal()

    def clear_checked(self, *, emit_signal: bool = True) -> None:
        """
        Clear all checked rows.

        Args:
            emit_signal: Whether to emit checked_changed signal
        """
        if not self._checked_rows:
            return

        self._checked_rows.clear()
        if emit_signal:
            self._schedule_checked_signal()

    # =====================================
    # Anchor Management
    # =====================================

    def get_anchor_row(self) -> int | None:
        """Get current anchor row for range selection."""
        return self._anchor_row

    def set_anchor_row(self, row: int | None, *, emit_signal: bool = True) -> None:
        """
        Set anchor row for range selection.

        Args:
            row: Row index to set as anchor, or None to clear
            emit_signal: Whether to emit anchor_changed signal
        """
        if row == self._anchor_row:
            return

        old_anchor = self._anchor_row
        self._anchor_row = row

        logger.debug(f"Anchor changed: {old_anchor} -> {row}")

        if emit_signal:
            self.anchor_changed.emit(row if row is not None else -1)

    # =====================================
    # Synchronization Operations
    # =====================================

    # (The sync_selection_to_checked and sync_checked_to_selection methods were removed as legacy)

    # =====================================
    # Batch Operations
    # =====================================

    def select_all(self, total_files: int) -> None:
        """
        Select all files efficiently.

        Args:
            total_files: Total number of files available
        """
        if total_files <= 0:
            return

        self._total_files = total_files
        all_rows = set(range(total_files))

        # Update both states atomically
        self._selected_rows = all_rows
        self._checked_rows = all_rows

        logger.info(f"Selected all: {total_files} files")

        # Emit both signals
        self._schedule_selection_signal()
        self._schedule_checked_signal()

    def invert_selection(self, total_files: int) -> None:
        """
        Invert current selection efficiently.

        Args:
            total_files: Total number of files available
        """
        if total_files <= 0:
            return

        self._total_files = total_files
        all_rows = set(range(total_files))
        inverted_rows = all_rows - self._selected_rows

        old_count = len(self._selected_rows)
        new_count = len(inverted_rows)

        # Update both states atomically
        self._selected_rows = inverted_rows
        self._checked_rows = inverted_rows

        logger.info(f"Inverted selection: {old_count} -> {new_count} files")

        # Emit both signals
        self._schedule_selection_signal()
        self._schedule_checked_signal()

    # =====================================
    # State Queries
    # =====================================

    def is_row_selected(self, row: int) -> bool:
        """Check if a specific row is selected."""
        return row in self._selected_rows

    def is_row_checked(self, row: int) -> bool:
        """Check if a specific row is checked."""
        return row in self._checked_rows

    def get_selection_count(self) -> int:
        """Get count of selected rows."""
        return len(self._selected_rows)

    def get_checked_count(self) -> int:
        """Get count of checked rows."""
        return len(self._checked_rows)

    def is_all_selected(self) -> bool:
        """Check if all files are selected."""
        return self._total_files > 0 and len(self._selected_rows) == self._total_files

    def is_none_selected(self) -> bool:
        """Check if no files are selected."""
        return len(self._selected_rows) == 0

    # =====================================
    # Performance & Utilities
    # =====================================

    def update_total_files(self, total: int) -> None:
        """
        Update total file count and validate current selections.

        Args:
            total: New total file count
        """
        old_total = self._total_files
        self._total_files = total

        if total < old_total:
            # Remove invalid selections
            valid_rows = set(range(total))
            self._selected_rows.intersection_update(valid_rows)
            self._checked_rows.intersection_update(valid_rows)

            # Validate anchor
            if self._anchor_row is not None and self._anchor_row >= total:
                self._anchor_row = None

        logger.debug(f"Total files updated: {old_total} -> {total}")

    def get_performance_stats(self) -> dict[str, Any]:
        """Get performance statistics."""
        return {
            "selected_count": len(self._selected_rows),
            "checked_count": len(self._checked_rows),
            "total_files": self._total_files,
            "anchor_row": self._anchor_row,
            "last_operation_time": self._last_operation_time,
            "batch_operations": self._batch_operations.copy(),
        }

    # =====================================
    # Signal Management (Debouncing)
    # =====================================

    def _schedule_selection_signal(self) -> None:
        """Schedule selection_changed signal emission with debouncing."""
        self._pending_selection_signal = True
        if not self._update_timer.isActive():
            self._update_timer.start()

    def _schedule_checked_signal(self) -> None:
        """Schedule checked_changed signal emission with debouncing."""
        self._pending_checked_signal = True
        if not self._update_timer.isActive():
            self._update_timer.start()

    def _emit_deferred_signals(self) -> None:
        """Emit pending signals after debounce timer."""
        if self._pending_selection_signal:
            self.selection_changed.emit(list(self._selected_rows))
            self._pending_selection_signal = False

        if self._pending_checked_signal:
            self.checked_changed.emit(list(self._checked_rows))
            self._pending_checked_signal = False

    # =====================================
    # Cleanup
    # =====================================

    def clear_all(self) -> None:
        """Clear all selection state."""
        self._selected_rows.clear()
        self._checked_rows.clear()
        self._anchor_row = None
        self._total_files = 0
        self._batch_operations.clear()
        self._file_model = None

        logger.debug("SelectionStore cleared", extra={"dev_only": True})
