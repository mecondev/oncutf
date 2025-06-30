"""
simple_icon_inverter.py

Simple system to create dark versions of icons for selected tree view items.
Uses direct pixmap manipulation for simplicity.

Author: Michael Economou
Date: 2025-06-30
"""

from typing import Dict

from core.qt_imports import QIcon, QPixmap, QPainter, QColor

from utils.svg_icon_generator import SVGIconGenerator
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class SimpleIconInverter:
    """
    Simple utility to create dark versions of icons for selected states.
    """

    def __init__(self):
        self.svg_generator = SVGIconGenerator(size=16)
        self._dark_icon_cache: Dict[str, QIcon] = {}

    def get_dark_icon(self, original_icon: QIcon, icon_type: str = "file") -> QIcon:
        """
        Get a dark version of an icon.

        Args:
            original_icon: Original QIcon
            icon_type: Type of icon ("file", "folder", etc.)

        Returns:
            Dark version of the icon
        """
        cache_key = f"{icon_type}_{hash(original_icon.cacheKey())}"

        if cache_key in self._dark_icon_cache:
            return self._dark_icon_cache[cache_key]

        # Try to generate dark icon from SVG
        try:
            dark_pixmap = self.svg_generator.generate_inverted_icon(icon_type, 16)
            if not dark_pixmap.isNull():
                dark_icon = QIcon()
                dark_icon.addPixmap(dark_pixmap)
                self._dark_icon_cache[cache_key] = dark_icon
                return dark_icon
        except Exception as e:
            logger.debug(f"[SimpleIconInverter] Could not generate SVG dark icon: {e}")

        # Fallback: create a darkened version of the original
        try:
            original_pixmap = original_icon.pixmap(16, 16)
            if not original_pixmap.isNull():
                dark_pixmap = self._darken_pixmap(original_pixmap)
                dark_icon = QIcon()
                dark_icon.addPixmap(dark_pixmap)
                self._dark_icon_cache[cache_key] = dark_icon
                return dark_icon
        except Exception as e:
            logger.debug(f"[SimpleIconInverter] Could not darken original icon: {e}")

        # Ultimate fallback: return original
        return original_icon

    def _darken_pixmap(self, pixmap: QPixmap) -> QPixmap:
        """
        Create a darkened version of a pixmap.

        Args:
            pixmap: Original QPixmap

        Returns:
            Darkened QPixmap
        """
        # Create a new pixmap with the same size
        dark_pixmap = QPixmap(pixmap.size())
        dark_pixmap.fill(QColor(0, 0, 0, 0))  # Transparent background

        # Paint the original with reduced opacity and dark color
        painter = QPainter(dark_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw the original icon in dark color
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        painter.fillRect(dark_pixmap.rect(), QColor(13, 19, 33))  # #0d1321
        painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        painter.drawPixmap(0, 0, pixmap)

        painter.end()

        return dark_pixmap


# Global instance
_icon_inverter = SimpleIconInverter()


def get_dark_icon_for_selection(original_icon: QIcon, is_folder: bool = False) -> QIcon:
    """
    Get a dark version of an icon for selected state.

    Args:
        original_icon: Original QIcon
        is_folder: True if this is a folder icon

    Returns:
        Dark version of the icon
    """
    icon_type = "folder" if is_folder else "file"
    return _icon_inverter.get_dark_icon(original_icon, icon_type)
