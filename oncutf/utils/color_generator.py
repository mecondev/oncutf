"""Module: color_generator.py

Author: Michael Economou
Date: 2025-12-22

Random color generator for folder auto-coloring functionality.
Generates unique random colors with minimum brightness constraints.
"""

from __future__ import annotations

import random

from oncutf.config import AUTO_COLOR_MAX_RETRIES, AUTO_COLOR_MIN_BRIGHTNESS
from oncutf.utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class ColorGenerator:
    """Generates random colors with uniqueness constraints."""

    def __init__(
        self,
        min_brightness: int = AUTO_COLOR_MIN_BRIGHTNESS,
        max_retries: int = AUTO_COLOR_MAX_RETRIES,
    ) -> None:
        """Initialize color generator.

        Args:
            min_brightness: Minimum value for each RGB component (0-255)
            max_retries: Maximum attempts to find a unique color

        """
        self.min_brightness = max(0, min(255, min_brightness))
        self.max_retries = max(1, max_retries)

    def generate_random_color(self) -> str:
        """Generate a single random color.

        Returns:
            Hex color string (e.g., "#A3B5C7")

        """
        r = random.randint(self.min_brightness, 255)
        g = random.randint(self.min_brightness, 255)
        b = random.randint(self.min_brightness, 255)
        return f"#{r:02x}{g:02x}{b:02x}"

    def generate_unique_color(self, existing_colors: set[str]) -> str | None:
        """Generate a unique random color not in existing set.

        Args:
            existing_colors: Set of existing hex colors to avoid

        Returns:
            Unique hex color string, or None if failed after max retries

        """
        for attempt in range(self.max_retries):
            color = self.generate_random_color()
            if color not in existing_colors:
                logger.debug("Generated unique color %s on attempt %d", color, attempt + 1)
                return color

        logger.warning(
            "Failed to generate unique color after %d attempts (existing colors: %d)",
            self.max_retries,
            len(existing_colors),
        )
        return None
