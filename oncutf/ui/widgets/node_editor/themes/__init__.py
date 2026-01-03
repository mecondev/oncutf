"""Theme system for customizing node editor appearance.

This module provides a theme engine that allows switching between
different visual themes for the node editor. Built-in themes include
dark and light variants.

Usage:
    Switch themes and access theme properties::

        from oncutf.ui.widgets.node_editor.themes import ThemeEngine

        ThemeEngine.set_theme("dark")
        theme = ThemeEngine.get_theme()
        bg_color = theme.node_background

Classes:
    ThemeEngine: Theme manager for loading and switching themes.
    BaseTheme: Abstract base class for theme definitions.
    DarkTheme: Dark color scheme theme.
    LightTheme: Light color scheme theme.

Author:
    Michael Economou

Date:
    2025-12-11
"""

from oncutf.ui.widgets.node_editor.themes.base_theme import BaseTheme

# Import and register built-in themes
from oncutf.ui.widgets.node_editor.themes.dark import DarkTheme
from oncutf.ui.widgets.node_editor.themes.light import LightTheme
from oncutf.ui.widgets.node_editor.themes.theme_engine import ThemeEngine

ThemeEngine.register_theme(DarkTheme)
ThemeEngine.register_theme(LightTheme)

# Set dark as default
ThemeEngine.set_theme("dark")

__all__ = [
    "ThemeEngine",
    "BaseTheme",
    "DarkTheme",
    "LightTheme",
]
