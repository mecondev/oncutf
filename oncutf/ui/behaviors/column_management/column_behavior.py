"""Column management behavior - main coordinator.

Provides column management functionality for table views through composition
of specialized managers.

Author: Michael Economou
Date: 2026-01-05
"""

from typing import TYPE_CHECKING

from PyQt5.QtCore import Qt

from oncutf.ui.behaviors.column_management.header_configurator import HeaderConfigurator
from oncutf.ui.behaviors.column_management.protocols import ColumnManageableWidget
from oncutf.ui.behaviors.column_management.visibility_manager import (
    ColumnVisibilityManager,
)
from oncutf.ui.behaviors.column_management.width_manager import ColumnWidthManager
from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.ui.managers.column_service import UnifiedColumnService

logger = get_cached_logger(__name__)


class ColumnManagementBehavior:
    """Manages column configuration, visibility, and persistence.

    This behavior handles:
    - Column visibility (add/remove columns)
    - Column width management (load/save preferences)
    - Header configuration and resize handling
    - Keyboard shortcuts (Ctrl+T, Ctrl+Shift+T)

    Uses composition with specialized managers:
    - ColumnWidthManager: Width loading, saving, scheduling
    - ColumnVisibilityManager: Add/remove columns, visibility config
    - HeaderConfigurator: Header setup and resize modes
    """

    def __init__(self, widget: ColumnManageableWidget):
        """Initialize column management behavior.

        Args:
            widget: Table widget that implements ColumnManageableWidget protocol

        """
        self._widget = widget
        self._service = self._get_column_service()

        # Initialize specialized managers
        self._width_manager = ColumnWidthManager(widget, self._service)
        self._visibility_manager = ColumnVisibilityManager(
            widget, self._service, self._width_manager
        )
        self._header_configurator = HeaderConfigurator(
            widget, self._service, self._width_manager, self._visibility_manager
        )
        self._header_configurator.set_resize_callback(self.handle_column_resized)

        # Internal state
        self._programmatic_resize = False
        self._column_alignments: dict[int, int] = {}
        self._shutdown_hook_registered = False

    def _get_column_service(self) -> "UnifiedColumnService":
        """Get or create column service instance."""
        from oncutf.ui.managers.column_service import get_column_service

        return get_column_service()

    # =====================================
    # Public API - Configuration
    # =====================================

    def configure_columns(self) -> None:
        """Configure columns with proper widths and visibility.

        Should be called after model is set up. Uses delayed configuration
        to ensure model synchronization.
        """
        from oncutf.utils.shared.timer_manager import (
            TimerPriority,
            TimerType,
            get_timer_manager,
        )

        self._header_configurator.is_configuring = True
        get_timer_manager().schedule(
            lambda: self._header_configurator.configure_columns_delayed(),
            delay=0,
            priority=TimerPriority.IMMEDIATE,
            timer_type=TimerType.UI_UPDATE,
        )

    def ensure_all_columns_proper_width(self) -> None:
        """Ensure all visible columns have proper widths."""
        visible_columns = self._visibility_manager.get_visible_columns_list()

        for column_index, column_key in enumerate(visible_columns):
            actual_column_index = column_index + 1  # +1 for status column
            current_width = self._widget.columnWidth(actual_column_index)
            proper_width = self._width_manager.ensure_column_proper_width(column_key, current_width)
            if proper_width != current_width:
                self._programmatic_resize = True
                self._widget.setColumnWidth(actual_column_index, proper_width)
                self._programmatic_resize = False

    def reset_column_widths_to_defaults(self) -> None:
        """Reset all column widths to their default values."""
        visible_columns = self._visibility_manager.get_visible_columns_list()

        for column_index, column_key in enumerate(visible_columns):
            actual_column_index = column_index + 1

            cfg = self._service.get_column_config(column_key)
            if cfg:
                default_width = cfg.width
                self._programmatic_resize = True
                self._widget.setColumnWidth(actual_column_index, default_width)
                self._programmatic_resize = False

        logger.info("[ColumnManagement] Reset all column widths to defaults")

    def check_and_fix_column_widths(self) -> None:
        """Check and fix any column width issues."""
        visible_columns = self._visibility_manager.get_visible_columns_list()

        for column_index, column_key in enumerate(visible_columns):
            actual_column_index = column_index + 1
            current_width = self._widget.columnWidth(actual_column_index)

            cfg = self._service.get_column_config(column_key)
            if cfg:
                min_width = cfg.min_width if hasattr(cfg, "min_width") else 30

                if current_width < min_width:
                    self._programmatic_resize = True
                    self._widget.setColumnWidth(actual_column_index, min_width)
                    self._programmatic_resize = False
                    logger.debug(
                        "[ColumnManagement] Fixed width for %s: %d -> %d",
                        column_key,
                        current_width,
                        min_width,
                    )

    def auto_fit_columns_to_content(self) -> None:
        """Auto-fit all columns to their content."""
        visible_columns = self._visibility_manager.get_visible_columns_list()

        for column_index, column_key in enumerate(visible_columns):
            actual_column_index = column_index + 1

            # Use Qt's resizeColumnToContents
            self._programmatic_resize = True
            self._widget.resizeColumnToContents(actual_column_index)
            self._programmatic_resize = False

            # Apply minimum width constraint
            cfg = self._service.get_column_config(column_key)
            if cfg:
                min_width = cfg.min_width if hasattr(cfg, "min_width") else 30
                current_width = self._widget.columnWidth(actual_column_index)
                if current_width < min_width:
                    self._widget.setColumnWidth(actual_column_index, min_width)

        logger.info("[ColumnManagement] Auto-fit all columns to content")

    # =====================================
    # Public API - Column Visibility
    # =====================================

    def add_column(self, column_key: str) -> None:
        """Add a column to the visible set.

        Args:
            column_key: Column identifier to show

        """
        self._visibility_manager.add_column(column_key)
        # Reconfigure columns to refresh header and apply proper width
        self.configure_columns()

    def remove_column(self, column_key: str) -> None:
        """Remove a column from the visible set.

        Args:
            column_key: Column identifier to hide

        """
        self._visibility_manager.remove_column(column_key)
        # Reconfigure columns to refresh header
        self.configure_columns()

    def get_visible_columns_list(self) -> list[str]:
        """Get list of currently visible column keys.

        Returns:
            List of visible column keys in display order

        """
        return self._visibility_manager.get_visible_columns_list()

    def refresh_columns_after_model_change(self) -> None:
        """Refresh column configuration after model changes."""
        self.configure_columns()

    def toggle_column_visibility(self, column_key: str) -> None:
        """Toggle visibility of a column.

        Args:
            column_key: Column key to toggle

        """
        self._visibility_manager.toggle_column_visibility(column_key)

    def sync_view_model_columns(self) -> None:
        """Ensure view and model have synchronized column visibility."""
        self._visibility_manager.sync_view_model_columns()

    def load_column_visibility_config(self) -> dict[str, bool]:
        """Load column visibility configuration from config.

        Returns:
            Column visibility state (column_key -> visible)

        """
        return self._visibility_manager.load_visibility_config()

    # =====================================
    # Public API - Persistence
    # =====================================

    def force_save_column_changes(self) -> None:
        """Force immediate save of pending column changes (called on shutdown)."""
        self._width_manager.force_save_pending_changes()

    # =====================================
    # Public API - Header Management
    # =====================================

    def _update_header_visibility(self) -> None:
        """Update header visibility based on table empty state.

        Note: This is a public API for backward compatibility with file_table/view.py.
        """
        self._header_configurator._update_header_visibility()

    # =====================================
    # Event Handlers
    # =====================================

    def handle_column_resized(self, logical_index: int, old_size: int, new_size: int) -> None:
        """Handle column resize events and save user preferences.

        Args:
            logical_index: Column logical index
            old_size: Previous column width
            new_size: New column width

        """
        if self._programmatic_resize:
            return

        column_key = self._header_configurator.get_column_key_from_index(logical_index)
        if not column_key:
            return

        # Enforce minimum width
        cfg = self._service.get_column_config(column_key)
        min_width = cfg.min_width if cfg else 30

        if new_size < min_width:
            self._programmatic_resize = True
            self._widget.setColumnWidth(logical_index, min_width)
            self._programmatic_resize = False
            new_size = min_width

        # Schedule delayed save
        from oncutf.config import COLUMN_RESIZE_BEHAVIOR

        if COLUMN_RESIZE_BEHAVIOR.get("PRESERVE_USER_WIDTHS", True):
            self._width_manager.schedule_column_save(column_key, new_size)

        # Update scrollbar visibility after column resize
        if hasattr(self._widget, "_update_scrollbar_visibility"):
            self._widget._update_scrollbar_visibility()

    def handle_column_moved(
        self, logical_index: int, old_visual_index: int, new_visual_index: int
    ) -> None:
        """Handle column reorder events.

        Args:
            logical_index: Column logical index
            old_visual_index: Previous visual position
            new_visual_index: New visual position

        """
        logger.debug(
            "Column %d moved from visual %d to %d",
            logical_index,
            old_visual_index,
            new_visual_index,
        )

    def handle_keyboard_shortcut(self, key: int, modifiers) -> bool:
        """Handle keyboard shortcuts for column management.

        Args:
            key: Qt key code
            modifiers: Qt keyboard modifiers

        Returns:
            True if shortcut was handled, False otherwise

        """
        # Check for Ctrl+T (auto-fit) or Ctrl+Shift+T (reset)
        if key == Qt.Key_T:
            if modifiers == (Qt.ControlModifier | Qt.ShiftModifier):
                # Ctrl+Shift+T: Reset column widths to default
                self.reset_column_widths_to_defaults()
                return True
            if modifiers == Qt.ControlModifier:
                # Ctrl+T: Auto-fit columns to content
                self.auto_fit_columns_to_content()
                return True

        return False

    # =====================================
    # Lifecycle
    # =====================================

    def register_shutdown_hook(self) -> None:
        """Register shutdown hook to save pending changes on app exit."""
        if self._shutdown_hook_registered:
            return

        try:
            from oncutf.ui.adapters.qt_app_context import get_qt_app_context

            context = get_qt_app_context()
            if hasattr(context, "register_shutdown_callback"):
                context.register_shutdown_callback(self.force_save_column_changes)
                self._shutdown_hook_registered = True
                logger.debug("[ColumnManagement] Registered shutdown hook")
        except Exception as e:
            # Suppress warning if context not yet initialized (normal during bootstrap)
            if "not initialized" not in str(e).lower():
                logger.warning("[ColumnManagement] Failed to register shutdown hook: %s", e)

    def unregister_shutdown_hook(self) -> None:
        """Unregister shutdown hook."""
        if not self._shutdown_hook_registered:
            return

        try:
            from oncutf.ui.adapters.qt_app_context import get_qt_app_context

            context = get_qt_app_context()
            if hasattr(context, "unregister_shutdown_callback"):
                context.unregister_shutdown_callback(self.force_save_column_changes)
                self._shutdown_hook_registered = False
                logger.debug("[ColumnManagement] Unregistered shutdown hook")
        except Exception as e:
            logger.warning("[ColumnManagement] Failed to unregister shutdown hook: %s", e)

    # =====================================
    # Internal Helpers
    # =====================================

    def _set_column_alignment(self, column_index: int, alignment: str) -> None:
        """Set text alignment for a specific column.

        Args:
            column_index: Column index
            alignment: Alignment string ('left', 'right', 'center')

        """
        if not self._widget.model():
            return

        # Map alignment strings to Qt constants
        alignment_map = {
            "left": Qt.AlignLeft | Qt.AlignVCenter,
            "right": Qt.AlignRight | Qt.AlignVCenter,
            "center": Qt.AlignCenter,
        }

        qt_alignment = alignment_map.get(alignment, Qt.AlignLeft | Qt.AlignVCenter)
        self._column_alignments[column_index] = qt_alignment

        logger.debug(
            "[ColumnManagement] Set alignment for column %d to %s",
            column_index,
            alignment,
        )

    def _clear_selection_for_column_update(self, _force_emit_signal: bool = False) -> None:
        """Clear selection before column update.

        Args:
            _force_emit_signal: Whether to force emit selection change signal

        """
        # This method can be overridden or connected to widget's selection clearing

    # =====================================
    # Properties for backward compatibility
    # =====================================

    @property
    def _visible_columns(self) -> dict[str, bool]:
        """Access visibility state (for backward compatibility)."""
        return self._visibility_manager.visible_columns

    @_visible_columns.setter
    def _visible_columns(self, value: dict[str, bool]) -> None:
        """Set visibility state (for backward compatibility)."""
        self._visibility_manager.visible_columns = value

    @property
    def _pending_column_changes(self) -> dict[str, int]:
        """Access pending changes (for backward compatibility)."""
        return self._width_manager._pending_column_changes


__all__ = ["ColumnManagementBehavior"]
