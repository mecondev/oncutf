"""
Module: theme.py

Author: Michael Economou
Date: 2025-05-06

theme.py
Theme management system using the new ThemeEngine.
Provides color access and theme utilities for the application.
"""

from config import THEME_NAME

# Global theme engine instance
_theme_engine = None


def _get_theme_engine():
    """Get the global theme engine instance."""
    global _theme_engine
    if _theme_engine is None:
        from oncutf.utils.theme_engine import ThemeEngine

        _theme_engine = ThemeEngine(THEME_NAME)
    return _theme_engine


def get_theme_color(color_key: str, _theme_name: str | None = None) -> str:
    """Get a color from the theme engine."""
    theme_engine = _get_theme_engine()
    return theme_engine.get_color(color_key)


def get_current_theme_colors() -> dict[str, str]:
    """Get all colors for the current theme."""
    theme_engine = _get_theme_engine()
    return theme_engine.colors


def get_qcolor(color_key: str, theme_name: str | None = None):
    """Get a QColor object from theme colors."""
    from core.pyqt_imports import QColor

    return QColor(get_theme_color(color_key, theme_name))
