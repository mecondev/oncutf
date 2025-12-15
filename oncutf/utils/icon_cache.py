"""
Module: icon_cache.py

Author: Michael Economou
Date: 2025-05-06

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
from oncutf.core.pyqt_imports import QIcon, QPixmap, Qt
from oncutf.utils.icon_utilities import create_colored_icon

# Initialize Logger
from oncutf.utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


ICON_NAMES = ["valid", "unchanged", "invalid", "duplicate"]
ICON_PATHS = {}


def prepare_status_icons(base_dir: str = None) -> dict[str, str]:
    """
    Prepares and caches status icons by creating colored icons if they do not exist.

    Args:
        base_dir (str): The base directory where icons will be stored. Defaults to project icons dir.

    Returns:
        dict[str, str]: A dictionary mapping icon names to their file paths.
    """
    from oncutf.utils.path_utils import get_icons_dir

    if base_dir is None:
        base_dir = str(get_icons_dir())

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
                border_thickness=1,
            )
            pixmap.save(path)

    return ICON_PATHS


def load_preview_status_icons(size: tuple[int, int] = None) -> dict[str, QIcon]:
    """
    Loads and scales preview status icons (valid, invalid, etc.) for use in the UI.

    Args:
        size (tuple[int, int]): Size to scale icons to. Default uses PREVIEW_INDICATOR_SIZE from config.

    Returns:
        dict[str, QIcon]: Mapping from status to QIcon.
    """
    # Use config size if not specified
    if size is None:
        size = PREVIEW_INDICATOR_SIZE

    paths = prepare_status_icons()  # ensures icons exist
    icon_map = {}

    for status, path in paths.items():
        pixmap = QPixmap(path).scaled(size[0], size[1], Qt.KeepAspectRatio, Qt.SmoothTransformation)
        icon_map[status] = QIcon(pixmap)

    return icon_map
