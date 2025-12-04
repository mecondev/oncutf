"""
Column Management Mixin for FileTableView.

This module provides column configuration, width management, and persistence
functionality for the file table view. It handles:
- Column configuration and delayed setup
- Column width calculation, validation, and persistence
- Column resize event handling with debounced saving
- Column alignment and visibility management
- Integration with UnifiedColumnService for column metadata

The mixin uses a sophisticated width recommendation system based on content types
and enforces minimum widths to prevent over-elision.
"""

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QHeaderView

from config import COLUMN_RESIZE_BEHAVIOR
from core.unified_column_service import get_column_service
from utils.logger_helper import get_logger
from utils.timer_manager import schedule_ui_update

logger = get_logger(__name__)


class ColumnManagementMixin:
    """
    Mixin providing column management functionality for FileTableView.

    This mixin handles all aspects of column configuration, width management,
    and persistence. It provides delayed column configuration, intelligent width
    calculation, debounced persistence, and resize event handling.

    Expected parent class methods:
        - model(): Return the table model
        - horizontalHeader(): Return the table header
        - viewport(): Return the viewport widget
        - _get_main_window(): Return main window reference
        - _update_header_visibility(): Update header visibility
        - _ensure_no_word_wrap(): Disable word wrap
        - _force_scrollbar_update(): Update scrollbar state

    Attributes:
        _pending_column_changes: Pending column width changes awaiting save
        _config_save_timer: Timer for debounced column config saves
        _configuring_columns: Flag to prevent recursive column configuration
        _programmatic_resize: Flag to prevent saving during programmatic resize
    """

    def _ensure_all_columns_proper_width(self) -> None:
        """Ensure all visible columns have proper width to minimize text elision."""
        try:
            if not self.model():
                return

            # Get visible columns from model
            visible_columns = (
                self.model().get_visible_columns()
                if hasattr(self.model(), "get_visible_columns")
                else []
            )

            for column_key in visible_columns:
                column_index = visible_columns.index(column_key) + 1  # +1 for status column

                if column_index >= self.model().columnCount():
                    continue

                # Get current width
                current_width = self.columnWidth(column_index)

                # Get recommended width
                recommended_width = self._ensure_column_proper_width(column_key, current_width)

                # Apply if different
                if recommended_width != current_width:
                    logger.debug(
                        f"[ColumnWidth] Adjusting column '{column_key}' width from {current_width}px to {recommended_width}px to reduce elision"
                    )
                    self.setColumnWidth(column_index, recommended_width)
                    self._schedule_column_save(column_key, recommended_width)

        except Exception as e:
            logger.warning(f"Error ensuring all columns proper width: {e}")

    def _configure_columns(self) -> None:
        """Configure columns with values from config.py."""

        if not self.model() or self.model().columnCount() == 0:
            return
        header = self.horizontalHeader()
        if not header:
            return

        # Prevent recursive calls during column configuration
        if hasattr(self, "_configuring_columns") and self._configuring_columns:
            return

        self._configuring_columns = True

        try:
            # Small delay to ensure model synchronization using global timer manager
            schedule_ui_update(
                self._configure_columns_delayed, delay=10, timer_id=f"column_config_{id(self)}"
            )
        except Exception as e:
            logger.error(f"[ColumnConfig] Error during column configuration: {e}")
            self._configuring_columns = False

    def _configure_columns_delayed(self) -> None:
        """Delayed column configuration to ensure model synchronization."""
        try:
            header = self.horizontalHeader()
            if not header or not self.model():
                return

            header.show()
            # Configure status column (always column 0)
            self.setColumnWidth(0, 45)
            header.setSectionResizeMode(0, QHeaderView.Fixed)

            # Get visible columns from model (this is the authoritative source)
            visible_columns = []
            if hasattr(self.model(), "get_visible_columns"):
                visible_columns = self.model().get_visible_columns()
            else:
                # Emergency fallback - load from service
                visible_columns = get_column_service().get_visible_columns()
                logger.warning(
                    f"[ColumnConfig] Model doesn't have get_visible_columns, using service: {visible_columns}"
                )

            # Configure each visible column
            for column_index, column_key in enumerate(visible_columns):
                actual_column_index = column_index + 1  # +1 because column 0 is status
                if actual_column_index < self.model().columnCount():
                    width = self._load_column_width(column_key)

                    # Apply intelligent width validation for all columns
                    width = self._ensure_column_proper_width(column_key, width)

                    header.setSectionResizeMode(actual_column_index, QHeaderView.Interactive)
                    self.setColumnWidth(actual_column_index, width)

                else:
                    logger.error(
                        f"[ColumnConfig] CRITICAL: Column {actual_column_index} ({column_key}) exceeds model columnCount {self.model().columnCount()}"
                    )
                    logger.error(
                        "[ColumnConfig] This indicates a sync issue between view and model visible columns"
                    )

            # Connect header resize signal if not already connected
            if not hasattr(self, "_header_resize_connected"):
                header.sectionResized.connect(self._on_column_resized)
                self._header_resize_connected = True

            # Force a viewport update to ensure visual refresh
            self.viewport().update()
            self.updateGeometry()

            # Update header visibility after column configuration is complete
            self._update_header_visibility()

        except Exception as e:
            logger.error(f"[ColumnConfig] Error during delayed column configuration: {e}")
        finally:
            self._configuring_columns = False

    def _ensure_column_proper_width(self, column_key: str, current_width: int) -> int:
        """Ensure column has proper width based on its content type and configuration."""
        service = get_column_service()
        column_config = service.get_column_config(column_key)
        default_width = column_config.width if column_config else 100
        min_width = column_config.min_width if column_config else 50

        # Analyze column content type to determine appropriate width
        content_type = self._analyze_column_content_type(column_key)
        recommended_width = self._get_recommended_width_for_content_type(
            content_type, default_width, min_width
        )

        # If current width is suspiciously small (likely from saved config), use recommended width
        if current_width < min_width:
            logger.debug(
                f"[ColumnWidth] Column '{column_key}' width {current_width}px is below minimum {min_width}px, using recommended {recommended_width}px"
            )
            return recommended_width

        # If current width is reasonable, use it but ensure it's not below minimum
        return max(current_width, min_width)

    def _analyze_column_content_type(self, column_key: str) -> str:
        """Analyze the content type of a column to determine appropriate width."""
        # Define content types based on column keys
        content_types = {
            # Short content (names, types, codes)
            "type": "short",
            "iso": "short",
            "rotation": "short",
            "duration": "short",
            "video_fps": "short",
            "audio_channels": "short",
            # Medium content (formats, models, sizes)
            "audio_format": "medium",
            "video_codec": "medium",
            "video_format": "medium",
            "white_balance": "medium",
            "compression": "medium",
            "device_model": "medium",
            "device_manufacturer": "medium",
            "image_size": "medium",
            "video_avg_bitrate": "medium",
            "aperture": "medium",
            "shutter_speed": "medium",
            # Long content (filenames, hashes, UMIDs)
            "filename": "long",
            "file_hash": "long",
            "target_umid": "long",
            "device_serial_no": "long",
            # Very long content (dates, file paths)
            "modified": "very_long",
            "file_size": "very_long",
        }

        return content_types.get(column_key, "medium")

    def _get_recommended_width_for_content_type(
        self, content_type: str, default_width: int, min_width: int
    ) -> int:
        """Get recommended width based on content type."""
        # Define width recommendations for different content types
        width_recommendations = {
            "short": max(80, min_width),  # Short codes, numbers
            "medium": max(120, min_width),  # Formats, models, sizes
            "long": max(200, min_width),  # Filenames, hashes, UMIDs
            "very_long": max(300, min_width),  # Dates, file paths
        }

        # Use the larger of default_width, min_width, or content_type recommendation
        recommended = width_recommendations.get(content_type, default_width)
        return max(recommended, default_width, min_width)

    def _load_column_width(self, column_key: str) -> int:
        """Load column width from main config system with fallback to defaults."""
        logger.debug(
            f"[ColumnWidth] Loading width for column '{column_key}'", extra={"dev_only": True}
        )
        try:
            # First, get the default width from UnifiedColumnService
            service = get_column_service()
            column_cfg = service.get_column_config(column_key)
            default_width = column_cfg.width if column_cfg else 100
            logger.debug(
                f"[ColumnWidth] Default width for '{column_key}': {default_width}px",
                extra={"dev_only": True},
            )

            # Try main config system first
            main_window = self._get_main_window()
            if main_window and hasattr(main_window, "window_config_manager"):
                try:
                    config_manager = main_window.window_config_manager.config_manager
                    window_config = config_manager.get_category("window")
                    column_widths = window_config.get("file_table_column_widths", {})

                    if column_key in column_widths:
                        saved_width = column_widths[column_key]
                        logger.debug(
                            f"[ColumnWidth] Found saved width for '{column_key}': {saved_width}px",
                            extra={"dev_only": True},
                        )
                        if saved_width == 100 and default_width > 120:
                            logger.debug(
                                f"[ColumnWidth] Column '{column_key}' has suspicious saved width (100px), using default {default_width}px"
                            )
                            return default_width
                        logger.debug(
                            f"[ColumnWidth] Using saved width for '{column_key}': {saved_width}px",
                            extra={"dev_only": True},
                        )
                        return saved_width
                    else:
                        logger.debug(
                            f"[ColumnWidth] No saved width found for '{column_key}' in main config",
                            extra={"dev_only": True},
                        )
                except Exception as e:
                    logger.warning(
                        f"[ColumnWidth] Error accessing main config for '{column_key}': {e}"
                    )

            # Fallback to old method
            from utils.json_config_manager import load_config

            config = load_config()
            column_widths = config.get("file_table_column_widths", {})
            if column_key in column_widths:
                saved_width = column_widths[column_key]
                logger.debug(
                    f"[ColumnWidth] Found saved width in fallback for '{column_key}': {saved_width}px"
                )
                if saved_width == 100 and default_width > 120:
                    logger.debug(
                        f"[ColumnWidth] Column '{column_key}' has suspicious saved width (100px), using default {default_width}px"
                    )
                    return default_width
                logger.debug(
                    f"[ColumnWidth] Using fallback saved width for '{column_key}': {saved_width}px"
                )
                return saved_width
            else:
                logger.debug(
                    f"[ColumnWidth] No saved width found for '{column_key}' in fallback config"
                )

            # Return default width from UnifiedColumnService
            logger.debug(f"[ColumnWidth] Using default width for '{column_key}': {default_width}px")
            return default_width

        except Exception as e:
            logger.warning(f"[ColumnWidth] Failed to load column width for {column_key}: {e}")
            # Emergency fallback to UnifiedColumnService defaults
            service = get_column_service()
            column_cfg = service.get_column_config(column_key)
            fallback_width = column_cfg.width if column_cfg else 100
            logger.debug(
                f"[ColumnWidth] Using emergency fallback width for '{column_key}': {fallback_width}px"
            )
            return fallback_width

    def _reset_column_widths_to_defaults(self) -> None:
        """Reset all column widths to their default values from config.py."""
        try:
            logger.info("Resetting column widths to defaults from config.py")

            # Clear saved column widths
            main_window = self._get_main_window()
            if main_window and hasattr(main_window, "window_config_manager"):
                try:
                    config_manager = main_window.window_config_manager.config_manager
                    window_config = config_manager.get_category("window")
                    window_config.set("file_table_column_widths", {})
                    config_manager.mark_dirty()
                except Exception as e:
                    logger.warning(f"[ColumnWidth] Error clearing main config: {e}")
                    # Continue to old format

            # Also clear from old format
            from utils.json_config_manager import load_config, save_config

            config = load_config()
            config["file_table_column_widths"] = {}
            save_config(config)

            # Reconfigure columns with defaults (only if model is available)
            if self.model() and self.model().columnCount() > 0:
                self._configure_columns()

            logger.info("Column widths reset to defaults successfully")

        except Exception as e:
            logger.error(f"Failed to reset column widths to defaults: {e}")

    def _save_column_width(self, column_key: str, width: int) -> None:
        """Save column width to main config system."""
        try:
            # Get the main window and its config manager
            main_window = self._get_main_window()
            if main_window and hasattr(main_window, "window_config_manager"):
                try:
                    config_manager = main_window.window_config_manager.config_manager
                    window_config = config_manager.get_category("window")

                    # Get current column widths
                    column_widths = window_config.get("file_table_column_widths", {})
                    column_widths[column_key] = width
                    window_config.set("file_table_column_widths", column_widths)

                    # Mark dirty for debounced save
                    config_manager.mark_dirty()
                except Exception as e:
                    logger.warning(f"[ColumnWidth] Error saving to main config: {e}")
                    # Continue to fallback method
            else:
                # Fallback to old method if main window not available
                from utils.json_config_manager import load_config, save_config

                config = load_config()
                if "file_table_column_widths" not in config:
                    config["file_table_column_widths"] = {}
                config["file_table_column_widths"][column_key] = width
                save_config(config)
        except Exception as e:
            logger.warning(f"Failed to save column width for {column_key}: {e}")

    def _schedule_column_save(self, column_key: str, width: int) -> None:
        """Schedule delayed save of column width changes."""
        if not COLUMN_RESIZE_BEHAVIOR.get("PRESERVE_USER_WIDTHS", True):
            return

        # Store the pending change
        self._pending_column_changes[column_key] = width

        # Cancel existing timer if any
        if self._config_save_timer:
            self._config_save_timer.stop()
            self._config_save_timer = None

        # Start new timer for delayed save (7 seconds)
        self._config_save_timer = QTimer()
        self._config_save_timer.setSingleShot(True)
        self._config_save_timer.timeout.connect(self._save_pending_column_changes)
        self._config_save_timer.start(7000)  # 7 seconds delay

        logger.debug(
            f"[FileTable] Scheduled delayed save for column '{column_key}' width {width}px (will save in 7 seconds)"
        )

    def _save_pending_column_changes(self) -> None:
        """Save all pending column width changes to config.json."""
        if not self._pending_column_changes:
            return

        try:
            # Try main config system first
            main_window = self._get_main_window()
            if main_window and hasattr(main_window, "window_config_manager"):
                try:
                    config_manager = main_window.window_config_manager.config_manager
                    window_config = config_manager.get_category("window")
                    column_widths = window_config.get("file_table_column_widths", {})

                    # Apply all pending changes
                    for column_key, width in self._pending_column_changes.items():
                        column_widths[column_key] = width

                    window_config.set("file_table_column_widths", column_widths)
                    config_manager.mark_dirty()

                    logger.info(
                        f"Saved {len(self._pending_column_changes)} column width changes to main config"
                    )

                    # Clear pending changes
                    self._pending_column_changes.clear()
                    return

                except Exception as e:
                    logger.warning(f"Failed to save to main config: {e}, trying fallback")

            # Fallback to old method
            from utils.json_config_manager import load_config, save_config

            config = load_config()
            if "file_table_column_widths" not in config:
                config["file_table_column_widths"] = {}

            # Apply all pending changes
            for column_key, width in self._pending_column_changes.items():
                config["file_table_column_widths"][column_key] = width

            save_config(config)

            logger.info(
                f"Saved {len(self._pending_column_changes)} column width changes to fallback config"
            )

            # Clear pending changes
            self._pending_column_changes.clear()

        except Exception as e:
            logger.error(f"Failed to save pending column changes: {e}")
        finally:
            # Clean up timer
            if self._config_save_timer:
                self._config_save_timer = None

    def _force_save_column_changes(self) -> None:
        """Force immediate save of any pending column changes (called on shutdown)."""
        if self._pending_column_changes:
            logger.debug("Force saving pending column changes on shutdown")
            self._save_pending_column_changes()

        # Cancel any pending timer
        if self._config_save_timer:
            self._config_save_timer.stop()
            self._config_save_timer = None

    def _on_column_resized(self, logical_index: int, old_size: int, new_size: int) -> None:
        """Handle column resize events and save user preferences."""
        if self._programmatic_resize:
            return  # Skip saving during programmatic resize

        # Get column key from logical index
        column_key = self._get_column_key_from_index(logical_index)
        if not column_key:
            return

        # Enforce minimum width immediately to prevent visual flickering
        service = get_column_service()
        cfg = service.get_column_config(column_key)
        min_width = cfg.min_width if cfg else 30

        if new_size < min_width:
            # Set the column back to minimum width immediately
            self._programmatic_resize = True  # Prevent recursion
            self.setColumnWidth(logical_index, min_width)
            self._programmatic_resize = False
            new_size = min_width  # Update the size we're working with
            logger.debug(f"[FileTable] Column '{column_key}' enforced minimum width: {min_width}px")

        # Schedule delayed save of column width
        self._schedule_column_save(column_key, new_size)

        # Ensure word wrap is disabled when user resizes columns
        self._ensure_no_word_wrap()

        # Update scrollbar visibility immediately and force viewport update
        self._force_scrollbar_update()

        # Force repaint and layout update so elidedText is recalculated
        if self.model():
            self.model().layoutChanged.emit()
        self.viewport().update()

        # Update header visibility after column resize
        self._update_header_visibility()

        logger.debug(f"[FileTable] Column '{column_key}' resized from {old_size}px to {new_size}px")

    def _get_column_key_from_index(self, logical_index: int) -> str | None:
        """Get column key from logical index."""
        if logical_index == 0:
            return "status"

        # Get visible columns from model
        visible_columns = []
        if hasattr(self.model(), "get_visible_columns"):
            visible_columns = self.model().get_visible_columns()
        else:
            # Fallback to service
            visible_columns = get_column_service().get_visible_columns()

        # Convert logical index to column key
        column_index = logical_index - 1  # -1 for status column
        if 0 <= column_index < len(visible_columns):
            return visible_columns[column_index]

        logger.warning(f"Invalid logical_index {logical_index} for column count {len(visible_columns)}")
        return None
