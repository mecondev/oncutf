"""Module: metadata_writer.py

Author: Michael Economou
Date: 2025-12-20
Updated: 2025-12-21

Metadata writer - handles all metadata save/write operations.
Extracted from unified_metadata_manager.py for better separation of concerns.

Responsibilities:
- Set metadata values (update cache)
- Save metadata for selected files
- Save all modified metadata
- Write metadata to disk using ExifTool
- Progress tracking and UI updates for save operations
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from PyQt5.QtCore import QObject

from oncutf.utils.filesystem.path_normalizer import normalize_path
from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.utils.shared.exiftool_wrapper import ExifToolWrapper

logger = get_cached_logger(__name__)


class MetadataWriter(QObject):
    """Writer service for metadata save/write operations.

    Responsibilities:
    - Set metadata values (update cache)
    - Save metadata for selected files
    - Save all modified metadata
    - Write metadata to disk using ExifTool
    - Progress tracking and UI updates
    """

    def __init__(self, parent_window: Any = None) -> None:
        """Initialize metadata writer with parent window reference."""
        super().__init__(parent_window)
        self.parent_window = parent_window
        self._exiftool_wrapper: ExifToolWrapper | None = None
        self._save_cancelled = False

    @property
    def exiftool_wrapper(self) -> ExifToolWrapper:
        """Lazy-initialized ExifTool wrapper."""
        if self._exiftool_wrapper is None:
            from oncutf.utils.shared.exiftool_wrapper import ExifToolWrapper

            self._exiftool_wrapper = ExifToolWrapper()
        return self._exiftool_wrapper

    def request_save_cancel(self) -> None:
        """Request cancellation of current save operation."""
        self._save_cancelled = True
        logger.info("[MetadataWriter] Save cancellation requested")

    def set_metadata_value(self, file_path: str, key_path: str, new_value: str) -> bool:
        """Set a metadata value for a file (updates cache only, doesn't write to disk).

        Args:
            file_path: Path to the file
            key_path: Metadata key path (e.g., "Rotation", "EXIF/DateTimeOriginal")
            new_value: New value to set

        Returns:
            bool: True if successful, False otherwise

        """
        try:
            # Stage the change
            try:
                staging_manager = self.parent_window.context.get_manager("metadata_staging")
                staging_manager.stage_change(file_path, key_path, new_value)
            except KeyError:
                logger.warning(
                    "[MetadataWriter] MetadataStagingManager not found during set_metadata_value"
                )

            # Update UI cache
            if hasattr(self.parent_window, "metadata_cache"):
                cache = self.parent_window.metadata_cache
                metadata_entry = cache.get_entry(file_path)

                if metadata_entry and hasattr(metadata_entry, "data"):
                    # Handle rotation as top-level key
                    if key_path.lower() == "rotation":
                        metadata_entry.data["Rotation"] = new_value
                    # Handle nested keys
                    elif "/" in key_path or ":" in key_path:
                        parts = key_path.replace(":", "/").split("/", 1)
                        if len(parts) == 2:
                            group, key = parts
                            if group not in metadata_entry.data:
                                metadata_entry.data[group] = {}
                            metadata_entry.data[group][key] = new_value
                    # Handle top-level keys
                    else:
                        metadata_entry.data[key_path] = new_value

                    metadata_entry.modified = True
                    logger.debug(
                        "[MetadataWriter] Set %s=%s for %s",
                        key_path,
                        new_value,
                        os.path.basename(file_path),
                    )
                    return True

            return False

        except Exception:
            logger.exception("[MetadataWriter] Error setting metadata value")
            return False

    def save_metadata_for_selected(self) -> None:
        """Save metadata for selected files."""
        if not self.parent_window:
            return

        # Get selected files
        selected_files = (
            self.parent_window.get_selected_files_ordered() if self.parent_window else []
        )

        if not selected_files:
            logger.info("[MetadataWriter] No files selected for metadata saving")
            if hasattr(self.parent_window, "status_manager"):
                self.parent_window.status_manager.set_selection_status(
                    "No files selected", selected_count=0, total_count=0, auto_reset=True
                )
            return

        # Get staging manager
        try:
            staging_manager = self.parent_window.context.get_manager("metadata_staging")
        except KeyError:
            logger.error("[MetadataWriter] MetadataStagingManager not found")
            return

        # Collect staged changes for selected files
        files_to_save = []
        all_staged_changes = {}

        for file_item in selected_files:
            if staging_manager.has_staged_changes(file_item.full_path):
                files_to_save.append(file_item)
                all_staged_changes[file_item.full_path] = staging_manager.get_staged_changes(
                    file_item.full_path
                )

        if not files_to_save:
            logger.info("[MetadataWriter] No staged changes for selected files")
            if hasattr(self.parent_window, "status_manager"):
                self.parent_window.status_manager.set_file_operation_status(
                    "No metadata changes to save", success=False, auto_reset=True
                )
            return

        logger.info(
            "[MetadataWriter] Saving metadata for %d selected file(s)",
            len(files_to_save),
        )
        self._save_metadata_files(files_to_save, all_staged_changes)

    def save_all_modified_metadata(self, is_exit_save: bool = False) -> None:
        """Save all modified metadata across all files.

        Args:
            is_exit_save: If True, indicates this is a save-on-exit operation.
                         ESC will be blocked to prevent incomplete saves.

        """
        if not self.parent_window:
            return

        # Get staging manager
        try:
            staging_manager = self.parent_window.context.get_manager("metadata_staging")
        except KeyError:
            logger.error("[MetadataWriter] MetadataStagingManager not found")
            return

        # Get all staged changes
        all_staged_changes = staging_manager.get_all_staged_changes()

        if not all_staged_changes:
            logger.info("[MetadataWriter] No staged metadata changes to save")
            if hasattr(self.parent_window, "status_manager"):
                self.parent_window.status_manager.set_file_operation_status(
                    "No metadata changes to save", success=False, auto_reset=True
                )
            return

        # Match staged changes to file items
        files_to_save = []
        file_model = getattr(self.parent_window, "file_model", None)

        if file_model and hasattr(file_model, "files"):
            # Create a map of normalized path -> file item for fast lookup
            path_map = {normalize_path(f.full_path): f for f in file_model.files}

            for staged_path in all_staged_changes:
                if staged_path in path_map:
                    files_to_save.append(path_map[staged_path])

        if not files_to_save:
            logger.info("[MetadataWriter] No files with staged metadata found in current view")
            if hasattr(self.parent_window, "status_manager"):
                self.parent_window.status_manager.set_file_operation_status(
                    "No metadata changes to save", success=False, auto_reset=True
                )
            return

        logger.info(
            "[MetadataWriter] Saving metadata for %d files with modifications (exit_save: %s)",
            len(files_to_save),
            is_exit_save,
        )
        # Reset cancellation flag before starting save
        self._save_cancelled = False
        self._save_metadata_files(files_to_save, all_staged_changes, is_exit_save=is_exit_save)

    def _save_metadata_files(
        self,
        files_to_save: list[Any],
        all_modifications: dict[str, Any],
        is_exit_save: bool = False,
    ) -> None:
        """Save metadata files using ExifTool.

        Args:
            files_to_save: List of FileItem objects to save
            all_modifications: Dictionary of all staged modifications
            is_exit_save: If True, ESC will be blocked in progress dialog

        """
        import contextlib

        from oncutf.core.pyqt_imports import QApplication
        from oncutf.utils.ui.cursor_helper import wait_cursor

        if not files_to_save:
            return

        success_count = 0
        failed_files: list[str] = []
        _loading_dialog = None

        file_count = len(files_to_save)
        save_mode = "single_file_wait_cursor" if file_count == 1 else "multiple_files_dialog"

        logger.info(
            "[MetadataWriter] Saving metadata for %d file(s) using mode: %s",
            file_count,
            save_mode,
        )

        try:
            if save_mode == "multiple_files_dialog":
                from oncutf.utils.ui.progress_dialog import ProgressDialog

                cancel_callback = self.request_save_cancel if not is_exit_save else None
                _loading_dialog = ProgressDialog(
                    parent=self.parent_window,
                    operation_type="metadata_save",
                    cancel_callback=cancel_callback,
                    show_enhanced_info=False,
                    is_exit_save=is_exit_save,
                )
                _loading_dialog.set_status("Saving metadata...")
                _loading_dialog.show()
                QApplication.processEvents()

            cursor_context = (
                wait_cursor()
                if save_mode == "single_file_wait_cursor"
                else contextlib.nullcontext()
            )

            with cursor_context:
                current_file_index = 0
                for file_item in files_to_save:
                    if self._save_cancelled:
                        logger.info(
                            "[MetadataWriter] Save cancelled after %d/%d files",
                            success_count,
                            file_count,
                        )
                        break

                    current_file_index += 1

                    if _loading_dialog:
                        _loading_dialog.set_filename(file_item.filename)
                        _loading_dialog.set_count(current_file_index, file_count)
                        _loading_dialog.set_progress(current_file_index, file_count)
                        QApplication.processEvents()

                    file_path = file_item.full_path
                    modifications = self._get_modified_metadata_for_file(
                        file_path, all_modifications
                    )

                    if not modifications:
                        continue

                    try:
                        success = self.exiftool_wrapper.write_metadata(file_path, modifications)

                        if success:
                            success_count += 1
                            self._update_file_after_save(file_item, modifications)
                        else:
                            failed_files.append(file_item.filename)

                    except Exception:
                        failed_files.append(file_item.filename)
                        logger.exception(
                            "[MetadataWriter] Error saving metadata for %s",
                            file_item.filename,
                        )

        except Exception:
            logger.exception("[MetadataWriter] Error in metadata saving process")
        finally:
            if _loading_dialog:
                _loading_dialog.close()

        was_cancelled = self._save_cancelled
        self._show_save_results(success_count, failed_files, files_to_save, was_cancelled)

        # Record save command
        if success_count > 0:
            self._record_save_command(files_to_save, failed_files, all_modifications)

    def _get_modified_metadata_for_file(
        self, file_path: str, all_modified_metadata: dict[str, Any]
    ) -> dict[str, Any]:
        """Get modified metadata for a specific file with path normalization."""
        # Try direct lookup first
        if file_path in all_modified_metadata:
            result: dict[str, Any] = all_modified_metadata[file_path]
            return result

        # Try normalized path lookup if direct fails (critical for cross-platform)
        normalized = normalize_path(file_path)

        for key, value in all_modified_metadata.items():
            if normalize_path(key) == normalized:
                result = value
                return result

        # Not found
        return {}

    def _update_file_after_save(
        self, file_item: Any, saved_metadata: dict[str, Any] | None = None
    ) -> None:
        """Update file item after successful metadata save."""
        import contextlib
        from datetime import datetime

        # Clear staged changes
        try:
            staging_manager = self.parent_window.context.get_manager("metadata_staging")
            staging_manager.clear_staged_changes(file_item.full_path)
        except KeyError:
            pass

        # Update caches
        if saved_metadata:
            self._update_caches_after_save(file_item, saved_metadata)

        # Clear modifications in tree view
        if hasattr(self.parent_window, "metadata_tree_view"):
            self.parent_window.metadata_tree_view.clear_modifications_for_file(file_item.full_path)

        # Update modification time
        with contextlib.suppress(Exception):
            file_item.date_modified = datetime.fromtimestamp(os.path.getmtime(file_item.full_path))

        # Refresh display if this file is shown
        self._refresh_display_if_current(file_item)

    def _update_caches_after_save(self, file_item: Any, saved_metadata: dict[str, Any]) -> None:
        """Update UI and persistent caches after save."""
        # Update UI cache
        if hasattr(self.parent_window, "metadata_cache"):
            cache = self.parent_window.metadata_cache
            entry = cache.get_entry(file_item.full_path)
            if entry and hasattr(entry, "data"):
                for key_path, new_value in saved_metadata.items():
                    self._update_nested_metadata(entry.data, key_path, new_value)
                entry.modified = False

        # Update persistent cache
        try:
            from oncutf.core.cache.persistent_metadata_cache import get_persistent_metadata_cache

            persistent_cache = get_persistent_metadata_cache()
            if persistent_cache:
                current = persistent_cache.get(file_item.full_path)
                if current:
                    updated = dict(current)
                    for key_path, new_value in saved_metadata.items():
                        self._update_nested_metadata(updated, key_path, new_value)
                    persistent_cache.set(file_item.full_path, updated, is_extended=False)
        except Exception:
            logger.warning("[MetadataWriter] Failed to update persistent cache", exc_info=True)

    def _update_nested_metadata(self, data: dict[str, Any], key_path: str, value: str) -> None:
        """Update nested metadata structure."""
        if "/" in key_path or ":" in key_path:
            sep = "/" if "/" in key_path else ":"
            parts = key_path.split(sep, 1)
            if len(parts) == 2:
                group, key = parts
                if group not in data:
                    data[group] = {}
                if isinstance(data[group], dict):
                    data[group][key] = value
                else:
                    data[group] = {key: value}
            else:
                data[key_path] = value
        else:
            data[key_path] = value

    def _refresh_display_if_current(self, file_item: Any) -> None:
        """Refresh metadata display if file is currently shown."""
        if not hasattr(self.parent_window, "metadata_tree_view"):
            return
        tree = self.parent_window.metadata_tree_view
        if hasattr(tree, "_current_file_path") and tree._current_file_path == file_item.full_path:
            if hasattr(self.parent_window, "metadata_cache"):
                entry = self.parent_window.metadata_cache.get_entry(file_item.full_path)
                if entry and hasattr(entry, "data"):
                    display_data = dict(entry.data)
                    display_data["FileName"] = file_item.filename
                    tree.display_metadata(display_data, context="after_save")

    def _show_save_results(
        self,
        success_count: int,
        failed_files: list[str],
        files_to_save: list[Any],
        was_cancelled: bool = False,
    ) -> None:
        """Show results of metadata save operation."""
        total_files = len(files_to_save)

        if was_cancelled:
            skipped_count = total_files - success_count - len(failed_files)
            message = (
                f"Save cancelled after {success_count}/{total_files} files"
                if success_count
                else "Save cancelled"
            )
            logger.info("[MetadataWriter] %s", message)

            if self.parent_window and hasattr(self.parent_window, "status_bar"):
                self.parent_window.status_bar.showMessage(message, 5000 if success_count else 3000)

            if self.parent_window:
                from oncutf.ui.widgets.custom_message_dialog import CustomMessageDialog

                msg_parts = ["Save operation cancelled by user."]
                if success_count > 0:
                    msg_parts.append(f"\nSuccessfully saved: {success_count} files")
                if failed_files:
                    msg_parts.append(f"Failed: {len(failed_files)} files")
                if skipped_count > 0:
                    msg_parts.append(f"Skipped: {skipped_count} files")

                CustomMessageDialog.information(
                    self.parent_window, "Save Cancelled", "\n".join(msg_parts)
                )
            return

        if success_count > 0:
            logger.info("[MetadataWriter] Saved metadata for %d files", success_count)
            if self.parent_window and hasattr(self.parent_window, "status_bar"):
                self.parent_window.status_bar.showMessage(
                    f"Metadata saved for {success_count} files", 3000
                )

        if failed_files:
            logger.warning("[MetadataWriter] Failed to save %d files", len(failed_files))
            if self.parent_window:
                from oncutf.core.pyqt_imports import QMessageBox

                QMessageBox.warning(
                    self.parent_window,
                    "Metadata Save Error",
                    f"Failed to save metadata for {len(failed_files)} files.\n\n"
                    f"Files: {', '.join(failed_files[:5])}"
                    f"{'...' if len(failed_files) > 5 else ''}",
                )

    def _record_save_command(
        self,
        files_to_save: list[Any],
        failed_files: list[str],
        all_modifications: dict[str, Any],
    ) -> None:
        """Record save command for undo/redo."""
        try:
            from oncutf.core.metadata_command_manager import get_metadata_command_manager
            from oncutf.core.metadata_commands import SaveMetadataCommand

            command_manager = get_metadata_command_manager()
            if command_manager:
                successful_files = []
                successful_metadata: dict[str, Any] = {}

                for file_item in files_to_save:
                    if file_item.filename not in failed_files:
                        successful_files.append(file_item.full_path)
                        mods = self._get_modified_metadata_for_file(
                            file_item.full_path, all_modifications
                        )
                        if mods:
                            successful_metadata[file_item.full_path] = mods

                if successful_files:
                    save_command = SaveMetadataCommand(
                        file_paths=successful_files, saved_metadata=successful_metadata
                    )
                    command_manager.execute_command(save_command)
        except Exception:
            logger.warning("[MetadataWriter] Error recording save command", exc_info=True)
