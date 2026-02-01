"""Module: field_compatibility.py.

Author: Michael Economou
Date: 2026-01-03

Field compatibility checking for metadata operations.
Determines which metadata fields are supported by different file types.

Features:
- File type detection (image, video, audio, document)
- Field support mapping for different standards (XMP, EXIF, IPTC)
- Compatibility checking for batch operations
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from oncutf.utils.filesystem.file_status_helpers import has_metadata
from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.models.file_item import FileItem

logger = get_cached_logger(__name__)


# Field support mapping based on exiftool output
FIELD_SUPPORT_MAP: dict[str, list[str]] = {
    "Title": ["EXIF:ImageDescription", "XMP:Title", "IPTC:Headline", "XMP:Description"],
    "Artist": ["EXIF:Artist", "XMP:Creator", "IPTC:By-line", "XMP:Author"],
    "Author": ["EXIF:Artist", "XMP:Creator", "IPTC:By-line", "XMP:Author"],
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
        "EXIF:Orientation",
        "QuickTime:Rotation",
        "Rotation",
        "CameraOrientation",
    ],
}

# File extension sets
IMAGE_EXTENSIONS = {
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

VIDEO_EXTENSIONS = {
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

AUDIO_EXTENSIONS = {
    "mp3",
    "flac",
    "wav",
    "ogg",
    "aac",
    "m4a",
    "wma",
    "opus",
}

DOCUMENT_EXTENSIONS = {
    "pdf",
    "doc",
    "docx",
    "xls",
    "xlsx",
    "ppt",
    "pptx",
    "odt",
    "ods",
    "odp",
}


class FieldCompatibilityChecker:
    """Checks field compatibility for metadata operations.

    Determines which metadata fields are supported by different file types
    based on their metadata content and file extensions.
    """

    def __init__(self, metadata_cache: Any = None) -> None:
        """Initialize the compatibility checker.

        Args:
            metadata_cache: Reference to metadata cache for checking loaded metadata

        """
        self._metadata_cache = metadata_cache

    def set_metadata_cache(self, cache: Any) -> None:
        """Set the metadata cache reference.

        Args:
            cache: Metadata cache instance

        """
        self._metadata_cache = cache

    def check_field_compatibility(self, selected_files: list[FileItem], field_name: str) -> bool:
        """Check if all selected files support a specific metadata field.

        Args:
            selected_files: List of FileItem objects to check
            field_name: Name of the metadata field to check

        Returns:
            bool: True if ALL selected files support the field

        """
        if not selected_files:
            logger.debug(
                "[FieldCompatibility] No files provided for %s check",
                field_name,
                extra={"dev_only": True},
            )
            return False

        # Check if all files have metadata loaded
        files_with_metadata = [f for f in selected_files if self._file_has_metadata(f)]
        if len(files_with_metadata) != len(selected_files):
            logger.debug(
                "[FieldCompatibility] Not all files have metadata for %s",
                field_name,
                extra={"dev_only": True},
            )
            return False

        # Check if all files support the specific field
        supported_count = sum(
            1 for file_item in selected_files if self.file_supports_field(file_item, field_name)
        )

        result = supported_count == len(selected_files)
        logger.debug(
            "[FieldCompatibility] %s: %d/%d files, enabled: %s",
            field_name,
            supported_count,
            len(selected_files),
            result,
            extra={"dev_only": True},
        )
        return result

    def file_supports_field(self, file_item: FileItem, field_name: str) -> bool:
        """Check if a file supports a specific metadata field.

        Args:
            file_item: FileItem object to check
            field_name: Name of the metadata field

        Returns:
            bool: True if the file supports the field

        """
        try:
            if not self._metadata_cache:
                return False

            cache_entry = self._metadata_cache.get_entry(file_item.full_path)
            if not cache_entry or not hasattr(cache_entry, "data") or not cache_entry.data:
                logger.debug(
                    "[FieldSupport] No cache for %s",
                    file_item.filename,
                    extra={"dev_only": True},
                )
                return False

            supported_fields = FIELD_SUPPORT_MAP.get(field_name, [])
            if not supported_fields:
                logger.debug(
                    "[FieldSupport] Unknown field: %s",
                    field_name,
                    extra={"dev_only": True},
                )
                return False

            metadata = cache_entry.data

        except Exception as e:
            logger.debug(
                "[FieldSupport] Error checking %s: %s",
                getattr(file_item, "filename", "unknown"),
                e,
            )
            return False
        else:
            result = False
            # Check if any supported field exists
            for field in supported_fields:
                if field in metadata:
                    result = True
                    break

            if not result:
                # Check file type compatibility
                file_type_support = self.get_file_type_field_support(file_item, metadata)
                result = field_name in file_type_support

            return result

    def get_file_type_field_support(
        self, file_item: FileItem, metadata: dict[str, Any]
    ) -> set[str]:
        """Determine which metadata fields a file type supports.

        Args:
            file_item: FileItem object
            metadata: Metadata dictionary from exiftool

        Returns:
            Set of supported field names

        """
        try:
            basic_fields = {"Title", "Description", "Keywords"}
            image_video_fields = {"Artist", "Author", "Copyright", "Rotation"}

            is_image = self.is_image_file(file_item, metadata)
            is_video = self.is_video_file(file_item, metadata)
            is_audio = self.is_audio_file(file_item, metadata)
            is_document = self.is_document_file(file_item, metadata)

            supported_fields = basic_fields.copy()

            if is_image or is_video:
                supported_fields.update(image_video_fields)
            elif is_audio:
                supported_fields.update({"Artist", "Author", "Copyright"})
            elif is_document:
                supported_fields.update({"Author", "Copyright"})

        except Exception as e:
            logger.debug("[FileTypeSupport] Error: %s", e)
            return {"Title", "Description", "Keywords"}
        else:
            return supported_fields

    def is_image_file(self, file_item: FileItem, metadata: dict[str, Any]) -> bool:
        """Check if file is an image based on metadata and extension."""
        if any(key.startswith(("EXIF:", "JFIF:", "PNG:", "GIF:")) for key in metadata):
            return True

        if hasattr(file_item, "filename"):
            ext = self._get_extension(file_item.filename)
            return ext in IMAGE_EXTENSIONS

        return False

    def is_video_file(self, file_item: FileItem, metadata: dict[str, Any]) -> bool:
        """Check if file is a video based on metadata and extension."""
        if any(key.startswith(("QuickTime:", "Matroska:", "RIFF:", "MPEG:")) for key in metadata):
            return True

        if hasattr(file_item, "filename"):
            ext = self._get_extension(file_item.filename)
            return ext in VIDEO_EXTENSIONS

        return False

    def is_audio_file(self, file_item: FileItem, metadata: dict[str, Any]) -> bool:
        """Check if file is an audio file based on metadata and extension."""
        if any(key.startswith(("ID3:", "FLAC:", "Vorbis:", "APE:")) for key in metadata):
            return True

        if hasattr(file_item, "filename"):
            ext = self._get_extension(file_item.filename)
            return ext in AUDIO_EXTENSIONS

        return False

    def is_document_file(self, file_item: FileItem, metadata: dict[str, Any]) -> bool:
        """Check if file is a document based on metadata and extension."""
        if any(key.startswith(("PDF:", "XMP-pdf:", "XMP-x:")) for key in metadata):
            return True

        if hasattr(file_item, "filename"):
            ext = self._get_extension(file_item.filename)
            return ext in DOCUMENT_EXTENSIONS

        return False

    def _get_extension(self, filename: str) -> str:
        """Get lowercase file extension."""
        return filename.lower().split(".")[-1] if "." in filename else ""

    def _file_has_metadata(self, file_item: FileItem) -> bool:
        """Check if a file has metadata loaded."""
        return has_metadata(file_item.full_path)


# Module-level singleton instance
_field_compatibility_checker: FieldCompatibilityChecker | None = None


def get_field_compatibility_checker(
    metadata_cache: Any = None,
) -> FieldCompatibilityChecker:
    """Get or create the field compatibility checker singleton.

    Args:
        metadata_cache: Optional metadata cache to set

    Returns:
        FieldCompatibilityChecker instance

    """
    global _field_compatibility_checker
    if _field_compatibility_checker is None:
        _field_compatibility_checker = FieldCompatibilityChecker(metadata_cache)
    elif metadata_cache is not None:
        _field_compatibility_checker.set_metadata_cache(metadata_cache)
    return _field_compatibility_checker
