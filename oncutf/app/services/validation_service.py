"""Validation service for metadata fields.

Author: Michael Economou
Date: 2026-01-24

This service provides a clean interface to domain validation logic,
isolating UI widgets from direct domain dependencies.

Architecture:
- UI widgets → ValidationService → Domain validators
- No direct imports of domain validators in UI layer
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from collections.abc import Callable

from oncutf.domain.validation import MetadataFieldValidator


class ValidationService:
    """Service for validating metadata field values.

    This service wraps domain validators and provides a clean
    interface for UI widgets to validate user input without
    directly importing domain classes.

    Usage:
        service = ValidationService()
        is_valid, error = service.validate_field("Title", "My Title")
    """

    # Map field names to validator methods
    _VALIDATOR_MAP: ClassVar[dict[str, Callable[[Any], tuple[bool, str]]]] = {
        "Title": MetadataFieldValidator.validate_title,
        "Artist": MetadataFieldValidator.validate_artist,
        "Copyright": MetadataFieldValidator.validate_copyright,
        "Description": MetadataFieldValidator.validate_description,
        "Keywords": MetadataFieldValidator.validate_keywords,
        "Rotation": MetadataFieldValidator.validate_rotation,
    }

    def validate_field(self, field_name: str, value: Any) -> tuple[bool, str]:
        """Validate a metadata field value.

        Args:
            field_name: Name of the metadata field
            value: Value to validate

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if validation passed
            - error_message: Empty string if valid, error description if invalid

        """
        # Get validator for this field
        validator = self._VALIDATOR_MAP.get(field_name)

        if validator is None:
            # No specific validator - use default that accepts all
            return (True, "")

        # Execute validation
        result: tuple[bool, str] = validator(value)
        return result

    def get_max_length(self, field_name: str) -> int | None:
        """Get maximum allowed length for a field.

        Args:
            field_name: Name of the metadata field

        Returns:
            Maximum length in characters, or None if no limit

        """
        length_map = {
            "Title": MetadataFieldValidator.MAX_TITLE_LENGTH,
            "Artist": MetadataFieldValidator.MAX_ARTIST_LENGTH,
            "Copyright": MetadataFieldValidator.MAX_COPYRIGHT_LENGTH,
            "Description": MetadataFieldValidator.MAX_DESCRIPTION_LENGTH,
            "Keywords": MetadataFieldValidator.MAX_KEYWORD_LENGTH,
        }
        return length_map.get(field_name)

    def get_blocked_characters(self, field_name: str) -> set[str]:
        """Get set of characters that should be blocked for a field.

        Args:
            field_name: Name of the metadata field

        Returns:
            Set of characters that are not allowed in this field

        """
        # Only Title field blocks filename-unsafe characters
        if field_name == "Title":
            return set(MetadataFieldValidator.INVALID_FILENAME_CHARS)
        return set()

    def get_field_requirements(self, field_name: str) -> dict[str, Any]:
        """Get validation requirements for a field.

        Args:
            field_name: Name of the metadata field

        Returns:
            Dict with validation requirements:
            - max_length: Maximum character length
            - required: Whether field is required
            - format: Expected format (if applicable)

        """
        requirements: dict[str, Any] = {
            "max_length": self.get_max_length(field_name),
            "required": False,  # Most fields are optional
            "format": None,
        }

        # Special requirements for specific fields
        if field_name == "Date":
            requirements["format"] = "YYYY:MM:DD HH:MM:SS or YYYY-MM-DD"

        if field_name == "Rating":
            requirements["format"] = "Integer 0-5"

        return requirements


# Singleton instance
_validation_service: ValidationService | None = None


def get_validation_service() -> ValidationService:
    """Get the global ValidationService instance.

    Returns:
        Singleton ValidationService instance

    """
    global _validation_service
    if _validation_service is None:
        _validation_service = ValidationService()
    return _validation_service
