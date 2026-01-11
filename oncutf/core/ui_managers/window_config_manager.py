"""Module: window_config_manager.py

Author: Michael Economou
Date: 2025-06-10

window_config_manager.py
Manages window configuration including geometry, state, and splitter positions.
Separates window management logic from MainWindow for better code organization.
"""

from oncutf.core.pyqt_imports import QApplication, QMainWindow
from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.shared.json_config_manager import get_app_config_manager

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
                "[Config] Loaded geometry from config: %s", geometry, extra={"dev_only": True}
            )

            if geometry:
                self.main_window.setGeometry(
                    geometry["x"], geometry["y"], geometry["width"], geometry["height"]
                )
                logger.debug(
                    "[Config] Applied saved window geometry: %s", geometry, extra={"dev_only": True}
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
            logger.error("[Config] Failed to load window configuration: %s", e)
            # If config loading fails, still set smart defaults
            logger.info("[Config] Exception occurred, applying smart defaults as fallback")
            self._set_smart_default_geometry()

    def save_window_config(self) -> None:
        """Save current window state to config manager.

        Saves in logical order:
        1. UI Geometry (window size, position, state)
        2. Splitters (layout proportions)
        3. Headers (column widths for all columns, not just visible)
        """
        try:
            # IMPORTANT: Reload config from file FIRST before making changes
            # This ensures we preserve other config data while updating window state
            if self.config_manager.config_file.exists():
                logger.debug(
                    "[Config] Reloading config before save to preserve other data",
                    extra={"dev_only": True},
                )
                self.config_manager.load()

            window_config = self.config_manager.get_category("window")

            # ====================================================================
            # SECTION 1: UI GEOMETRY
            # ====================================================================

            # Save geometry (use normal geometry if maximized)
            if self.main_window.isMaximized():
                # Use stored restore geometry if available, otherwise use initial
                geo = self._restore_geometry or self._initial_geometry
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

            # Save sort order and other window-related settings
            if hasattr(self.main_window, "context") and self.main_window.context:
                window_config.set("last_folder", self.main_window.context.get_current_folder() or "")
                window_config.set("recursive_mode", self.main_window.context.is_recursive_mode())
            if hasattr(self.main_window, "current_sort_column"):
                window_config.set("sort_column", self.main_window.current_sort_column)
            if hasattr(self.main_window, "current_sort_order"):
                window_config.set("sort_order", int(self.main_window.current_sort_order))

            # ====================================================================
            # SECTION 2: SPLITTERS (layout proportions)
            # ====================================================================

            splitter_states = {}
            if hasattr(self.main_window, "horizontal_splitter"):
                splitter_states["horizontal"] = self.main_window.horizontal_splitter.sizes()
                logger.debug(
                    "[Config] Saved horizontal splitter: %s",
                    splitter_states["horizontal"],
                    extra={"dev_only": True},
                )
            if hasattr(self.main_window, "vertical_splitter"):
                splitter_states["vertical"] = self.main_window.vertical_splitter.sizes()
                logger.debug(
                    "[Config] Saved vertical splitter: %s",
                    splitter_states["vertical"],
                    extra={"dev_only": True},
                )
            if hasattr(self.main_window, "lower_section_splitter"):
                splitter_states["lower_section"] = self.main_window.lower_section_splitter.sizes()
                logger.debug(
                    "[Config] Saved lower section splitter: %s",
                    splitter_states["lower_section"],
                    extra={"dev_only": True},
                )
            window_config.set("splitter_states", splitter_states)

            # ====================================================================
            # SECTION 3: HEADERS (column widths for ALL columns)
            # ====================================================================

            # Save file table column widths (ALL columns, not just visible)
            if hasattr(self.main_window, "file_table_view"):
                file_model = self.main_window.file_table_view.model()
                if file_model:
                    column_widths = {}

                    # Save status column (always column 0)
                    column_widths["status"] = self.main_window.file_table_view.columnWidth(0)

                    # Get all columns via the column manager service, not the model
                    if hasattr(self.main_window, "column_manager") and hasattr(
                        self.main_window.column_manager, "column_service"
                    ):
                        all_columns = self.main_window.column_manager.column_service.get_all_columns()
                    elif hasattr(file_model, "get_all_columns"):
                        all_columns = file_model.get_all_columns()
                    else:
                        # Fallback: get visible columns
                        all_columns = dict.fromkeys(file_model.get_visible_columns())

                    # Save ALL columns by their keys (including hidden ones)
                    for i, column_key in enumerate(all_columns.keys()):
                        column_index = i + 1  # +1 because status is column 0
                        if column_index < self.main_window.file_table_view.columnCount():
                            column_widths[column_key] = self.main_window.file_table_view.columnWidth(
                                column_index
                            )

                    window_config.set("file_table_column_widths", column_widths)
                    logger.info(
                        "[Config] Saved file table column widths for %d columns: %s",
                        len(column_widths),
                        list(column_widths.keys()),
                        extra={"dev_only": True},
                    )

            # Save metadata tree column widths
            if hasattr(self.main_window, "metadata_tree_view"):
                metadata_model = self.main_window.metadata_tree_view.model()
                if metadata_model:
                    metadata_column_widths = {}
                    # Metadata tree has "key" and "value" columns (indices 0 and 1)
                    metadata_column_widths["key"] = self.main_window.metadata_tree_view.columnWidth(0)
                    metadata_column_widths["value"] = self.main_window.metadata_tree_view.columnWidth(1)
                    window_config.set("metadata_tree_column_widths", metadata_column_widths)
                    logger.debug(
                        "[Config] Saved metadata tree column widths: %s",
                        metadata_column_widths,
                        extra={"dev_only": True},
                    )

            # Save column visibility states
            if hasattr(self.main_window, "column_manager"):
                column_states = {
                    "file_table": self.main_window.column_manager.save_column_state("file_table"),
                    "metadata_tree": self.main_window.column_manager.save_column_state(
                        "metadata_tree"
                    ),
                }
                window_config.set("column_states", column_states)

            # Save file tree expanded state
            if hasattr(self.main_window, "file_tree_view"):
                expanded_paths = self.main_window.file_tree_view._save_expanded_state()
                window_config.set("file_tree_expanded_paths", expanded_paths)
                logger.debug(
                    "[Config] Saved %d file tree expanded paths",
                    len(expanded_paths),
                    extra={"dev_only": True},
                )

            # Mark dirty for debounced save
            self.config_manager.mark_dirty()

            logger.info("[Config] Window configuration marked for save", extra={"dev_only": True})

        except Exception as e:
            logger.error("[Config] Failed to save window configuration: %s", e)

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

            logger.info("[Config] Primary screen detected: %dx%d", screen_width, screen_height)

            # Import screen size configuration from config
            from oncutf.core.config_imports import (
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
                "[Config] Smart geometry set: %dx%d at (%d, %d)", window_width, window_height, x, y
            )

        except Exception as e:
            logger.error("[Config] Failed to set smart default geometry: %s", e)
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
                    "[Config] Applied horizontal splitter: %s",
                    splitter_states["horizontal"],
                    extra={"dev_only": True},
                )

            if "vertical" in splitter_states and hasattr(self.main_window, "vertical_splitter"):
                self.main_window.vertical_splitter.setSizes(splitter_states["vertical"])
                logger.debug(
                    "[Config] Applied vertical splitter: %s",
                    splitter_states["vertical"],
                    extra={"dev_only": True},
                )

            if "lower_section" in splitter_states and hasattr(
                self.main_window, "lower_section_splitter"
            ):
                self.main_window.lower_section_splitter.setSizes(splitter_states["lower_section"])
                logger.debug(
                    "[Config] Applied lower section splitter: %s",
                    splitter_states["lower_section"],
                    extra={"dev_only": True},
                )

            # Store config values for later use
            self.main_window._last_folder_from_config = window_config.get("last_folder", "")
            self.main_window._recursive_mode_from_config = window_config.get(
                "recursive_mode", False
            )
            # NOTE: Sort column restoration feature tracked in TODO.md
            # For now, default to filename (column 2) instead of color (column 1)
            self.main_window._sort_column_from_config = window_config.get("sort_column", 2)
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

            # Restore file tree expanded state
            if hasattr(self.main_window, "file_tree_view"):
                expanded_paths = window_config.get("file_tree_expanded_paths", [])
                if expanded_paths:
                    self.main_window.file_tree_view._restore_expanded_state(expanded_paths)
                    logger.debug(
                        "[Config] Restored %d file tree expanded paths",
                        len(expanded_paths),
                        extra={"dev_only": True},
                    )

            logger.info("[Config] Configuration applied successfully", extra={"dev_only": True})

        except Exception as e:
            logger.error("[Config] Failed to apply loaded configuration: %s", e)

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
            logger.error("[Config] Error handling window state change: %s", e)

    def _refresh_file_table_for_window_change(self) -> None:
        """Refresh file table layout after window state changes."""
        try:
            if hasattr(self.main_window, "file_table_view") and self.main_window.file_table_view:
                # Schedule a delayed refresh to allow window state to settle
                from oncutf.utils.shared.timer_manager import TimerType, get_timer_manager

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
            logger.error("[Config] Error refreshing file table for window change: %s", e)

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
            logger.info("[Config] Window centered at (%d, %d)", x, y)

        except Exception as e:
            logger.error("[Config] Error centering window: %s", e)

    def get_last_folder_from_config(self) -> str:
        """Get the last folder path from configuration."""
        return getattr(self.main_window, "_last_folder_from_config", "")

    def get_recursive_mode_from_config(self) -> bool:
        """Get the recursive mode from configuration."""
        return getattr(self.main_window, "_recursive_mode_from_config", False)

    def get_sort_settings_from_config(self) -> tuple[int, int]:
        """Get sort column and order from configuration."""
        # NOTE: Sort column restoration feature tracked in TODO.md
        # Default to filename column (2) instead of color (1)
        column = getattr(self.main_window, "_sort_column_from_config", 2)
        order = getattr(self.main_window, "_sort_order_from_config", 0)
        return column, order

    def restore_last_folder_if_available(self) -> None:
        """Restore the last folder if available and user wants it."""
        # Use MainWindowController for session restore orchestration
        if not hasattr(self.main_window, "main_window_controller"):
            logger.warning("[Config] MainWindowController not available for session restore")
            return

        # Get configuration values
        last_folder = getattr(self.main_window, "_last_folder_from_config", None)
        recursive = getattr(self.main_window, "_recursive_mode_from_config", False)
        sort_column = getattr(self.main_window, "_sort_column_from_config", None)
        sort_order = getattr(self.main_window, "_sort_order_from_config", None)

        if not last_folder:
            return

        logger.info("[Config] Using MainWindowController for session restore")

        # Call MainWindowController orchestration method
        result = self.main_window.main_window_controller.restore_last_session_workflow(
            last_folder=last_folder,
            recursive=recursive,
            load_metadata=False,  # Don't auto-load metadata on restore
            sort_column=sort_column,
            sort_order=sort_order,
        )

        # Apply sort configuration if needed
        if (
            result.get("success")
            and result.get("sort_column") is not None
            and hasattr(self.main_window, "sort_by_column")
        ):
            from oncutf.core.pyqt_imports import Qt

            qt_sort_order = Qt.AscendingOrder if result["sort_order"] == 0 else Qt.DescendingOrder
            self.main_window.sort_by_column(result["sort_column"], qt_sort_order)

            logger.info(
                "[Config] Applied sort: column=%d, order=%s",
                result["sort_column"],
                "ASC" if result["sort_order"] == 0 else "DESC",
            )

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
