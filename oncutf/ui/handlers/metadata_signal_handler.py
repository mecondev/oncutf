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

        # Refresh thumbnail immediately if a rotation field was changed.
        if "rotation" in key_path.lower():
            self._refresh_thumbnail_after_rotation_edit(old_value, new_value)

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
        except Exception:
            logger.exception("[MainWindow] Error in unified preview update")

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

    def _refresh_thumbnail_after_rotation_edit(self, old_value: str, new_value: str) -> None:
        """Refresh the thumbnail for the currently selected file after a rotation edit.

        Applies an in-place rotation to the cached pixmap so the thumbnail viewport
        shows the new orientation immediately, without waiting for a file save.

        The rotation angle applied is: new_angle - old_angle (normalised to 0-359).
        If the cached pixmap cannot be found, the method returns silently.

        Args:
            old_value: Previous rotation value (e.g. "90", "90deg", "0")
            new_value: New rotation value

        """
        from pathlib import Path

        from PyQt5.QtGui import QTransform

        thumbnail_manager = getattr(self.main_window, "thumbnail_manager", None)
        thumbnail_viewport = getattr(self.main_window, "thumbnail_viewport", None)
        if thumbnail_manager is None or thumbnail_viewport is None:
            return

        # Resolve the current FileItem (single-file metadata editing)
        file_item = None
        if hasattr(self.main_window, "metadata_tree_view"):
            tree = self.main_window.metadata_tree_view
            file_path = getattr(tree, "_current_file_path", None)
            if file_path:
                # Lightweight lookup: find matching FileItem in model
                file_model = getattr(self.main_window, "file_model", None)
                if file_model:
                    for fi in file_model.files:
                        if fi.full_path == file_path:
                            file_item = fi
                            break

        if file_item is None:
            return

        # Parse angle strings: strip non-numeric suffix (e.g. "90deg" -> 90)
        def _parse_angle(v: str) -> int:
            try:
                import re

                m = re.search(r"-?\d+", v)
                return int(m.group()) % 360 if m else 0
            except (ValueError, AttributeError):
                return 0

        old_angle = _parse_angle(old_value)
        new_angle = _parse_angle(new_value)
        delta = (new_angle - old_angle) % 360
        if delta == 0:
            return

        try:
            stat = Path(file_item.full_path).stat()
            cached_pixmap = thumbnail_manager._cache.get(
                file_item.full_path, stat.st_mtime, stat.st_size
            )
            if cached_pixmap is None or cached_pixmap.isNull():
                return

            # The display pixmap was rotated CW by old_angle (ffmpeg auto-rotate).
            # To show new_angle rotation we must undo old and apply new:
            # net delta CW = new_angle - old_angle.
            rotated = cached_pixmap.transformed(QTransform().rotate(delta))
            if rotated.isNull():
                return

            thumbnail_manager._cache.put(file_item.full_path, stat.st_mtime, stat.st_size, rotated)
            thumbnail_viewport.refresh_thumbnail(file_item.full_path, rotated)
            logger.debug(
                "[MetadataEdit] Refreshed thumbnail for %s (delta=%d deg)",
                file_item.filename,
                delta,
            )
        except (OSError, ValueError) as e:
            logger.debug(
                "[MetadataEdit] Could not refresh thumbnail for %s: %s",
                file_item.full_path if file_item else "?",
                e,
            )
