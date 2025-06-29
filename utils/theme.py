"""
theme.py

Loads and combines modular QSS files for the selected application theme.
Supports expansion for light/dark themes and separates widget styles.

Current implementation loads the 'dark' theme from style/dark_theme/.

Author: Michael Economou
Date: 2025-05-21
"""

import os
from typing import Dict, Optional

from config import THEME_COLORS, THEME_NAME

# Initialize Logger
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


def load_stylesheet() -> str:
    """
    Loads the stylesheet based on THEME_NAME defined in config.py.
    """
    from utils.path_utils import get_project_root, get_theme_dir
    base_dir = str(get_theme_dir(THEME_NAME))
    project_root = str(get_project_root())

    qss_files = [
        "base.qss",
        "buttons.qss",
        "combo_box.qss",
        "scrollbars.qss",
        "table_view.qss",
        "tree_view.qss",
        "tooltip.qss",
        "dialogs.qss"
        # Add more QSS files here if needed
    ]

    full_style = ""
    for filename in qss_files:
        path = os.path.join(base_dir, filename)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                qss = f.read()

                # Replace relative paths with absolute paths for resources
                # This fixes issues when running the app from different directories
                qss = qss.replace("url(resources/", f"url({project_root}/resources/")

                # Debug: Check if SVG files exist for tree view icons
                if filename == "tree_view.qss":
                    _debug_svg_paths(qss, project_root)

                full_style += qss + "\n"
                logger.debug(f"Loaded {filename} ({len(qss)} characters)", extra={"dev_only": True})
        else:
            logger.warning(f"QSS file not found: {filename}")

    return full_style


def _debug_svg_paths(qss_content: str, project_root: str) -> None:
    """Debug function to check if SVG paths in QSS exist."""
    import re

    # Find all url() references in the QSS
    url_pattern = r'url\(([^)]+)\)'
    urls = re.findall(url_pattern, qss_content)

    for url in urls:
        # Remove quotes if present
        clean_url = url.strip('"\'')

        # Convert to absolute path if it starts with project root
        if clean_url.startswith(project_root):
            file_path = clean_url
        else:
            file_path = os.path.join(project_root, clean_url)

        if os.path.exists(file_path):
            logger.debug(f"✓ SVG icon found: {file_path}", extra={"dev_only": True})
        else:
            logger.warning(f"✗ SVG icon missing: {file_path}")


def get_theme_color(color_key: str, theme_name: Optional[str] = None) -> str:
    """
    Get a color from the current theme.

    Args:
        color_key: The color key (e.g., 'hover', 'selected')
        theme_name: Theme name (defaults to THEME_NAME from config)

    Returns:
        The color hex string
    """
    actual_theme = theme_name if theme_name is not None else THEME_NAME
    return THEME_COLORS.get(actual_theme, {}).get(color_key, "#ffffff")


def get_current_theme_colors() -> Dict[str, str]:
    """
    Get all colors for the current theme.

    Returns:
        Dictionary with all color definitions for current theme
    """
    return THEME_COLORS.get(THEME_NAME, {})


def get_qcolor(color_key: str, theme_name: Optional[str] = None) -> str:
    """
    Get a QColor object from theme colors.

    Args:
        color_key: The color key (e.g., 'hover', 'selected')
        theme_name: Theme name (defaults to THEME_NAME from config)

    Returns:
        QColor object
    """
    from core.qt_imports import QColor
    return QColor(get_theme_color(color_key, theme_name))
