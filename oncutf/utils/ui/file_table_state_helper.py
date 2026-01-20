"""Module: file_table_state_helper.py

Author: Michael Economou
Date: 2025-12-30

FileTableStateHelper: Helper for saving and restoring file table state.

This helper provides utilities for capturing and restoring file table state,
including:
- Selected file paths
- Checked file states
- Scroll position
- Anchor row

Used in two scenarios:
1. Auto-refresh after save/rename: Preserve all state for seamless UX
2. Manual refresh (F5): Clear state for full reset
"""

import logging
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from oncutf.core.application_context import ApplicationContext
    from oncutf.ui.widgets.file_table import FileTableView

logger = logging.getLogger(__name__)


class FileTableState(NamedTuple):
    """Captured state of file table for restoration."""

    selected_paths: list[str]  # Paths of selected files
    checked_paths: set[str]  # Paths of checked files
    anchor_row: int | None  # Anchor row for range selection
    scroll_position: int  # Vertical scroll position


class FileTableStateHelper:
    """Helper for saving and restoring file table state.

    This helper provides two key workflows:
    1. save_state() -> restore_state(): For auto-refresh after save/rename
    2. clear_all_state(): For manual F5 refresh

    Example usage:
        # Auto-refresh after save (preserve state)
        state = FileTableStateHelper.save_state(file_table_view, context)
        # ... perform file operations ...
        FileTableStateHelper.restore_state(file_table_view, context, state)

        # Manual F5 refresh (clear state)
        FileTableStateHelper.clear_all_state(file_table_view, context, metadata_tree_view)
    """

    @staticmethod
    def save_state(
        file_table_view: "FileTableView", context: "ApplicationContext"
    ) -> FileTableState:
        """Save current file table state for later restoration.

        Args:
            file_table_view: File table view widget
            context: Application context with selection store

        Returns:
            FileTableState with captured state

        """
        selected_paths: list[str] = []
        checked_paths: set[str] = set()
        anchor_row: int | None = None
        scroll_position: int = 0

        try:
            # Get model and selection store
            file_table_model = file_table_view.model()
            file_items = None
            if file_table_model is not None:
                file_items = getattr(file_table_model, "file_items", None)
                if file_items is None:
                    file_items = getattr(file_table_model, "files", None)

            if not file_table_model or file_items is None:
                logger.warning("[StateHelper] No model or files available")
                return FileTableState(selected_paths, checked_paths, anchor_row, scroll_position)

            # Save selected file paths
            if context and context.selection_store:
                selected_rows = context.selection_store.get_selected_rows()
                for row in selected_rows:
                    if 0 <= row < len(file_items):
                        file_item = file_items[row]
                        path = (
                            file_item.full_path
                            if hasattr(file_item, "full_path")
                            else str(file_item)
                        )
                        selected_paths.append(path)

                # Save anchor row
                anchor_row = context.selection_store.get_anchor_row()

                logger.info(
                    "[StateHelper] Saved %d selected paths, anchor_row=%s",
                    len(selected_paths),
                    anchor_row,
                )

            # Save checked file paths
            for file_item in file_items:
                if getattr(file_item, "checked", False):
                    path = (
                        file_item.full_path if hasattr(file_item, "full_path") else str(file_item)
                    )
                    checked_paths.add(path)

            logger.info("[StateHelper] Saved %d checked paths", len(checked_paths))

            # Save scroll position
            scroll_bar = file_table_view.verticalScrollBar()
            if scroll_bar:
                scroll_position = scroll_bar.value()
                logger.debug(
                    "[StateHelper] Saved scroll position: %d",
                    scroll_position,
                    extra={"dev_only": True},
                )

        except Exception as e:
            logger.warning("[StateHelper] Error saving state: %s", e)

        return FileTableState(selected_paths, checked_paths, anchor_row, scroll_position)

    @staticmethod
    def restore_state(
        file_table_view: "FileTableView",
        context: "ApplicationContext",
        state: FileTableState,
        delay_ms: int = 100,
    ) -> None:
        """Restore file table state after file operations.

        This method schedules state restoration using TimerManager to ensure
        the file table model is fully updated before restoration.

        Args:
            file_table_view: File table view widget
            context: Application context with selection store
            state: Saved state to restore
            delay_ms: Delay in milliseconds before restoration (default: 100)

        """
        from oncutf.utils.shared.timer_manager import (
            TimerPriority,
            TimerType,
            get_timer_manager,
        )

        def restore():
            """Execute state restoration."""
            try:
                file_table_model = file_table_view.model()
                file_items = None
                if file_table_model is not None:
                    file_items = getattr(file_table_model, "file_items", None)
                    if file_items is None:
                        file_items = getattr(file_table_model, "files", None)

                if not file_table_model or file_items is None:
                    logger.warning("[StateHelper] No model/files available for restoration")
                    return

                # Restore checked state
                restored_checked = 0
                for file_item in file_items:
                    path = (
                        file_item.full_path if hasattr(file_item, "full_path") else str(file_item)
                    )
                    if path in state.checked_paths:
                        file_item.checked = True
                        restored_checked += 1

                logger.info("[StateHelper] Restored %d checked items", restored_checked)

                # Restore selected rows
                if context and context.selection_store:
                    rows_to_select = set()
                    for row, file_item in enumerate(file_items):
                        path = (
                            file_item.full_path
                            if hasattr(file_item, "full_path")
                            else str(file_item)
                        )
                        if path in state.selected_paths:
                            rows_to_select.add(row)

                    if rows_to_select:
                        # Update SelectionStore
                        context.selection_store.set_selected_rows(
                            rows_to_select, emit_signal=True, force_emit=True
                        )

                        # CRITICAL: Also update Qt selection model for visual feedback
                        # This ensures the selection is visible in the table
                        selection_model = file_table_view.selectionModel()
                        if selection_model:
                            from oncutf.core.pyqt_imports import QItemSelection, QItemSelectionModel

                            model = file_table_view.model()
                            if model:
                                # Clear existing selection
                                selection_model.clearSelection()

                                # Build Qt selection for all rows
                                selection = QItemSelection()
                                for row in sorted(rows_to_select):
                                    if 0 <= row < model.rowCount():
                                        left_index = model.index(row, 0)
                                        right_index = model.index(row, model.columnCount() - 1)
                                        selection.select(left_index, right_index)

                                # Apply selection to Qt model
                                selection_model.select(selection, QItemSelectionModel.Select)

                        logger.info(
                            "[StateHelper] Restored %d/%d selected rows (visual + store)",
                            len(rows_to_select),
                            len(state.selected_paths),
                        )

                    # Restore anchor row
                    if state.anchor_row is not None:
                        context.selection_store.set_anchor_row(state.anchor_row, emit_signal=False)
                        logger.debug(
                            "[StateHelper] Restored anchor row: %d",
                            state.anchor_row,
                            extra={"dev_only": True},
                        )

                # Restore scroll position
                if state.scroll_position > 0:
                    scroll_bar = file_table_view.verticalScrollBar()
                    if scroll_bar:
                        scroll_bar.setValue(state.scroll_position)
                        logger.debug(
                            "[StateHelper] Restored scroll position: %d",
                            state.scroll_position,
                            extra={"dev_only": True},
                        )

                # Update viewport to reflect changes
                file_table_view.viewport().update()

            except Exception as e:
                logger.exception("[StateHelper] Error restoring state: %s", e)

        # Schedule restoration with delay
        get_timer_manager().schedule(
            restore,
            delay=delay_ms,
            priority=TimerPriority.HIGH,
            timer_type=TimerType.UI_UPDATE,
            timer_id="file_table_state_restore",
        )

        logger.debug(
            "[StateHelper] Scheduled state restoration with %dms delay",
            delay_ms,
            extra={"dev_only": True},
        )

    @staticmethod
    def restore_state_sync(
        file_table_view: "FileTableView",
        context: "ApplicationContext",
        state: FileTableState,
    ) -> None:
        """Restore file table state SYNCHRONOUSLY (no timer delay).

        Use this when you've already ensured the model is ready (e.g., after
        debouncing on files_loaded signal).

        Args:
            file_table_view: File table view widget
            context: Application context with selection store
            state: Saved state to restore

        """
        try:
            file_table_model = file_table_view.model()
            file_items = None
            if file_table_model is not None:
                file_items = getattr(file_table_model, "file_items", None)
                if file_items is None:
                    file_items = getattr(file_table_model, "files", None)

            if not file_table_model or file_items is None:
                logger.warning("[StateHelper] No model/files available for sync restoration")
                return

            # Restore checked state
            restored_checked = 0
            for file_item in file_items:
                path = file_item.full_path if hasattr(file_item, "full_path") else str(file_item)
                if path in state.checked_paths:
                    file_item.checked = True
                    restored_checked += 1

            logger.info("[StateHelper] Sync restored %d checked items", restored_checked)

            # Restore selected rows
            if context and context.selection_store:
                rows_to_select = set()
                for row, file_item in enumerate(file_items):
                    path = (
                        file_item.full_path if hasattr(file_item, "full_path") else str(file_item)
                    )
                    if path in state.selected_paths:
                        rows_to_select.add(row)

                if rows_to_select:
                    # Update SelectionStore
                    context.selection_store.set_selected_rows(
                        rows_to_select, emit_signal=True, force_emit=True
                    )

                    # CRITICAL: Also update Qt selection model for visual feedback
                    selection_model = file_table_view.selectionModel()
                    if selection_model:
                        from oncutf.core.pyqt_imports import QItemSelection, QItemSelectionModel

                        model = file_table_view.model()
                        if model:
                            # Clear existing selection
                            selection_model.clearSelection()

                            # Build Qt selection for all rows
                            selection = QItemSelection()
                            for row in sorted(rows_to_select):
                                if 0 <= row < model.rowCount():
                                    left_index = model.index(row, 0)
                                    right_index = model.index(row, model.columnCount() - 1)
                                    selection.select(left_index, right_index)

                            # Apply selection to Qt model
                            selection_model.select(selection, QItemSelectionModel.Select)

                    logger.info(
                        "[StateHelper] Sync restored %d/%d selected rows (visual + store)",
                        len(rows_to_select),
                        len(state.selected_paths),
                    )

                # Restore anchor row
                if state.anchor_row is not None:
                    context.selection_store.set_anchor_row(state.anchor_row, emit_signal=False)

            # Restore scroll position
            if state.scroll_position > 0:
                scroll_bar = file_table_view.verticalScrollBar()
                if scroll_bar:
                    scroll_bar.setValue(state.scroll_position)

            # Update viewport to reflect changes
            file_table_view.viewport().update()

        except Exception as e:
            logger.exception("[StateHelper] Error in sync state restoration: %s", e)

    @staticmethod
    def clear_all_state(
        file_table_view: "FileTableView",
        context: "ApplicationContext",
        metadata_tree_view=None,
    ) -> None:
        """Clear all file table state for manual F5 refresh.

        This method:
        1. Clears all selections
        2. Clears metadata tree
        3. Resets scroll position
        4. Resets anchor row

        Args:
            file_table_view: File table view widget
            context: Application context with selection store
            metadata_tree_view: Optional metadata tree view to clear

        """
        from oncutf.utils.ui.cursor_helper import wait_cursor

        logger.info("[StateHelper] Clearing all file table state (F5 refresh)")

        with wait_cursor():
            try:
                # Clear selection in selection store
                if context and context.selection_store:
                    context.selection_store.clear_selection(emit_signal=False)
                    logger.debug("[StateHelper] Cleared selection store")

                # Clear Qt selection model
                selection_model = file_table_view.selectionModel()
                if selection_model:
                    selection_model.clearSelection()
                    logger.debug("[StateHelper] Cleared Qt selection model")

                # Uncheck all files in model
                file_table_model = file_table_view.model()
                if file_table_model and hasattr(file_table_model, "files"):
                    for file_item in file_table_model.files:
                        file_item.checked = False
                    logger.debug("[StateHelper] Unchecked all files")

                # Clear metadata tree
                if metadata_tree_view and hasattr(metadata_tree_view, "clear_view"):
                    metadata_tree_view.clear_view()
                    logger.debug("[StateHelper] Cleared metadata tree view")

                # Reset scroll position
                scroll_bar = file_table_view.verticalScrollBar()
                if scroll_bar:
                    scroll_bar.setValue(0)
                    logger.debug("[StateHelper] Reset scroll position")

                # Update viewport
                file_table_view.viewport().update()

            except Exception as e:
                logger.exception("[StateHelper] Error clearing state: %s", e)
