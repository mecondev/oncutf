"""Module: theme_manager.py

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

from typing import Any, Optional

from oncutf.core.pyqt_imports import QObject, pyqtSignal
from oncutf.utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)

# Singleton instance
_theme_manager_instance: Optional["ThemeManager"] = None


class ThemeManager(QObject):
    """Centralized theme management system.

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

    def __init__(self) -> None:
        """Initialize ThemeManager with default dark theme."""
        super().__init__()
        self._current_theme = "dark"
        self._theme_tokens: dict[str, dict[str, str]] = {}
        self._qss_cache = ""
        self._load_theme_tokens()
        logger.debug("[ThemeManager] Initialized with dark theme", extra={"dev_only": True})

    def _load_theme_tokens(self) -> None:
        """Load theme tokens from config."""
        try:
            from oncutf.config import THEME_TOKENS

            self._theme_tokens = THEME_TOKENS
            logger.debug(
                "[ThemeManager] Loaded %d theme definitions",
                len(self._theme_tokens),
                extra={"dev_only": True},
            )
        except ImportError:
            logger.error("[ThemeManager] Failed to load THEME_TOKENS from config")
            self._theme_tokens = {}

    def get_current_theme(self) -> str:
        """Get the currently active theme name.

        Returns:
            Current theme name ('dark' or 'light')

        """
        return self._current_theme

    def set_theme(self, theme_name: str) -> None:
        """Set the active theme and emit change signal.

        Args:
            theme_name: Name of theme to activate ('dark' or 'light')

        Raises:
            ValueError: If theme_name is not valid

        """
        if theme_name not in self._theme_tokens:
            available = ", ".join(self._theme_tokens.keys())
            raise ValueError(f"Invalid theme '{theme_name}'. Available themes: {available}")

        if theme_name != self._current_theme:
            old_theme = self._current_theme
            self._current_theme = theme_name
            self._qss_cache = ""  # Invalidate cache
            logger.info("[ThemeManager] Theme changed: %s -> %s", old_theme, theme_name)
            self.theme_changed.emit(theme_name)

    def get_color(self, token: str) -> str:
        """Get color value for a specific token in current theme.

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
                "[ThemeManager] Color token '%s' not found in theme '%s'",
                token,
                self._current_theme,
            )
            raise KeyError(f"Color token '{token}' not found in theme '{self._current_theme}'")

        return theme_colors[token]

    @property
    def colors(self) -> dict[str, Any]:
        """Get all color tokens for current theme.

        Returns:
            Dictionary of token -> color mappings

        """
        return self._theme_tokens.get(self._current_theme, {})

    def get_qss(self) -> str:
        """Get rendered QSS stylesheet for current theme.

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
        """Render QSS template with current theme colors.

        Reads resources/styles/main.qss.template and replaces
        {{token}} placeholders with actual color values.

        Returns:
            Rendered QSS string

        """
        import os

        template_path = os.path.join("resources", "styles", "main.qss.template")

        if not os.path.exists(template_path):
            logger.warning("[ThemeManager] QSS template not found: %s", template_path)
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

            # Resolve chevron icon paths to absolute file URLs to avoid CWD issues
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            icons_dir = os.path.join(project_root, "resources", "icons")
            chevron_right = os.path.join(icons_dir, "chevron-right.png").replace("\\", "/")
            chevron_down = os.path.join(icons_dir, "chevron-down.png").replace("\\", "/")

            template = template.replace(
                "url(resources/icons/chevron-right.png)", f"url({chevron_right})"
            )
            template = template.replace(
                "url(resources/icons/chevron-down.png)", f"url({chevron_down})"
            )

            logger.debug(
                "[ThemeManager] Rendered QSS template (%d chars)",
                len(template),
                extra={"dev_only": True},
            )
            return template

        except Exception as e:
            logger.error("[ThemeManager] Error rendering QSS template: %s", e)
            return ""

    def apply_theme(self, app: Any) -> None:
        """Apply current theme to QApplication.

        Sets the global application stylesheet.

        Args:
            app: QApplication instance

        """
        qss = self.get_qss()
        if qss:
            app.setStyleSheet(qss)
            logger.info("[ThemeManager] Applied theme '%s' to application", self._current_theme)
        else:
            logger.warning("[ThemeManager] No QSS to apply (empty or error)")

    def reload_theme(self) -> None:
        """Reload theme tokens from config and re-render QSS.

        Useful for development/debugging.
        """
        self._load_theme_tokens()
        self._qss_cache = ""
        logger.info("[ThemeManager] Theme tokens reloaded")

    def get_constant(self, key: str) -> int:
        """Get a layout/sizing constant from theme tokens.

        Args:
            key: Constant name (e.g., 'table_row_height', 'button_height', 'combo_height')

        Returns:
            Integer value for the constant (default: 0 if not found)

        """
        try:
            value_str = self.get_color(key)
            return int(value_str)
        except (KeyError, ValueError):
            logger.debug(
                "[ThemeManager] Constant '%s' not found or not numeric",
                key,
                extra={"dev_only": True},
            )
            return 0

    def get_font_sizes(self) -> dict[str, str]:
        """Get font size definitions for the current theme.

        Returns:
            Dictionary with font size configurations

        """
        return {
            "base_family": "Inter",
            "base_size": "9pt",
            "base_weight": "400",
            "interface_size": "9pt",
            "tree_size": "10pt",
            "medium_weight": "500",
            "semibold_weight": "600",
        }

    @property
    def fonts(self) -> dict[str, str]:
        """Get fonts configuration.

        Returns:
            Dictionary with font settings

        """
        return self.get_font_sizes()

    @property
    def constants(self) -> dict[str, int]:
        """Get layout/sizing constants.

        Returns:
            Dictionary with constant values

        """
        return {
            "table_row_height": self.get_constant("table_row_height"),
            "button_height": self.get_constant("button_height"),
            "combo_height": self.get_constant("combo_height"),
        }

    def get_context_menu_stylesheet(self) -> str:
        """Get QSS stylesheet specifically for context menus.

        Returns:
            QSS stylesheet string for context menus

        """
        # Return a lightweight stylesheet for context menus using current theme colors
        try:
            bg = self.get_color("background")
            text = self.get_color("text")
            hover = self.get_color("selected")
            border = self.get_color("border")
            disabled = self.get_color("disabled_text")

            return f"""
                QMenu {{
                    background-color: {bg};
                    color: {text};
                    border: 1px solid {border};
                    padding: 4px;
                }}
                QMenu::item {{
                    padding: 6px 24px 6px 12px;
                    border-radius: 3px;
                }}
                QMenu::item:selected {{
                    background-color: {hover};
                }}
                QMenu::item:disabled {{
                    color: {disabled};
                }}
                QMenu::separator {{
                    height: 1px;
                    background: {border};
                    margin: 4px 8px;
                }}
            """
        except KeyError:
            logger.warning("[ThemeManager] Failed to generate context menu stylesheet")
            return ""

    def apply_complete_theme(self, app: Any, main_window: Any = None) -> None:
        """Apply complete theming to the entire application.

        Args:
            app: QApplication instance
            main_window: Optional QMainWindow instance (for additional styling)

        """
        # Clear any existing stylesheets
        app.setStyleSheet("")
        if main_window:
            main_window.setStyleSheet("")

        # Apply the theme using get_qss
        qss = self.get_qss()
        if qss:
            app.setStyleSheet(qss)
            logger.info(
                "[ThemeManager] Applied complete theme '%s' to application", self._current_theme
            )
        else:
            logger.warning("[ThemeManager] No QSS available for complete theme")


def get_theme_manager() -> ThemeManager:
    """Get the global ThemeManager singleton instance.

    Returns:
        ThemeManager instance

    """
    global _theme_manager_instance
    if _theme_manager_instance is None:
        _theme_manager_instance = ThemeManager()
    return _theme_manager_instance
