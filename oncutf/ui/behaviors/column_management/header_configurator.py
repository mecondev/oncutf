"""Header configuration operations.

Handles header setup, resize modes, and delayed configuration.

Author: Michael Economou
Date: 2026-01-05
"""

from typing import TYPE_CHECKING

from PyQt5.QtWidgets import QHeaderView

from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.ui.behaviors.column_management.protocols import ColumnManageableWidget
    from oncutf.ui.behaviors.column_management.visibility_manager import (
        ColumnVisibilityManager,
    )
    from oncutf.ui.behaviors.column_management.width_manager import ColumnWidthManager
    from oncutf.ui.managers.column_service import UnifiedColumnService

logger = get_cached_logger(__name__)


class HeaderConfigurator:
    """Handles header configuration and setup."""

    def __init__(
        self,
        widget: "ColumnManageableWidget",
        service: "UnifiedColumnService",
        width_manager: "ColumnWidthManager",
        visibility_manager: "ColumnVisibilityManager",
    ):
        """Initialize header configurator.

        Args:
            widget: The table widget to manage
            service: Column service for configuration
            width_manager: Width manager for width operations
            visibility_manager: Visibility manager for column tracking

        """
        self._widget = widget
        self._service = service
        self._width_manager = width_manager
        self._visibility_manager = visibility_manager
        self._header_resize_connected = False
        self._section_moved_connected = False
        self._configuring_columns = False
        self._on_resize_callback: callable | None = None

    def set_resize_callback(self, callback: callable) -> None:
        """Set callback for resize events.

        Args:
            callback: Function to call on resize (logical_index, old_size, new_size)

        """
        self._on_resize_callback = callback

    def _load_columns_lock_state(self) -> bool:
        """Load columns lock state from config.

        Returns:
            True if columns are locked (not movable), False otherwise

        """
        try:
            main_window = self._widget._get_main_window()
            if main_window and hasattr(main_window, "window_config_manager"):
                config_manager = main_window.window_config_manager.config_manager
                window_config = config_manager.get_category("window")
                return window_config.get("columns_locked", False)
        except Exception:
            pass

        return False

    def _load_column_order(self) -> list[str] | None:
        """Load saved column order from config.

        Returns:
            List of column keys in visual order, or None if no saved order

        """
        try:
            main_window = self._widget._get_main_window()
            if main_window and hasattr(main_window, "window_config_manager"):
                config_manager = main_window.window_config_manager.config_manager
                window_config = config_manager.get_category("window")
                return window_config.get("column_order", None)
        except Exception:
            pass
        return None

    def _save_column_order(self) -> None:
        """Save current visual column order to config."""
        try:
            header = self._widget.horizontalHeader()
            if not header:
                return

            # Get current visual order (skip status column 0)
            visual_order = []
            for visual_index in range(1, header.count()):
                logical_index = header.logicalIndex(visual_index)
                column_key = self.get_column_key_from_index(logical_index)
                if column_key:  # Skip status column (empty string)
                    visual_order.append(column_key)

            # Save to config
            main_window = self._widget._get_main_window()
            if main_window and hasattr(main_window, "window_config_manager"):
                config_manager = main_window.window_config_manager.config_manager
                window_config = config_manager.get_category("window")
                window_config.set("column_order", visual_order)
                config_manager.mark_dirty()

                logger.info("Saved column order: %s", visual_order)
        except Exception as e:
            logger.warning("Failed to save column order: %s", e)

    def _restore_column_order(self) -> None:
        """Restore saved visual column order."""
        try:
            saved_order = self._load_column_order()
            if not saved_order:
                return  # No saved order, use default

            header = self._widget.horizontalHeader()
            if not header:
                return

            visible_columns = self._visibility_manager.get_visible_columns_list()

            # Build mapping: column_key -> logical_index
            key_to_logical = {}
            for logical_index, column_key in enumerate(visible_columns):
                key_to_logical[column_key] = logical_index + 1  # +1 for status column

            # Apply saved visual order
            for target_visual_index, column_key in enumerate(saved_order):
                if column_key not in key_to_logical:
                    continue  # Column not visible, skip

                logical_index = key_to_logical[column_key]
                current_visual_index = header.visualIndex(logical_index)
                target_position = target_visual_index + 1  # +1 for status column

                if current_visual_index != target_position:
                    header.moveSection(current_visual_index, target_position)

            logger.info("Restored column order from config")
        except Exception as e:
            logger.warning("Failed to restore column order: %s", e)

    def _on_section_moved(self, logical_index: int, old_visual: int, new_visual: int) -> None:
        """Handle column reordering via drag & drop.

        Args:
            logical_index: The logical index of the moved section
            old_visual: Previous visual index
            new_visual: New visual index

        """
        # Don't save during configuration
        if self._configuring_columns:
            return

        # Prevent status column (0) from being moved - CRITICAL CHECK
        if logical_index == 0 or old_visual == 0 or new_visual == 0:
            header = self._widget.horizontalHeader()
            if header:
                # Find where status column ended up
                current_visual = header.visualIndex(0)
                # Only restore if it's not already at position 0 (avoid infinite loop)
                if current_visual != 0:
                    logger.info(
                        "[COLUMN_LOCK] Restoring status column from visual %d to 0",
                        current_visual,
                    )
                    header.blockSignals(True)
                    try:
                        # Allow controlled move even if InteractiveHeader blocks normal moves
                        header._allow_forced_section_move = True
                        QHeaderView.moveSection(header, current_visual, 0)
                    except Exception:
                        logger.warning(
                            "[COLUMN_LOCK] Failed to force status column restore",
                            exc_info=True,
                        )
                    finally:
                        header._allow_forced_section_move = False
                        header.blockSignals(False)
            return

        logger.debug(
            "Column moved: logical=%d, visual %d -> %d",
            logical_index,
            old_visual,
            new_visual,
        )

        # Save new order
        self._save_column_order()

    def configure_columns_delayed(self) -> None:
        """Delayed column configuration to ensure model synchronization."""
        try:
            header = self._widget.horizontalHeader()
            if not header or not self._widget.model():
                return

            # Store current selection before reconfiguration
            saved_selection = set()
            if hasattr(self._widget, "_selection_behavior"):
                saved_selection = self._widget._selection_behavior.get_current_selection_safe()

            header.show()

            # Configure column reordering based on saved lock state
            columns_locked = self._load_columns_lock_state()
            header.setSectionsMovable(not columns_locked)

            # Configure status column (always column 0)
            self._widget.setColumnWidth(0, 45)
            header.setSectionResizeMode(0, header.Fixed)
            # Set property to disable hover for status column
            header.setProperty("oncutf_status_column_no_hover", True)

            # Get visible columns from model
            visible_columns = []
            if hasattr(self._widget.model(), "get_visible_columns"):
                visible_columns = self._widget.model().get_visible_columns()
            else:
                visible_columns = self._service.get_visible_columns()

            # Configure each visible column
            for column_index, column_key in enumerate(visible_columns):
                actual_column_index = column_index + 1
                if actual_column_index < self._widget.model().columnCount():
                    width = self._width_manager.load_column_width(column_key)
                    width = self._width_manager.ensure_column_proper_width(column_key, width)

                    from oncutf.config import FILE_TABLE_COLUMN_CONFIG

                    column_config = FILE_TABLE_COLUMN_CONFIG.get(column_key, {})
                    is_resizable = column_config.get("resizable", True)

                    # Set resize mode (Fixed = can't resize width, but can still move position)
                    if is_resizable:
                        header.setSectionResizeMode(actual_column_index, header.Interactive)
                    else:
                        header.setSectionResizeMode(actual_column_index, header.Fixed)

                    self._widget.setColumnWidth(actual_column_index, width)

            # Connect header resize signal
            if not self._header_resize_connected and self._on_resize_callback:
                header.sectionResized.connect(self._on_resize_callback)
                self._header_resize_connected = True

            # Connect section moved signal for order persistence
            if not self._section_moved_connected:
                header.sectionMoved.connect(self._on_section_moved)
                self._section_moved_connected = True

            # Update header visibility
            self._update_header_visibility()

            # Restore saved column order (after configuration, before delegates)
            self._restore_column_order()

            # Setup column-specific delegates (e.g., color column)
            if hasattr(self._widget, "_setup_column_delegates"):
                self._widget._setup_column_delegates()

            # Force complete viewport refresh to clear artifacts
            self._widget.viewport().update()
            self._widget.updateGeometry()

            # Restore selection if we had one
            if saved_selection and hasattr(self._widget, "_selection_behavior"):
                self._widget._selection_behavior.update_selection_store(
                    saved_selection, emit_signal=True
                )

        finally:
            self._configuring_columns = False

    def _update_header_visibility(self) -> None:
        """Update header visibility based on table empty state."""
        header = self._widget.horizontalHeader()
        if not header:
            return

        is_empty = self._widget.is_empty()
        header.setVisible(not is_empty)

        logger.debug(
            "[FileTableView] Header visibility: %s (empty: %s)",
            "hidden" if is_empty else "visible",
            is_empty,
            extra={"dev_only": True},
        )

    def ensure_new_column_proper_width(self) -> None:
        """Ensure newly added column has proper width."""
        if not self._widget.model():
            return

        visible_columns = self._visibility_manager.get_visible_columns_list()
        if not visible_columns:
            return

        # Get last visible column (the newly added one)
        new_column_key = visible_columns[-1]
        column_index = len(visible_columns)  # +1 for status, -1 for 0-index = same

        if column_index < self._widget.model().columnCount():
            width = self._width_manager.load_column_width(new_column_key)
            width = self._width_manager.ensure_column_proper_width(new_column_key, width)
            self._widget.setColumnWidth(column_index, width)

    def get_column_key_from_index(self, logical_index: int) -> str:
        """Get column key from logical index.

        Args:
            logical_index: Column logical index

        Returns:
            Column key or empty string for status column

        """
        if logical_index == 0:
            return ""  # Status column has no key

        visible_columns = self._visibility_manager.get_visible_columns_list()
        column_index = logical_index - 1  # Subtract 1 for status column

        if 0 <= column_index < len(visible_columns):
            return visible_columns[column_index]

        return ""

    @property
    def is_configuring(self) -> bool:
        """Check if currently configuring columns."""
        return self._configuring_columns

    @is_configuring.setter
    def is_configuring(self, value: bool) -> None:
        """Set configuring state."""
        self._configuring_columns = value

    @property
    def header_resize_connected(self) -> bool:
        """Check if header resize is connected."""
        return self._header_resize_connected


__all__ = ["HeaderConfigurator"]
