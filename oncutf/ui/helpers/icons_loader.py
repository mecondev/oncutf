"""Module: icons_loader.py.

Author: Michael Economou
Date: 2025-05-31

This module provides unified icon loading functionality for the application.
It handles different types of icons:
- Metadata status icons
- Menu icons
- Application icons
- Preview status icons

Each icon type has its own loading function and caching mechanism.

Usage:
    from oncutf.ui.helpers.icons_loader import load_metadata_icons, get_menu_icon
    menu_icon = get_menu_icon("draft")
"""

import os
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPixmap

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)

# Cache for metadata icons to avoid regeneration
_metadata_icons_cache: dict[str, QPixmap] | None = None


def load_metadata_icons(_base_dir: str | None = None) -> dict[str, QPixmap]:
    """Loads metadata status icons for the file table's first column.

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

    from oncutf.ui.helpers.svg_icon_generator import generate_metadata_icons

    logger.debug("[IconLoader] Loading SVG metadata icons", extra={"dev_only": True})

    # Generate SVG icons with proper colors
    icon_map = generate_metadata_icons(size=16)

    # Add basic info icon (not included in generate_metadata_icons by default)
    from oncutf.ui.helpers.svg_icon_generator import SVGIconGenerator

    generator = SVGIconGenerator(size=16)
    icon_map["basic"] = generator.generate_icon("basic")

    logger.debug(
        "[IconLoader] Generated %d SVG metadata icons",
        len(icon_map),
        extra={"dev_only": True},
    )

    # Cache the result
    _metadata_icons_cache = icon_map

    return icon_map


# Theme icon loader implementation
class ThemeIconLoader:
    """Handles loading SVG icons with theme-specific functionality.

    This class loads SVG icons from the resources directory, with
    support for different themes (dark/light). It caches icons
    for better performance.
    """

    def __init__(self, theme: str = "dark"):
        """Initialize the ThemeIconLoader.

        Args:
            theme: The current theme ("dark" or "light")

        """
        self.theme = theme
        self.icon_cache: dict[str, dict[str, QIcon]] = {"dark": {}, "light": {}}
        self.base_dir = self._get_base_dir()

    def _get_base_dir(self) -> str:
        """Returns the base directory for icon resources."""
        from oncutf.utils.filesystem.path_utils import get_icons_dir

        return str(get_icons_dir())

    def get_icon_path(self, name: str, theme: str | None = None) -> str:
        """Get the full path to an icon file.

        Search order:
        1. Categorized Material Design folders (navigation, editing, files, etc.)
        2. Root icons folder

        Args:
            name: The icon name (without extension)
            theme: Optional theme override (default: None, uses the instance theme)

        Returns:
            The full path to the icon file

        """
        theme = theme or self.theme

        base_path = Path(self.base_dir)

        # 1. Try categorized Material Design folders (SVG only)
        categorized_folders = [
            "filetypes",  # File type icons (image, movie, audio_file, etc.)
            "navigation",  # Navigation icons (menu, search, close, etc.)
            "editing",  # Editing icons (cut, copy, paste, rotate, etc.)
            "files",  # File operations (folder, save, download, etc.)
            "utilities",  # Utility icons (info, tag, zoom, filter, etc.)
            "metadata",  # Metadata icons (check_circle, error, etc.)
            "preview",  # Preview icons (check_circle, error, etc.)
            "selection",  # Selection icons (checkbox, etc.)
            "toggles",  # Toggle icons (add, remove, toggle_on, etc.)
        ]

        for folder in categorized_folders:
            svg_path = base_path / folder / f"{name}.svg"
            if svg_path.exists():
                return str(svg_path)

        # 2. Fall back to root icons folder (PNG only)
        fallback_png_path = base_path / f"{name}.png"
        if fallback_png_path.exists():
            return str(fallback_png_path)

        # Silently return empty string if not found (no warning spam)
        return ""

    def load_icon(self, name: str, theme: str | None = None) -> QIcon:
        """Load an icon with caching.

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

        # For SVG icons, colorize them based on theme
        icon = self._load_colorized_svg_icon(path, theme) if path.endswith(".svg") else QIcon(path)

        # Cache the icon
        self.icon_cache[theme][name] = icon
        return icon

    def _load_colorized_svg_icon(self, svg_path: str, theme: str) -> QIcon:
        """Load and colorize an SVG icon based on theme.

        Args:
            svg_path: Path to SVG file
            theme: Current theme ("dark" or "light")

        Returns:
            Colorized QIcon

        """
        from PyQt5.QtGui import QPixmap
        from PyQt5.QtSvg import QSvgRenderer

        # Theme colors for icons (matching text color)
        theme_colors = {
            "dark": "#f0ebd8",  # Light text for dark theme
            "light": "#212121",  # Dark text for light theme
        }
        color = theme_colors.get(theme, "#f0ebd8")

        try:
            # Read SVG content
            svg_path_obj = Path(svg_path)
            svg_content = svg_path_obj.read_text(encoding="utf-8")

            # Colorize SVG
            svg_content = self._colorize_svg(svg_content, color)

            # Render to QPixmap at standard sizes
            renderer = QSvgRenderer()
            renderer.load(svg_content.encode("utf-8"))

            # Create pixmap at 24x24 (standard icon size)
            pixmap = QPixmap(24, 24)
            pixmap.fill(Qt.transparent)

            from PyQt5.QtGui import QPainter

            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()

            return QIcon(pixmap)

        except Exception:
            logger.exception("[IconLoader] Error colorizing SVG icon: %s", svg_path)
            # Fallback to non-colorized
            return QIcon(svg_path)

    def _colorize_svg(self, svg_content: str, color: str) -> str:
        """Colorize SVG content for theme.

        Args:
            svg_content: Original SVG content
            color: Target color (hex format)

        Returns:
            Colorized SVG content

        """
        import re

        # Detect icon type based on fill attribute
        is_stroke_based = 'fill="none"' in svg_content

        if is_stroke_based:
            # Stroke-based icons (outline style)
            svg_content = svg_content.replace('stroke="currentColor"', f'stroke="{color}"')
            svg_content = svg_content.replace("stroke='currentColor'", f"stroke='{color}'")
            svg_content = svg_content.replace('stroke="#000"', f'stroke="{color}"')
            svg_content = svg_content.replace('stroke="#000000"', f'stroke="{color}"')

            if "stroke=" not in svg_content:
                svg_content = svg_content.replace("<svg", f'<svg stroke="{color}"')
        else:
            # Material Design icons: fill-based
            # Replace currentColor first (theme-aware placeholder)
            svg_content = svg_content.replace('fill="currentColor"', f'fill="{color}"')
            svg_content = svg_content.replace("fill='currentColor'", f"fill='{color}'")

            # Replace existing fills
            svg_content = svg_content.replace('fill="#000"', f'fill="{color}"')
            svg_content = svg_content.replace('fill="#000000"', f'fill="{color}"')

            # Add fill to SVG root if not present
            if not re.search(r"<svg[^>]*\sfill=", svg_content):
                svg_content = re.sub(r"<svg\s+", f'<svg fill="{color}" ', svg_content, count=1)

        return svg_content

    def set_theme(self, theme: str) -> None:
        """Set the current theme.

        Args:
            theme: The theme to use ("dark" or "light")

        """
        if theme not in ["dark", "light"]:
            logger.warning("Invalid theme: %s, using 'dark' instead", theme)
            theme = "dark"

        self.theme = theme

    def get_menu_icon(self, name: str) -> QIcon:
        """Get an icon specifically for use in menus.

        Args:
            name: The icon name (without extension)

        Returns:
            QIcon object for the requested icon

        """
        return self.load_icon(name)

    def get_app_icon(self) -> QIcon:
        """Get the main application icon (favicon) for window icon.

        Returns:
            QIcon object for the application icon

        """
        from oncutf.utils.filesystem.path_utils import get_assets_dir

        favicon_path = get_assets_dir() / "favicon.ico"

        if favicon_path.exists():
            logger.debug("[IconLoader] Loading app icon from: %s", favicon_path)
            return QIcon(str(favicon_path))
        logger.warning("[IconLoader] App icon not found at: %s", favicon_path)
        return QIcon()


