"""Pure specified text logic (Qt-free).

Author: Michael Economou
Date: 2026-02-03
"""

from typing import Any

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class SpecifiedTextLogic:
    """Pure specified text logic without Qt dependencies."""

    @staticmethod
    def apply_from_data(
        data: dict[str, Any],
        _file_item: Any,
        _index: int = 0,
        _metadata_cache: dict[str, Any] | None = None,
    ) -> str:
        """Generate custom text from module data.

        Args:
            data: Module configuration with 'text' key
            _file_item: FileItem being renamed (unused)
            _index: Index in file list (unused)
            _metadata_cache: Optional metadata cache (unused)

        Returns:
            The custom text string, or INVALID_FILENAME_MARKER if invalid

        """
        logger.debug(
            "[SpecifiedTextLogic] apply_from_data called with data: %s",
            data,
            extra={"dev_only": True},
        )
        text = data.get("text", "")

        if not text:
            logger.debug(
                "[SpecifiedTextLogic] Empty text input, returning empty string.",
                extra={"dev_only": True},
            )
            return ""

        # Validate using new system
        from oncutf.utils.naming.filename_validator import validate_filename_part

        is_valid, _validated_text = validate_filename_part(text)
        if not is_valid:
            logger.warning("[SpecifiedTextLogic] Invalid filename text: '%s'", text)
            from oncutf.config import INVALID_FILENAME_MARKER

            return INVALID_FILENAME_MARKER

        # Return the text exactly as entered by the user
        return text

    @staticmethod
    def is_effective_data(data: dict[str, Any]) -> bool:
        """Check if specified text module data is effective.

        Args:
            data: Module configuration with 'text' key

        Returns:
            True if text is non-empty, False otherwise

        """
        return bool(data.get("text", ""))
