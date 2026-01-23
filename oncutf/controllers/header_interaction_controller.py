"""Module: header_interaction_controller.py.

Author: Michael Economou
Date: 2026-01-12

UI-agnostic controller for header interactions.
Orchestrates sort, toggle, and column drag operations
without Qt dependencies in business logic.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.core.pyqt_imports import Qt

logger = get_cached_logger(__name__)


class MainWindowProtocol(Protocol):
    """Protocol for main window interface needed by HeaderInteractionController."""

    def handle_header_toggle(self, checked: int) -> None:
        """Toggle select all/unselect all files."""
        ...

    def sort_by_column(self, column: int, force_order: Qt.SortOrder | None = None) -> None:
        """Sort table by column."""
        ...


class HeaderInteractionController:
    """UI-agnostic controller for header interactions.

    Separates business logic from Qt widget implementation.
    Enables future node editor integration and testability.
    """

    def __init__(self, main_window: MainWindowProtocol) -> None:
        """Initialize controller with main window reference.

        Args:
            main_window: Main window implementing the required protocol.

        """
        self._main_window = main_window

    def handle_toggle_all(self) -> None:
        """Handle toggle select all/unselect all action.

        This is triggered when user clicks on status column (column 0).
        """
        logger.info("[CONTROLLER] Toggle all files")
        from oncutf.core.pyqt_imports import Qt
        checked = Qt.Checked
        self._main_window.handle_header_toggle(checked)

    def handle_sort(self, column: int, force_order: Qt.SortOrder | None = None) -> None:
        """Handle sort by column action.

        Args:
            column: Logical column index to sort by.
            force_order: Optional forced sort order (from context menu).
                        If None, toggles between ascending/descending.

        """
        logger.info("[CONTROLLER] Sort by column %d (force_order=%s)", column, force_order)
        self._main_window.sort_by_column(column, force_order=force_order)

    def validate_column_drag(self, from_visual: int, to_visual: int) -> bool:
        """Validate if a column drag operation is allowed.

        Args:
            from_visual: Visual index of column being dragged.
            to_visual: Target visual index for drop.

        Returns:
            True if drag is allowed, False if blocked.

        """
        # Block any move that would involve status column (visual 0)
        if from_visual == 0 or to_visual == 0:
            logger.debug(
                "[CONTROLLER] Blocked column drag: from_visual=%d, to_visual=%d (status column protected)",
                from_visual,
                to_visual,
            )
            return False

        logger.debug(
            "[CONTROLLER] Allowed column drag: from_visual=%d -> to_visual=%d",
            from_visual,
            to_visual,
        )
        return True

    def is_status_column(self, logical_index: int) -> bool:
        """Check if column is the status column (column 0).

        Args:
            logical_index: Logical column index.

        Returns:
            True if this is the status column.

        """
        return logical_index == 0

    def should_handle_click(
        self,
        pressed_index: int,
        released_index: int,
        manhattan_length: int,
        click_actions_enabled: bool,
    ) -> tuple[bool, str]:
        """Determine if a click should trigger an action.

        Args:
            pressed_index: Logical index where mouse was pressed.
            released_index: Logical index where mouse was released.
            manhattan_length: Manhattan distance of mouse movement.
            click_actions_enabled: Whether click actions are enabled.

        Returns:
            Tuple of (should_handle, action_type) where action_type is:
            - "toggle" for status column click
            - "sort" for other column clicks
            - "" if click should not be handled

        """
        # Check if actions are disabled
        if not click_actions_enabled:
            logger.debug("[CONTROLLER] Click actions disabled")
            return False, ""

        # Check for drag (manhattan distance > 4)
        if manhattan_length > 4:
            logger.debug("[CONTROLLER] Click ignored - drag detected (manhattan=%d)", manhattan_length)
            return False, ""

        # Check if release position matches press position
        if released_index != pressed_index or released_index == -1:
            logger.debug(
                "[CONTROLLER] Click ignored - position mismatch (pressed=%d, released=%d)",
                pressed_index,
                released_index,
            )
            return False, ""

        # Determine action type
        if released_index == 0:
            return True, "toggle"
        return True, "sort"
