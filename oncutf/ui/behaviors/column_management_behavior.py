"""Module: column_management_behavior.py

Author: Michael Economou
Date: 2025-12-28

ColumnManagementBehavior - Composition-based column management.

This is the behavioral replacement for ColumnManagementMixin.
Uses protocol-based composition instead of inheritance.

Provides:
- Column configuration and width management
- Column visibility toggling (add/remove columns)
- Config persistence (load/save column widths and visibility)
- Header visibility management
- Intelligent width validation and content-type detection
- Delayed save mechanism (7 seconds) for performance
- Shutdown hook for forced save
"""

from typing import Protocol

from oncutf.core.pyqt_imports import QHeaderView, QTimer
from oncutf.core.ui_managers.column_service import get_column_service
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class ColumnManageableWidget(Protocol):
    """Protocol defining requirements for widgets that can use ColumnManagementBehavior."""

    def horizontalHeader(self) -> QHeaderView:
        """Return horizontal header."""
        ...

    def model(self):
        """Return Qt model."""
        ...

    def setColumnWidth(self, index: int, width: int) -> None:
        """Set column width."""
        ...

    def columnWidth(self, index: int) -> int:
        """Get column width."""
        ...

    def resizeColumnToContents(self, index: int) -> None:
        """Auto-resize column to contents."""
        ...

    def viewport(self):
        """Return viewport widget."""
        ...

    def updateGeometry(self) -> None:
        """Update widget geometry."""
        ...

    def is_empty(self) -> bool:
        """Check if table is empty."""
        ...

    def _get_main_window(self):
        """Get main window reference."""
        ...


