"""Module: original_name_module.py.

Author: Michael Economou
Date: 2025-05-19

original_name_module.py
Module for applying original name transformations.
"""

import os
from typing import Any

from oncutf.models.file_item import FileItem
from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.naming.transform_utils import apply_transform

logger = get_cached_logger(__name__)


class OriginalNameModule:
    """Logic component (non-UI) for applying original name transformations.
    Used during rename preview and execution.
    """

    # Phase 3.1: Module metadata for auto-discovery
    DISPLAY_NAME = "Original Name"
    UI_ROWS = 1
    DESCRIPTION = "Keep original filename with optional transformations"
    CATEGORY = "Text"

    @staticmethod
    def apply_from_data(
        data: dict[str, Any],
        file_item: FileItem,
        _index: int = 0,
        _metadata_cache: dict[str, Any] | None = None,
    ) -> str:
        """Applies original filename with optional Greeklish transformation.
        Case and separator transformations are handled by NameTransformModule.

        Args:
            data (dict): Contains 'greeklish' flag
            file_item (FileItem): The file being renamed
            index (int): Not used
            metadata_cache (dict): Not used

        Returns:
            str: Original filename base with optional Greeklish conversion

        """
        base_name = os.path.splitext(file_item.filename)[0]
        logger.debug("[OriginalNameModule] Starting with: %s", base_name, extra={"dev_only": True})

        # Only apply Greeklish transformation if requested
        if data.get("greeklish"):
            base_name = apply_transform(base_name, "greeklish")
            logger.debug(
                "[OriginalNameModule] After Greeklish: %s",
                base_name,
                extra={"dev_only": True},
            )

        if not base_name.strip():
            logger.warning(
                "[OriginalNameModule] Empty result fallback to original filename: %s",
                file_item.filename,
            )
            base_name = os.path.splitext(file_item.filename)[0]

        return base_name

    @staticmethod
    def is_effective_data(data: dict[str, Any]) -> bool:
        """The original name module is always effective because it produces output."""
        _ = data
        return True
