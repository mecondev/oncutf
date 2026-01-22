"""UI state management service - Application layer facade.

Provides Qt-independent UI state operations for core modules.
Delegates to FileTableStateHelper for actual implementation.

This is a temporary facade during Phase A migration. Ultimately,
UI state management should be event-driven from UI layer.

Author: Michael Economou
Date: 2026-01-26
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, NamedTuple

if TYPE_CHECKING:
    from oncutf.core.application_context import ApplicationContext
    from oncutf.ui.widgets.file_table.view import FileTableView


class UIState(NamedTuple):
    """Captured UI state for restoration.

    This is a facade for FileTableState to avoid direct utils.ui imports.
    """

    selected_paths: list[str]
    checked_paths: set[str]
    anchor_row: int | None
    scroll_position: int


def save_ui_state(file_table_view: FileTableView, context: ApplicationContext) -> Any:
    """Save current UI state (selection, checked, scroll position).

    Args:
        file_table_view: File table view widget
        context: Application context

    Returns:
        Opaque state object for later restoration

    """
    from oncutf.utils.ui.file_table_state_helper import FileTableStateHelper

    return FileTableStateHelper.save_state(file_table_view, context)


def restore_ui_state(
    file_table_view: FileTableView, context: ApplicationContext, state: Any, delay_ms: int = 0
) -> None:
    """Restore previously saved UI state.

    Args:
        file_table_view: File table view widget
        context: Application context
        state: State object from save_ui_state() or UIState instance
        delay_ms: Optional delay before restoration (for layout completion)

    """
    from oncutf.utils.ui.file_table_state_helper import FileTableStateHelper

    FileTableStateHelper.restore_state(file_table_view, context, state, delay_ms)


def restore_ui_state_sync(
    file_table_view: FileTableView, context: ApplicationContext, state: Any
) -> None:
    """Restore UI state synchronously (no delay).

    Args:
        file_table_view: File table view widget
        context: Application context
        state: UIState instance with selection/checked/scroll data

    """
    from oncutf.utils.ui.file_table_state_helper import (
        FileTableState,
        FileTableStateHelper,
    )

    # Convert UIState to FileTableState if needed
    if isinstance(state, UIState):
        state = FileTableState(
            selected_paths=state.selected_paths,
            checked_paths=state.checked_paths,
            anchor_row=state.anchor_row,
            scroll_position=state.scroll_position,
        )

    FileTableStateHelper.restore_state_sync(file_table_view, context, state)


def clear_ui_state(
    file_table_view: FileTableView, context: ApplicationContext, metadata_tree_view: Any = None
) -> None:
    """Clear all UI state (selection, checked, scroll position).

    This is a facade that delegates to FileTableStateHelper.
    Temporary solution for Phase A - should be replaced with event-driven
    architecture where UI listens to domain events.

    Args:
        file_table_view: File table view widget
        context: Application context
        metadata_tree_view: Optional metadata tree view

    """
    from oncutf.utils.ui.file_table_state_helper import FileTableStateHelper

    FileTableStateHelper.clear_all_state(file_table_view, context, metadata_tree_view)
