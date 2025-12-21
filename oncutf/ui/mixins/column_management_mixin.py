"""
Module: column_management_mixin.py

Author: Michael Economou
Date: 2025-05-21

Column management mixin for FileTableView.

Provides comprehensive column management functionality including:
- Column configuration and width management
- Column visibility toggling (add/remove columns)
- Keyboard shortcuts for auto-fit (Ctrl+T) and reset (Ctrl+Shift+T)
- Config persistence (load/save column widths and visibility)
- Header visibility management
- Intelligent width validation and content-type detection

Extracted from FileTableView to improve maintainability and reduce complexity.
This follows the same pattern as SelectionMixin and DragDropMixin.
"""

from oncutf.core.pyqt_imports import QHeaderView, Qt
from oncutf.utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class ColumnManagementMixin:
    """
    Provides column management functionality for table views.

    This mixin handles all aspects of column management including:
    - Width configuration and persistence
    - Visibility management (show/hide columns)
    - Auto-fit and reset shortcuts
    - Intelligent width validation
    - Header state management

    Expected to be mixed with QTableView or its subclasses.
    Requires:
    - self.horizontalHeader() - QHeaderView instance
    - self.model() - QAbstractItemModel instance
    - self.setColumnWidth(index, width) - method to set column width
    - self.columnWidth(index) - method to get column width
    - self.resizeColumnToContents(index) - method to auto-resize
    """

    # =====================================
    # Column Configuration & Setup
    # =====================================

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
                        "[ColumnWidth] Adjusting column '%s' width from %dpx to %dpx to reduce elision",
                        column_key,
                        current_width,
                        recommended_width,
                    )
                    self.setColumnWidth(column_index, recommended_width)
                    self._schedule_column_save(column_key, recommended_width)

        except Exception as e:
            logger.warning("Error ensuring all columns proper width: %s", e)

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
            from oncutf.utils.timer_manager import schedule_ui_update

            schedule_ui_update(
                self._configure_columns_delayed, delay=10, timer_id=f"column_config_{id(self)}"
            )
        except Exception as e:
            logger.error("[ColumnConfig] Error during column configuration: %s", e)
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
            header.setSectionResizeMode(0, header.Fixed)

            # Get visible columns from model (this is the authoritative source)
            visible_columns = []
            if hasattr(self.model(), "get_visible_columns"):
                visible_columns = self.model().get_visible_columns()
            else:
                # Emergency fallback - load from service
                from oncutf.core.unified_column_service import get_column_service

                visible_columns = get_column_service().get_visible_columns()
                logger.warning(
                    "[ColumnConfig] Model doesn't have get_visible_columns, using service: %s",
                    visible_columns,
                )

            # Configure each visible column
            for column_index, column_key in enumerate(visible_columns):
                actual_column_index = column_index + 1  # +1 because column 0 is status
                if actual_column_index < self.model().columnCount():
                    width = self._load_column_width(column_key)

                    # Apply intelligent width validation for all columns
                    width = self._ensure_column_proper_width(column_key, width)

                    # Check if column is resizable (default: True)
                    from oncutf.config import FILE_TABLE_COLUMN_CONFIG

                    column_config = FILE_TABLE_COLUMN_CONFIG.get(column_key, {})
                    is_resizable = column_config.get("resizable", True)

                    if is_resizable:
                        header.setSectionResizeMode(actual_column_index, header.Interactive)
                    else:
                        header.setSectionResizeMode(actual_column_index, header.Fixed)

                    self.setColumnWidth(actual_column_index, width)

                else:
                    logger.error(
                        "[ColumnConfig] CRITICAL: Column %d (%s) exceeds model columnCount %d",
                        actual_column_index,
                        column_key,
                        self.model().columnCount(),
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
            logger.error("[ColumnConfig] Error during delayed column configuration: %s", e)
        finally:
            self._configuring_columns = False

    def _ensure_column_proper_width(self, column_key: str, current_width: int) -> int:
        """Ensure column has proper width based on its content type and configuration."""
        from oncutf.core.unified_column_service import get_column_service

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
                "[ColumnWidth] Column '%s' width %dpx is below minimum %dpx, using recommended %dpx",
                column_key,
                current_width,
                min_width,
                recommended_width,
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

    def _update_header_visibility(self) -> None:
        """Update header visibility based on whether there are files in the model."""
        if not self.model():
            logger.debug("[FileTableView] No model - header hidden", extra={"dev_only": True})
            return

        header = self.horizontalHeader()
        if not header:
            logger.debug(
                "[FileTableView] No header - cannot update visibility", extra={"dev_only": True}
            )
            return

        # Hide header when table is empty, show when it has content
        is_empty = self.is_empty()
        header.setVisible(not is_empty)

        logger.debug(
            "[FileTableView] Header visibility: %s (empty: %s)",
            "hidden" if is_empty else "visible",
            is_empty,
            extra={"dev_only": True},
        )

    def _ensure_header_visibility(self) -> None:
        """Ensure header visibility is correct after column configuration."""
        self._update_header_visibility()

    def _set_column_alignment(self, column_index: int, alignment: str) -> None:
        """Set text alignment for a specific column."""
        if not self.model():
            return

        # Map alignment strings to Qt constants
        alignment_map = {
            "left": Qt.AlignLeft | Qt.AlignVCenter,
            "right": Qt.AlignRight | Qt.AlignVCenter,
            "center": Qt.AlignCenter,
        }

        qt_alignment = alignment_map.get(alignment, Qt.AlignLeft | Qt.AlignVCenter)

        # Store alignment for use in delegates or model
        if not hasattr(self, "_column_alignments"):
            self._column_alignments = {}
        self._column_alignments[column_index] = qt_alignment

    # =====================================
    # Width Management & Persistence
    # =====================================

    def _load_column_width(self, column_key: str) -> int:
        """Load column width from main config system with fallback to defaults."""
        logger.debug(
            "[ColumnWidth] Loading width for column '%s'",
            column_key,
            extra={"dev_only": True},
        )
        try:
            # First, get the default width from UnifiedColumnService
            from oncutf.core.unified_column_service import get_column_service

            service = get_column_service()
            column_cfg = service.get_column_config(column_key)
            default_width = column_cfg.width if column_cfg else 100
            logger.debug(
                "[ColumnWidth] Default width for '%s': %dpx",
                column_key,
                default_width,
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
                            "[ColumnWidth] Found saved width for '%s': %dpx",
                            column_key,
                            saved_width,
                            extra={"dev_only": True},
                        )
                        if saved_width == 100 and default_width > 120:
                            logger.debug(
                                "[ColumnWidth] Column '%s' has suspicious saved width (100px), using default %dpx",
                                column_key,
                                default_width,
                            )
                            return default_width
                        logger.debug(
                            "[ColumnWidth] Using saved width for '%s': %dpx",
                            column_key,
                            saved_width,
                            extra={"dev_only": True},
                        )
                        return saved_width
                    else:
                        logger.debug(
                            "[ColumnWidth] No saved width found for '%s' in main config",
                            column_key,
                            extra={"dev_only": True},
                        )
                except Exception as e:
                    logger.warning(
                        "[ColumnWidth] Error accessing main config for '%s': %s",
                        column_key,
                        e,
                    )

            # Fallback to old method
            from oncutf.utils.json_config_manager import load_config

            config = load_config()
            column_widths = config.get("file_table_column_widths", {})
            if column_key in column_widths:
                saved_width = column_widths[column_key]
                logger.debug(
                    "[ColumnWidth] Found saved width in fallback for '%s': %dpx",
                    column_key,
                    saved_width,
                )
                if saved_width == 100 and default_width > 120:
                    logger.debug(
                        "[ColumnWidth] Column '%s' has suspicious saved width (100px), using default %dpx",
                        column_key,
                        default_width,
                    )
                    return default_width
                logger.debug(
                    "[ColumnWidth] Using fallback saved width for '%s': %dpx",
                    column_key,
                    saved_width,
                )
                return saved_width
            else:
                logger.debug(
                    "[ColumnWidth] No saved width found for '%s' in fallback config",
                    column_key,
                )

            # Return default width from UnifiedColumnService
            logger.debug(
                "[ColumnWidth] Using default width for '%s': %dpx",
                column_key,
                default_width,
            )
            return default_width

        except Exception as e:
            logger.warning("[ColumnWidth] Failed to load column width for %s: %s", column_key, e)
            # Emergency fallback to UnifiedColumnService defaults
            from oncutf.core.unified_column_service import get_column_service

            service = get_column_service()
            column_cfg = service.get_column_config(column_key)
            fallback_width = column_cfg.width if column_cfg else 100
            logger.debug(
                "[ColumnWidth] Using emergency fallback width for '%s': %dpx",
                column_key,
                fallback_width,
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
                    logger.warning("[ColumnWidth] Error clearing main config: %s", e)
                    # Continue to old format

            # Also clear from old format
            from oncutf.utils.json_config_manager import load_config, save_config

            config = load_config()
            config["file_table_column_widths"] = {}
            save_config(config)

            # Reconfigure columns with defaults (only if model is available)
            if self.model() and self.model().columnCount() > 0:
                self._configure_columns()

            logger.info("Column widths reset to defaults successfully")

        except Exception as e:
            logger.error("Failed to reset column widths to defaults: %s", e)

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
                    logger.warning("[ColumnWidth] Error saving to main config: %s", e)
                    # Continue to fallback method
            else:
                # Fallback to old method if main window not available
                from oncutf.utils.json_config_manager import load_config, save_config

                config = load_config()
                if "file_table_column_widths" not in config:
                    config["file_table_column_widths"] = {}
                config["file_table_column_widths"][column_key] = width
                save_config(config)
        except Exception as e:
            logger.warning("Failed to save column width for %s: %s", column_key, e)

    def _schedule_column_save(self, column_key: str, width: int) -> None:
        """Schedule delayed save of column width changes."""
        from oncutf.config import COLUMN_RESIZE_BEHAVIOR
        from oncutf.core.pyqt_imports import QTimer

        if not COLUMN_RESIZE_BEHAVIOR.get("PRESERVE_USER_WIDTHS", True):
            return

        # Store the pending change
        if not hasattr(self, "_pending_column_changes"):
            self._pending_column_changes = {}
        self._pending_column_changes[column_key] = width

        # Cancel existing timer if any
        if hasattr(self, "_config_save_timer") and self._config_save_timer:
            self._config_save_timer.stop()
            self._config_save_timer = None

        # Start new timer for delayed save (7 seconds)
        self._config_save_timer = QTimer()
        self._config_save_timer.setSingleShot(True)
        self._config_save_timer.timeout.connect(self._save_pending_column_changes)
        self._config_save_timer.start(7000)  # 7 seconds delay

        logger.debug(
            "[FileTable] Scheduled delayed save for column '%s' width %dpx (will save in 7 seconds)",
            column_key,
            width,
        )

    def _save_pending_column_changes(self) -> None:
        """Save all pending column width changes to config.json."""
        if not hasattr(self, "_pending_column_changes") or not self._pending_column_changes:
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
                        "Saved %d column width changes to main config",
                        len(self._pending_column_changes),
                    )

                    # Clear pending changes
                    self._pending_column_changes.clear()
                    return

                except Exception as e:
                    logger.warning("Failed to save to main config: %s, trying fallback", e)

            # Fallback to old method
            from oncutf.utils.json_config_manager import load_config, save_config

            config = load_config()
            if "file_table_column_widths" not in config:
                config["file_table_column_widths"] = {}

            # Apply all pending changes
            for column_key, width in self._pending_column_changes.items():
                config["file_table_column_widths"][column_key] = width

            save_config(config)

            logger.info(
                "Saved %d column width changes to fallback config",
                len(self._pending_column_changes),
            )

            # Clear pending changes
            self._pending_column_changes.clear()

        except Exception as e:
            logger.error("Failed to save pending column changes: %s", e)
        finally:
            # Clean up timer
            if hasattr(self, "_config_save_timer"):
                self._config_save_timer = None

    def _force_save_column_changes(self) -> None:
        """Force immediate save of any pending column changes (called on shutdown)."""
        if hasattr(self, "_pending_column_changes") and self._pending_column_changes:
            logger.debug("Force saving pending column changes on shutdown")
            self._save_pending_column_changes()

        # Cancel any pending timer
        if hasattr(self, "_config_save_timer") and self._config_save_timer:
            self._config_save_timer.stop()
            self._config_save_timer = None

    def _on_column_resized(self, logical_index: int, old_size: int, new_size: int) -> None:
        """Handle column resize events and save user preferences."""
        if hasattr(self, "_programmatic_resize") and self._programmatic_resize:
            return  # Skip saving during programmatic resize

        # Get column key from logical index
        column_key = self._get_column_key_from_index(logical_index)
        if not column_key:
            return

        # Enforce minimum width immediately to prevent visual flickering
        from oncutf.core.unified_column_service import get_column_service

        service = get_column_service()
        cfg = service.get_column_config(column_key)
        min_width = cfg.min_width if cfg else 30

        if new_size < min_width:
            # Set the column back to minimum width immediately
            if not hasattr(self, "_programmatic_resize"):
                self._programmatic_resize = False
            self._programmatic_resize = True  # Prevent recursion
            self.setColumnWidth(logical_index, min_width)
            self._programmatic_resize = False
            new_size = min_width  # Update the size we're working with
            logger.debug(
                "[FileTable] Column '%s' enforced minimum width: %dpx",
                column_key,
                min_width,
            )

        # Schedule delayed save of column width
        self._schedule_column_save(column_key, new_size)

        # Ensure word wrap is disabled when user resizes columns
        if hasattr(self, "_ensure_no_word_wrap"):
            self._ensure_no_word_wrap()

        # Update scrollbar visibility immediately and force viewport update
        if hasattr(self, "_force_scrollbar_update"):
            self._force_scrollbar_update()

        # Force repaint and layout update so elidedText is recalculated
        if self.model():
            self.model().layoutChanged.emit()
        self.viewport().update()

        # Update header visibility after column resize
        self._update_header_visibility()

        logger.debug(
            "[FileTable] Column '%s' resized from %dpx to %dpx",
            column_key,
            old_size,
            new_size,
        )

    def _on_column_moved(
        self, logical_index: int, old_visual_index: int, new_visual_index: int
    ) -> None:
        """Handle column reordering and save order to config."""
        if logical_index == 0:  # Don't allow moving status column
            # Revert the move by moving it back to position 0
            header = self.horizontalHeader()
            if header and new_visual_index != 0:
                header.moveSection(new_visual_index, 0)
            return

        # Save new column order to config
        try:
            # config = load_config()
            # TODO: Implement column order saving
            logger.debug(
                "Column moved from position %d to %d",
                old_visual_index,
                new_visual_index,
            )
        except Exception as e:
            logger.warning("Failed to save column order: %s", e)

        # Update header visibility after column move
        self._update_header_visibility()

    def _get_column_key_from_index(self, logical_index: int) -> str:
        """Get column key from logical index."""
        if logical_index == 0:
            return "status"

        # Get visible columns from model
        visible_columns = []
        if hasattr(self.model(), "get_visible_columns"):
            visible_columns = self.model().get_visible_columns()
        else:
            visible_columns = ["filename", "file_size", "type", "modified"]

        # Convert logical index to column key
        column_index = logical_index - 1  # -1 because column 0 is status
        if 0 <= column_index < len(visible_columns):
            return visible_columns[column_index]

        return ""

    # =====================================
    # Column Visibility Management
    # =====================================

    def _load_column_visibility_config(self) -> dict:
        """Load column visibility configuration from config.json."""
        try:
            # Try main config system first
            main_window = self._get_main_window()
            if main_window and hasattr(main_window, "window_config_manager"):
                config_manager = main_window.window_config_manager.config_manager
                window_config = config_manager.get_category("window")
                saved_visibility = window_config.get("file_table_columns", {})

                if saved_visibility:
                    logger.debug(
                        "[ColumnVisibility] Loaded from main config: %s",
                        saved_visibility,
                    )
                    # Ensure we have all columns from config, not just saved ones
                    from oncutf.core.unified_column_service import get_column_service

                    service = get_column_service()

                    complete_visibility = {}
                    for key, cfg in service.get_all_columns().items():
                        # Use saved value if available, otherwise use default
                        complete_visibility[key] = saved_visibility.get(key, cfg.default_visible)
                    logger.debug(
                        "[ColumnVisibility] Complete visibility state: %s",
                        complete_visibility,
                    )
                    return complete_visibility

            # Fallback to old method
            from oncutf.utils.json_config_manager import load_config

            config = load_config()
            saved_visibility = config.get("file_table_columns", {})

            if saved_visibility:
                logger.debug(
                    "[ColumnVisibility] Loaded from fallback config: %s",
                    saved_visibility,
                )
                # Ensure we have all columns from config, not just saved ones
                from oncutf.core.unified_column_service import get_column_service

                service = get_column_service()

                complete_visibility = {}
                for key, cfg in service.get_all_columns().items():
                    # Use saved value if available, otherwise use default
                    complete_visibility[key] = saved_visibility.get(key, cfg.default_visible)
                logger.debug(
                    "[ColumnVisibility] Complete visibility state: %s",
                    complete_visibility,
                )
                return complete_visibility

        except Exception as e:
            logger.warning("[ColumnVisibility] Error loading config: %s", e)

        # Return default configuration
        from oncutf.core.unified_column_service import get_column_service

        service = get_column_service()

        default_visibility = {
            key: cfg.default_visible for key, cfg in service.get_all_columns().items()
        }
        return default_visibility

    def _save_column_visibility_config(self) -> None:
        """Save column visibility configuration to main config system."""
        try:
            # Get the main window and its config manager
            main_window = self._get_main_window()
            if main_window and hasattr(main_window, "window_config_manager"):
                config_manager = main_window.window_config_manager.config_manager
                window_config = config_manager.get_category("window")

                # Save current visibility state
                if hasattr(self, "_visible_columns"):
                    window_config.set("file_table_columns", self._visible_columns)
                    logger.debug(
                        "[ColumnVisibility] Saved to main config: %s",
                        self._visible_columns,
                    )

                    # Mark dirty for debounced save
                    config_manager.mark_dirty()
            else:
                # Fallback to old method
                from oncutf.utils.json_config_manager import load_config, save_config

                config = load_config()
                if hasattr(self, "_visible_columns"):
                    config["file_table_columns"] = self._visible_columns
                    save_config(config)
                    logger.debug(
                        "[ColumnVisibility] Saved to fallback config: %s",
                        self._visible_columns,
                    )
        except Exception as e:
            logger.warning("Failed to save column visibility config: %s", e)

    def _sync_view_model_columns(self) -> None:
        """Ensure view and model have synchronized column visibility."""
        model = self.model()
        if not model or not hasattr(model, "get_visible_columns"):
            logger.debug("[ColumnSync] No model or model doesn't support get_visible_columns")
            return

        try:
            # Ensure we have complete visibility state
            if not hasattr(self, "_visible_columns") or not self._visible_columns:
                logger.warning("[ColumnSync] _visible_columns not initialized, reloading")
                self._visible_columns = self._load_column_visibility_config()

            # Get current state from both view and model
            view_visible = [key for key, visible in self._visible_columns.items() if visible]
            model_visible = model.get_visible_columns()

            logger.debug("[ColumnSync] View visible: %s", view_visible)
            logger.debug("[ColumnSync] Model visible: %s", model_visible)

            # Sort both lists to ensure consistent comparison
            view_visible_sorted = sorted(view_visible)
            model_visible_sorted = sorted(model_visible)

            # If they don't match, update model to match view (view is authoritative)
            if view_visible_sorted != model_visible_sorted:
                logger.warning("[ColumnSync] Columns out of sync! Updating model to match view")
                logger.debug("[ColumnSync] View wants: %s", view_visible_sorted)
                logger.debug("[ColumnSync] Model has: %s", model_visible_sorted)

                if hasattr(model, "update_visible_columns"):
                    model.update_visible_columns(view_visible)

                    # Verify the update worked
                    updated_model_visible = model.get_visible_columns()
                    logger.debug(
                        "[ColumnSync] Model updated to: %s",
                        sorted(updated_model_visible),
                    )

                    if sorted(updated_model_visible) != view_visible_sorted:
                        logger.error("[ColumnSync] CRITICAL: Model update failed!")
                        logger.error("[ColumnSync] Expected: %s", view_visible_sorted)
                        logger.error(
                            "[ColumnSync] Got: %s",
                            sorted(updated_model_visible),
                        )
                else:
                    logger.error("[ColumnSync] Model doesn't support update_visible_columns")
            else:
                logger.debug("[ColumnSync] View and model are already synchronized")

        except Exception as e:
            logger.exception("[ColumnSync] Error syncing columns: %s", e)

    def _toggle_column_visibility(self, column_key: str) -> None:
        """Toggle visibility of a specific column and refresh the table."""

        from oncutf.core.unified_column_service import get_column_service

        all_columns = get_column_service().get_all_columns()
        if column_key not in all_columns:
            logger.warning("Unknown column key: %s", column_key)
            return

        column_config = all_columns[column_key]
        if not getattr(column_config, "removable", True):
            logger.warning("Cannot toggle non-removable column: %s", column_key)
            return  # Can't toggle non-removable columns

        # Ensure we have complete visibility state
        if not hasattr(self, "_visible_columns") or not self._visible_columns:
            logger.warning("[ColumnToggle] _visible_columns not initialized, reloading config")
            self._visible_columns = self._load_column_visibility_config()

        # Toggle visibility
        current_visibility = self._visible_columns.get(column_key, column_config.default_visible)
        new_visibility = not current_visibility
        self._visible_columns[column_key] = new_visibility

        logger.info(
            "Toggled column '%s' visibility to %s",
            column_key,
            new_visibility,
        )
        logger.debug(
            "[ColumnToggle] Current visibility state: %s",
            self._visible_columns,
        )

        # Verify we have all columns in visibility state
        from oncutf.core.unified_column_service import get_column_service

        for key, cfg in get_column_service().get_all_columns().items():
            if key not in self._visible_columns:
                self._visible_columns[key] = cfg.default_visible
                logger.debug(
                    "[ColumnToggle] Added missing column '%s' with default visibility %s",
                    key,
                    cfg.default_visible,
                )

        # Save configuration immediately
        self._save_column_visibility_config()

        # Ensure view and model are synchronized before updating
        self._sync_view_model_columns()

        # Update table display (clears selection)
        self._update_table_columns()

        logger.info("Column '%s' visibility toggle completed", column_key)

        # Debug: Show current visible columns
        visible_cols = [key for key, visible in self._visible_columns.items() if visible]
        logger.debug("[ColumnToggle] Currently visible columns: %s", visible_cols)

    def add_column(self, column_key: str) -> None:
        """Add a column to the table (make it visible)."""

        from oncutf.core.unified_column_service import get_column_service

        if column_key not in get_column_service().get_all_columns():
            logger.warning("Cannot add unknown column: %s", column_key)
            return

        # Ensure we have complete visibility state
        if not hasattr(self, "_visible_columns") or not self._visible_columns:
            self._visible_columns = self._load_column_visibility_config()

        # Make column visible
        if not self._visible_columns.get(column_key, False):
            self._visible_columns[column_key] = True
            logger.info("Added column '%s' to table", column_key)

            # Save and update
            self._save_column_visibility_config()
            self._sync_view_model_columns()
            self._update_table_columns()

            # Force configure columns after model update to ensure new column gets proper width
            from oncutf.utils.timer_manager import schedule_ui_update

            schedule_ui_update(
                self._configure_columns_delayed,
                delay=50,
                timer_id=f"configure_new_column_{column_key}",
            )

            # Ensure proper width for the newly added column
            schedule_ui_update(
                self._ensure_new_column_proper_width,
                delay=100,
                timer_id=f"ensure_column_width_{column_key}",
            )

            # Debug
            visible_cols = [key for key, visible in self._visible_columns.items() if visible]
            logger.debug("[AddColumn] Currently visible columns: %s", visible_cols)
        else:
            logger.debug("Column '%s' is already visible", column_key)

    def _ensure_new_column_proper_width(self) -> None:
        """Ensure newly added column has proper width."""
        try:
            if not self.model():
                return

            # Get visible columns from model
            visible_columns = (
                self.model().get_visible_columns()
                if hasattr(self.model(), "get_visible_columns")
                else []
            )

            # Check all visible columns for proper width
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
                        "[ColumnWidth] Adjusting column '%s' width from %dpx to %dpx",
                        column_key,
                        current_width,
                        recommended_width,
                    )
                    self.setColumnWidth(column_index, recommended_width)
                    self._schedule_column_save(column_key, recommended_width)

        except Exception as e:
            logger.warning("Error ensuring new column proper width: %s", e)

    def remove_column(self, column_key: str) -> None:
        """Remove a column from the table (make it invisible)."""

        from oncutf.core.unified_column_service import get_column_service

        all_columns = get_column_service().get_all_columns()
        if column_key not in all_columns:
            logger.warning("Cannot remove unknown column: %s", column_key)
            return

        column_config = all_columns[column_key]
        if not getattr(column_config, "removable", True):
            logger.warning("Cannot remove non-removable column: %s", column_key)
            return

        # Ensure we have complete visibility state
        if not hasattr(self, "_visible_columns") or not self._visible_columns:
            self._visible_columns = self._load_column_visibility_config()

        # Make column invisible
        if self._visible_columns.get(column_key, False):
            self._visible_columns[column_key] = False
            logger.info("Removed column '%s' from table", column_key)

            # Save and update
            self._save_column_visibility_config()
            self._sync_view_model_columns()
            self._update_table_columns()

            # Debug
            visible_cols = [key for key, visible in self._visible_columns.items() if visible]
            logger.debug("[RemoveColumn] Currently visible columns: %s", visible_cols)
        else:
            logger.debug("Column '%s' is already invisible", column_key)

    def get_visible_columns_list(self) -> list:
        """Get list of currently visible column keys."""
        if not hasattr(self, "_visible_columns") or not self._visible_columns:
            self._visible_columns = self._load_column_visibility_config()
        return [key for key, visible in self._visible_columns.items() if visible]

    def debug_column_state(self) -> None:
        """Debug method to print current column state."""
        logger.debug("[ColumnDebug] === FileTableView Column State ===")
        if hasattr(self, "_visible_columns"):
            logger.debug("[ColumnDebug] _visible_columns: %s", self._visible_columns)
        visible_cols = self.get_visible_columns_list()
        logger.debug("[ColumnDebug] Visible columns list: %s", visible_cols)

        model = self.model()
        if model and hasattr(model, "get_visible_columns"):
            model_visible = model.get_visible_columns()
            logger.debug("[ColumnDebug] Model visible columns: %s", model_visible)
            logger.debug("[ColumnDebug] Model column count: %d", model.columnCount())

            if hasattr(model, "debug_column_state"):
                model.debug_column_state()
        else:
            logger.debug("[ColumnDebug] No model or model doesn't support get_visible_columns")

        logger.debug("[ColumnDebug] =========================================")

    def _clear_selection_for_column_update(self, force_emit_signal: bool = False) -> None:
        """Clear selection during column updates."""
        self.clearSelection()

        if hasattr(self, "_get_selection_store"):
            selection_store = self._get_selection_store()
            if selection_store and hasattr(self, "_legacy_selection_mode") and not self._legacy_selection_mode:
                selection_store.set_selected_rows(set(), emit_signal=force_emit_signal)

    def _handle_column_update_lifecycle(self, update_function: callable) -> None:
        """Handle the complete lifecycle of a column update operation."""
        try:
            if not hasattr(self, "_updating_columns"):
                self._updating_columns = False
            self._updating_columns = True
            self._clear_selection_for_column_update(force_emit_signal=False)
            update_function()
        except Exception as e:
            logger.exception("[ColumnUpdate] Error during column update: %s", e)
            raise
        finally:
            self._updating_columns = False
            self._clear_selection_for_column_update(force_emit_signal=True)

    def _update_table_columns(self) -> None:
        """Update table columns based on visibility configuration."""
        model = self.model()
        if not model:
            return

        def perform_column_update():
            visible_columns = self.get_visible_columns_list()

            if hasattr(model, "update_visible_columns"):
                model.update_visible_columns(visible_columns)

            self._configure_columns()
            self._update_header_visibility()
            if hasattr(self, "_force_scrollbar_update"):
                self._force_scrollbar_update()

        self._handle_column_update_lifecycle(perform_column_update)

    # =====================================
    # Column Shortcuts & Utilities
    # =====================================

    def _reset_columns_to_default(self) -> None:
        """Reset all column widths to their default values (Ctrl+Shift+T).

        Restores all columns to config defaults with Interactive resize mode.
        """
        try:
            from oncutf.core.unified_column_service import get_column_service

            visible_columns = []
            if hasattr(self.model(), "get_visible_columns"):
                visible_columns = self.model().get_visible_columns()
            else:
                visible_columns = ["filename", "file_size", "type", "modified"]

            header = self.horizontalHeader()
            if not header:
                return

            for i, column_key in enumerate(visible_columns):
                column_index = i + 1  # +1 because column 0 is status column
                cfg = get_column_service().get_column_config(column_key)
                default_width = cfg.width if cfg else 100

                # Reset to Interactive mode for all columns
                header.setSectionResizeMode(column_index, QHeaderView.Interactive)

                # Apply intelligent width validation for all columns
                final_width = self._ensure_column_proper_width(column_key, default_width)

                self.setColumnWidth(column_index, final_width)
                self._schedule_column_save(column_key, final_width)

            self._update_header_visibility()

        except Exception as e:
            logger.error("Error resetting columns to default: %s", e)

    def _auto_fit_columns_to_content(self) -> None:
        """Auto-fit all column widths to their content (Ctrl+T).

        Special handling:
        - Filename column: stretches to fill available space (last stretch)
        - Other columns: resize to fit content with min/max constraints
        """
        try:
            from oncutf.config import GLOBAL_MIN_COLUMN_WIDTH

            if not self.model() or self.model().rowCount() == 0:
                return

            visible_columns = []
            if hasattr(self.model(), "get_visible_columns"):
                visible_columns = self.model().get_visible_columns()
            else:
                visible_columns = ["filename", "file_size", "type", "modified"]

            header = self.horizontalHeader()
            if not header:
                return

            for i, column_key in enumerate(visible_columns):
                column_index = i + 1  # +1 because column 0 is status column
                from oncutf.core.unified_column_service import get_column_service

                cfg = get_column_service().get_column_config(column_key)

                # Special handling for filename column: set to stretch
                if column_key == "filename":
                    header.setSectionResizeMode(column_index, QHeaderView.Stretch)
                    continue

                # For other columns: resize to contents with constraints
                self.resizeColumnToContents(column_index)

                # Apply minimum width constraint
                min_width = max(
                    (cfg.min_width if cfg else GLOBAL_MIN_COLUMN_WIDTH), GLOBAL_MIN_COLUMN_WIDTH
                )
                current_width = self.columnWidth(column_index)
                final_width = max(current_width, min_width)

                # Apply intelligent width validation for all columns
                final_width = self._ensure_column_proper_width(column_key, final_width)

                if final_width != current_width:
                    self.setColumnWidth(column_index, final_width)

                self._schedule_column_save(column_key, final_width)

            self._update_header_visibility()

        except Exception as e:
            logger.error("Error auto-fitting columns to content: %s", e)

    def refresh_columns_after_model_change(self) -> None:
        """Refresh columns after model changes."""
        self._configure_columns()
        if hasattr(self, "update_placeholder_visibility"):
            self.update_placeholder_visibility()
        self._update_header_visibility()
        self.viewport().update()

        # Ensure word wrap is disabled after column changes
        if hasattr(self, "_ensure_no_word_wrap"):
            self._ensure_no_word_wrap()

    def _check_and_fix_column_widths(self) -> None:
        """Check if column widths need to be reset due to incorrect saved values."""
        try:
            # Get current saved widths
            main_window = self._get_main_window()
            saved_widths = {}

            if main_window and hasattr(main_window, "window_config_manager"):
                try:
                    config_manager = main_window.window_config_manager.config_manager
                    window_config = config_manager.get_category("window")
                    saved_widths = window_config.get("file_table_column_widths", {})
                except Exception:
                    # Try fallback method
                    from oncutf.utils.json_config_manager import load_config

                    config = load_config()
                    saved_widths = config.get("file_table_column_widths", {})

            # Check if most columns are set to 100px (suspicious)
            suspicious_count = 0
            total_count = 0

            from oncutf.core.unified_column_service import get_column_service

            for column_key, column_config in get_column_service().get_all_columns().items():
                if getattr(column_config, "default_visible", False):
                    total_count += 1
                    default_width = getattr(column_config, "width", 100)
                    saved_width = saved_widths.get(column_key, default_width)

                    if saved_width == 100 and default_width > 120:
                        suspicious_count += 1

            # If most visible columns have suspicious widths, reset them
            if total_count > 0 and suspicious_count >= (total_count * 0.5):
                self._reset_column_widths_to_defaults()
                if self.model() and self.model().columnCount() > 0:
                    from oncutf.utils.timer_manager import schedule_ui_update

                    schedule_ui_update(self._configure_columns, delay=10)

        except Exception as e:
            logger.error("Failed to check column widths: %s", e)
