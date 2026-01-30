"""Module: metadata_signal_handler.py.

Author: Michael Economou
Date: 2026-01-01

Handler for metadata tree widget signals in MainWindow.
Handles value edits, resets, copy operations, and widget refresh.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from oncutf.ui.main_window import MainWindow

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class MetadataSignalHandler:
    """Handles signals from metadata tree widgets."""

    def __init__(self, main_window: MainWindow) -> None:
        """Initialize handler with MainWindow reference.

        Args:
            main_window: Reference to the main window instance

        """
        self.main_window = main_window
        logger.debug("[MetadataSignalHandler] Initialized")

    def on_metadata_value_edited(self, key_path: str, old_value: str, new_value: str) -> None:
        """Handle metadata value edited signal from metadata tree view.

        Args:
            key_path: The metadata key path (e.g. "EXIF/Rotation")
            old_value: The previous value
            new_value: The new value

        """
        logger.info(
            "[MetadataEdit] Value changed: %s = '%s' -> '%s'",
            key_path,
            old_value,
            new_value,
        )

        # Use specialized metadata status method if status manager is available
        if hasattr(self.main_window, "status_manager") and self.main_window.status_manager:
            self.main_window.status_manager.set_metadata_status(
                f"Modified {key_path}: {old_value} -> {new_value}",
                operation_type="success",
                auto_reset=True,
            )

        # The file icon status update is already handled by MetadataTreeView._update_file_icon_status()
        # Just log the change for debugging
        logger.debug("[MetadataEdit] Modified metadata field: %s", key_path)

    def on_metadata_value_reset(self, key_path: str) -> None:
        """Handle metadata value reset signal from metadata tree view.

        Args:
            key_path: The metadata key path that was reset

        """
        logger.info("[MetadataEdit] Value reset: %s", key_path)

        # Use specialized metadata status method if status manager is available
        if hasattr(self.main_window, "status_manager") and self.main_window.status_manager:
            self.main_window.status_manager.set_metadata_status(
                f"Reset {key_path} to original value",
                operation_type="success",
                auto_reset=True,
            )

        # The file icon status update is already handled by MetadataTreeView._update_file_icon_status()
        logger.debug("[MetadataEdit] Reset metadata field: %s", key_path)

    def on_metadata_value_copied(self, value: str) -> None:
        """Handle metadata value copied signal from metadata tree view.

        Args:
            value: The value that was copied to clipboard

        """
        logger.debug("[MetadataEdit] Value copied to clipboard: %s", value)

        # Use specialized file operation status method if status manager is available
        if hasattr(self.main_window, "status_manager") and self.main_window.status_manager:
            self.main_window.status_manager.set_file_operation_status(
                f"Copied '{value}' to clipboard", success=True, auto_reset=True
            )

            # Override the reset delay for clipboard operations (shorter feedback)
            if (
                hasattr(self.main_window.status_manager, "_status_timer")
                and self.main_window.status_manager._status_timer
            ):
                self.main_window.status_manager._status_timer.stop()
                self.main_window.status_manager._status_timer.start(
                    2000
                )  # 2 seconds for clipboard feedback

    def refresh_metadata_widgets(self):
        """Refresh all active MetadataWidget instances and trigger preview update."""
        logger.debug(
            "[MainWindow] refresh_metadata_widgets CALLED (hash_worker signal or selection)"
        )
        try:
            from oncutf.ui.widgets.metadata_widget import MetadataWidget

            for module_widget in self.main_window.rename_modules_area.module_widgets:
                if hasattr(module_widget, "current_module_widget"):
                    widget = module_widget.current_module_widget
                    if isinstance(widget, MetadataWidget):
                        widget.trigger_update_options()
                        widget.emit_if_changed()
            # Force preview update after metadata widget changes using UnifiedRenameEngine
            self._trigger_unified_preview_update()
        except Exception:
            pass

    def _trigger_unified_preview_update(self):
        """Trigger preview update using UnifiedRenameEngine ONLY."""
        try:
            if (
                hasattr(self.main_window, "unified_rename_engine")
                and self.main_window.unified_rename_engine
            ):
                # Clear cache to force fresh preview
                self.main_window.unified_rename_engine.clear_cache()
                logger.debug("[MainWindow] Unified preview update triggered")
            else:
                logger.warning("[MainWindow] UnifiedRenameEngine not available")
        except Exception as e:
            logger.error("[MainWindow] Error in unified preview update: %s", e)

    def update_active_metadata_widget_options(self):
        """Find the active MetadataWidget and call trigger_update_options and emit_if_changed (for selection change)."""
        try:
            from oncutf.ui.widgets.metadata_widget import MetadataWidget

            for module_widget in self.main_window.rename_modules_area.module_widgets:
                if hasattr(module_widget, "current_module_widget"):
                    widget = module_widget.current_module_widget
                    if isinstance(widget, MetadataWidget):
                        widget.trigger_update_options()
                        widget.emit_if_changed()
        except Exception as e:
            logger.warning("[MainWindow] Error updating metadata widget: %s", e)
