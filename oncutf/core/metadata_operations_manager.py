"""Module: metadata_operations_manager.py

Author: Michael Economou
Date: 2025-06-15

Manages metadata-related operations for file metadata export, field editing, and compatibility checks.

Features:
- Metadata export to JSON/Markdown formats
- Metadata field editing (Title, Artist, Copyright, etc.)
- Field compatibility checking for different file types
- File type detection (image, video, audio, document)
- Metadata field standard resolution (XMP, EXIF, IPTC)
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from oncutf.models.file_item import FileItem
from oncutf.utils.filesystem.file_status_helpers import has_metadata
from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QWidget

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

        Args:
            selected_files: List of FileItem objects to check
            field_name: Name of the metadata field to check support for

        Returns:
            bool: True if ALL selected files support the field, False otherwise

        """
        return self._check_metadata_field_compatibility(selected_files, field_name)

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
            not hasattr(self.parent_window, "file_table_model")
            or not self.parent_window.file_table_model
        ):
            return False

        all_files = self.parent_window.file_table_model.get_all_file_items()
        return any(self._file_has_metadata(f) for f in all_files)

    # ===== Metadata Export =====

    def _handle_export_metadata(
        self,
        file_items: list[FileItem],
        scope: str,  # noqa: ARG002
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

    def _execute_export(self, dialog, format_combo, file_items: list[FileItem], scope: str) -> None:
        """Execute the actual export process."""
        from PyQt5.QtWidgets import QFileDialog, QMessageBox

        # Get format
        format_map = {0: "json", 1: "markdown"}
        format_type = format_map.get(format_combo.currentIndex(), "json")

        # Get output directory
        from oncutf.utils.ui.multiscreen_helper import get_existing_directory_on_parent_screen

        output_dir = get_existing_directory_on_parent_screen(
            dialog,
            f"Select Export Directory - {scope.title()} Files",
            "",
            QFileDialog.Options(QFileDialog.ShowDirsOnly),
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
                QMessageBox.information(
                    self.parent_window,
                    "Export Successful",
                    f"Metadata exported successfully to:\n{output_dir}",
                )
            else:
                QMessageBox.warning(
                    self.parent_window,
                    "Export Failed",
                    "Failed to export metadata. Check the logs for details.",
                )

        except Exception as e:
            logger.exception("[EventHandler] Export error: %s", e)
            QMessageBox.critical(
                self.parent_window, "Export Error", f"An error occurred during export:\n{str(e)}"
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
            from oncutf.ui.widgets.metadata_edit_dialog import MetadataEditDialog

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
            from oncutf.utils.ui.dialog_utils import show_error_message

            show_error_message(
                self.parent_window,
                "Error",
                "Metadata editing dialog is not available. Please check the installation.",
            )
        except Exception as e:
            logger.exception("[MetadataEdit] Unexpected error during %s editing: %s", field_name, e)
            from oncutf.utils.ui.dialog_utils import show_error_message

            show_error_message(
                self.parent_window,
                "Error",
                f"An error occurred during {field_name} editing: {str(e)}",
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
            file_type_support = self._get_file_type_field_support(file_item, metadata)
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

    # ===== Field Compatibility Detection =====

    def _check_metadata_field_compatibility(
        self, selected_files: list[FileItem], field_name: str
    ) -> bool:
        """Check if all selected files support a specific metadata field.
        Uses exiftool metadata to determine compatibility.

        Args:
            selected_files: List of FileItem objects to check
            field_name: Name of the metadata field to check support for

        Returns:
            bool: True if ALL selected files support the field, False otherwise

        """
        if not selected_files:
            logger.debug(
                "[FieldCompatibility] No files provided for %s compatibility check",
                field_name,
                extra={"dev_only": True},
            )
            return False

        # Check if all files have metadata loaded
        files_with_metadata = [f for f in selected_files if self._file_has_metadata(f)]
        if len(files_with_metadata) != len(selected_files):
            logger.debug(
                "[FieldCompatibility] Not all files have metadata loaded for %s check",
                field_name,
                extra={"dev_only": True},
            )
            return False

        # Check if all files support the specific field
        supported_count = sum(
            1 for file_item in selected_files if self._file_supports_field(file_item, field_name)
        )

        # Enable only if ALL selected files support the field
        result = supported_count == len(selected_files)
        logger.debug(
            "[FieldCompatibility] %s support: %d/%d files, enabled: %s",
            field_name,
            supported_count,
            len(selected_files),
            result,
            extra={"dev_only": True},
        )
        return result

    def _file_supports_field(self, file_item, field_name: str) -> bool:
        """Check if a file supports a specific metadata field.
        Uses exiftool's field availability information from metadata cache.

        Args:
            file_item: FileItem object to check
            field_name: Name of the metadata field

        Returns:
            bool: True if the file supports the field, False otherwise

        """
        try:
            # Get metadata from cache
            cache_entry = self.parent_window.metadata_cache.get_entry(file_item.full_path)
            if not cache_entry or not hasattr(cache_entry, "data") or not cache_entry.data:
                logger.debug(
                    "[FieldSupport] No metadata cache for %s",
                    file_item.filename,
                    extra={"dev_only": True},
                )
                return False

            # Field support mapping based on exiftool output
            field_support_map = {
                "Title": ["EXIF:ImageDescription", "XMP:Title", "IPTC:Headline", "XMP:Description"],
                "Artist": ["EXIF:Artist", "XMP:Creator", "IPTC:By-line", "XMP:Author"],
                "Author": [
                    "EXIF:Artist",
                    "XMP:Creator",
                    "IPTC:By-line",
                    "XMP:Author",
                ],  # Same as Artist
                "Copyright": [
                    "EXIF:Copyright",
                    "XMP:Rights",
                    "IPTC:CopyrightNotice",
                    "XMP:UsageTerms",
                ],
                "Description": [
                    "EXIF:ImageDescription",
                    "XMP:Description",
                    "IPTC:Caption-Abstract",
                    "XMP:Title",
                ],
                "Keywords": ["XMP:Keywords", "IPTC:Keywords", "XMP:Subject"],
                "Rotation": [
                    "EXIF:Orientation",  # Images (JPEG, TIFF, etc)
                    "QuickTime:Rotation",  # Videos (MP4, MOV, etc)
                    "Rotation",  # Generic/Composite field
                    "CameraOrientation",  # Alternative field
                ],  # Images/Videos with comprehensive format support
            }

            # Get supported fields for this field name
            supported_fields = field_support_map.get(field_name, [])
            if not supported_fields:
                logger.debug(
                    "[FieldSupport] Unknown field name: %s",
                    field_name,
                    extra={"dev_only": True},
                )
                return False

            # Check if any of the supported fields exist in metadata OR could be written
            metadata = cache_entry.data

            # Check existing fields
            for field in supported_fields:
                if field in metadata:
                    logger.debug(
                        "[FieldSupport] %s supports %s via existing %s",
                        file_item.filename,
                        field_name,
                        field,
                    )
                    return True

            # For files with metadata, we can generally write standard fields
            # Check if file type supports the field category
            file_type_support = self._get_file_type_field_support(file_item, metadata)

            supports_field = field_name in file_type_support
            if supports_field:
                logger.debug(
                    "[FieldSupport] %s supports %s via file type compatibility",
                    file_item.filename,
                    field_name,
                )
            else:
                logger.debug(
                    "[FieldSupport] %s does not support %s",
                    file_item.filename,
                    field_name,
                )

            return supports_field

        except Exception as e:
            logger.debug(
                "[FieldSupport] Error checking field support for %s: %s",
                getattr(file_item, "filename", "unknown"),
                e,
            )
            return False

    # ===== File Type Detection =====

    def _get_file_type_field_support(self, file_item, metadata: dict[str, Any]) -> set[str]:
        """Determine which metadata fields a file type supports based on its metadata.

        Args:
            file_item: FileItem object
            metadata: Metadata dictionary from exiftool

        Returns:
            set: Set of supported field names

        """
        try:
            # Basic fields that most files with metadata support
            basic_fields = {"Title", "Description", "Keywords"}

            # Check for image/video specific fields
            image_video_fields = {"Artist", "Author", "Copyright", "Rotation"}

            # Determine file type from metadata or extension
            is_image = self._is_image_file(file_item, metadata)
            is_video = self._is_video_file(file_item, metadata)
            is_audio = self._is_audio_file(file_item, metadata)
            is_document = self._is_document_file(file_item, metadata)

            supported_fields = basic_fields.copy()

            if is_image or is_video:
                # Images and videos support creative fields and rotation
                supported_fields.update(image_video_fields)
            elif is_audio:
                # Audio files support creative fields but not rotation
                supported_fields.update({"Artist", "Author", "Copyright"})
            elif is_document:
                # Documents support author and copyright but not rotation
                supported_fields.update({"Author", "Copyright"})

            return supported_fields

        except Exception as e:
            logger.debug("[FileTypeSupport] Error determining file type support: %s", e)
            # Return basic fields as fallback
            return {"Title", "Description", "Keywords"}

    def _is_image_file(self, file_item, metadata: dict[str, Any]) -> bool:
        """Check if file is an image based on metadata and extension."""
        # Check metadata for image indicators
        if any(key.startswith(("EXIF:", "JFIF:", "PNG:", "GIF:")) for key in metadata):
            return True

        # Check file extension as fallback
        if hasattr(file_item, "filename"):
            ext = file_item.filename.lower().split(".")[-1] if "." in file_item.filename else ""
            return ext in {
                "jpg",
                "jpeg",
                "png",
                "gif",
                "bmp",
                "tiff",
                "tif",
                "webp",
                "heic",
                "raw",
                "cr2",
                "nef",
                "arw",
            }

        return False

    def _is_video_file(self, file_item, metadata: dict[str, Any]) -> bool:
        """Check if file is a video based on metadata and extension."""
        # Check metadata for video indicators
        if any(key.startswith(("QuickTime:", "Matroska:", "RIFF:", "MPEG:")) for key in metadata):
            return True

        # Check file extension as fallback
        if hasattr(file_item, "filename"):
            ext = file_item.filename.lower().split(".")[-1] if "." in file_item.filename else ""
            return ext in {
                "mp4",
                "avi",
                "mkv",
                "mov",
                "wmv",
                "flv",
                "webm",
                "m4v",
                "3gp",
                "mpg",
                "mpeg",
            }

        return False

    def _is_audio_file(self, file_item, metadata: dict[str, Any]) -> bool:
        """Check if file is an audio file based on metadata and extension."""
        # Check metadata for audio indicators
        if any(key.startswith(("ID3:", "FLAC:", "Vorbis:", "APE:")) for key in metadata):
            return True

        # Check file extension as fallback
        if hasattr(file_item, "filename"):
            ext = file_item.filename.lower().split(".")[-1] if "." in file_item.filename else ""
            return ext in {"mp3", "flac", "wav", "ogg", "aac", "m4a", "wma", "opus"}

        return False

    def _is_document_file(self, file_item, metadata: dict[str, Any]) -> bool:
        """Check if file is a document based on metadata and extension."""
        # Check metadata for document indicators
        if any(key.startswith(("PDF:", "XMP-pdf:", "XMP-x:")) for key in metadata):
            return True

        # Check file extension as fallback
        if hasattr(file_item, "filename"):
            ext = file_item.filename.lower().split(".")[-1] if "." in file_item.filename else ""
            return ext in {"pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "odt", "ods", "odp"}

        return False

    # ===== Helper Methods =====

    def _file_has_metadata(self, file_item) -> bool:
        """Check if a file has metadata loaded."""
        return has_metadata(file_item.full_path)
