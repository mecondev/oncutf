"""Module: rotation_handlers.py.

Author: Michael Economou
Date: 2026-01-01

Rotation-related context menu handlers.
Handles bulk rotation operations and rotation-related prompts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from oncutf.config import STATUS_COLORS
from oncutf.utils.filesystem.path_utils import paths_equal
from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.models.file_item import FileItem

logger = get_cached_logger(__name__)


class RotationHandlers:
    """Handles rotation-related context menu operations."""

    def __init__(self, parent_window: Any) -> None:
        """Initialize rotation handlers with parent window reference."""
        self.parent_window = parent_window

    def _handle_bulk_rotation(self, selected_files: list[FileItem]) -> None:
        """Handle bulk rotation setting to 0 deg for selected files.
        Analyzes metadata availability and prompts user to load if needed.

        Args:
            selected_files: List of FileItem objects to process

        """
        if not selected_files:
            logger.warning("[BulkRotation] No files selected for bulk rotation")
            return

        logger.info("[BulkRotation] Starting bulk rotation for %d files", len(selected_files))

        # Analyze which files have metadata loaded
        files_with_metadata = []
        files_without_metadata = []

        for file_item in selected_files:
            if self._has_metadata_loaded(file_item):
                files_with_metadata.append(file_item)
            else:
                files_without_metadata.append(file_item)

        logger.debug(
            "[BulkRotation] Metadata analysis: %d with metadata, %d without metadata",
            len(files_with_metadata),
            len(files_without_metadata),
            extra={"dev_only": True},
        )

        # If files without metadata exist, prompt user
        files_to_process = selected_files
        if files_without_metadata:
            choice = self._show_load_metadata_prompt(
                len(files_with_metadata), len(files_without_metadata)
            )

            if choice == "load":
                logger.info(
                    "[BulkRotation] Loading metadata for %d files",
                    len(files_without_metadata),
                )
                self.parent_window.load_metadata_for_items(
                    files_without_metadata, use_extended=False, source="rotation_prep"
                )
                files_to_process = selected_files
            elif choice == "skip":
                if not files_with_metadata:
                    logger.info("[BulkRotation] No files with metadata to process")
                    return
                files_to_process = files_with_metadata
                logger.info(
                    "[BulkRotation] Skipping %d files without metadata",
                    len(files_without_metadata),
                )
            else:  # cancel
                logger.debug("[BulkRotation] User cancelled operation", extra={"dev_only": True})
                return

        try:
            from oncutf.ui.dialogs.bulk_rotation_dialog import BulkRotationDialog

            final_files = BulkRotationDialog.get_bulk_rotation_choice(
                self.parent_window, files_to_process, self.parent_window.metadata_cache
            )

            if not final_files:
                logger.debug(
                    "[BulkRotation] User cancelled bulk rotation or no files selected",
                    extra={"dev_only": True},
                )
                return

            logger.info("[BulkRotation] Processing %d files", len(final_files))
            self._apply_bulk_rotation(final_files)

        except ImportError:
            logger.exception("[BulkRotation] Failed to import BulkRotationDialog")
            from oncutf.app.services import show_error_message

            show_error_message(
                self.parent_window,
                "Error",
                "Bulk rotation dialog is not available. Please check the installation.",
            )
        except Exception as e:
            logger.exception("[BulkRotation] Unexpected error")
            from oncutf.app.services import show_error_message

            show_error_message(
                self.parent_window,
                "Error",
                f"An error occurred during bulk rotation: {e!s}",
            )

    def _has_metadata_loaded(self, file_item: FileItem) -> bool:
        """Check if a file has metadata loaded in cache."""
        if not self.parent_window or not hasattr(self.parent_window, "metadata_cache"):
            return False

        metadata_entry = self.parent_window.metadata_cache.get_entry(file_item.full_path)
        if metadata_entry and hasattr(metadata_entry, "data") and metadata_entry.data:
            return True

        return hasattr(file_item, "metadata") and bool(file_item.metadata)

    def _show_load_metadata_prompt(
        self, with_metadata_count: int, without_metadata_count: int
    ) -> str:
        """Show prompt asking user whether to load metadata for files that don't have it.

        Returns:
            'load': Load metadata and continue
            'skip': Skip files without metadata
            'cancel': Cancel operation

        """
        from oncutf.ui.dialogs.custom_message_dialog import CustomMessageDialog

        message_parts = []
        if with_metadata_count > 0:
            message_parts.append(
                f"{with_metadata_count} file(s) have metadata and can be processed"
            )

        message_parts.append(f"{without_metadata_count} file(s) don't have metadata loaded yet")
        message_parts.append("\nLoad metadata for these files first?")
        message_parts.append("(This ensures rotation changes can be saved properly)")

        message = "\n".join(message_parts)

        buttons = ["Load & Continue", "Skip", "Cancel"]
        dlg = CustomMessageDialog("Load Metadata First?", message, buttons, self.parent_window)

        if self.parent_window:
            from oncutf.ui.services.dialog_positioning import ensure_dialog_centered

            ensure_dialog_centered(dlg, self.parent_window)

        dlg.exec_()

        button_map: dict[str, str] = {
            "Load & Continue": "load",
            "Skip": "skip",
            "Cancel": "cancel",
        }

        selected: str = dlg.selected or "cancel"
        return button_map.get(selected, "cancel")

    def _apply_bulk_rotation(self, files_to_process: list[FileItem]) -> None:
        """Apply 0 deg rotation to the specified files, but only to files that actually need the change.

        Args:
            files_to_process: List of FileItem objects to set rotation to 0 deg

        """
        if not files_to_process:
            return

        logger.info("[BulkRotation] Checking rotation for %d files", len(files_to_process))

        try:
            try:
                staging_manager = self.parent_window.context.get_manager("metadata_staging")
            except KeyError:
                logger.exception("[BulkRotation] MetadataStagingManager not found")
                return

            modified_count = 0
            skipped_count = 0

            for file_item in files_to_process:
                current_rotation = self._get_current_rotation_for_file(file_item)

                if current_rotation == "0":
                    logger.debug(
                        "[BulkRotation] Skipping %s - already has 0 deg rotation",
                        file_item.filename,
                        extra={"dev_only": True},
                    )
                    skipped_count += 1
                    continue

                staging_manager.stage_change(file_item.full_path, "Rotation", "0")

                cache_entry = self.parent_window.metadata_cache.get_entry(file_item.full_path)
                if not cache_entry:
                    metadata_dict = getattr(file_item, "metadata", {}) or {}
                    self.parent_window.metadata_cache.set(file_item.full_path, metadata_dict)
                    cache_entry = self.parent_window.metadata_cache.get_entry(file_item.full_path)

                if cache_entry and hasattr(cache_entry, "data"):
                    cache_entry.data["Rotation"] = "0"
                    cache_entry.modified = True

                    if not hasattr(file_item, "metadata") or file_item.metadata is None:
                        file_item.metadata = {}
                    file_item.metadata["Rotation"] = "0"

                    file_item.metadata_status = "modified"
                    modified_count += 1

                    logger.debug(
                        "[BulkRotation] Set rotation=0 for %s (was: %s)",
                        file_item.filename,
                        current_rotation,
                        extra={"dev_only": True},
                    )

            # Update UI to reflect changes
            if modified_count > 0:
                if hasattr(self.parent_window, "file_model"):
                    for file_item in files_to_process:
                        if file_item.metadata_status == "modified":
                            try:
                                for row, model_file in enumerate(
                                    self.parent_window.file_model.files
                                ):
                                    if paths_equal(model_file.full_path, file_item.full_path):
                                        idx = self.parent_window.file_model.index(row, 0)
                                        self.parent_window.file_model.dataChanged.emit(idx, idx)
                                        break
                            except Exception as e:
                                logger.warning(
                                    "[BulkRotation] Error updating icon for %s: %s",
                                    file_item.filename,
                                    e,
                                )

                    self.parent_window.file_model.layoutChanged.emit()

                # Update metadata tree view to mark items as modified
                if hasattr(self.parent_window, "metadata_tree_view"):
                    for file_item in files_to_process:
                        if file_item.metadata_status == "modified":
                            if not self.parent_window.metadata_tree_view._scroll_behavior._path_in_dict(
                                file_item.full_path,
                                self.parent_window.metadata_tree_view.modified_items_per_file,
                            ):
                                self.parent_window.metadata_tree_view._scroll_behavior._set_in_path_dict(
                                    file_item.full_path,
                                    set(),
                                    self.parent_window.metadata_tree_view.modified_items_per_file,
                                )

                            existing_modifications = self.parent_window.metadata_tree_view._scroll_behavior._get_from_path_dict(
                                file_item.full_path,
                                self.parent_window.metadata_tree_view.modified_items_per_file,
                            )
                            if existing_modifications is None:
                                existing_modifications = set()
                            existing_modifications.add("Rotation")
                            self.parent_window.metadata_tree_view._scroll_behavior._set_in_path_dict(
                                file_item.full_path,
                                existing_modifications,
                                self.parent_window.metadata_tree_view.modified_items_per_file,
                            )

                            if hasattr(
                                self.parent_window.metadata_tree_view,
                                "_current_file_path",
                            ) and paths_equal(
                                self.parent_window.metadata_tree_view._current_file_path,
                                file_item.full_path,
                            ):
                                self.parent_window.metadata_tree_view.modified_items.add("Rotation")

                    self.parent_window.metadata_tree_view.update_from_parent_selection()

                if hasattr(self.parent_window, "request_preview_update"):
                    self.parent_window.request_preview_update()

                if hasattr(self.parent_window, "set_status"):
                    if skipped_count > 0:
                        status_msg = (
                            f"Set rotation to 0 deg for {modified_count} file(s), "
                            f"{skipped_count} already had 0 deg rotation"
                        )
                    else:
                        status_msg = f"Set rotation to 0 deg for {modified_count} file(s)"

                    self.parent_window.set_status(
                        status_msg,
                        color=STATUS_COLORS["operation_success"],
                        auto_reset=True,
                    )

                logger.info(
                    "[BulkRotation] Successfully applied rotation to %d files, skipped %d files",
                    modified_count,
                    skipped_count,
                )
            else:
                logger.info("[BulkRotation] No files needed rotation changes")
                if hasattr(self.parent_window, "set_status"):
                    self.parent_window.set_status(
                        "All selected files already have 0 deg rotation",
                        color=STATUS_COLORS["neutral_info"],
                        auto_reset=True,
                    )

        except Exception as e:
            logger.exception("[BulkRotation] Error applying rotation")
            from oncutf.app.services import show_error_message

            show_error_message(
                self.parent_window, "Error", f"Failed to apply rotation changes: {e!s}"
            )

    def _get_current_rotation_for_file(self, file_item: FileItem) -> str:
        """Get the current rotation value for a file, checking cache first then file metadata.

        Returns:
            str: Current rotation value ("0", "90", "180", "270") or "0" if not found

        """
        if hasattr(self.parent_window, "metadata_cache"):
            cache_entry = self.parent_window.metadata_cache.get_entry(file_item.full_path)
            if cache_entry and hasattr(cache_entry, "data"):
                rotation = cache_entry.data.get("Rotation")
                if rotation is not None:
                    return str(rotation)

        if hasattr(file_item, "metadata") and file_item.metadata:
            rotation = file_item.metadata.get("Rotation")
            if rotation is not None:
                return str(rotation)

        return "0"
