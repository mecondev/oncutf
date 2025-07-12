"""
Module: dpi_helper.py

Author: Michael Economou
Date: 2025-06-10

dpi_helper.py
DPI adaptation utilities for cross-platform font and UI scaling.
Handles differences between Windows and Linux DPI scaling behavior.
"""

import logging
import platform
from typing import Dict

from core.pyqt_imports import QApplication

logger = logging.getLogger(__name__)


class DPIHelper:
    """
    Cross-platform DPI adaptation helper.

    Handles font scaling and UI element sizing to ensure consistent
    appearance across Windows and Linux systems.
    """

    def __init__(self):
        self.system = platform.system()
        self.dpi_scale = 1.0
        self.font_scale = 1.0
        self._calculate_scaling()

    def _calculate_scaling(self) -> None:
        """Calculate DPI and font scaling factors."""
        try:
            app = QApplication.instance()
            if not app:
                logger.warning("[DPI] No QApplication instance found, using default scaling")
                return

            # Get primary screen
            primary_screen = app.primaryScreen()
            if not primary_screen:
                logger.warning("[DPI] No primary screen found, using default scaling")
                return

            # Get DPI information
            logical_dpi = primary_screen.logicalDotsPerInch()
            physical_dpi = primary_screen.physicalDotsPerInch()
            device_pixel_ratio = primary_screen.devicePixelRatio()

            logger.debug(f"[DPI] System: {self.system}", extra={"dev_only": True})
            logger.debug(f"[DPI] Logical DPI: {logical_dpi}", extra={"dev_only": True})
            logger.debug(f"[DPI] Physical DPI: {physical_dpi}", extra={"dev_only": True})
            logger.debug(f"[DPI] Device Pixel Ratio: {device_pixel_ratio}", extra={"dev_only": True})

            # Calculate base DPI scale (96 DPI is standard)
            base_dpi = 96.0
            self.dpi_scale = logical_dpi / base_dpi

            # Apply system-specific adjustments
            if self.system == "Windows":
                # Windows tends to scale fonts more aggressively
                # Apply a reduction factor to compensate
                if self.dpi_scale > 1.0:
                    # For high DPI Windows systems, reduce font scaling
                    self.font_scale = max(0.85, 1.0 / self.dpi_scale)
                else:
                    # For normal DPI, use slight reduction
                    self.font_scale = 0.9

                logger.debug(f"[DPI] Windows font scale adjustment: {self.font_scale}", extra={"dev_only": True})

            elif self.system == "Linux":
                # Linux generally handles DPI scaling better
                # Use more conservative adjustments
                if self.dpi_scale > 1.25:
                    # Only adjust for very high DPI
                    self.font_scale = 0.95
                else:
                    self.font_scale = 1.0

                logger.debug(f"[DPI] Linux font scale adjustment: {self.font_scale}", extra={"dev_only": True})

            else:
                # macOS or other systems - use default
                self.font_scale = 1.0

            logger.debug(f"[DPI] Final scaling - DPI: {self.dpi_scale:.2f}, Font: {self.font_scale:.2f}", extra={"dev_only": True})

        except Exception as e:
            logger.error(f"[DPI] Error calculating scaling: {e}")
            self.dpi_scale = 1.0
            self.font_scale = 1.0

    def scale_font_size(self, base_size: int) -> int:
        """
        Scale font size based on system and DPI.

        Args:
            base_size: Base font size in points

        Returns:
            Scaled font size in points
        """
        scaled_size = int(base_size * self.font_scale)

        # Ensure minimum readable size
        min_size = 8 if self.system == "Windows" else 9
        max_size = 16  # Prevent overly large fonts

        return max(min_size, min(max_size, scaled_size))

    def scale_ui_size(self, base_size: int) -> int:
        """
        Scale UI element size based on DPI.

        Args:
            base_size: Base size in pixels

        Returns:
            Scaled size in pixels
        """
        return int(base_size * self.dpi_scale)

    def get_font_sizes(self) -> Dict[str, int]:
        """
        Get recommended font sizes for different UI elements.

        Returns:
            Dictionary with font sizes for different use cases
        """
        base_sizes = {
            'small': 8,      # Small labels, status text
            'normal': 9,     # Default UI text
            'medium': 10,    # Buttons, headers
            'large': 11,     # Titles
            'tree': 9,       # Tree views (file/metadata trees)
            'table': 9,      # Table views
        }

        # Apply scaling to all sizes
        scaled_sizes = {}
        for use_case, size in base_sizes.items():
            scaled_sizes[use_case] = self.scale_font_size(size)

        # Special handling for tree/table views on Windows
        if self.system == "Windows":
            # Windows tends to make tree/table fonts too large
            scaled_sizes['tree'] = max(8, scaled_sizes['tree'] - 1)
            scaled_sizes['table'] = max(8, scaled_sizes['table'] - 1)

        logger.debug(f"[DPI] Font sizes: {scaled_sizes}", extra={"dev_only": True})
        return scaled_sizes

    def get_system_info(self) -> Dict[str, any]:
        """Get system DPI information for debugging."""
        try:
            app = QApplication.instance()
            if not app:
                return {"error": "No QApplication instance"}

            primary_screen = app.primaryScreen()
            if not primary_screen:
                return {"error": "No primary screen"}

            return {
                "system": self.system,
                "logical_dpi": primary_screen.logicalDotsPerInch(),
                "physical_dpi": primary_screen.physicalDotsPerInch(),
                "device_pixel_ratio": primary_screen.devicePixelRatio(),
                "screen_geometry": primary_screen.geometry(),
                "available_geometry": primary_screen.availableGeometry(),
                "dpi_scale": self.dpi_scale,
                "font_scale": self.font_scale,
            }
        except Exception as e:
            return {"error": str(e)}


# Global instance
_dpi_helper = None


def get_dpi_helper() -> DPIHelper:
    """Get the global DPI helper instance."""
    global _dpi_helper
    if _dpi_helper is None:
        _dpi_helper = DPIHelper()
    return _dpi_helper


def scale_font_size(base_size: int) -> int:
    """Convenience function to scale font size."""
    return get_dpi_helper().scale_font_size(base_size)


def scale_ui_size(base_size: int) -> int:
    """Convenience function to scale UI size."""
    return get_dpi_helper().scale_ui_size(base_size)


def get_font_sizes() -> Dict[str, int]:
    """Convenience function to get font sizes."""
    return get_dpi_helper().get_font_sizes()


def log_dpi_info() -> None:
    """Log DPI information for debugging."""
    info = get_dpi_helper().get_system_info()
    logger.debug(f"[DPI] System info: {info}", extra={"dev_only": True})
