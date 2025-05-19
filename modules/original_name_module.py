"""
original_name_module.py

Module for applying original name transformations.

Author: Michael Economou
Date: 2025-05-15
"""
import os
from models.file_item import FileItem
from utils.transform_utils import apply_transform
from utils.logger_helper import get_logger

logger = get_logger(__name__)

class OriginalNameModule:
    """
    Logic component (non-UI) for applying original name transformations.
    Used during rename preview and execution.
    """

    @staticmethod
    def apply_from_data(data: dict, file_item: FileItem, index: int = 0, metadata_cache: dict = None) -> str:
        """
        Applies original filename transformation based on provided data.

        Args:
            data (dict): Contains 'case', 'separator', 'greeklish'
            file_item (FileItem): The file being renamed
            index (int): Not used
            metadata_cache (dict): Not used

        Returns:
            str: Transformed filename base
        """
        base_name = os.path.splitext(file_item.filename)[0]
        logger.debug(f"[OriginalNameModule] Starting with: {base_name}")

        if data.get("greeklish"):
            base_name = apply_transform(base_name, "greeklish")

        case = data.get("case", "original")
        sep = data.get("separator", "none")

        # Apply case transformation
        if case in ("lower", "UPPER"):
            base_name = apply_transform(base_name, case)

        # Apply separator transformation
        if sep in ("snake_case", "kebab-case", "space"):
            base_name = apply_transform(base_name, sep)

        if not base_name.strip():
            logger.warning(f"[OriginalNameModule] Empty result fallback to original filename: {file_item.filename}")
            base_name = os.path.splitext(file_item.filename)[0]

        return base_name

    @staticmethod
    def is_effective(data: dict) -> bool:
        return (
            data.get("case", "original") != "original" or
            data.get("separator", "as-is") != "as-is" or
            data.get("greeklish", False)
        )
