"""Metadata operation delegates for MainWindow.

Author: Michael Economou
Date: 2026-01-10
"""


class MetadataDelegates:
    """Delegate class for metadata operations.

    All methods delegate to metadata_controller or metadata_signal_handler.
    """

    def shortcut_load_metadata(self) -> None:
        """Load fast metadata via Application Service."""
        return self.shortcut_handler.shortcut_load_metadata()

    def shortcut_load_extended_metadata(self) -> None:
        """Load extended metadata via Application Service."""
        return self.shortcut_handler.shortcut_load_extended_metadata()

    def shortcut_save_selected_metadata(self) -> None:
        """Save selected metadata via Application Service."""
        return self.shortcut_handler.shortcut_save_selected_metadata()

    def shortcut_save_all_metadata(self) -> None:
        """Save all modified metadata via Application Service."""
        return self.shortcut_handler.shortcut_save_all_metadata()

    def load_metadata_for_items(
        self, items: list, use_extended: bool = False, source: str = "unknown"
    ) -> None:
        """Load metadata for items via MetadataController."""
        from oncutf.utils.logging.logger_factory import get_cached_logger

        logger = get_cached_logger(__name__)

        result = self.metadata_controller.load_metadata(items, use_extended, source)
        logger.debug(
            "[MetadataController] load_metadata result: %s",
            result.get("success"),
            extra={"dev_only": True},
        )

    def restore_fileitem_metadata_from_cache(self) -> None:
        """Restore metadata from cache via MetadataController."""
        from oncutf.utils.logging.logger_factory import get_cached_logger

        logger = get_cached_logger(__name__)

        result = self.metadata_controller.restore_metadata_from_cache()
        logger.debug(
            "[MetadataController] restore_metadata_from_cache result: %s",
            result.get("success"),
            extra={"dev_only": True},
        )

    def get_common_metadata_fields(self) -> list[str]:
        """Get common metadata fields via MetadataController."""
        return self.metadata_controller.get_common_metadata_fields()

    def determine_metadata_mode(self) -> tuple[bool, bool]:
        """Determine metadata mode via MetadataController."""
        return self.metadata_controller.determine_metadata_mode()

    def should_use_extended_metadata(self) -> bool:
        """Determine if extended metadata should be used via MetadataController."""
        return self.metadata_controller.should_use_extended_metadata()

    def show_metadata_status(self) -> None:
        """Delegates to InitializationManager for metadata status display."""
        self.initialization_manager.show_metadata_status()

    def on_metadata_value_edited(self, key_path: str, old_value: str, new_value: str) -> None:
        """Handle metadata value edited signal from metadata tree view.

        Args:
            key_path: The metadata key path (e.g. "EXIF/Rotation")
            old_value: The previous value
            new_value: The new value

        """
        return self.metadata_signal_handler.on_metadata_value_edited(key_path, old_value, new_value)

    def on_metadata_value_reset(self, key_path: str) -> None:
        """Handle metadata value reset signal from metadata tree view.

        Args:
            key_path: The metadata key path that was reset

        """
        return self.metadata_signal_handler.on_metadata_value_reset(key_path)

    def on_metadata_value_copied(self, value: str) -> None:
        """Handle metadata value copied signal from metadata tree view.

        Args:
            value: The value that was copied to clipboard

        """
        return self.metadata_signal_handler.on_metadata_value_copied(value)

    def refresh_metadata_widgets(self):
        """Refresh all active MetadataWidget instances and trigger preview update."""
        return self.metadata_signal_handler.refresh_metadata_widgets()

    def _trigger_unified_preview_update(self):
        """Trigger preview update using UnifiedRenameEngine ONLY."""
        return self.metadata_signal_handler._trigger_unified_preview_update()

    def update_active_metadata_widget_options(self):
        """Find the active MetadataWidget and call trigger_update_options and emit_if_changed (for selection change)."""
        return self.metadata_signal_handler.update_active_metadata_widget_options()
