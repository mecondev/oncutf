"""
Module: metadata_writer.py

Author: Michael Economou (refactored)
Date: 2025-12-20

Metadata writer - handles all metadata save/write operations.
Extracted from unified_metadata_manager.py for better separation of concerns.
"""

import os

from PyQt5.QtCore import QObject

from oncutf.models.file_item import FileItem
from oncutf.utils.cursor_helper import wait_cursor
from oncutf.utils.logger_factory import get_cached_logger
from oncutf.utils.path_normalizer import normalize_path
from oncutf.utils.progress_dialog import ProgressDialog

logger = get_cached_logger(__name__)


class MetadataWriter(QObject):
    """
    Writer service for metadata save/write operations.

    Responsibilities:
    - Set metadata values (update cache)
    - Save metadata for selected files
    - Save all modified metadata
    - Write metadata to disk using ExifTool
    - Progress tracking and UI updates
    """

    def __init__(self, parent_window=None):
        """Initialize metadata writer with parent window reference."""
        super().__init__(parent_window)
        self.parent_window = parent_window
        self._exiftool_wrapper = None
        self._save_cancelled = False

    @property
    def exiftool_wrapper(self):
        """Lazy-initialized ExifTool wrapper."""
        if self._exiftool_wrapper is None:
            from oncutf.utils.exiftool_wrapper import ExifToolWrapper

            self._exiftool_wrapper = ExifToolWrapper()
        return self._exiftool_wrapper

    def request_save_cancel(self) -> None:
        """Request cancellation of current save operation."""
        self._save_cancelled = True
        logger.info("[MetadataWriter] Save cancellation requested")

    def set_metadata_value(self, file_path: str, key_path: str, new_value: str) -> bool:
        """
        Set a metadata value for a file (updates cache only, doesn't write to disk).

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
        self, files_to_save: list, all_modifications: dict, is_exit_save: bool = False
    ) -> None:
        """Save metadata files using ExifTool.

        NOTE: This is a stub implementation. Full save logic with progress dialogs
        will be implemented in the next step to keep changes incremental.

        Args:
            files_to_save: List of FileItem objects to save
            all_modifications: Dictionary of all staged modifications
            is_exit_save: If True, ESC will be blocked in progress dialog
        """
        if not files_to_save:
            return

        logger.debug(
            "[MetadataWriter] _save_metadata_files stub called with %d files", len(files_to_save)
        )
        # Full implementation to be added in next step

    def _get_modified_metadata_for_file(self, file_path: str, all_modified_metadata: dict) -> dict:
        """Get modified metadata for a specific file with path normalization."""
        # Try direct lookup first
        if file_path in all_modified_metadata:
            return all_modified_metadata[file_path]

        # Try normalized path lookup if direct fails (critical for cross-platform)
        normalized = normalize_path(file_path)

        for key, value in all_modified_metadata.items():
            if normalize_path(key) == normalized:
                return value

        # Not found
        return {}
