"""
Module: icon_cache.py

Author: Michael Economou
Date: 2025-05-01

This utility module provides functions for caching QIcons or other
visual assets to avoid redundant loading and improve GUI performance.

Used by oncutf to store and reuse icons across different widgets
without unnecessary overhead.

Supports:
- Icon retrieval by file type or status
- In-memory caching of icons
- Integration with GUI elements via shared cache
"""

import os
from config import PREVIEW_COLORS, PREVIEW_INDICATOR_SHAPE, PREVIEW_INDICATOR_SIZE
from utils.icons import create_colored_icon

# Initialize Logger
from utils.logger_helper import get_logger
logger = get_logger(__name__)


ICON_NAMES = ["valid", "unchanged", "invalid", "duplicate"]

ICON_PATHS = {}

def prepare_status_icons(base_dir: str = "resources/icons") -> dict[str, str]:
    """
    Prepares and caches status icons by creating colored icons if they do not exist.

    Args:
        base_dir (str): The base directory where icons will be stored. Defaults to "resources/icons".

    Returns:
        dict[str, str]: A dictionary mapping icon names to their file paths.
    """

    os.makedirs(base_dir, exist_ok=True)

    for name in ICON_NAMES:
        path = os.path.join(base_dir, f"{name}.png")
        ICON_PATHS[name] = path

        if not os.path.exists(path):
            pixmap = create_colored_icon(
                fill_color=PREVIEW_COLORS[name],
                shape=PREVIEW_INDICATOR_SHAPE,
                size_x=PREVIEW_INDICATOR_SIZE[0],
                size_y=PREVIEW_INDICATOR_SIZE[1],
                border_color="#222222",
                border_thickness=1
            )
            pixmap.save(path)

    return ICON_PATHS
