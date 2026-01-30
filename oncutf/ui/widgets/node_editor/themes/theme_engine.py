"""Theme engine for managing visual themes.

This module provides ThemeEngine, which handles theme registration,
switching, and stylesheet application. It maintains the current theme
state and provides access to theme properties.

Usage:
    Register and switch themes::

        from oncutf.ui.widgets.node_editor.themes import ThemeEngine

        ThemeEngine.set_theme("dark")
        theme = ThemeEngine.get_theme()
        background = theme.node_background

Author:
    Michael Economou

Date:
    2025-12-11
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, ClassVar

from PyQt5.QtCore import QFile
from PyQt5.QtWidgets import QApplication

if TYPE_CHECKING:
    from oncutf.ui.widgets.node_editor.themes.base_theme import BaseTheme

logger = logging.getLogger(__name__)


class ThemeEngine:
    """Manages theme registration, switching, and application.

    Maintains a registry of available themes and handles the
    application of theme stylesheets when switching.

    Attributes:
        _current_theme: Currently active theme instance.
        _themes: Dictionary mapping theme names to theme classes.

    """

    _current_theme: ClassVar[BaseTheme | None] = None
    _themes: ClassVar[dict[str, type[BaseTheme]]] = {}

    @classmethod
    def register_theme(cls, theme_class: type[BaseTheme]) -> None:
        """Register a theme class for use.

        Args:
            theme_class: Theme class inheriting from BaseTheme.

        """
        cls._themes[theme_class.name] = theme_class

    @classmethod
    def current_theme(cls) -> BaseTheme:
        """Get the current theme, auto-initializing if needed.

        If no theme is set, automatically initializes with dark theme.

        Returns:
            Currently active theme instance.

        """
        if cls._current_theme is None:
            from oncutf.ui.widgets.node_editor.themes.dark import DarkTheme
            from oncutf.ui.widgets.node_editor.themes.light import LightTheme

            cls.register_theme(DarkTheme)
            cls.register_theme(LightTheme)
            cls.set_theme("dark")
        return cls._current_theme

    @classmethod
    def get_theme(cls, name: str | None = None) -> BaseTheme | None:
        """Get current theme or a specific theme by name.

        Args:
            name: Theme name to retrieve, or None for current theme.

        Returns:
            Theme instance, or None if named theme not found.

        """
        if name:
            theme_class = cls._themes.get(name)
            return theme_class() if theme_class else None
        return cls._current_theme

    @classmethod
    def set_theme(cls, name: str) -> None:
        """Activate a theme and apply its stylesheet.

        Args:
            name: Name of registered theme to activate.

        Raises:
            ValueError: If theme name is not registered.

        """
        if name not in cls._themes:
            available = ", ".join(cls._themes.keys())
            raise ValueError(f"Theme '{name}' not registered. Available: {available}")

        theme_class = cls._themes[name]
        cls._current_theme = theme_class()
        cls._apply_stylesheet(name)

    @classmethod
    def _apply_stylesheet(cls, theme_name: str) -> None:
        """Load and apply QSS stylesheet for a theme.

        Args:
            theme_name: Name of theme whose stylesheet to apply.

        """
        theme_dir = os.path.dirname(__file__)
        qss_path = os.path.join(theme_dir, theme_name, "style.qss")

        if os.path.exists(qss_path):
            file = QFile(qss_path)
            if file.open(QFile.ReadOnly | QFile.Text):
                stylesheet = str(file.readAll(), encoding="utf-8")
                file.close()
                app = QApplication.instance()
                if app:
                    app.setStyleSheet(stylesheet)

    @classmethod
    def available_themes(cls) -> list:
        """Get list of registered theme names.

        Returns:
            List of available theme name strings.

        """
        return list(cls._themes.keys())

    @classmethod
    def reload_theme(cls) -> None:
        """Reload and reapply the current theme.

        Useful for refreshing after QSS file modifications.
        """
        if cls._current_theme:
            cls.set_theme(cls._current_theme.name)

    @classmethod
    def refresh_graphics_items(cls, scene) -> None:
        """Refresh theme assets on all graphics items in a scene.

        Call after set_theme() to update colors/pens on existing items.

        Args:
            scene: Scene instance whose graphics items should refresh.

        """
        # Refresh scene
        if hasattr(scene, "graphics_scene") and hasattr(scene.graphics_scene, "init_assets"):
            scene.graphics_scene.init_assets()
            scene.graphics_scene.update()

        # Refresh all nodes
        for node in scene.nodes:
            if node.graphics_node and hasattr(node.graphics_node, "init_assets"):
                node.graphics_node.init_assets()
                node.graphics_node.update()

            # Refresh sockets
            for socket in node.inputs + node.outputs:
                if hasattr(socket.graphics_socket, "init_assets"):
                    socket.graphics_socket.init_assets()
                    socket.graphics_socket.update()

        # Refresh all edges
        for edge in scene.edges:
            if edge.graphics_edge and hasattr(edge.graphics_edge, "init_assets"):
                edge.graphics_edge.init_assets()
                edge.graphics_edge.update()
