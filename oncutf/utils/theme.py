"""
Module: theme.py

Author: Michael Economou
Date: 2025-05-06

Theme utility functions for accessing colors and theme settings.

DEPRECATED: These helper functions delegate to ThemeManager.
For new code, use: from oncutf.core.theme_manager import get_theme_manager
"""

from oncutf.core.theme_manager import get_theme_manager


def get_theme_color(color_key: str, _theme_name: str | None = None) -> str:
    """
    Get a color from the current theme.

    Delegates to ThemeManager.get_color().

    Args:
        color_key: Color token name
        _theme_name: Ignored (for backwards compatibility)

    Returns:
        Hex color string
    """
    manager = get_theme_manager()
    try:
        return manager.get_color(color_key)
    except KeyError:
        # Fallback for legacy color names - try mapping
        color_mapping = {
            "app_background": "background",
            "app_text": "text",
            "input_background": "input_bg",
            "input_text": "input_text",
            "table_background": "table_background",
            "text": "text",
        }
        token = color_mapping.get(color_key, color_key)
        try:
            return manager.get_color(token)
        except KeyError:
            return "#000000"


def get_current_theme_colors() -> dict[str, str]:
    """
    Get all colors for the current theme.

    Delegates to ThemeManager.colors property.

    Returns:
        Dictionary of token -> color mappings
    """
    manager = get_theme_manager()
    return manager.colors


def get_qcolor(color_key: str, theme_name: str | None = None):
    """
    Get a QColor object from theme colors.

    Args:
        color_key: Color token name
        theme_name: Ignored (for backwards compatibility)

    Returns:
        QColor object
    """
    from oncutf.core.pyqt_imports import QColor

    return QColor(get_theme_color(color_key, theme_name))