class ColumnManagementBehavior:
    """Behavior class providing comprehensive column management.

    This is the composition-based replacement for ColumnManagementMixin.
    Handles all aspects of column management including width persistence,
    visibility management, auto-fit, and intelligent validation.

    State management:
    - All column state is stored in this behavior instance
    - Delayed save mechanism (7 seconds) for performance
    - Shutdown hook integration for forced save

    Usage:
        class MyTableView(QTableView):
            def __init__(self):
                super().__init__()
                self._column_mgmt = ColumnManagementBehavior(self)
                self._column_mgmt.configure_columns()
    """

    def __init__(self, widget: ColumnManageableWidget):
        """Initialize behavior with widget reference.

        Args:
            widget: Widget implementing ColumnManageableWidget protocol
        """
        self._widget = widget
        self._service = get_column_service()

        # Column state
        self._visible_columns: dict = {}
        self._config_save_timer: QTimer | None = None
        self._pending_column_changes: dict[str, int] = {}
        self._programmatic_resize = False
        self._configuring_columns = False
        self._header_resize_connected = False
        self._column_alignments: dict[int, int] = {}
        self._shutdown_hook_registered = False

    # =====================================
    # Public API - Configuration
    # =====================================

    def configure_columns(self) -> None:
        """Configure columns with values from config."""
        if not self._widget.model() or self._widget.model().columnCount() == 0:
            return

        header = self._widget.horizontalHeader()
        if not header:
            return

        # Prevent recursive calls
        if self._configuring_columns:
            return

        self._configuring_columns = True

        try:
            from oncutf.utils.shared.timer_manager import schedule_ui_update

            schedule_ui_update(
                self._configure_columns_delayed,
                delay=10,
                timer_id=f"column_config_{id(self._widget)}",
            )
        except Exception as e:
            logger.error("[ColumnConfig] Error during column configuration: %s", e)
            self._configuring_columns = False

    def ensure_all_columns_proper_width(self) -> None:
        """Ensure all visible columns have proper width to minimize text elision."""
        try:
            if not self._widget.model():
                return

            visible_columns = (
                self._widget.model().get_visible_columns()
                if hasattr(self._widget.model(), "get_visible_columns")
                else []
            )

            for column_key in visible_columns:
                column_index = visible_columns.index(column_key) + 1  # +1 for status column

                if column_index >= self._widget.model().columnCount():
                    continue

                current_width = self._widget.columnWidth(column_index)
                recommended_width = self._ensure_column_proper_width(column_key, current_width)

                if recommended_width != current_width:
                    logger.debug(
                        "[ColumnWidth] Adjusting '%s' from %dpx to %dpx",
                        column_key,
                        current_width,
                        recommended_width,
                    )
                    self._widget.setColumnWidth(column_index, recommended_width)
                    self._schedule_column_save(column_key, recommended_width)

        except Exception as e:
            logger.warning("Error ensuring all columns proper width: %s", e)

    def reset_column_widths_to_defaults(self) -> None:
        """Reset all column widths to their default values."""
        try:
            # Delegate to service
            self._service.reset_all_widths()

            # Reconfigure columns
            self.configure_columns()
            logger.info("Column widths reset to defaults")

        except Exception as e:
            logger.error("Failed to reset column widths: %s", e)

    def check_and_fix_column_widths(self) -> None:
        """Check if column widths need to be reset due to incorrect saved values."""
        try:
            # Get current saved widths
            main_window = self._widget._get_main_window()
            saved_widths = {}

            if main_window and hasattr(main_window, "window_config_manager"):
                try:
                    config_manager = main_window.window_config_manager.config_manager
                    window_config = config_manager.get_category("window")
                    saved_widths = window_config.get("file_table_column_widths", {})
                except Exception:
                    # Try fallback method
                    from oncutf.utils.shared.json_config_manager import load_config

                    config = load_config()
                    saved_widths = config.get("file_table_column_widths", {})

            # Check if most columns are set to 100px (suspicious)
            suspicious_count = 0
            total_count = 0


            for column_key, column_config in self._service.get_all_columns().items():
                if getattr(column_config, "default_visible", False):
                    total_count += 1
                    default_width = getattr(column_config, "width", 100)
                    saved_width = saved_widths.get(column_key, default_width)

                    if saved_width == 100 and default_width > 120:
                        suspicious_count += 1

            # If most visible columns have suspicious widths, reset them
            if total_count > 0 and suspicious_count >= (total_count * 0.5):
                self.reset_column_widths_to_defaults()
                if self._widget.model() and self._widget.model().columnCount() > 0:
                    from oncutf.utils.shared.timer_manager import schedule_ui_update

                    schedule_ui_update(lambda: self.configure_columns(), delay=10)

        except Exception as e:
            logger.error("Failed to check column widths: %s", e)

    def auto_fit_columns_to_content(self) -> None:
        """Auto-fit all visible columns to their content."""
        try:
            from oncutf.config import GLOBAL_MIN_COLUMN_WIDTH

            if not self._widget.model():
                return

            visible_columns = (
                self._widget.model().get_visible_columns()
                if hasattr(self._widget.model(), "get_visible_columns")
                else []
            )

            header = self._widget.horizontalHeader()
            if not header:
                return

            for i, column_key in enumerate(visible_columns):
                column_index = i + 1  # +1 for status column


                cfg = self._service.get_column_config(column_key)

                # Filename column: set to stretch
                if column_key == "filename":
                    header.setSectionResizeMode(column_index, QHeaderView.Stretch)
                    continue

                # Other columns: resize to contents
                self._widget.resizeColumnToContents(column_index)

                # Apply minimum width
                min_width = max(
                    (cfg.min_width if cfg else GLOBAL_MIN_COLUMN_WIDTH), GLOBAL_MIN_COLUMN_WIDTH
                )
                current_width = self._widget.columnWidth(column_index)
                final_width = max(current_width, min_width)

                # Apply intelligent validation
                final_width = self._ensure_column_proper_width(column_key, final_width)

                if final_width != current_width:
                    self._widget.setColumnWidth(column_index, final_width)

                self._schedule_column_save(column_key, final_width)

            self._update_header_visibility()

        except Exception as e:
            logger.error("Error auto-fitting columns: %s", e)

    # =====================================
    # Public API - Column Visibility
    # =====================================

    def add_column(self, column_key: str) -> None:
        """Add a column to the visible columns list."""
        try:
            if not self._widget.model():
                return

            # Clear selection
            self._clear_selection_for_column_update()

            # Get current visible columns and add the new one
            current_columns = self.get_visible_columns_list()
            if column_key not in current_columns:
                # Determine position based on column config order
                from oncutf.config import FILE_TABLE_COLUMN_CONFIG

                # Build ordered list based on config
                config_order = list(FILE_TABLE_COLUMN_CONFIG.keys())
                new_columns = current_columns.copy()

                # Find the right position to insert
                insert_pos = len(new_columns)
                for _i, key in enumerate(config_order):
                    if key == column_key:
                        # Find the position after the last column that comes before this one
                        for j, existing_key in enumerate(new_columns):
                            if existing_key in config_order:
                                existing_pos = config_order.index(existing_key)
                                if existing_pos > config_order.index(column_key):
                                    insert_pos = j
                                    break
                        break

                new_columns.insert(insert_pos, column_key)

                # Update internal tracking BEFORE updating model
                self._visible_columns[column_key] = True

                # Sync widget's _visible_columns if it exists
                if hasattr(self._widget, "_visible_columns"):
                    self._widget._visible_columns[column_key] = True

                # Update model with new columns list
                if hasattr(self._widget.model(), "update_visible_columns"):
                    self._widget.model().update_visible_columns(new_columns)

            # Ensure proper width
            from oncutf.utils.shared.timer_manager import schedule_ui_update

            schedule_ui_update(self._ensure_new_column_proper_width, delay=50)

            # Save visibility config
            self._save_column_visibility_config()

            logger.info("Added column: %s", column_key)

        except Exception as e:
            logger.error("Error adding column %s: %s", column_key, e)

    def remove_column(self, column_key: str) -> None:
        """Remove a column from the visible columns list."""
        try:
            if not self._widget.model():
                return

            # Clear selection
            self._clear_selection_for_column_update()

            # Get current visible columns and remove the specified one
            current_columns = self.get_visible_columns_list()
            if column_key in current_columns:
                new_columns = [c for c in current_columns if c != column_key]

                # Update internal tracking BEFORE updating model
                self._visible_columns[column_key] = False

                # Sync widget's _visible_columns if it exists
                if hasattr(self._widget, "_visible_columns"):
                    self._widget._visible_columns[column_key] = False

                # Update model with new columns list
                if hasattr(self._widget.model(), "update_visible_columns"):
                    self._widget.model().update_visible_columns(new_columns)

            # Save visibility config
            self._save_column_visibility_config()

            logger.info("Removed column: %s", column_key)

        except Exception as e:
            logger.error("Error removing column %s: %s", column_key, e)

    def get_visible_columns_list(self) -> list:
        """Get list of currently visible column keys."""
        if self._widget.model() and hasattr(self._widget.model(), "get_visible_columns"):
            return self._widget.model().get_visible_columns()
        return []

    def refresh_columns_after_model_change(self) -> None:
        """Refresh columns after model changes."""
        self.configure_columns()
        if hasattr(self._widget, "update_placeholder_visibility"):
            self._widget.update_placeholder_visibility()
        self._update_header_visibility()
        self._widget.viewport().update()

        if hasattr(self._widget, "_ensure_no_word_wrap"):
            self._widget._ensure_no_word_wrap()

    # =====================================
    # Public API - Shutdown & Persistence
    # =====================================

    def force_save_column_changes(self) -> None:
        """Force immediate save of pending column changes (called on shutdown)."""
        if self._pending_column_changes:
            logger.debug("Force saving pending column changes on shutdown")
            self._save_pending_column_changes()

        if self._config_save_timer:
            self._config_save_timer.stop()
            self._config_save_timer = None

    # =====================================
    # Event Handlers
    # =====================================

    def handle_column_resized(self, logical_index: int, old_size: int, new_size: int) -> None:
        """Handle column resize events and save user preferences."""
        if self._programmatic_resize:
            return

        column_key = self._get_column_key_from_index(logical_index)
        if not column_key:
            return

        # Enforce minimum width

        service = self._service
        cfg = service.get_column_config(column_key)
        min_width = cfg.min_width if cfg else 30

        if new_size < min_width:
            self._programmatic_resize = True
            self._widget.setColumnWidth(logical_index, min_width)
            self._programmatic_resize = False
            new_size = min_width

        # Schedule delayed save
        from oncutf.config import COLUMN_RESIZE_BEHAVIOR

        if COLUMN_RESIZE_BEHAVIOR.get("PRESERVE_USER_WIDTHS", True):
            self._schedule_column_save(column_key, new_size)

        # Update scrollbar visibility after column resize
        if hasattr(self._widget, "_update_scrollbar_visibility"):
            self._widget._update_scrollbar_visibility()

    def handle_column_moved(
        self, logical_index: int, old_visual_index: int, new_visual_index: int
    ) -> None:
        """Handle column reorder events."""
        logger.debug(
            "Column %d moved from visual %d to %d", logical_index, old_visual_index, new_visual_index
        )

    # =====================================
    # Internal Implementation
    # =====================================

    def _configure_columns_delayed(self) -> None:
        """Delayed column configuration to ensure model synchronization."""
        try:
            header = self._widget.horizontalHeader()
            if not header or not self._widget.model():
                return

            header.show()

            # Configure status column (always column 0)
            self._widget.setColumnWidth(0, 45)
            header.setSectionResizeMode(0, header.Fixed)

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
                    width = self._load_column_width(column_key)
                    width = self._ensure_column_proper_width(column_key, width)

                    from oncutf.config import FILE_TABLE_COLUMN_CONFIG

                    column_config = FILE_TABLE_COLUMN_CONFIG.get(column_key, {})
                    is_resizable = column_config.get("resizable", True)

                    if is_resizable:
                        header.setSectionResizeMode(actual_column_index, header.Interactive)
                    else:
                        header.setSectionResizeMode(actual_column_index, header.Fixed)

                    self._widget.setColumnWidth(actual_column_index, width)

            # Connect header resize signal
            if not self._header_resize_connected:
                header.sectionResized.connect(self.handle_column_resized)
                self._header_resize_connected = True

            # Force viewport update
            self._widget.viewport().update()
            self._widget.updateGeometry()

            # Update header visibility
            self._update_header_visibility()

        finally:
            self._configuring_columns = False

    def _ensure_column_proper_width(self, column_key: str, current_width: int) -> int:
        """Ensure column has proper width based on content type."""

        cfg = self._service.get_column_config(column_key)
        if not cfg:
            return current_width

        # Get content type
        content_type = self._analyze_column_content_type(column_key)

        # Get recommended width
        recommended_width = self._get_recommended_width_for_content_type(
            content_type, current_width, cfg.min_width if hasattr(cfg, "min_width") else 30
        )

        return recommended_width

    def _analyze_column_content_type(self, column_key: str) -> str:
        """Analyze column content type for width recommendations."""
        return self._service.analyze_column_content_type(column_key)

    def _get_recommended_width_for_content_type(
        self, content_type: str, current_width: int, min_width: int
    ) -> int:
        """Get recommended width based on content type."""
        return self._service.get_recommended_width_for_content_type(
            content_type, current_width, min_width
        )

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

    def _load_column_width(self, column_key: str) -> int:
        """Load column width from config with fallback to defaults."""
        try:

            service = self._service
            column_cfg = service.get_column_config(column_key)
            default_width = column_cfg.width if column_cfg else 100

            # Try main config system
            main_window = self._widget._get_main_window()
            if main_window and hasattr(main_window, "window_config_manager"):
                try:
                    config_manager = main_window.window_config_manager.config_manager
                    window_config = config_manager.get_category("window")
                    column_widths = window_config.get("file_table_column_widths", {})

                    if column_key in column_widths:
                        saved_width = column_widths[column_key]
                        # Avoid suspicious 100px widths
                        if saved_width == 100 and default_width > 120:
                            return default_width
                        return saved_width
                except Exception:
                    pass

            # Fallback to old method
            from oncutf.utils.shared.json_config_manager import load_config

            config = load_config()
            column_widths = config.get("file_table_column_widths", {})
            return column_widths.get(column_key, default_width)

        except Exception as e:
            logger.warning("Error loading column width for %s: %s", column_key, e)
            return 100

    def _schedule_column_save(self, column_key: str, width: int) -> None:
        """Schedule delayed save of column width changes."""
        from oncutf.config import COLUMN_RESIZE_BEHAVIOR

        if not COLUMN_RESIZE_BEHAVIOR.get("PRESERVE_USER_WIDTHS", True):
            return

        self._pending_column_changes[column_key] = width

        # Cancel existing timer
        if self._config_save_timer:
            self._config_save_timer.stop()
            self._config_save_timer = None

        # Start new timer (7 seconds)
        self._config_save_timer = QTimer()
        self._config_save_timer.setSingleShot(True)
        self._config_save_timer.timeout.connect(self._save_pending_column_changes)
        self._config_save_timer.start(7000)

        logger.debug(
            "[FileTable] Scheduled delayed save for '%s' width %dpx", column_key, width
        )

    def _save_pending_column_changes(self) -> None:
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

    def _save_column_visibility_config(self) -> None:
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
                from oncutf.utils.shared.json_config_manager import load_config, save_config

                config = load_config()
                if "window" not in config:
                    config["window"] = {}
                config["window"]["file_table_columns"] = visibility_dict
                save_config(config)

            # Invalidate column service cache so it picks up the new settings
            service = self._service
            service.invalidate_cache()

            visible_columns = self.get_visible_columns_list()
            logger.info("Saved column visibility config: %s", visible_columns)

        except Exception as e:
            logger.error("Failed to save column visibility config: %s", e)

    def _get_column_key_from_index(self, logical_index: int) -> str:
        """Get column key from logical index."""
        if logical_index == 0:
            return ""  # Status column has no key

        visible_columns = self.get_visible_columns_list()
        column_index = logical_index - 1  # Subtract 1 for status column

        if 0 <= column_index < len(visible_columns):
            return visible_columns[column_index]

        return ""

    def _ensure_new_column_proper_width(self) -> None:
        """Ensure newly added column has proper width."""
        if not self._widget.model():
            return

        visible_columns = self.get_visible_columns_list()
        if not visible_columns:
            return

        # Get last visible column (the newly added one)
        new_column_key = visible_columns[-1]
        column_index = len(visible_columns)  # +1 for status, -1 for 0-index = same

        if column_index < self._widget.model().columnCount():
            width = self._load_column_width(new_column_key)
            width = self._ensure_column_proper_width(new_column_key, width)
            self._widget.setColumnWidth(column_index, width)

    def _clear_selection_for_column_update(self, force_emit_signal: bool = False) -> None:
        """Clear selection before column update."""
        # This method can be overridden or connected to widget's selection clearing

    def _set_column_alignment(self, column_index: int, alignment: str) -> None:
        """Set text alignment for a specific column.

        Args:
            column_index: Column index
            alignment: Alignment string ('left', 'right', 'center')
        """
        from oncutf.core.pyqt_imports import Qt

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

    def load_column_visibility_config(self) -> dict[str, bool]:
        """Load column visibility configuration from config.

        Returns:
            dict: Column visibility state (column_key -> visible)
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

                    service = self._service
                    complete_visibility = {}
                    for key, cfg in service.get_all_columns().items():
                        complete_visibility[key] = saved_visibility.get(key, cfg.default_visible)
                    return complete_visibility

            # Fallback to old method
            from oncutf.utils.shared.json_config_manager import load_config

            config = load_config()
            saved_visibility = config.get("file_table_columns", {})

            if saved_visibility:

                service = self._service
                complete_visibility = {}
                for key, cfg in service.get_all_columns().items():
                    complete_visibility[key] = saved_visibility.get(key, cfg.default_visible)
                return complete_visibility

        except Exception as e:
            logger.warning("[ColumnVisibility] Error loading config: %s", e)

        # Return default configuration

        service = self._service
        return {key: cfg.default_visible for key, cfg in service.get_all_columns().items()}

    def sync_view_model_columns(self) -> None:
        """Ensure view and model have synchronized column visibility."""
        model = self._widget.model()
        if not model or not hasattr(model, "get_visible_columns"):
            logger.debug(
                "[ColumnSync] No model or model doesn't support get_visible_columns"
            )
            return

        try:
            # Ensure we have complete visibility state
            if not self._visible_columns:
                logger.warning("[ColumnSync] _visible_columns not initialized, reloading")
                self._visible_columns = self.load_column_visibility_config()

            # Get current state from both view and model
            view_visible = [key for key, visible in self._visible_columns.items() if visible]
            model_visible = model.get_visible_columns()

            logger.debug("[ColumnSync] View visible: %s", view_visible)
            logger.debug("[ColumnSync] Model visible: %s", model_visible)

            # If they differ, update model to match view
            if view_visible != model_visible:
                logger.info("[ColumnSync] Syncing model columns to match view")
                if hasattr(model, "set_visible_columns"):
                    model.set_visible_columns(view_visible)

        except Exception as e:
            logger.error("[ColumnSync] Error syncing columns: %s", e)

    def toggle_column_visibility(self, column_key: str) -> None:
        """Toggle visibility of a column.

        Args:
            column_key: Column key to toggle
        """
        if not self._visible_columns:
            self._visible_columns = self.load_column_visibility_config()

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

    def register_shutdown_hook(self) -> None:
        """Register shutdown hook to save pending changes on app exit."""
        if self._shutdown_hook_registered:
            return

        try:
            from oncutf.core.application_context import get_app_context

            context = get_app_context()
            if hasattr(context, "register_shutdown_callback"):
                context.register_shutdown_callback(self.force_save_column_changes)
                self._shutdown_hook_registered = True
                logger.debug("[ColumnManagement] Registered shutdown hook")
        except Exception as e:
            logger.warning("[ColumnManagement] Failed to register shutdown hook: %s", e)

    def unregister_shutdown_hook(self) -> None:
        """Unregister shutdown hook."""
        if not self._shutdown_hook_registered:
            return

        try:
            from oncutf.core.application_context import get_app_context

            context = get_app_context()
            if hasattr(context, "unregister_shutdown_callback"):
                context.unregister_shutdown_callback(self.force_save_column_changes)
                self._shutdown_hook_registered = False
                logger.debug("[ColumnManagement] Unregistered shutdown hook")
        except Exception as e:
            logger.warning("[ColumnManagement] Failed to unregister shutdown hook: %s", e)

    def handle_keyboard_shortcut(self, key: int, modifiers) -> bool:
        """Handle keyboard shortcuts for column management.

        Args:
            key: Qt key code
            modifiers: Qt keyboard modifiers

        Returns:
            bool: True if shortcut was handled, False otherwise
        """
        from oncutf.core.pyqt_imports import Qt

        # Check for Ctrl+T (auto-fit) or Ctrl+Shift+T (reset)
        if key == Qt.Key_T:
            if modifiers == (Qt.ControlModifier | Qt.ShiftModifier):
                # Ctrl+Shift+T: Reset column widths to default
                self.reset_column_widths_to_defaults()
                return True
            elif modifiers == Qt.ControlModifier:
                # Ctrl+T: Auto-fit columns to content
                self.auto_fit_columns_to_content()
                return True

        return False


__all__ = ["ColumnManagementBehavior", "ColumnManageableWidget"]

