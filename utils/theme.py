"""
theme.py

Theme management system using Python-based styling instead of QSS files.
Provides color access and theme utilities for the application.

Author: Michael Economou
Date: 2025-06-30
"""

from typing import Dict, Optional
from config import THEME_COLORS, THEME_NAME
from utils.comprehensive_theme_system import ComprehensiveThemeColors


def get_theme_color(color_key: str, theme_name: Optional[str] = None) -> str:
    """Get a color from the comprehensive theme system."""
    if theme_name is None:
        theme_name = THEME_NAME

    if theme_name == "dark":
        return ComprehensiveThemeColors.DARK.get(color_key, "#ffffff")

    # Fallback to config colors for compatibility
    return THEME_COLORS.get(theme_name, {}).get(color_key, "#ffffff")


def get_current_theme_colors() -> Dict[str, str]:
    """Get all colors for the current theme."""
    if THEME_NAME == "dark":
        return ComprehensiveThemeColors.DARK

    return THEME_COLORS.get(THEME_NAME, {})


def get_qcolor(color_key: str, theme_name: Optional[str] = None):
    """Get a QColor object from theme colors."""
    from core.qt_imports import QColor
    return QColor(get_theme_color(color_key, theme_name))
