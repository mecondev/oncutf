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
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "style", f"{THEME_NAME}_theme"))
    qss_files = [
        "base.qss",
        "buttons.qss",
        "combo_box.qss",
        "scrollbars.qss",
        "table_view.qss",
        "tree_view.qss",
        "tooltip.qss"
        # Add more QSS files here if needed
    ]

    full_style = ""
    for filename in qss_files:
        path = os.path.join(base_dir, filename)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                qss = f.read()
                full_style += qss + "\n"
                logger.debug(f"Loaded {filename} ({len(qss)} characters)", extra={"dev_only": True})
        else:
            logger.warning(f"QSS file not found: {filename}")

    return full_style


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
    from PyQt5.QtGui import QColor
    return QColor(get_theme_color(color_key, theme_name))
