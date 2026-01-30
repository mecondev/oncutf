"""Column width management operations.

Handles width loading, saving, scheduling delayed saves, and width enforcement.

Author: Michael Economou
Date: 2026-01-05
"""
from typing import TYPE_CHECKING

from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.shared.timer_manager import cancel_timer, schedule_dialog_close

if TYPE_CHECKING:
    from oncutf.ui.behaviors.column_management.protocols import ColumnManageableWidget
    from oncutf.ui.managers.column_service import UnifiedColumnService

logger = get_cached_logger(__name__)


class ColumnWidthManager:
    """Manages column width operations including persistence."""

    def __init__(
        self,
        widget: "ColumnManageableWidget",
        service: "UnifiedColumnService",
    ):
        """Initialize width manager.

        Args:
            widget: The table widget to manage
            service: Column service for configuration

        """
        self._widget = widget
        self._service = service
        self._pending_column_changes: dict[str, int] = {}
        self._config_save_timer_id: str | None = None

    def load_column_width(self, column_key: str) -> int:
        """Load column width from config with fallback to defaults.

        Args:
            column_key: Column identifier

        Returns:
            Saved or default width

        """
        try:
            column_cfg = self._service.get_column_config(column_key)
            default_width = column_cfg.width if column_cfg else 100

            main_window = self._widget._get_main_window()
            if main_window and hasattr(main_window, "window_config_manager"):
                try:
                    config_manager = main_window.window_config_manager.config_manager
                    window_config = config_manager.get_category("window")
                    column_widths = window_config.get("file_table_column_widths", {})

                    if column_key in column_widths:
                        saved_width = column_widths[column_key]
                        if saved_width == 100 and default_width > 120:
                            return default_width
                        return saved_width

                    if column_key == "filename":
                        return self._calculate_dynamic_filename_width()
                except Exception:
                    pass

            from oncutf.utils.shared.json_config_manager import load_config

            config = load_config()
            column_widths = config.get("file_table_column_widths", {})

            if column_key == "filename" and column_key not in column_widths:
                return self._calculate_dynamic_filename_width()

            return column_widths.get(column_key, default_width)

        except Exception as e:
            logger.warning("Error loading column width for %s: %s", column_key, e)
            return 100

    def _calculate_dynamic_filename_width(self) -> int:
        """Calculate dynamic filename width based on available space.

        Returns:
            Calculated filename width in pixels

        """
        try:
            from oncutf.ui.helpers.layout_calculators import calculate_dynamic_filename_width
            from oncutf.utils.shared.json_config_manager import get_app_config_manager

            config_manager = get_app_config_manager()
            window_config = config_manager.get_category("window")
            fixed_columns = window_config.get("file_table_fixed_columns", {
                "color": 50,
                "file_size": 85,
                "type": 60,
                "modified": 154,
            })

            viewport = self._widget.viewport()
            if viewport:
                panel_width = viewport.width()
            else:
                main_window = self._widget._get_main_window()
                if main_window and hasattr(main_window, "horizontal_splitter"):
                    splitter_sizes = main_window.horizontal_splitter.sizes()
                    panel_width = splitter_sizes[1] if len(splitter_sizes) > 1 else 800
                else:
                    panel_width = 800

            width = calculate_dynamic_filename_width(
                panel_width=panel_width,
                fixed_column_widths=fixed_columns,
                min_width=80,
                reserved_space=55,
            )

            logger.debug(
                "[WidthManager] Calculated dynamic filename width: %dpx (panel: %dpx)",
                width,
                panel_width
            )
            return width

        except Exception as e:
            logger.warning("Error calculating dynamic filename width: %s", e)
            return 300

    def ensure_column_proper_width(self, column_key: str, current_width: int) -> int:
        """Ensure column has proper width based on content type.

        Args:
            column_key: Column identifier
            current_width: Current column width

        Returns:
            Recommended width for the column

        """
        cfg = self._service.get_column_config(column_key)
        if not cfg:
            return current_width

        # Get content type and recommended width
        content_type = self._service.analyze_column_content_type(column_key)
        min_width = cfg.min_width if hasattr(cfg, "min_width") else 30

        return self._service.get_recommended_width_for_content_type(
            content_type, current_width, min_width
        )

    def schedule_column_save(self, column_key: str, width: int) -> None:
        """Schedule delayed save of column width changes.

        Uses a 7-second delay to batch rapid changes.

        Args:
            column_key: Column identifier
            width: New width to save

        """
        from oncutf.config import COLUMN_RESIZE_BEHAVIOR

        if not COLUMN_RESIZE_BEHAVIOR.get("PRESERVE_USER_WIDTHS", True):
            return

        self._pending_column_changes[column_key] = width

        # Cancel existing timer
        if self._config_save_timer_id:
            cancel_timer(self._config_save_timer_id)
            self._config_save_timer_id = None

        # Start new timer (7 seconds) via TimerManager
        self._config_save_timer_id = schedule_dialog_close(self._save_pending_changes, delay=7000)

        logger.debug(
            "[FileTable] Scheduled delayed save for '%s' width %dpx", column_key, width
        )

    def _save_pending_changes(self) -> None:
        """Save all pending column width changes to config."""
        if not self._pending_column_changes:
            return

        try:
            # Try main config system
            main_window = self._widget._get_main_window()
            if main_window and hasattr(main_window, "window_config_manager"):
                try:
                    config_manager = main_window.window_config_manager.config_manager
                    window_config = config_manager.get_category("window")
                    column_widths = window_config.get("file_table_column_widths", {})

                    for column_key, width in self._pending_column_changes.items():
                        column_widths[column_key] = width

                    window_config.set("file_table_column_widths", column_widths)
                    config_manager.mark_dirty()

                    logger.info(
                        "Saved %d column width changes to main config",
                        len(self._pending_column_changes),
                    )

                    self._pending_column_changes.clear()
                    return

                except Exception as e:
                    logger.warning("Failed to save to main config: %s", e)

            # Fallback
            from oncutf.utils.shared.json_config_manager import load_config, save_config

            config = load_config()
            if "file_table_column_widths" not in config:
                config["file_table_column_widths"] = {}

            for column_key, width in self._pending_column_changes.items():
                config["file_table_column_widths"][column_key] = width

            save_config(config)

            logger.info(
                "Saved %d column width changes to fallback config",
                len(self._pending_column_changes),
            )

            self._pending_column_changes.clear()

        except Exception as e:
            logger.error("Failed to save pending column changes: %s", e)
        finally:
            self._config_save_timer = None

    def force_save_pending_changes(self) -> None:
        """Force immediate save of pending column changes.

        Called on shutdown to ensure changes are persisted.
        """
        if self._pending_column_changes:
            logger.debug("Force saving pending column changes on shutdown")
            self._save_pending_changes()

        if self._config_save_timer:
            self._config_save_timer.stop()
            self._config_save_timer = None

    @property
    def has_pending_changes(self) -> bool:
        """Check if there are unsaved width changes."""
        return bool(self._pending_column_changes)


__all__ = ["ColumnWidthManager"]
