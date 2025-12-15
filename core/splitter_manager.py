"""
Module: splitter_manager.py

Author: Michael Economou
Date: 2025-06-10

splitter_manager.py
This module defines the SplitterManager class, which handles all splitter-related
functionality for the oncutf application. It manages splitter movement events,
optimal size calculations, and UI updates that depend on splitter positions.
"""

from typing import TYPE_CHECKING

from oncutf.utils.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from main_window import MainWindow

logger = get_cached_logger(__name__)


class SplitterManager:
    """
    Manages splitter functionality for the main window.

    This class handles:
    - Horizontal and vertical splitter movement events
    - Optimal splitter size calculations
    - UI updates that depend on splitter positions
    - Coordination between different UI elements affected by splitter changes
    """

    def __init__(self, parent_window: "MainWindow") -> None:
        """
        Initialize the SplitterManager.

        Args:
            parent_window: Reference to the main window instance
        """
        self.parent_window = parent_window
        logger.debug("[SplitterManager] Initialized", extra={"dev_only": True})

    def on_horizontal_splitter_moved(self, pos: int, index: int) -> None:
        """
        Handle horizontal splitter movement.
        Updates UI elements that depend on horizontal space allocation.

        Args:
            pos: New position of the splitter
            index: Index of the splitter section that moved
        """
        logger.debug(
            f"[SplitterManager] Horizontal moved: pos={pos}, index={index}",
            extra={"dev_only": True},
        )

        # Update any UI elements that need to respond to horizontal space changes
        if hasattr(self.parent_window, "folder_tree"):
            self.parent_window.folder_tree.on_horizontal_splitter_moved(pos, index)

        if hasattr(self.parent_window, "file_table_view"):
            self.parent_window.file_table_view.on_horizontal_splitter_moved(pos, index)

    def on_vertical_splitter_moved(self, pos: int, index: int) -> None:
        """
        Handle vertical splitter movement.
        Updates UI elements that depend on vertical space allocation.

        Args:
            pos: New position of the splitter
            index: Index of the splitter section that moved
        """
        logger.debug(
            f"[SplitterManager] Vertical moved: pos={pos}, index={index}", extra={"dev_only": True}
        )

        # Update any UI elements that need to respond to vertical space changes
        if hasattr(self.parent_window, "folder_tree"):
            self.parent_window.folder_tree.on_vertical_splitter_moved(pos, index)

        if hasattr(self.parent_window, "file_table_view"):
            self.parent_window.file_table_view.on_vertical_splitter_moved(pos, index)

        if hasattr(self.parent_window, "preview_tables_view"):
            self.parent_window.preview_tables_view.handle_splitter_moved(pos, index)

    def calculate_optimal_splitter_sizes(self, window_width: int) -> list[int]:
        """
        Calculate optimal splitter sizes based on window width with smart adaptation for wide screens.

        Args:
            window_width: Current window width in pixels

        Returns:
            List of optimal sizes for splitter sections
        """
        # Import configuration constants
        from core.config_imports import (
            LEFT_PANEL_MAX_WIDTH,
            LEFT_PANEL_MIN_WIDTH,
            RIGHT_PANEL_MAX_WIDTH,
            RIGHT_PANEL_MIN_WIDTH,
            ULTRA_WIDE_SCREEN_THRESHOLD,
            WIDE_SCREEN_THRESHOLD,
        )

        # Calculate optimal sizes based on window width
        if window_width >= ULTRA_WIDE_SCREEN_THRESHOLD:
            # Ultra-wide screens: give more space to center, moderate increase to panels
            left_width = min(LEFT_PANEL_MAX_WIDTH + 50, int(window_width * 0.15))
            right_width = min(RIGHT_PANEL_MAX_WIDTH + 100, int(window_width * 0.25))
            center_width = window_width - left_width - right_width
            optimal_sizes = [left_width, center_width, right_width]
            logger.debug(
                f"[SplitterManager] Ultra-wide screen layout: {optimal_sizes}",
                extra={"dev_only": True},
            )

        elif window_width >= WIDE_SCREEN_THRESHOLD:
            # Wide screens: balanced increase for all panels
            left_width = min(LEFT_PANEL_MAX_WIDTH, int(window_width * 0.18))
            right_width = min(RIGHT_PANEL_MAX_WIDTH, int(window_width * 0.22))
            center_width = window_width - left_width - right_width
            optimal_sizes = [left_width, center_width, right_width]
            logger.debug(
                f"[SplitterManager] Wide screen layout: {optimal_sizes}", extra={"dev_only": True}
            )

        else:
            # Standard screens: use minimum viable sizes
            left_width = max(LEFT_PANEL_MIN_WIDTH, int(window_width * 0.15))
            right_width = max(RIGHT_PANEL_MIN_WIDTH, int(window_width * 0.20))
            center_width = window_width - left_width - right_width

            # Ensure center panel has reasonable space
            if center_width < 400:
                # Reduce panel sizes if window is too narrow
                left_width = max(LEFT_PANEL_MIN_WIDTH, int(window_width * 0.12))
                right_width = max(RIGHT_PANEL_MIN_WIDTH, int(window_width * 0.18))
                center_width = window_width - left_width - right_width

            optimal_sizes = [left_width, center_width, right_width]
            logger.debug(
                f"[SplitterManager] Standard screen layout: {optimal_sizes}",
                extra={"dev_only": True},
            )

        # Log the calculation details
        logger.debug(
            f"[SplitterManager] Calculated splitter sizes for {window_width}px: {optimal_sizes} "
            f"(left: {optimal_sizes[0]}, center: {optimal_sizes[1]}, right: {optimal_sizes[2]})",
            extra={"dev_only": True},
        )

        return optimal_sizes

    def update_splitter_sizes_for_window_width(self, window_width: int) -> None:
        """
        Update splitter sizes based on new window width.

        Args:
            window_width: New window width in pixels
        """
        if not hasattr(self.parent_window, "horizontal_splitter"):
            logger.debug("[SplitterManager] No horizontal splitter found, skipping size update")
            return

        # Calculate new optimal sizes
        optimal_sizes = self.calculate_optimal_splitter_sizes(window_width)

        # Get current sizes for comparison
        current_sizes = self.parent_window.horizontal_splitter.sizes()

        # Only update if sizes have changed significantly (avoid unnecessary updates)
        if self._sizes_differ_significantly(current_sizes, optimal_sizes):
            # Update splitter sizes
            self.parent_window.horizontal_splitter.setSizes(optimal_sizes)
            logger.debug(
                f"[SplitterManager] Updated splitter sizes for {window_width}px: {optimal_sizes}"
            )
        else:
            logger.debug(f"[SplitterManager] Splitter sizes already optimal for {window_width}px")

    def _sizes_differ_significantly(
        self, current_sizes: list[int], optimal_sizes: list[int], threshold: int = 50
    ) -> bool:
        """
        Check if current and optimal sizes differ significantly.

        Args:
            current_sizes: Current splitter sizes
            optimal_sizes: Optimal splitter sizes
            threshold: Minimum difference threshold in pixels

        Returns:
            True if sizes differ significantly, False otherwise
        """
        if len(current_sizes) != len(optimal_sizes):
            return True

        for current, optimal in zip(current_sizes, optimal_sizes, strict=False):
            if abs(current - optimal) > threshold:
                return True

        return False

    def get_current_splitter_sizes(self) -> tuple[list[int], list[int]]:
        """
        Get current splitter sizes.

        Returns:
            Tuple of (horizontal_sizes, vertical_sizes)
        """
        horizontal_sizes = []
        vertical_sizes = []

        if hasattr(self.parent_window, "horizontal_splitter"):
            horizontal_sizes = self.parent_window.horizontal_splitter.sizes()

        if hasattr(self.parent_window, "vertical_splitter"):
            vertical_sizes = self.parent_window.vertical_splitter.sizes()

        return horizontal_sizes, vertical_sizes

    def trigger_column_adjustment_after_splitter_change(self) -> None:
        """
        Trigger column adjustment in UI elements after splitter changes.
        This is useful when splitter movements affect column layouts.
        """
        # For file table, use the original sophisticated logic
        if hasattr(self.parent_window, "file_table_view"):
            # Use existing splitter logic for column sizing (original implementation)
            if hasattr(self.parent_window, "horizontal_splitter"):
                sizes = self.parent_window.horizontal_splitter.sizes()
                self.parent_window.file_table_view.on_horizontal_splitter_moved(sizes[1], 1)
                logger.debug("[SplitterManager] Triggered original file table column adjustment")

        # Use ColumnManager for other table views that don't have sophisticated logic
        if hasattr(self.parent_window, "column_manager"):
            # Adjust metadata tree columns
            if hasattr(self.parent_window, "metadata_tree_view"):
                self.parent_window.column_manager.adjust_columns_for_splitter_change(
                    self.parent_window.metadata_tree_view, "metadata_tree"
                )

            # Adjust preview table columns
            if hasattr(self.parent_window, "preview_tables_view"):
                if hasattr(self.parent_window.preview_tables_view, "old_names_table"):
                    self.parent_window.column_manager.adjust_columns_for_splitter_change(
                        self.parent_window.preview_tables_view.old_names_table, "preview_old"
                    )
                if hasattr(self.parent_window.preview_tables_view, "new_names_table"):
                    self.parent_window.column_manager.adjust_columns_for_splitter_change(
                        self.parent_window.preview_tables_view.new_names_table, "preview_new"
                    )

            logger.debug("[SplitterManager] Triggered ColumnManager adjustment for other tables")
