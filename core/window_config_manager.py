"""
Module: window_config_manager.py

Author: Michael Economou
Date: 2025-06-10

window_config_manager.py
Manages window configuration including geometry, state, and splitter positions.
Separates window management logic from MainWindow for better code organization.
"""

import os
from typing import Tuple

from core.pyqt_imports import QApplication, QMainWindow
from utils.json_config_manager import get_app_config_manager
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class WindowConfigManager:
    """Manages window configuration and state persistence."""

    def __init__(self, main_window: QMainWindow) -> None:
        """Initialize WindowConfigManager."""
        self.main_window = main_window
        self.config_manager = get_app_config_manager()
        self._initial_geometry = None
        self._restore_geometry = None
        logger.debug("[WindowConfigManager] Initialized", extra={"dev_only": True})

    def load_window_config(self) -> None:
        """Load and apply window configuration from config manager."""
        try:
            window_config = self.config_manager.get_category("window")

            # Load geometry
            geometry = window_config.get("geometry")
            logger.debug(
                f"[Config] Loaded geometry from config: {geometry}", extra={"dev_only": True}
            )

            if geometry:
                self.main_window.setGeometry(
                    geometry["x"], geometry["y"], geometry["width"], geometry["height"]
                )
                logger.debug(
                    f"[Config] Applied saved window geometry: {geometry}", extra={"dev_only": True}
                )
            else:
                # No saved geometry - set smart defaults based on screen size
                logger.info("[Config] No saved geometry found, applying smart defaults")
                self._set_smart_default_geometry()

            # Load window state
            window_state = window_config.get("window_state", "normal")
            if window_state == "maximized":
                self.main_window.showMaximized()
            elif window_state == "minimized":
                self.main_window.showMinimized()
            else:
                self.main_window.showNormal()

            # Store initial geometry AFTER smart sizing for proper restore behavior
            self._initial_geometry = self.main_window.geometry()

            logger.info(
                "[Config] Window configuration loaded successfully", extra={"dev_only": True}
            )

        except Exception as e:
            logger.error(f"[Config] Failed to load window configuration: {e}")
            # If config loading fails, still set smart defaults
            logger.info("[Config] Exception occurred, applying smart defaults as fallback")
            self._set_smart_default_geometry()

    def save_window_config(self) -> None:
        """Save current window state to config manager."""
        try:
            window_config = self.config_manager.get_category("window")

            # Save geometry (use normal geometry if maximized)
            if self.main_window.isMaximized():
                # Use stored restore geometry if available, otherwise use initial
                if self._restore_geometry:
                    geo = self._restore_geometry
                else:
                    geo = self._initial_geometry
            else:
                geo = self.main_window.geometry()

            window_config.set(
                "geometry",
                {"x": geo.x(), "y": geo.y(), "width": geo.width(), "height": geo.height()},
            )

            # Save window state
            if self.main_window.isMaximized():
                window_state = "maximized"
            elif self.main_window.isMinimized():
                window_state = "minimized"
            else:
                window_state = "normal"
            window_config.set("window_state", window_state)

            # Save splitter states
            splitter_states = {}
            if hasattr(self.main_window, "horizontal_splitter"):
                splitter_states["horizontal"] = self.main_window.horizontal_splitter.sizes()
            if hasattr(self.main_window, "vertical_splitter"):
                splitter_states["vertical"] = self.main_window.vertical_splitter.sizes()
            window_config.set("splitter_states", splitter_states)

            # Save other window-related settings
            if hasattr(self.main_window, "current_folder_path"):
                window_config.set("last_folder", self.main_window.current_folder_path or "")
            if hasattr(self.main_window, "current_folder_is_recursive"):
                window_config.set("recursive_mode", self.main_window.current_folder_is_recursive)
            if hasattr(self.main_window, "current_sort_column"):
                window_config.set("sort_column", self.main_window.current_sort_column)
            if hasattr(self.main_window, "current_sort_order"):
                window_config.set("sort_order", int(self.main_window.current_sort_order))

            # Save column widths using new dictionary format
            if hasattr(self.main_window, "file_table_view"):
                file_model = self.main_window.file_table_view.model()
                if file_model:
                    column_widths = {}
                    # Get visible columns from the model
                    visible_columns = file_model.get_visible_columns()

                    # Save status column (always column 0)
                    column_widths["status"] = self.main_window.file_table_view.columnWidth(0)

                    # Save other columns by their keys
                    for i, column_key in enumerate(visible_columns):
                        column_index = i + 1  # +1 because status is column 0
                        column_widths[column_key] = self.main_window.file_table_view.columnWidth(
                            column_index
                        )

                    window_config.set("file_table_column_widths", column_widths)

            # Save column states using ColumnManager
            if hasattr(self.main_window, "column_manager"):
                column_states = {
                    "file_table": self.main_window.column_manager.save_column_state("file_table"),
                    "metadata_tree": self.main_window.column_manager.save_column_state(
                        "metadata_tree"
                    ),
                }
                window_config.set("column_states", column_states)

            # Actually save the configuration to file
            self.config_manager.save()

            logger.info(
                "[Config] Window configuration saved successfully", extra={"dev_only": True}
            )

        except Exception as e:
            logger.error(f"[Config] Failed to save window configuration: {e}")

    def _set_smart_default_geometry(self) -> None:
        """Set smart default window geometry based on screen size and aspect ratio."""
        try:
            # Use modern QScreen API instead of deprecated QDesktopWidget
            app = QApplication.instance()
            if not app:
                raise RuntimeError("No QApplication instance found")

            # Get the primary screen using modern API
            primary_screen = app.primaryScreen()  # type: ignore[attr-defined]
            if not primary_screen:
                raise RuntimeError("No primary screen found")

            # Get screen geometry (available area excluding taskbars, docks, etc.)
            screen_geometry = primary_screen.availableGeometry()
            screen_width = screen_geometry.width()
            screen_height = screen_geometry.height()

            logger.info(f"[Config] Primary screen detected: {screen_width}x{screen_height}")

            # Import screen size configuration from config
            from core.config_imports import (
                LARGE_SCREEN_MIN_HEIGHT,
                LARGE_SCREEN_MIN_WIDTH,
                SCREEN_SIZE_BREAKPOINTS,
                SCREEN_SIZE_PERCENTAGES,
                WINDOW_MIN_SMART_HEIGHT,
                WINDOW_MIN_SMART_WIDTH,
            )

            # Calculate smart window dimensions based on screen size
            if screen_width >= SCREEN_SIZE_BREAKPOINTS["large_4k"]:
                percentages = SCREEN_SIZE_PERCENTAGES["large_4k"]
                window_width = max(int(screen_width * percentages["width"]), LARGE_SCREEN_MIN_WIDTH)
                window_height = max(
                    int(screen_height * percentages["height"]), LARGE_SCREEN_MIN_HEIGHT
                )
            elif screen_width >= SCREEN_SIZE_BREAKPOINTS["full_hd"]:
                percentages = SCREEN_SIZE_PERCENTAGES["full_hd"]
                window_width = int(screen_width * percentages["width"])
                window_height = int(screen_height * percentages["height"])
            elif screen_width >= SCREEN_SIZE_BREAKPOINTS["laptop"]:
                percentages = SCREEN_SIZE_PERCENTAGES["laptop"]
                window_width = int(screen_width * percentages["width"])
                window_height = int(screen_height * percentages["height"])
            else:
                percentages = SCREEN_SIZE_PERCENTAGES["small"]
                window_width = max(int(screen_width * percentages["width"]), WINDOW_MIN_SMART_WIDTH)
                window_height = max(
                    int(screen_height * percentages["height"]), WINDOW_MIN_SMART_HEIGHT
                )

            # Ensure minimum dimensions and screen bounds
            window_width = max(min(window_width, screen_width - 100), WINDOW_MIN_SMART_WIDTH)
            window_height = max(min(window_height, screen_height - 100), WINDOW_MIN_SMART_HEIGHT)

            # Calculate centered position
            x = screen_geometry.x() + (screen_width - window_width) // 2
            y = screen_geometry.y() + (screen_height - window_height) // 2

            # Apply the geometry
            self.main_window.setGeometry(x, y, window_width, window_height)
            logger.info(
                f"[Config] Smart geometry set: {window_width}x{window_height} at ({x}, {y})"
            )

        except Exception as e:
            logger.error(f"[Config] Failed to set smart default geometry: {e}")
            # Ultimate fallback
            self.main_window.setGeometry(100, 100, 1200, 800)

    def apply_loaded_config(self) -> None:
        """Apply loaded configuration to window components."""
        try:
            window_config = self.config_manager.get_category("window")

            # Apply splitter states
            splitter_states = window_config.get("splitter_states", {})
            if "horizontal" in splitter_states and hasattr(self.main_window, "horizontal_splitter"):
                self.main_window.horizontal_splitter.setSizes(splitter_states["horizontal"])
                logger.debug(
                    f"[Config] Applied horizontal splitter: {splitter_states['horizontal']}",
                    extra={"dev_only": True},
                )

            if "vertical" in splitter_states and hasattr(self.main_window, "vertical_splitter"):
                self.main_window.vertical_splitter.setSizes(splitter_states["vertical"])
                logger.debug(
                    f"[Config] Applied vertical splitter: {splitter_states['vertical']}",
                    extra={"dev_only": True},
                )

            # Store config values for later use
            self.main_window._last_folder_from_config = window_config.get("last_folder", "")
            self.main_window._recursive_mode_from_config = window_config.get(
                "recursive_mode", False
            )
            self.main_window._sort_column_from_config = window_config.get("sort_column", 1)
            self.main_window._sort_order_from_config = window_config.get("sort_order", 0)

            # Load column states using ColumnManager
            if hasattr(self.main_window, "column_manager"):
                column_states = window_config.get("column_states", {})
                if column_states:
                    for table_type, state_data in column_states.items():
                        if state_data:
                            self.main_window.column_manager.load_column_state(
                                table_type, state_data
                            )

            logger.info("[Config] Configuration applied successfully", extra={"dev_only": True})

        except Exception as e:
            logger.error(f"[Config] Failed to apply loaded configuration: {e}")

    def handle_window_state_change(self) -> None:
        """Handle window state changes (maximize, minimize, restore)."""
        try:
            # Store current geometry before state change for proper restore
            if not self.main_window.isMaximized() and not self.main_window.isMinimized():
                self._restore_geometry = self.main_window.geometry()

            # Handle window state specific logic
            if self.main_window.isMaximized():
                logger.debug("[Config] Window maximized")
                self._refresh_file_table_for_window_change()
            elif not self.main_window.isMinimized():
                logger.debug("[Config] Window restored to normal state")
                self._refresh_file_table_for_window_change()

        except Exception as e:
            logger.error(f"[Config] Error handling window state change: {e}")

    def _refresh_file_table_for_window_change(self) -> None:
        """Refresh file table layout after window state changes."""
        try:
            if hasattr(self.main_window, "file_table_view") and self.main_window.file_table_view:
                # Schedule a delayed refresh to allow window state to settle
                from utils.timer_manager import TimerType, get_timer_manager

                def refresh():
                    # Reset manual column preference for auto-sizing - use original FileTableView logic
                    if hasattr(self.main_window.file_table_view, "_manual_column_resize"):
                        self.main_window.file_table_view._manual_column_resize = False
                    if hasattr(self.main_window.file_table_view, "_has_manual_preference"):
                        self.main_window.file_table_view._has_manual_preference = False

                    # Trigger column auto-sizing using original logic
                    if hasattr(self.main_window, "_ensure_initial_column_sizing"):
                        self.main_window._ensure_initial_column_sizing()

                get_timer_manager().schedule(refresh, delay=100, timer_type=TimerType.GENERIC)

        except Exception as e:
            logger.error(f"[Config] Error refreshing file table for window change: {e}")

    def center_window(self) -> None:
        """Center the window on the primary screen."""
        try:
            app = QApplication.instance()
            if not app:
                return

            primary_screen = app.primaryScreen()  # type: ignore[attr-defined]
            if not primary_screen:
                return

            screen_geometry = primary_screen.availableGeometry()
            window_geometry = self.main_window.geometry()

            x = screen_geometry.x() + (screen_geometry.width() - window_geometry.width()) // 2
            y = screen_geometry.y() + (screen_geometry.height() - window_geometry.height()) // 2

            self.main_window.move(x, y)
            logger.info(f"[Config] Window centered at ({x}, {y})")

        except Exception as e:
            logger.error(f"[Config] Error centering window: {e}")

    def get_last_folder_from_config(self) -> str:
        """Get the last folder path from configuration."""
        return getattr(self.main_window, "_last_folder_from_config", "")

    def get_recursive_mode_from_config(self) -> bool:
        """Get the recursive mode from configuration."""
        return getattr(self.main_window, "_recursive_mode_from_config", False)

    def get_sort_settings_from_config(self) -> Tuple[int, int]:
        """Get sort column and order from configuration."""
        column = getattr(self.main_window, "_sort_column_from_config", 1)
        order = getattr(self.main_window, "_sort_order_from_config", 0)
        return column, order

    def restore_last_folder_if_available(self) -> None:
        """Restore the last folder if available and user wants it."""
        if (
            hasattr(self.main_window, "_last_folder_from_config")
            and self.main_window._last_folder_from_config
        ):
            last_folder = self.main_window._last_folder_from_config
            if os.path.exists(last_folder):
                logger.info(f"[Config] Restoring last folder: {last_folder}")
                # Use the file load manager to load the folder
                recursive = getattr(self.main_window, "_recursive_mode_from_config", False)
                if hasattr(self.main_window, "file_load_manager"):
                    self.main_window.file_load_manager.load_folder(
                        last_folder, merge=False, recursive=recursive
                    )

                # Apply sort configuration after loading
                if hasattr(self.main_window, "_sort_column_from_config") and hasattr(
                    self.main_window, "_sort_order_from_config"
                ):
                    from core.pyqt_imports import Qt

                    sort_order = (
                        Qt.AscendingOrder
                        if self.main_window._sort_order_from_config == 0
                        else Qt.DescendingOrder
                    )
                    if hasattr(self.main_window, "sort_by_column"):
                        self.main_window.sort_by_column(
                            self.main_window._sort_column_from_config, sort_order
                        )
            else:
                logger.warning(f"[Config] Last folder no longer exists: {last_folder}")

    def ensure_initial_column_sizing(self) -> None:
        """Ensure column widths are properly sized on startup, especially when no config exists."""
        if (
            hasattr(self.main_window, "file_table_view")
            and self.main_window.file_table_view.model()
        ):
            # No longer need column adjustment - columns maintain fixed widths from config
            logger.debug(
                "[Config] Column sizing handled by fixed-width configuration",
                extra={"dev_only": True},
            )
