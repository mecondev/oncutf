"""
Module: icons_loader.py

Author: Michael Economou
Date: 2025-05-31

import os
from typing import Dict, Optional
from core.pyqt_imports import QIcon, QPixmap
from utils.logger_factory import get_cached_logger
logger = get_cached_logger(__name__)
# Cache for metadata icons to avoid regeneration
_metadata_icons_cache: Optional[dict[str, QPixmap]] = None
def load_metadata_icons(base_dir: Optional[str] = None) -> dict[str, QPixmap]:
"""
"""
Icons Loader Module

This module provides unified icon loading functionality for the application.
It handles different types of icons:
- Metadata status icons
- Menu icons (from Feather icon set)
- Application icons
- Preview status icons

Each icon type has its own loading function and caching mechanism.

Usage:
    from utils.icons_loader import load_metadata_icons, get_menu_icon
    menu_icon = get_menu_icon("file")

"""

import os
from typing import Dict, Optional

from core.pyqt_imports import QIcon, QPixmap
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)

# Cache for metadata icons to avoid regeneration
_metadata_icons_cache: Optional[dict[str, QPixmap]] = None


def load_metadata_icons(base_dir: Optional[str] = None) -> dict[str, QPixmap]:
    """
    Loads metadata status icons for the file table's first column.

    Now uses SVG-based icons with proper theming instead of PNG files.
    Implements caching to avoid regenerating icons on every call.

    Args:
        base_dir: Base directory where icon files are stored (optional, kept for compatibility)

    Returns:
        Dictionary mapping status names to QPixmap objects
    """
    global _metadata_icons_cache

    # Return cached icons if available
    if _metadata_icons_cache is not None:
        logger.debug("[IconLoader] Using cached metadata icons", extra={"dev_only": True})
        return _metadata_icons_cache

    from utils.svg_icon_generator import generate_metadata_icons

    logger.debug("[IconLoader] Loading SVG metadata icons", extra={"dev_only": True})

    # Generate SVG icons with proper colors
    icon_map = generate_metadata_icons(size=16)

    # Add basic info icon (not included in generate_metadata_icons by default)
    from utils.svg_icon_generator import SVGIconGenerator
    generator = SVGIconGenerator(size=16)
    icon_map['basic'] = generator.generate_icon('basic')

    logger.debug(f"[IconLoader] Generated {len(icon_map)} SVG metadata icons", extra={"dev_only": True})

    # Cache the result
    _metadata_icons_cache = icon_map

    return icon_map


# Theme icon loader implementation
class ThemeIconLoader:
    """
    Handles loading SVG icons with theme-specific functionality.

    This class loads SVG icons from the resources directory, with
    support for different themes (dark/light). It caches icons
    for better performance.
    """

    def __init__(self, theme: str = "dark"):
        """
        Initialize the ThemeIconLoader.

        Args:
            theme: The current theme ("dark" or "light")
        """
        self.theme = theme
        self.icon_cache: Dict[str, Dict[str, QIcon]] = {
            "dark": {},
            "light": {}
        }
        self.base_dir = self._get_base_dir()

    def _get_base_dir(self) -> str:
        """Returns the base directory for icon resources."""
        from utils.path_utils import get_icons_dir
        return str(get_icons_dir())

    def get_icon_path(self, name: str, theme: Optional[str] = None) -> str:
        """
        Get the full path to an icon file.

        Args:
            name: The icon name (without extension)
            theme: Optional theme override (default: None, uses the instance theme)

        Returns:
            The full path to the icon file
        """
        theme = theme or self.theme

        # Try feather icons folder first (more modern, consistent style)
        feather_path = os.path.join(self.base_dir, "feather_icons", f"{name}.svg")
        if os.path.exists(feather_path):
            return feather_path

        # Fall back to other folders if needed
        fallback_path = os.path.join(self.base_dir, f"{name}.svg")
        if os.path.exists(fallback_path):
            return fallback_path

        logger.warning(f"Icon '{name}' not found in any icon directories")
        return ""

    def load_icon(self, name: str, theme: Optional[str] = None) -> QIcon:
        """
        Load an icon with caching.

        Args:
            name: The icon name (without extension)
            theme: Optional theme override (default: None, uses the instance theme)

        Returns:
            QIcon object for the requested icon
        """
        theme = theme or self.theme

        # Check if already cached
        if name in self.icon_cache[theme]:
            return self.icon_cache[theme][name]

        # Load the icon
        path = self.get_icon_path(name, theme)
        if not path:
            # Return empty icon if not found
            return QIcon()

        icon = QIcon(path)

        # Cache the icon
        self.icon_cache[theme][name] = icon
        return icon

    def set_theme(self, theme: str) -> None:
        """
        Set the current theme.

        Args:
            theme: The theme to use ("dark" or "light")
        """
        if theme not in ["dark", "light"]:
            logger.warning(f"Invalid theme: {theme}, using 'dark' instead")
            theme = "dark"

        self.theme = theme

    def get_menu_icon(self, name: str) -> QIcon:
        """
        Get an icon specifically for use in menus.

        Args:
            name: The icon name (without extension)

        Returns:
            QIcon object for the requested icon
        """
        return self.load_icon(name)

    def get_app_icon(self) -> QIcon:
        """
        Get the main application icon (favicon) for window icon.

        Returns:
            QIcon object for the application icon
        """
        from utils.path_utils import get_assets_dir
        favicon_path = get_assets_dir() / "favicon.ico"

        if os.path.exists(str(favicon_path)):
            logger.debug(f"[IconLoader] Loading app icon from: {favicon_path}")
            return QIcon(str(favicon_path))
        else:
            logger.warning(f"[IconLoader] App icon not found at: {favicon_path}")
            return QIcon()


# Create a singleton instance for global use
icons_loader = ThemeIconLoader(theme="dark")


def get_menu_icon(name: str) -> QIcon:
    """
    Convenience function to get a menu icon from the global icon loader.

    Args:
        name: The icon name (without extension)

    Returns:
        QIcon object for the requested icon
    """
    return icons_loader.get_menu_icon(name)


def get_menu_icon_path(name: str) -> str:
    """
    Convenience function to get the file path of a menu icon for use in stylesheets.

    Args:
        name: The icon name (without extension)

    Returns:
        str: The full path to the icon file
    """
    return icons_loader.get_icon_path(name)


def get_app_icon() -> QIcon:
    """
    Convenience function to get the application icon from the global icon loader.

    Returns:
        QIcon object for the application icon
    """
    return icons_loader.get_app_icon()
