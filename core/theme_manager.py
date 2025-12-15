"""
Module: theme_manager.py

Author: Michael Economou
Date: 2025-12-01

ThemeManager - Centralized theme and color management system.

This manager provides:
- Single source of truth for all application colors
- Runtime theme switching capability (dark/light)
- QSS template rendering with color token replacement
- Singleton pattern for global access
- Signal emission for theme change notifications

Architecture:
- Reads theme definitions from config.THEME_TOKENS
- Renders QSS templates with color placeholders
- Provides color token access via get_color() API
- Emits signals when theme changes for dynamic UI updates
"""

from typing import Optional

from core.pyqt_imports import QObject, pyqtSignal
from oncutf.utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)

# Singleton instance
_theme_manager_instance: Optional["ThemeManager"] = None


class ThemeManager(QObject):
    """
    Centralized theme management system.

    Manages application-wide theme (dark/light) and provides:
    - Color token resolution
    - QSS template rendering
    - Runtime theme switching
    - Theme change notifications

    Usage:
        theme = get_theme_manager()
        color = theme.get_color("background")
        theme.apply_theme(app)
    """

    # Signal emitted when theme changes (emits new theme name)
    theme_changed = pyqtSignal(str)

    def __init__(self):
        """Initialize ThemeManager with default dark theme."""
        super().__init__()
        self._current_theme = "dark"
        self._theme_tokens = {}
        self._qss_cache = ""
        self._load_theme_tokens()
        logger.debug("[ThemeManager] Initialized with dark theme", extra={"dev_only": True})

    def _load_theme_tokens(self) -> None:
        """Load theme tokens from config."""
        try:
            from config import THEME_TOKENS

            self._theme_tokens = THEME_TOKENS
            logger.debug(
                f"[ThemeManager] Loaded {len(self._theme_tokens)} theme definitions",
                extra={"dev_only": True},
            )
        except ImportError:
            logger.error("[ThemeManager] Failed to load THEME_TOKENS from config")
            self._theme_tokens = {}

    def get_current_theme(self) -> str:
        """
        Get the currently active theme name.

        Returns:
            Current theme name ('dark' or 'light')
        """
        return self._current_theme

    def set_theme(self, theme_name: str) -> None:
        """
        Set the active theme and emit change signal.

        Args:
            theme_name: Name of theme to activate ('dark' or 'light')

        Raises:
            ValueError: If theme_name is not valid
        """
        if theme_name not in self._theme_tokens:
            available = ", ".join(self._theme_tokens.keys())
            raise ValueError(
                f"Invalid theme '{theme_name}'. Available themes: {available}"
            )

        if theme_name != self._current_theme:
            old_theme = self._current_theme
            self._current_theme = theme_name
            self._qss_cache = ""  # Invalidate cache
            logger.info(f"[ThemeManager] Theme changed: {old_theme} -> {theme_name}")
            self.theme_changed.emit(theme_name)

    def get_color(self, token: str) -> str:
        """
        Get color value for a specific token in current theme.

        Args:
            token: Color token name (e.g., 'background', 'text', 'selected')

        Returns:
            Hex color string (e.g., '#181818')

        Raises:
            KeyError: If token doesn't exist in current theme
        """
        theme_colors = self._theme_tokens.get(self._current_theme, {})
        if token not in theme_colors:
            logger.warning(
                f"[ThemeManager] Color token '{token}' not found in theme '{self._current_theme}'"
            )
            raise KeyError(f"Color token '{token}' not found in theme '{self._current_theme}'")

        return theme_colors[token]

    @property
    def colors(self) -> dict:
        """
        Get all color tokens for current theme.

        Returns:
            Dictionary of token -> color mappings
        """
        return self._theme_tokens.get(self._current_theme, {})

    def get_qss(self) -> str:
        """
        Get rendered QSS stylesheet for current theme.

        Renders the QSS template with current theme colors.
        Results are cached until theme changes.

        Returns:
            Complete QSS stylesheet string
        """
        if self._qss_cache:
            return self._qss_cache

        self._qss_cache = self._render_qss_template()
        return self._qss_cache

    def _render_qss_template(self) -> str:
        """
        Render QSS template with current theme colors.

        Reads resources/styles/main.qss.template and replaces
        {{token}} placeholders with actual color values.

        Returns:
            Rendered QSS string
        """
        import os

        template_path = os.path.join("resources", "styles", "main.qss.template")

        if not os.path.exists(template_path):
            logger.warning(f"[ThemeManager] QSS template not found: {template_path}")
            return ""

        try:
            with open(template_path, encoding="utf-8") as f:
                template = f.read()

            # Replace {{token}} with actual colors
            theme_colors = self.colors
            for token, color in theme_colors.items():
                placeholder = f"{{{{{token}}}}}"
                template = template.replace(placeholder, color)

            # Replace theme_name placeholder
            template = template.replace("{{theme_name}}", self._current_theme)

            logger.debug(
                f"[ThemeManager] Rendered QSS template ({len(template)} chars)",
                extra={"dev_only": True},
            )
            return template

        except Exception as e:
            logger.error(f"[ThemeManager] Error rendering QSS template: {e}")
            return ""

    def apply_theme(self, app) -> None:
        """
        Apply current theme to QApplication.

        Sets the global application stylesheet.

        Args:
            app: QApplication instance
        """
        qss = self.get_qss()
        if qss:
            app.setStyleSheet(qss)
            logger.info(f"[ThemeManager] Applied theme '{self._current_theme}' to application")
        else:
            logger.warning("[ThemeManager] No QSS to apply (empty or error)")

    def reload_theme(self) -> None:
        """
        Reload theme tokens from config and re-render QSS.

        Useful for development/debugging.
        """
        self._load_theme_tokens()
        self._qss_cache = ""
        logger.info("[ThemeManager] Theme tokens reloaded")


def get_theme_manager() -> ThemeManager:
    """
    Get the global ThemeManager singleton instance.

    Returns:
        ThemeManager instance
    """
    global _theme_manager_instance
    if _theme_manager_instance is None:
        _theme_manager_instance = ThemeManager()
    return _theme_manager_instance
