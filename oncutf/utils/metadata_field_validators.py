"""Module: metadata_field_validators.py

Author: Michael Economou
Date: 2025-06-20

metadata_field_validators.py
Validation system for metadata field editing.
Provides validation rules and error messages for different metadata field types.
"""


def _default_validator(_value):
    """Default validator for unknown fields: reject them."""
    # Return (is_valid: bool, error_message_or_None)
    # Ensure test expectation: mention "validator" in the message
    return (False, "No validator available for this field (validator missing)")


class MetadataFieldValidator:
    """Validation rules for different metadata fields.

    Provides static methods for validating various metadata field types
    with appropriate error messages and length limits.
    """

    # Invalid characters for filename-safe fields
    INVALID_FILENAME_CHARS = '<>:"/\\|?*'

    # Maximum lengths for different field types
    MAX_TITLE_LENGTH = 255
    MAX_ARTIST_LENGTH = 100
    MAX_COPYRIGHT_LENGTH = 200
    MAX_DESCRIPTION_LENGTH = 2000
    MAX_KEYWORD_LENGTH = 30
    MAX_KEYWORDS_COUNT = 50

    @staticmethod
    def validate_title(value: str) -> tuple[bool, str]:
        """Validate title field.

        Rules:
        - Cannot be empty (after stripping)
        - Maximum 255 characters
        - No invalid filename characters

        Args:
            value: Title string to validate

        Returns:
            Tuple of (is_valid, error_message)

        """
        if not isinstance(value, str):
            return False, "Title must be a string"

        stripped_value = value.strip()

        if not stripped_value:
            return False, "Title cannot be empty"

        if len(stripped_value) > MetadataFieldValidator.MAX_TITLE_LENGTH:
            return (
                False,
                f"Title is too long (maximum {MetadataFieldValidator.MAX_TITLE_LENGTH} characters)",
            )

        # Check for invalid filename characters
        invalid_chars_found = [
            char for char in MetadataFieldValidator.INVALID_FILENAME_CHARS if char in stripped_value
        ]
        if invalid_chars_found:
            return False, f"Title contains invalid characters: {''.join(invalid_chars_found)}"

        return True, ""

    @staticmethod
    def validate_artist(value: str) -> tuple[bool, str]:
        """Validate artist/author field.

        Rules:
        - Can be empty
        - Maximum 100 characters
        - No special restrictions on characters

        Args:
            value: Artist string to validate

        Returns:
            Tuple of (is_valid, error_message)

        """
        if not isinstance(value, str):
            return False, "Artist must be a string"

        stripped_value = value.strip()

        # Artist can be empty
        if not stripped_value:
            return True, ""

        if len(stripped_value) > MetadataFieldValidator.MAX_ARTIST_LENGTH:
            return (
                False,
                f"Artist name is too long (maximum {MetadataFieldValidator.MAX_ARTIST_LENGTH} characters)",
            )

        return True, ""

    @staticmethod
    def validate_copyright(value: str) -> tuple[bool, str]:
        """Validate copyright field.

        Rules:
        - Can be empty
        - Maximum 200 characters
        - Should follow standard copyright format (optional validation)

        Args:
            value: Copyright string to validate

        Returns:
            Tuple of (is_valid, error_message)

        """
        if not isinstance(value, str):
            return False, "Copyright must be a string"

        stripped_value = value.strip()

        # Copyright can be empty
        if not stripped_value:
            return True, ""

        if len(stripped_value) > MetadataFieldValidator.MAX_COPYRIGHT_LENGTH:
            return (
                False,
                f"Copyright is too long (maximum {MetadataFieldValidator.MAX_COPYRIGHT_LENGTH} characters)",
            )

        return True, ""

    @staticmethod
    def validate_description(value: str) -> tuple[bool, str]:
        """Validate description field.

        Rules:
        - Can be empty
        - Maximum 2000 characters (multiline support)
        - No special character restrictions

        Args:
            value: Description string to validate

        Returns:
            Tuple of (is_valid, error_message)

        """
        if not isinstance(value, str):
            return False, "Description must be a string"

        stripped_value = value.strip()

        # Description can be empty
        if not stripped_value:
            return True, ""

        if len(stripped_value) > MetadataFieldValidator.MAX_DESCRIPTION_LENGTH:
            return (
                False,
                f"Description is too long (maximum {MetadataFieldValidator.MAX_DESCRIPTION_LENGTH} characters)",
            )

        return True, ""

    @staticmethod
    def validate_keywords(value: str) -> tuple[bool, str]:
        """Validate keywords field (comma-separated).

        Rules:
        - Can be empty
        - Maximum 50 keywords
        - Each keyword maximum 30 characters
        - Comma-separated format
        - Automatic trimming of whitespace

        Args:
            value: Keywords string to validate (comma-separated)

        Returns:
            Tuple of (is_valid, error_message)

        """
        if not isinstance(value, str):
            return False, "Keywords must be a string"

        stripped_value = value.strip()

        # Keywords can be empty
        if not stripped_value:
            return True, ""

        # Split by comma and clean up
        keywords = [keyword.strip() for keyword in stripped_value.split(",")]

        # Remove empty keywords
        keywords = [keyword for keyword in keywords if keyword]

        if len(keywords) > MetadataFieldValidator.MAX_KEYWORDS_COUNT:
            return False, f"Too many keywords (maximum {MetadataFieldValidator.MAX_KEYWORDS_COUNT})"

        # Check individual keyword length
        for keyword in keywords:
            if len(keyword) > MetadataFieldValidator.MAX_KEYWORD_LENGTH:
                return (
                    False,
                    f"Keyword '{keyword}' is too long (maximum {MetadataFieldValidator.MAX_KEYWORD_LENGTH} characters)",
                )

        return True, ""

    @staticmethod
    def validate_rotation(value: str) -> tuple[bool, str]:
        """Validate rotation field.

        Rules:
        - Can be empty (defaults to 0)
        - Must be one of the standard rotation values: 0, 90, 180, 270
        - Accepts values with or without degree symbol

        Args:
            value: Rotation string to validate

        Returns:
            Tuple of (is_valid, error_message)

        """
        if not isinstance(value, str):
            return False, "Rotation must be a string"

        stripped_value = value.strip()

        # Rotation can be empty (defaults to 0)
        if not stripped_value:
            return True, ""

        # Clean the value - remove degree symbol and extra spaces
        clean_value = stripped_value.replace("°", "").replace(" ", "")

        # Valid rotation values
        valid_rotations = {"0", "90", "180", "270"}

        # Check if it's one of the valid rotation values
        if clean_value in valid_rotations:
            return True, ""

        # Try to parse as number and check if it's close to a valid rotation
        try:
            rotation_num = float(clean_value)
            # Normalize to 0-359 range
            normalized = rotation_num % 360

            # Check if it's close to a standard rotation (within 1 degree)
            for valid_rot in valid_rotations:
                if abs(normalized - float(valid_rot)) < 1:
                    return (
                        False,
                        f"Rotation must be exactly {valid_rot}°. Use one of: 0°, 90°, 180°, 270°",
                    )

            return False, "Rotation must be one of: 0°, 90°, 180°, 270°"

        except ValueError:
            return False, "Rotation must be a valid number (0, 90, 180, or 270)"

    @staticmethod
    def parse_keywords(value: str) -> list[str]:
        """Parse and clean keywords string into a list.

        Args:
            value: Keywords string (comma-separated)

        Returns:
            List of cleaned keyword strings

        """
        if not isinstance(value, str):
            return []

        stripped_value = value.strip()
        if not stripped_value:
            return []

        # Split by comma, strip whitespace, and remove empty items
        keywords = [keyword.strip() for keyword in stripped_value.split(",")]
        return [keyword for keyword in keywords if keyword]

    @staticmethod
    def format_keywords(keywords: list[str]) -> str:
        """Format a list of keywords into a comma-separated string.

        Args:
            keywords: List of keyword strings

        Returns:
            Comma-separated keywords string

        """
        if not keywords:
            return ""

        # Clean and filter keywords
        clean_keywords = [keyword.strip() for keyword in keywords if keyword and keyword.strip()]
        return ", ".join(clean_keywords)

    @staticmethod
    def get_field_validator(field_name: str):
        """Get the appropriate validator function for a field name.

        Args:
            field_name: Name of the field to validate

        Returns:
            Validator function or None if not found

        """
        validators = {
            "Title": MetadataFieldValidator.validate_title,
            "Artist": MetadataFieldValidator.validate_artist,
            "Author": MetadataFieldValidator.validate_artist,  # Same validation as Artist
            "Copyright": MetadataFieldValidator.validate_copyright,
            "Description": MetadataFieldValidator.validate_description,
            "Keywords": MetadataFieldValidator.validate_keywords,
            "Rotation": MetadataFieldValidator.validate_rotation,
        }

        return validators.get(field_name)

    @staticmethod
    def validate_field(field_name: str, value):
        """Validate a field by name. Always returns (bool, error_message_or_None).
        Uses _default_validator when no callable is found.

        Args:
            field_name: Name of the field
            value: Value to validate

        Returns:
            Tuple of (is_valid, error_message)

        """
        # Lookup validator at runtime to avoid forward-reference issues
        validator = MetadataFieldValidator.get_field_validator(field_name)
        if validator is None or not callable(validator):
            validator = _default_validator
        # Some validators might return just bool or (bool, str). Normalize.
        result = validator(value)
        if isinstance(result, tuple):
            return result
        if isinstance(result, bool):
            return (result, None if result else "Invalid value")
        # Any other return type -> interpret falsy/truthy
        return (bool(result), None if result else "Invalid value")
