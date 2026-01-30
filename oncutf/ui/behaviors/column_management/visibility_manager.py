"""Column visibility management operations.

Handles add/remove columns, visibility config loading/saving, and sync.

Author: Michael Economou
Date: 2026-01-05
"""

from typing import TYPE_CHECKING

from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.ui.behaviors.column_management.protocols import ColumnManageableWidget
    from oncutf.ui.behaviors.column_management.width_manager import ColumnWidthManager
    from oncutf.ui.managers.column_service import UnifiedColumnService

logger = get_cached_logger(__name__)


class ColumnVisibilityManager:
    """Manages column visibility state and operations."""

    def __init__(
        self,
        widget: "ColumnManageableWidget",
        service: "UnifiedColumnService",
        width_manager: "ColumnWidthManager",
    ):
        """Initialize visibility manager.

        Args:
            widget: The table widget to manage
            service: Column service for configuration
            width_manager: Width manager for width operations

        """
        self._widget = widget
        self._service = service
        self._width_manager = width_manager
        self._visible_columns: dict[str, bool] = {}

    def load_visibility_config(self) -> dict[str, bool]:
        """Load column visibility configuration from config.

        Returns:
            Column visibility state (column_key -> visible)

        """
        try:
            # Try main config system first
            main_window = self._widget._get_main_window()
            if main_window and hasattr(main_window, "window_config_manager"):
                config_manager = main_window.window_config_manager.config_manager
                window_config = config_manager.get_category("window")
                saved_visibility = window_config.get("file_table_columns", {})

                if saved_visibility:
                    logger.debug(
                        "[ColumnVisibility] Loaded from main config: %s",
                        saved_visibility,
                    )
                    # Ensure we have all columns from config
                    complete_visibility = {}
                    for key, cfg in self._service.get_all_columns().items():
                        complete_visibility[key] = saved_visibility.get(key, cfg.default_visible)
                    return complete_visibility

            # Fallback to old method
            from oncutf.utils.shared.json_config_manager import load_config

            config = load_config()
            saved_visibility = config.get("file_table_columns", {})

            if saved_visibility:
                complete_visibility = {}
                for key, cfg in self._service.get_all_columns().items():
                    complete_visibility[key] = saved_visibility.get(key, cfg.default_visible)
                return complete_visibility

        except Exception as e:
            logger.warning("[ColumnVisibility] Error loading config: %s", e)

        # Return default configuration
        return {key: cfg.default_visible for key, cfg in self._service.get_all_columns().items()}

    def save_visibility_config(self) -> None:
        """Save column visibility configuration."""
        try:
            # Build visibility dict from internal tracking
            visibility_dict = self._visible_columns.copy()

            main_window = self._widget._get_main_window()
            if main_window and hasattr(main_window, "window_config_manager"):
                config_manager = main_window.window_config_manager.config_manager
                window_config = config_manager.get_category("window")
                window_config.set("file_table_columns", visibility_dict)
                config_manager.mark_dirty()
            else:
                from oncutf.utils.shared.json_config_manager import (
                    load_config,
                    save_config,
                )

                config = load_config()
                if "window" not in config:
                    config["window"] = {}
                config["window"]["file_table_columns"] = visibility_dict
                save_config(config)

            # Invalidate column service cache so it picks up the new settings
            self._service.invalidate_cache()

            visible_columns = self.get_visible_columns_list()
            logger.info("Saved column visibility config: %s", visible_columns)

        except Exception as e:
            logger.error("Failed to save column visibility config: %s", e)

    def get_visible_columns_list(self) -> list[str]:
        """Get list of currently visible column keys.

        Returns:
            List of visible column keys in display order

        """
        if not self._visible_columns:
            self._visible_columns = self.load_visibility_config()

        # Get order from column service
        all_columns = self._service.get_all_columns()

        visible = []
        for key in all_columns:
            if self._visible_columns.get(key, False):
                visible.append(key)

        return visible

    def add_column(self, column_key: str) -> None:
        """Add a column to the visible set.

        Args:
            column_key: Column identifier to show

        """
        if not self._visible_columns:
            self._visible_columns = self.load_visibility_config()

        if self._visible_columns.get(column_key, False):
            logger.debug("[ColumnVisibility] Column %s already visible", column_key)
            return

        self._visible_columns[column_key] = True

        # Update model
        self._update_model_columns()

        # Save config
        self.save_visibility_config()

        logger.info("[ColumnVisibility] Added column: %s", column_key)

    def remove_column(self, column_key: str) -> None:
        """Remove a column from the visible set.

        Args:
            column_key: Column identifier to hide

        """
        if not self._visible_columns:
            self._visible_columns = self.load_visibility_config()

        if not self._visible_columns.get(column_key, False):
            logger.debug("[ColumnVisibility] Column %s already hidden", column_key)
            return

        self._visible_columns[column_key] = False

        # Update model
        self._update_model_columns()

        # Save config
        self.save_visibility_config()

        logger.info("[ColumnVisibility] Removed column: %s", column_key)

    def toggle_column_visibility(self, column_key: str) -> None:
        """Toggle visibility of a column.

        Args:
            column_key: Column key to toggle

        """
        if not self._visible_columns:
            self._visible_columns = self.load_visibility_config()

        current_visibility = self._visible_columns.get(column_key, False)
        new_visibility = not current_visibility

        if new_visibility:
            self.add_column(column_key)
        else:
            self.remove_column(column_key)

        logger.info(
            "[ColumnManagement] Toggled %s visibility: %s -> %s",
            column_key,
            current_visibility,
            new_visibility,
        )

    def _update_model_columns(self) -> None:
        """Update model with current visible columns."""
        model = self._widget.model()
        if model and hasattr(model, "update_visible_columns"):
            # Store current selection before model update
            saved_selection = set()
            if hasattr(self._widget, "_selection_behavior"):
                saved_selection = self._widget._selection_behavior.get_current_selection_safe()

            visible_list = self.get_visible_columns_list()
            model.update_visible_columns(visible_list)

            # Restore selection after model update
            if saved_selection and hasattr(self._widget, "_selection_behavior"):
                self._widget._selection_behavior.update_selection_store(
                    saved_selection, emit_signal=True
                )

    def sync_view_model_columns(self) -> None:
        """Ensure view and model have synchronized column visibility."""
        model = self._widget.model()
        if not model or not hasattr(model, "get_visible_columns"):
            logger.debug("[ColumnSync] No model or model doesn't support get_visible_columns")
            return

        try:
            # Ensure we have complete visibility state
            if not self._visible_columns:
                logger.warning("[ColumnSync] _visible_columns not initialized, reloading")
                self._visible_columns = self.load_visibility_config()

            # Get current state from both view and model
            view_visible = [key for key, visible in self._visible_columns.items() if visible]
            model_visible = model.get_visible_columns()

            logger.debug("[ColumnSync] View visible: %s", view_visible)
            logger.debug("[ColumnSync] Model visible: %s", model_visible)

            # If they differ, update model to match view
            if view_visible != model_visible:
                logger.info("[ColumnSync] Syncing model columns to match view")
                if hasattr(model, "update_visible_columns"):
                    model.update_visible_columns(view_visible)

        except Exception as e:
            logger.error("[ColumnSync] Error syncing columns: %s", e)

    @property
    def visible_columns(self) -> dict[str, bool]:
        """Access the visibility state dict."""
        if not self._visible_columns:
            self._visible_columns = self.load_visibility_config()
        return self._visible_columns

    @visible_columns.setter
    def visible_columns(self, value: dict[str, bool]) -> None:
        """Set the visibility state dict."""
        self._visible_columns = value


__all__ = ["ColumnVisibilityManager"]
