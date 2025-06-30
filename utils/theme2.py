"""
theme.py

Loads and combines modular QSS files for the selected application theme.
Supports expansion for light/dark themes and separates widget styles.

Works on both Windows and Unix-like systems by avoiding absolute path substitution.

Author: Michael Economou
Date: 2025-06-30
"""

import os
from typing import Dict, Optional
from config import THEME_COLORS, THEME_NAME

from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


def load_stylesheet() -> str:
    """
    Loads and combines modular QSS files for the selected application theme.
    Uses relative resource paths (e.g. url(resources/...) for Qt compatibility across OSes.
    """
    from utils.path_utils import get_theme_dir
    base_dir = str(get_theme_dir(THEME_NAME))

    qss_files = [
        "fixed_base.qss",
        "fixed_buttons.qss",
        "fixed_combo_box.qss",
        "fixed_scrollbars.qss",
        "fixed_table_view.qss",
        "fixed_tree_view.qss",
        "fixed_tooltip.qss",
        "fixed_dialogs.qss"
    ]

    full_style = ""
    for filename in qss_files:
        path = os.path.join(base_dir, filename)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                qss = f.read()
                # No path rewriting – assume relative to working directory
                full_style += qss + "\n"
                logger.debug(f"Loaded {filename} ({len(qss)} characters)", extra={"dev_only": True})
        else:
            logger.warning(f"QSS file not found: {filename}")

    logger.debug(f"Total stylesheet length: {len(full_style)}", extra={"dev_only": True})
    return full_style


def get_theme_color(color_key: str, theme_name: Optional[str] = None) -> str:
    actual_theme = theme_name if theme_name is not None else THEME_NAME
    return THEME_COLORS.get(actual_theme, {}).get(color_key, "#ffffff")


def get_current_theme_colors() -> Dict[str, str]:
    return THEME_COLORS.get(THEME_NAME, {})


def get_qcolor(color_key: str, theme_name: Optional[str] = None) -> str:
    from core.qt_imports import QColor
    return QColor(get_theme_color(color_key, theme_name))
