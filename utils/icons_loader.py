"""
icons_loader.py

Author: Michael Economou
Date: 2025-05-20

This utility provides helper functions to load various types of icons:
- Metadata status icons for use in the metadata icon delegate
- Theme-aware SVG icons for menus and buttons
- Preview status icons

Each icon type has its own loading function and caching mechanism.

Usage:
    from utils.icons_loader import load_metadata_icons, get_menu_icon
    icon_map = load_metadata_icons()
    menu_icon = get_menu_icon("file")
"""

from PyQt5.QtGui import QPixmap, QIcon, QPainter, QColor
from PyQt5.QtCore import Qt
import os
from typing import Dict, Optional

from utils.logger_helper import get_logger
logger = get_logger(__name__)


def load_metadata_icons(base_dir: str = "resources/icons") -> dict[str, QPixmap]:
    """
    Loads metadata status icons for the file table's first column.

    Args:
        base_dir: Base directory where icon files are stored

    Returns:
        Dictionary mapping status names to QPixmap objects
    """
    icon_files = {
        'loaded': "info_loaded.png",
        'extended': "info_extended.png",
        'partial': "info_partial.png",
        'invalid': "info_invalid.png",
        'modified': "info_modified.png",
    }

    logger.debug("[IconLoader] Loading metadata icons")

    icon_map = {}
    for status, filename in icon_files.items():
        path = os.path.join(base_dir, filename)
        pixmap = QPixmap(path)
        if pixmap.isNull():
            logger.warning(f"[IconLoader] Failed to load icon for '{status}' from {path}")
        icon_map[status] = pixmap

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
        # Get the directory where this module is located
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up one level to get project root
        project_root = os.path.dirname(current_dir)
        return os.path.join(project_root, "resources", "icons")

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