# Create a singleton instance for global use
icons_loader = ThemeIconLoader(theme="dark")


def get_menu_icon(name: str) -> QIcon:
    """Convenience function to get a menu icon from the global icon loader.

    Args:
        name: The icon name (without extension)

    Returns:
        QIcon object for the requested icon

    """
    return icons_loader.get_menu_icon(name)


def get_menu_icon_path(icon_name: str) -> str:
    """Get the absolute path to a menu icon file.

    Search order:
    1. Categorized Material Design folders (navigation, editing, files, etc.)
    2. Root icons folder

    Args:
        icon_name: Name of the icon (without extension)

    Returns:
        str: Absolute path to the icon file

    """
    try:
        from pathlib import Path

        from oncutf.utils.filesystem.path_utils import get_resource_path

        # Categorized folders for Material Design icons
        categorized_folders = [
            "filetypes",
            "navigation",
            "editing",
            "files",
            "utilities",
            "metadata",
            "preview",
            "selection",
            "toggles",
        ]

        # 1. Try categorized Material Design folders (SVG only)
        for folder in categorized_folders:
            relative_path_svg = str(
                Path("oncutf") / "resources" / "icons" / folder / f"{icon_name}.svg"
            )
            icon_path_svg = get_resource_path(relative_path_svg)

            if icon_path_svg.exists():
                return str(icon_path_svg)

        # Log warning if not found
        logger.warning("Icon not found: %s", icon_name)
    except Exception:
        logger.exception("Error getting icon path for '%s'", icon_name)
        # Return empty string as fallback
        return ""
    else:
        return ""


def get_app_icon() -> QIcon:
    """Convenience function to get the application icon from the global icon loader.

    Returns:
        QIcon object for the application icon

    """
    return icons_loader.get_app_icon()
