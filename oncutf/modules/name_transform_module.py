"""Module: name_transform_module.py.

Author: Michael Economou
Date: 2025-05-27

modules/name_transform_module.py
Applies case and separator transformations to a given base name.
"""

from typing import Any

from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.naming.transform_utils import apply_transform

logger = get_cached_logger(__name__)


class NameTransformModule:
    """Logic component (non-UI) for applying case and separator transformations."""

    # Phase 3.1: Module metadata for auto-discovery
    DISPLAY_NAME = "Name Transform"
    UI_ROWS = 2
    DESCRIPTION = "Apply case and separator transformations"
    CATEGORY = "Transform"

    @staticmethod
    def apply_from_data(data: dict[str, Any], base_name: str) -> str:
        """Applies transformation options to the given base name.

        Args:
            data (dict): Contains 'case', 'separator', and 'greeklish'
            base_name (str): Input string to transform

        Returns:
            str: Transformed base name

        """
        original = base_name
        case = data.get("case", "original")
        sep = data.get("separator", "as-is")
        greeklish = data.get("greeklish", False)

        logger.debug(
            "[NameTransformModule] Input: %s | case: %s | sep: %s | greeklish: %s",
            base_name,
            case,
            sep,
            greeklish,
        )

        # Apply Greeklish first (if enabled)
        if greeklish:
            base_name = apply_transform(base_name, "greeklish")
            logger.debug("[NameTransformModule] After Greeklish: %s", base_name)

        # Apply case transformation
        if case in ("lower", "UPPER", "Capitalize", "camelCase", "PascalCase", "Title Case"):
            base_name = apply_transform(base_name, case)

        # Apply separator transformation
        if sep in ("snake_case", "kebab-case", "space"):
            base_name = apply_transform(base_name, sep)

        if not base_name.strip():
            logger.warning("[NameTransformModule] Empty output, fallback to original: %s", original)
            return original

        return base_name

    @staticmethod
    def is_effective_data(data: dict[str, Any]) -> bool:
        """Returns True if any transformation is active."""
        return (
            data.get("case", "original") != "original"
            or data.get("separator", "as-is") != "as-is"
            or data.get("greeklish", False)
        )
