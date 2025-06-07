"""
modules/name_transform_module.py

Author: Michael Economou
Date: 2025-05-25

Applies case and separator transformations to a given base name.
"""

from utils.logger_helper import get_logger
from utils.transform_utils import apply_transform

logger = get_logger(__name__)


class NameTransformModule:
    """
    Logic component (non-UI) for applying case and separator transformations.
    """

    @staticmethod
    def apply_from_data(data: dict, base_name: str) -> str:
        """
        Applies transformation options to the given base name.

        Args:
            data (dict): Contains 'case' and 'separator'
            base_name (str): Input string to transform

        Returns:
            str: Transformed base name
        """
        original = base_name
        case = data.get("case", "original")
        sep = data.get("separator", "as-is")

        logger.debug(f"[NameTransformModule] Input: {base_name} | case: {case} | sep: {sep}")

        if case in ("lower", "UPPER", "Capitalize", "camelCase", "PascalCase", "Title Case"):
            base_name = apply_transform(base_name, case)

        if sep in ("snake_case", "kebab-case", "space"):
            base_name = apply_transform(base_name, sep)

        if not base_name.strip():
            logger.warning(f"[NameTransformModule] Empty output, fallback to original: {original}")
            return original

        return base_name

    @staticmethod
    def is_effective(data: dict) -> bool:
        """
        Returns True if any transformation is active.
        """
        return (
            data.get("case", "original") != "original" or
            data.get("separator", "as-is") != "as-is"
        )
