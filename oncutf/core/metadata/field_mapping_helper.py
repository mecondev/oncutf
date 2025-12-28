"""metadata_field_mapping_helper.py

Centralized metadata field mapping and conversion helper.
Handles file-type-specific field mapping for read/write operations.

Author: Michael Economou
Date: 2025-11-25
"""

import os

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class MetadataFieldMappingHelper:
    """Centralized helper for metadata field mapping and value conversion.

    Handles:
    - File-type-specific field name mapping for write operations
    - Value conversion and validation for different metadata standards
    - Consistent read/write field mapping across all file formats
    """

    # Define supported file extensions by category
    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".gif"}
    RAW_EXTENSIONS = {".cr2", ".nef", ".arw", ".orf", ".rw2", ".dng"}
    VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".3gp", ".avi", ".mkv", ".wmv"}
    AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg"}

    # Field mapping for write operations (maps generic field -> file-specific field)
    WRITE_FIELD_MAPPING: dict[str, dict[str, str | None]] = {
        # Rotation/Orientation handling
        "Rotation": {
            "image": "EXIF:Orientation",  # JPEG, TIFF use EXIF:Orientation
            "raw": "EXIF:Orientation",  # RAW files use EXIF:Orientation
            "video": "Rotation",  # Video files use generic Rotation
            "audio": None,  # Audio doesn't support rotation
        },
        # Descriptive metadata
        "Title": {
            "image": "EXIF:ImageDescription",  # Images use EXIF:ImageDescription
            "raw": "EXIF:ImageDescription",  # RAW files use EXIF:ImageDescription
            "video": "XMP:Title",  # Videos prefer XMP:Title
            "audio": "TIT2",  # Audio uses ID3 tags
        },
        "Artist": {
            "image": "EXIF:Artist",  # Images use EXIF:Artist
            "raw": "EXIF:Artist",  # RAW files use EXIF:Artist
            "video": "XMP:Creator",  # Videos use XMP:Creator
            "audio": "TPE1",  # Audio uses ID3 TPE1
        },
        "Description": {
            "image": "EXIF:ImageDescription",  # Images use EXIF:ImageDescription
            "raw": "EXIF:ImageDescription",  # RAW files use EXIF:ImageDescription
            "video": "XMP:Description",  # Videos use XMP:Description
            "audio": "COMM",  # Audio uses ID3 COMM
        },
        "Keywords": {
            "image": "IPTC:Keywords",  # Images use IPTC:Keywords
            "raw": "IPTC:Keywords",  # RAW files use IPTC:Keywords
            "video": "XMP:Keywords",  # Videos use XMP:Keywords
            "audio": None,  # Audio doesn't typically support keywords
        },
        "Copyright": {
            "image": "EXIF:Copyright",  # Images use EXIF:Copyright
            "raw": "EXIF:Copyright",  # RAW files use EXIF:Copyright
            "video": "XMP:Rights",  # Videos use XMP:Rights
            "audio": "TCOP",  # Audio uses ID3 TCOP
        },
        # Technical metadata (usually read-only, but some can be modified)
        "ISO": {
            "image": "EXIF:ISO",  # Images use EXIF:ISO
            "raw": "EXIF:ISO",  # RAW files use EXIF:ISO
            "video": None,  # Videos don't typically have ISO
            "audio": None,  # Audio doesn't have ISO
        },
    }

    # Value conversion rules for special cases
    VALUE_CONVERSIONS = {
        "Rotation": {
            "image": {
                # Convert degrees to EXIF orientation text values
                "0": "Horizontal (normal)",
                "90": "Rotate 90 CW",
                "180": "Rotate 180",
                "270": "Rotate 270 CW",
            },
            "raw": {
                # RAW files use same as images
                "0": "Horizontal (normal)",
                "90": "Rotate 90 CW",
                "180": "Rotate 180",
                "270": "Rotate 270 CW",
            },
            "video": {
                # Videos use numeric degrees directly
                "0": "0",
                "90": "90",
                "180": "180",
                "270": "270",
            },
        }
    }

    @classmethod
    def get_file_category(cls, file_path: str) -> str:
        """Determine the file category based on extension.

        Args:
            file_path: Path to the file

        Returns:
            File category: 'image', 'raw', 'video', 'audio', or 'unknown'

        """
        ext = os.path.splitext(file_path)[1].lower()

        if ext in cls.IMAGE_EXTENSIONS:
            return "image"
        elif ext in cls.RAW_EXTENSIONS:
            return "raw"
        elif ext in cls.VIDEO_EXTENSIONS:
            return "video"
        elif ext in cls.AUDIO_EXTENSIONS:
            return "audio"
        else:
            return "unknown"

    @classmethod
    def get_write_field_name(cls, generic_field: str, file_path: str) -> str | None:
        """Get the appropriate field name for writing metadata to a specific file type.

        Args:
            generic_field: Generic field name (e.g., "Rotation", "Title")
            file_path: Path to the target file

        Returns:
            File-specific field name or None if not supported

        """
        category = cls.get_file_category(file_path)

        if generic_field not in cls.WRITE_FIELD_MAPPING:
            logger.warning("[FieldMapper] Unknown generic field: %s", generic_field)
            return None

        field_mapping = cls.WRITE_FIELD_MAPPING[generic_field]
        specific_field = field_mapping.get(category)

        if specific_field is None:
            logger.debug(
                "[FieldMapper] Field '%s' not supported for %s files",
                generic_field,
                category,
            )
            return None

        logger.debug(
            "[FieldMapper] Mapping %s -> %s for %s file",
            generic_field,
            specific_field,
            category,
        )
        return specific_field

    @classmethod
    def convert_value_for_write(cls, generic_field: str, value: str, file_path: str) -> str:
        """Convert a generic field value to the appropriate format for a specific file type.

        Args:
            generic_field: Generic field name
            value: Generic value
            file_path: Path to the target file

        Returns:
            Converted value appropriate for the file type

        """
        category = cls.get_file_category(file_path)

        # Check if this field has special conversion rules
        if generic_field in cls.VALUE_CONVERSIONS:
            field_conversions = cls.VALUE_CONVERSIONS[generic_field]
            if category in field_conversions:
                category_conversions = field_conversions[category]
                converted_value = category_conversions.get(value, value)

                logger.debug(
                    "[FieldMapper] Converting %s value '%s' -> '%s' for %s",
                    generic_field,
                    value,
                    converted_value,
                    category,
                )
                return converted_value

        # No conversion needed, return as-is
        return value

    @classmethod
    def prepare_metadata_for_write(
        cls, metadata_changes: dict[str, str], file_path: str
    ) -> dict[str, str]:
        """Prepare metadata changes dictionary for writing to a specific file.

        Args:
            metadata_changes: Dictionary of generic field -> value mappings
            file_path: Path to the target file

        Returns:
            Dictionary of file-specific field -> converted value mappings

        """
        prepared_changes = {}
        category = cls.get_file_category(file_path)

        logger.debug(
            "[FieldMapper] Preparing %d metadata changes for %s file",
            len(metadata_changes),
            category,
        )

        for generic_field, value in metadata_changes.items():
            # Get the file-specific field name
            specific_field = cls.get_write_field_name(generic_field, file_path)
            if specific_field is None:
                logger.warning(
                    "[FieldMapper] Skipping unsupported field '%s' for %s file",
                    generic_field,
                    category,
                )
                continue

            # Convert the value if necessary
            converted_value = cls.convert_value_for_write(generic_field, value, file_path)

            prepared_changes[specific_field] = converted_value

        logger.debug("[FieldMapper] Prepared %d field mappings", len(prepared_changes))
        return prepared_changes

    @classmethod
    def get_supported_fields_for_file(cls, file_path: str) -> dict[str, str]:
        """Get all supported metadata fields for a specific file type.

        Args:
            file_path: Path to the file

        Returns:
            Dictionary mapping generic field names to file-specific field names

        """
        category = cls.get_file_category(file_path)
        supported_fields = {}

        for generic_field, field_mapping in cls.WRITE_FIELD_MAPPING.items():
            specific_field = field_mapping.get(category)
            if specific_field is not None:
                supported_fields[generic_field] = specific_field

        return supported_fields
