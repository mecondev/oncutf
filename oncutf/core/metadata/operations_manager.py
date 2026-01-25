"""Module: metadata_operations_manager.py.

Author: Michael Economou
Date: 2025-06-15

Manages metadata-related operations for file metadata export, field editing, and compatibility checks.

Features:
- Metadata export to JSON/Markdown formats
- Metadata field editing (Title, Artist, Copyright, etc.)
- Field compatibility checking for different file types
- File type detection (image, video, audio, document)
- Metadata field standard resolution (XMP, EXIF, IPTC)

Refactored: 2026-01-03 - Extracted field compatibility to field_compatibility.py
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from oncutf.core.metadata.field_compatibility import get_field_compatibility_checker
from oncutf.utils.filesystem.file_status_helpers import has_metadata
from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QWidget

    from oncutf.models.file_item import FileItem

logger = get_cached_logger(__name__)


class MetadataOperationsManager:
    """Manages all metadata-related operations (export, field editing, compatibility).

    This manager handles:
    - Exporting metadata to JSON or Markdown formats
    - Editing metadata fields across multiple files
    - Checking field compatibility for different file types
    - Determining file types and supported metadata standards
    """

    def __init__(self, parent_window: QWidget) -> None:
        """Initialize the metadata operations manager.

        Args:
            parent_window: Reference to the main window for accessing models, views, and managers

        """
        self.parent_window: Any = parent_window
        logger.debug("MetadataOperationsManager initialized", extra={"dev_only": True})

    # ===== Public Interface Methods =====

    def handle_export_metadata(self, file_items: list[FileItem], scope: str) -> None:
        """Handle metadata export dialog and process.

        Args:
            file_items: List of FileItem objects to export
            scope: Either "selected" or "all" for display purposes

        """
        self._handle_export_metadata(file_items, scope)

    def handle_metadata_field_edit(self, selected_files: list[FileItem], field_name: str) -> None:
        """Handle metadata field editing for selected files.

        Args:
            selected_files: List of FileItem objects to edit
            field_name: Name of the field to edit (Title, Artist, etc.)

        """
        self._handle_metadata_field_edit(selected_files, field_name)

    def check_metadata_field_compatibility(
        self, selected_files: list[FileItem], field_name: str
    ) -> bool:
        """Check if all selected files support a specific metadata field.

        Delegates to FieldCompatibilityChecker for actual logic.

        Args:
            selected_files: List of FileItem objects to check
            field_name: Name of the metadata field to check support for

        Returns:
            bool: True if ALL selected files support the field, False otherwise

        """
        checker = get_field_compatibility_checker(self.parent_window.metadata_cache)
        return checker.check_field_compatibility(selected_files, field_name)

    def check_selected_files_have_metadata(self, selected_files: list[FileItem]) -> bool:
        """Check if any of the selected files have metadata.

        Args:
            selected_files: List of FileItem objects to check

        Returns:
            bool: True if any files have metadata, False otherwise

        """
        return any(self._file_has_metadata(f) for f in selected_files)

    def check_any_files_have_metadata(self) -> bool:
        """Check if any file in the current folder has metadata.

        Returns:
            bool: True if any files have metadata, False otherwise

        """
        if (
            not hasattr(self.parent_window, "file_model")
            or not self.parent_window.file_model
        ):
            return False

        all_files = self.parent_window.file_model.get_all_file_items()
        return any(self._file_has_metadata(f) for f in all_files)

    # ===== Metadata Export =====

    def _handle_export_metadata(
        self,
        file_items: list[FileItem],
        scope: str,
    ) -> None:
        """Handle metadata export dialog and process."""
        from PyQt5.QtWidgets import (
            QDialog,
            QHBoxLayout,
            QLabel,
            QPushButton,
            QVBoxLayout,
        )

        from oncutf.ui.widgets.styled_combo_box import StyledComboBox

        # Create export dialog
        dialog = QDialog(self.parent_window)
        dialog.setWindowTitle(f"Export Metadata - {scope.title()} Files")
        dialog.setModal(True)
        dialog.resize(400, 200)

        layout = QVBoxLayout(dialog)

        # Format selection
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Export Format:"))

        format_combo = StyledComboBox()
        format_combo.addItems(["JSON (Structured)", "Markdown (Human Readable)"])
        format_layout.addWidget(format_combo)

        layout.addLayout(format_layout)

        # Buttons
        button_layout = QHBoxLayout()

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_button)

        export_button = QPushButton("Export...")
        export_button.clicked.connect(
            lambda: self._execute_export(dialog, format_combo, file_items, scope)
        )
        export_button.setDefault(True)
        button_layout.addWidget(export_button)

        layout.addLayout(button_layout)

        # Show dialog
        dialog.exec_()

    def _execute_export(self, dialog: Any, format_combo: Any, file_items: list[FileItem], scope: str) -> None:
        """Execute the actual export process."""
        from oncutf.ui.dialogs.custom_message_dialog import CustomMessageDialog

        # Get format
        format_map = {0: "json", 1: "markdown"}
        format_type = format_map.get(format_combo.currentIndex(), "json")

        # Get output directory
        from oncutf.app.services.folder_selection import select_folder

        output_dir = select_folder(
            dialog,
            f"Select Export Directory - {scope.title()} Files",
            "",
        )

        if not output_dir:
            return

        dialog.accept()

        # Perform export
        try:
            from oncutf.core.metadata.exporter import MetadataExporter

            exporter = MetadataExporter(self.parent_window)

            # Export based on scope
            if scope == "selected":
                success = exporter.export_files(file_items, output_dir, format_type)
            else:
                success = exporter.export_all_files(output_dir, format_type)

            # Show result
            if success:
                CustomMessageDialog.information(
                    self.parent_window,
                    "Export Successful",
                    f"Metadata exported successfully to:\n{output_dir}",
                )
            else:
                CustomMessageDialog.show_warning(
                    self.parent_window,
                    "Export Failed",
                    "Failed to export metadata. Check the logs for details.",
                )

        except Exception as e:
            logger.exception("[EventHandler] Export error: %s", e)
            CustomMessageDialog.show_error(
                self.parent_window, "Export Error", f"An error occurred during export:\n{e!s}"
            )

    # ===== Metadata Field Editing =====

    def _handle_metadata_field_edit(self, selected_files: list[FileItem], field_name: str) -> None:
        """Handle metadata field editing for selected files.

        Args:
            selected_files: List of FileItem objects to edit
            field_name: Name of the field to edit (Title, Artist, etc.)

        """
        if not selected_files:
            logger.warning("[MetadataEdit] No files selected for %s editing", field_name)
            return

        logger.info(
            "[MetadataEdit] Starting %s editing for %d files",
            field_name,
            len(selected_files),
        )

        try:
            # Get current value (for single file editing)
            current_value = ""
            if len(selected_files) == 1:
                current_value = self._get_current_field_value(selected_files[0], field_name) or ""

            # Import and show the metadata edit dialog
            from oncutf.ui.dialogs.metadata_edit_dialog import MetadataEditDialog

            success, new_value, files_to_modify = MetadataEditDialog.edit_metadata_field(
                parent=self.parent_window,
                selected_files=selected_files,
                metadata_cache=self.parent_window.metadata_cache,
                field_name=field_name,
                current_value=current_value,
            )

            if not success:
                logger.debug("[MetadataEdit] User cancelled %s editing", field_name)
                return

            if not files_to_modify:
                logger.debug("[MetadataEdit] No files selected for %s modification", field_name)
                return

            # Apply the changes
            self._apply_metadata_field_changes(files_to_modify, field_name, new_value)

            # Update status
            if hasattr(self.parent_window, "set_status"):
                from oncutf.config import STATUS_COLORS

                status_msg = f"Updated {field_name} for {len(files_to_modify)} file(s)"
                self.parent_window.set_status(
                    status_msg, color=STATUS_COLORS["operation_success"], auto_reset=True
                )

            logger.info(
                "[MetadataEdit] Successfully updated %s for %d files",
                field_name,
                len(files_to_modify),
            )

        except ImportError as e:
            logger.error("[MetadataEdit] Failed to import MetadataEditDialog: %s", e)
            from oncutf.app.services import show_error_message

            show_error_message(
                self.parent_window,
                "Error",
                "Metadata editing dialog is not available. Please check the installation.",
            )
        except Exception as e:
            logger.exception("[MetadataEdit] Unexpected error during %s editing: %s", field_name, e)
            from oncutf.app.services import show_error_message

            show_error_message(
                self.parent_window,
                "Error",
                f"An error occurred during {field_name} editing: {e!s}",
            )

    def _get_current_field_value(self, file_item: FileItem, field_name: str) -> str:
        """Get the current value of a metadata field for a file.

        Args:
            file_item: FileItem object
            field_name: Name of the field

        Returns:
            str: Current value or empty string if not found

        """
        try:
            if not self.parent_window.metadata_cache:
                return ""

            # Check metadata cache first
            cache_entry = self.parent_window.metadata_cache.get_entry(file_item.full_path)
            if cache_entry and hasattr(cache_entry, "data"):
                # Try different field standards based on field name
                standards = self._get_field_standards_for_reading(field_name)
                for standard in standards:
                    value = cache_entry.data.get(standard)
                    if value:
                        return str(value)

            # Fallback to file metadata
            if hasattr(file_item, "metadata") and file_item.metadata:
                standards = self._get_field_standards_for_reading(field_name)
                for standard in standards:
                    value = file_item.metadata.get(standard)
                    if value:
                        return str(value)

            return ""

        except Exception as e:
            logger.debug("[MetadataEdit] Error getting current %s value: %s", field_name, e)
            return ""

    def _get_supported_standards(self, file_path: str) -> list[str]:
        """Get supported metadata standards for a file extension."""
        ext = os.path.splitext(file_path)[1].lower()
        image_exts = [".jpg", ".jpeg", ".png", ".tiff", ".webp", ".heic"]
        video_exts = [".mp4", ".mov", ".avi", ".mkv", ".m4v"]

        standards: list[str] = []
        if ext in image_exts:
            standards.extend(["XMP", "EXIF", "IPTC"])
        elif ext in video_exts:
            standards.extend(["XMP", "QuickTime"])
        # Add more conditions for other file types if needed
        return standards

    def _get_field_standards_for_reading(self, field_name: str) -> list[str]:
        """Get the metadata standards for reading a field (in priority order)."""
        field_standards = {
            "Title": ["XMP:Title", "IPTC:Headline", "EXIF:ImageDescription"],
            "Artist": ["XMP:Creator", "IPTC:By-line", "EXIF:Artist"],
            "Author": ["XMP:Creator", "IPTC:By-line", "EXIF:Artist"],
            "Copyright": ["XMP:Rights", "IPTC:CopyrightNotice", "EXIF:Copyright"],
            "Description": ["XMP:Description", "IPTC:Caption-Abstract", "EXIF:ImageDescription"],
            "Keywords": ["XMP:Keywords", "IPTC:Keywords"],
        }
        return field_standards.get(field_name, [])

    def _apply_metadata_field_changes(
        self, files_to_modify: list[FileItem], field_name: str, new_value: str
    ) -> None:
        """Apply metadata field changes to files by updating the metadata tree view.
        This ensures the changes are properly tracked and can be saved later.
        """
        if not hasattr(self.parent_window, "metadata_tree_view"):
            logger.warning("[EventHandler] No metadata tree view available for field changes")
            return

        metadata_tree_view = self.parent_window.metadata_tree_view

        # Apply changes to each file
        for file_item in files_to_modify:
            logger.debug(
                "[EventHandler] Applying %s change to %s: '%s'",
                field_name,
                file_item.filename,
                new_value,
            )

            # Get the preferred field standard for this file
            field_standard = self._get_preferred_field_standard(file_item, field_name)
            if not field_standard:
                logger.warning(
                    "[EventHandler] No field standard found for %s in %s",
                    field_name,
                    file_item.filename,
                )
                continue

            # Apply the change through metadata tree view
            metadata_tree_view.apply_field_change_to_file(
                file_item.full_path, field_standard, new_value
            )

        logger.info(
            "[EventHandler] Applied %s changes to %d files",
            field_name,
            len(files_to_modify),
        )

    def _get_preferred_field_standard(self, file_item: FileItem, field_name: str) -> str | None:
        """Get the preferred metadata standard for a field based on file type and existing metadata.

        Args:
            file_item: FileItem object
            field_name: Name of the metadata field

        Returns:
            str: Preferred field standard name (e.g., "XMP:Title") or None if not supported

        """
        try:
            cache_entry = self.parent_window.metadata_cache.get_entry(file_item.full_path)
            if not cache_entry or not hasattr(cache_entry, "data"):
                return None

            # Priority order (exiftool's preference: XMP > IPTC > EXIF)
            field_priorities = {
                "Title": ["XMP:Title", "IPTC:Headline", "EXIF:ImageDescription", "XMP:Description"],
                "Artist": ["XMP:Creator", "IPTC:By-line", "EXIF:Artist", "XMP:Author"],
                "Author": ["XMP:Creator", "IPTC:By-line", "EXIF:Artist", "XMP:Author"],
                "Copyright": [
                    "XMP:Rights",
                    "IPTC:CopyrightNotice",
                    "EXIF:Copyright",
                    "XMP:UsageTerms",
                ],
                "Description": [
                    "XMP:Description",
                    "IPTC:Caption-Abstract",
                    "EXIF:ImageDescription",
                ],
                "Keywords": ["XMP:Keywords", "IPTC:Keywords", "XMP:Subject"],
                "Rotation": [
                    "EXIF:Orientation",  # Images priority
                    "QuickTime:Rotation",  # Videos priority
                    "Rotation",  # Generic fallback
                    "CameraOrientation",  # Alternative
                ],
            }

            priorities = field_priorities.get(field_name, [])
            if not priorities:
                return None

            metadata = cache_entry.data

            # Check if any priority field already exists (prefer existing)
            for standard in priorities:
                if standard in metadata:
                    logger.debug(
                        "[FieldStandard] Using existing %s for %s in %s",
                        standard,
                        field_name,
                        file_item.filename,
                    )
                    return standard

            # No existing field, return the highest priority standard that file type supports
            checker = get_field_compatibility_checker(self.parent_window.metadata_cache)
            file_type_support = checker.get_file_type_field_support(file_item, metadata)
            if field_name in file_type_support:
                # Use the first (highest priority) standard
                logger.debug(
                    "[FieldStandard] Using new %s for %s in %s",
                    priorities[0],
                    field_name,
                    file_item.filename,
                )
                return priorities[0]

            return None

        except Exception as e:
            logger.debug(
                "[FieldStandard] Error getting preferred standard for %s: %s", field_name, e
            )
            return None

    # ===== Helper Methods =====

    def _file_has_metadata(self, file_item: FileItem) -> bool:
        """Check if a file has metadata loaded."""
        return has_metadata(file_item.full_path)
