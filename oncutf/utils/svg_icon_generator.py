"""
Module: svg_icon_generator.py

Author: Michael Economou
Date: 2025-06-20

svg_icon_generator.py
SVG Icon Generator for OnCutF metadata status icons.
Creates colored SVG icons from feather icons with proper theming.
This replaces the old PNG-based system with scalable SVG icons that match
the application's color scheme and progress bar colors.
Usage:
from oncutf.utils.svg_icon_generator import generate_metadata_icons
icon_map = generate_metadata_icons()
"""

from oncutf.config import METADATA_ICON_COLORS
from oncutf.core.pyqt_imports import QByteArray, QColor, QPainter, QPixmap, QSvgRenderer
from oncutf.utils.logger_factory import get_cached_logger
from oncutf.utils.path_utils import get_icons_dir

logger = get_cached_logger(__name__)


class SVGIconGenerator:
    """
    Generates colored SVG icons for metadata status display.

    Uses feather icons as base and applies OnCutF color scheme from config.
    """

    # Icon mappings - feather icon name for each status
    ICON_MAPPINGS = {
        "basic": "info",
        "extended": "info",
        "invalid": "alert-circle",
        "loaded": "check-circle",
        "modified": "edit-2",
        "partial": "alert-triangle",
        "hash": "key",
        "none": "circle",  # Empty circle for no metadata
    }

    def __init__(self, size: int = 16):
        """
        Initialize the SVG icon generator.

        Args:
            size: Icon size in pixels (default: 16)
        """
        self.size = size
        self.icons_dir = get_icons_dir()
        self.feather_dir = self.icons_dir / "feather_icons"

    def _load_svg_content(self, icon_name: str) -> str | None:
        """
        Load SVG content from feather icons directory.

        Args:
            icon_name: Name of the feather icon (without .svg extension)

        Returns:
            SVG content as string, or None if not found
        """
        svg_path = self.feather_dir / f"{icon_name}.svg"

        try:
            with open(svg_path, encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"[SVGIconGenerator] Feather icon not found: {svg_path}")
            return None
        except Exception as e:
            logger.error(f"[SVGIconGenerator] Error reading SVG: {e}")
            return None

    def _colorize_svg(self, svg_content: str, color: str) -> str:
        """
        Replace colors in SVG content with the specified color.

        Args:
            svg_content: Original SVG content
            color: Target color (hex format like #ff0000)

        Returns:
            Modified SVG content with new color
        """
        # Replace various stroke color formats used in feather icons
        svg_content = svg_content.replace('stroke="currentColor"', f'stroke="{color}"')
        svg_content = svg_content.replace("stroke='currentColor'", f"stroke='{color}'")
        svg_content = svg_content.replace(
            'stroke="#d6d6d6"', f'stroke="{color}"'
        )  # Feather default
        svg_content = svg_content.replace('stroke="#000"', f'stroke="{color}"')
        svg_content = svg_content.replace('stroke="#000000"', f'stroke="{color}"')
        svg_content = svg_content.replace('stroke="black"', f'stroke="{color}"')

        # Handle fill colors for some icons
        svg_content = svg_content.replace('fill="currentColor"', f'fill="{color}"')
        svg_content = svg_content.replace("fill='currentColor'", f"fill='{color}'")

        # If no stroke attribute exists, add it to the main SVG element
        if "stroke=" not in svg_content:
            svg_content = svg_content.replace("<svg", f'<svg stroke="{color}"')

        return svg_content

    def generate_icon(self, status: str, size: int | None = None) -> QPixmap:
        """
        Generate a colored icon for the given status.

        Args:
            status: Status name (basic, extended, invalid, loaded, modified, partial, hash)
            size: Icon size override (default: use instance size)

        Returns:
            QPixmap with the generated icon
        """
        if size is None:
            size = self.size

        # Get icon name and color for this status
        icon_name = self.ICON_MAPPINGS.get(status)
        color = METADATA_ICON_COLORS.get(status)

        if not icon_name or not color:
            logger.warning(f"[SVGIconGenerator] Unknown status: {status}")
            return self._create_fallback_pixmap(size)

        # Load and colorize SVG
        svg_content = self._load_svg_content(icon_name)
        if not svg_content:
            return self._create_fallback_pixmap(size)

        colored_svg = self._colorize_svg(svg_content, color)

        # Render to pixmap
        return self._render_svg_to_pixmap(colored_svg, size)

    def _render_svg_to_pixmap(self, svg_content: str, size: int) -> QPixmap:
        """
        Render SVG content to a QPixmap.

        Args:
            svg_content: SVG content as string
            size: Target size in pixels

        Returns:
            QPixmap with rendered SVG
        """
        try:
            # Create SVG renderer
            renderer = QSvgRenderer()
            success = renderer.load(QByteArray(svg_content.encode("utf-8")))

            if not success:
                logger.warning("[SVGIconGenerator] Failed to load SVG content")
                return self._create_fallback_pixmap(size)

            # Create transparent pixmap
            pixmap = QPixmap(size, size)
            pixmap.fill(QColor(0, 0, 0, 0))  # Transparent background

            # Render SVG to pixmap
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            renderer.render(painter)
            painter.end()

            return pixmap

        except Exception as e:
            logger.error(f"[SVGIconGenerator] Error rendering SVG: {e}")
            return self._create_fallback_pixmap(size)

    def _create_fallback_pixmap(self, size: int) -> QPixmap:
        """
        Create a fallback pixmap when SVG generation fails.

        Args:
            size: Pixmap size in pixels

        Returns:
            Empty transparent pixmap
        """
        pixmap = QPixmap(size, size)
        pixmap.fill(QColor(0, 0, 0, 0))  # Transparent
        return pixmap

    def generate_all_icons(self, size: int | None = None) -> dict[str, QPixmap]:
        """
        Generate all metadata status icons.

        Args:
            size: Icon size override (default: use instance size)

        Returns:
            Dictionary mapping status names to QPixmap objects
        """
        if size is None:
            size = self.size

        logger.debug(
            f"[SVGIconGenerator] Generating all metadata icons at {size}px",
            extra={"dev_only": True},
        )

        icons = {}
        for status in METADATA_ICON_COLORS:
            # Generate all icons including hash since we use it in file table model
            icons[status] = self.generate_icon(status, size)

        logger.debug(
            f"[SVGIconGenerator] Generated {len(icons)} metadata icons", extra={"dev_only": True}
        )
        return icons

    def generate_inverted_icon(self, _icon_name: str, _size: int | None = None) -> QPixmap:
        """
        Generate an inverted (dark) version of an icon for selection states.
        REMOVED: This functionality was too complex and not needed.
        """
        return QPixmap()

    def generate_icon_pair(
        self, icon_name: str, size: int | None = None
    ) -> tuple[QPixmap, QPixmap]:
        """
        Generate both normal and inverted versions of an icon.
        REMOVED: This functionality was too complex and not needed.
        """
        normal = self.generate_icon(icon_name, size)
        return normal, QPixmap()


# Convenience functions for backward compatibility
def generate_metadata_icons(size: int = 16) -> dict[str, QPixmap]:
    """
    Generate all metadata status icons.

    Args:
        size: Icon size in pixels (default: 16)

    Returns:
        Dictionary mapping status names to QPixmap objects
    """
    generator = SVGIconGenerator(size)
    return generator.generate_all_icons()


def generate_hash_icon(size: int = 16) -> QPixmap:
    """
    Generate hash operation icon.

    Args:
        size: Icon size in pixels (default: 16)

    Returns:
        QPixmap with hash icon
    """
    generator = SVGIconGenerator(size)
    return generator.generate_icon("hash", size)
