"""Field type detection for metadata editing.

This module provides utilities for detecting and normalizing
metadata field types (date/time, editable fields, etc.).

Author: Michael Economou
Date: 2026-01-01
"""

from typing import ClassVar

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class FieldDetector:
    """Detects and normalizes metadata field types.

    Provides methods to determine if fields are:
    - Date/time fields
    - Editable fields
    - And to normalize field names
    """

    # Date/time keywords for field detection
    DATE_KEYWORDS: ClassVar[frozenset[str]] = frozenset(
        [
            "date",
            "time",
            "datetime",
            "timestamp",
            "created",
            "modified",
            "accessed",
            "filemodifydate",
            "filecreatedate",
            "createdate",
            "modifydate",
            "datetimeoriginal",
            "datetimedigitized",
        ]
    )

    # Editable metadata fields (case-insensitive)
    EDITABLE_FIELDS = frozenset(
        [
            # Rotation/Orientation
            "rotation",
            "orientation",
            "exif:orientation",
            # Dates
            "datetimeoriginal",
            "createdate",
            "modifydate",
            "exif:datetimeoriginal",
            "exif:createdate",
            "exif:modifydate",
            "file:filemodifydate",
            # XMP fields
            "xmp:creator",
            "xmp:title",
            "xmp:description",
            "creator",
            "title",
            "description",
        ]
    )

    # Mapping of field variants to canonical names
    FIELD_MAPPING: ClassVar[dict[str, str]] = {
        # Rotation variants
        "rotation": "Rotation",
        "orientation": "Rotation",
        "exif:orientation": "Rotation",
        "exif/orientation": "Rotation",
        # Date variants
        "datetimeoriginal": "EXIF:DateTimeOriginal",
        "exif:datetimeoriginal": "EXIF:DateTimeOriginal",
        "exif/datetimeoriginal": "EXIF:DateTimeOriginal",
        "createdate": "EXIF:CreateDate",
        "exif:createdate": "EXIF:CreateDate",
        "exif/createdate": "EXIF:CreateDate",
        "modifydate": "EXIF:ModifyDate",
        "exif:modifydate": "EXIF:ModifyDate",
        "exif/modifydate": "EXIF:ModifyDate",
        "file:filemodifydate": "File:FileModifyDate",
        "file/filemodifydate": "File:FileModifyDate",
        # XMP variants
        "creator": "XMP:Creator",
        "xmp:creator": "XMP:Creator",
        "xmp/creator": "XMP:Creator",
        "title": "XMP:Title",
        "xmp:title": "XMP:Title",
        "xmp/title": "XMP:Title",
        "description": "XMP:Description",
        "xmp:description": "XMP:Description",
        "xmp/description": "XMP:Description",
    }

    def is_date_time_field(self, key_path: str) -> bool:
        """Check if a metadata field is a date/time field.

        Args:
            key_path: Metadata key path

        Returns:
            bool: True if field is date/time related

        """
        key_lower = key_path.lower()
        return any(keyword in key_lower for keyword in self.DATE_KEYWORDS)

    def get_date_type_from_field(self, key_path: str) -> str:
        """Determine date type (created/modified) from field name.

        Args:
            key_path: Metadata key path

        Returns:
            str: "created" or "modified"

        """
        key_lower = key_path.lower()

        # Check for creation date patterns
        if any(keyword in key_lower for keyword in ["create", "dateoriginal", "digitized"]):
            return "created"

        # Check for modification date patterns
        if any(keyword in key_lower for keyword in ["modify", "modified", "change", "changed"]):
            return "modified"

        # Default to modified for generic date/time fields
        return "modified"

    def is_editable_metadata_field(self, key_path: str) -> bool:
        """Check if a metadata field can be edited directly.

        Standard metadata fields that can be edited:
        - EXIF:Orientation / Rotation
        - EXIF:DateTimeOriginal / Create Date
        - EXIF:ModifyDate / Modify Date
        - XMP:Creator / Author
        - XMP:Title / Title
        - XMP:Description / Description

        Args:
            key_path: Metadata key path

        Returns:
            bool: True if field is editable

        """
        # Normalize key path for comparison
        key_lower = key_path.lower().strip()

        # If it's a grouped key path (e.g., "File Info (12 fields)/Rotation"),
        # extract just the field name after the last separator (/ or \)
        # Handle both Unix (/) and Windows (\) path separators
        if "/" in key_lower or "\\" in key_lower:
            # Replace backslashes with forward slashes for consistency
            key_normalized = key_lower.replace("\\", "/")
            key_lower = key_normalized.split("/")[-1].strip()

        return key_lower in self.EDITABLE_FIELDS

    def normalize_metadata_field_name(self, key_path: str) -> str:
        """Normalize metadata field name for consistency.

        Maps various field name variants to their canonical form.

        Args:
            key_path: Metadata key path

        Returns:
            str: Normalized key path

        """
        key_lower = key_path.lower().strip()

        # Check for direct mapping
        if key_lower in self.FIELD_MAPPING:
            return self.FIELD_MAPPING[key_lower]

        # Return original if no mapping found
        return key_path


# Singleton instance for convenience
_field_detector = FieldDetector()


def is_date_time_field(key_path: str) -> bool:
    """Check if a metadata field is a date/time field."""
    return _field_detector.is_date_time_field(key_path)


def get_date_type_from_field(key_path: str) -> str:
    """Determine date type (created/modified) from field name."""
    return _field_detector.get_date_type_from_field(key_path)


def is_editable_metadata_field(key_path: str) -> bool:
    """Check if a metadata field can be edited directly."""
    return _field_detector.is_editable_metadata_field(key_path)


def normalize_metadata_field_name(key_path: str) -> str:
    """Normalize metadata field name for consistency."""
    return _field_detector.normalize_metadata_field_name(key_path)
