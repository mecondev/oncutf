"""Window Setup Controller.

Author: Michael Economou
Date: 2026-01-02

Handles main window configuration: size, title, icon, and positioning.
"""

from typing import TYPE_CHECKING

from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QApplication

from oncutf.config import (
    WINDOW_HEIGHT,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
    WINDOW_WIDTH,
)
from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.ui.icons_loader import get_app_icon

if TYPE_CHECKING:
    from oncutf.ui.main_window import MainWindow

logger = get_cached_logger(__name__)


class WindowSetupController:
    """Controller for main window setup and configuration.

    Responsibilities:
    - Window sizing and positioning
    - Window title and icon
    - Adaptive sizing based on screen resolution
    """

    def __init__(self, parent_window: "MainWindow"):
        """Initialize controller with parent window reference.

        Args:
            parent_window: The main application window
        """
        self.parent_window = parent_window
        logger.debug("WindowSetupController initialized", extra={"dev_only": True})

    def setup(self) -> None:
        """Configure main window properties."""
        self._setup_title_and_icon()
        self._setup_size()
        self._center_window()

    def _setup_title_and_icon(self) -> None:
        """Set window title and application icon."""
        self.parent_window.setWindowTitle("oncutf - Batch File Renamer and More")

        app_icon = get_app_icon()
        if not app_icon.isNull():
            self.parent_window.setWindowIcon(app_icon)
            logger.debug("Window icon set using icon loader", extra={"dev_only": True})
        else:
            logger.warning("Failed to load application icon")

    def _setup_size(self) -> None:
        """Calculate and set optimal window size based on screen resolution."""
        optimal_size = self._calculate_optimal_window_size()
        self.parent_window.resize(optimal_size.width(), optimal_size.height())
        self.parent_window.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

    def _center_window(self) -> None:
        """Center window on screen using DialogManager."""
        self.parent_window.context.get_manager("dialog").center_window(self.parent_window)

    def _calculate_optimal_window_size(self) -> QSize:
        """Calculate optimal window size based on screen resolution and aspect ratio.

        Returns:
            QSize with optimal width and height
        """
        # Get primary screen geometry
        screen = QApplication.desktop().screenGeometry()  # type: ignore
        screen_width = screen.width()
        screen_height = screen.height()
        screen_aspect = screen_width / screen_height

        logger.debug(
            "Screen resolution: %dx%d, aspect: %.2f",
            screen_width,
            screen_height,
            screen_aspect,
            extra={"dev_only": True},
        )

        # Define target percentages of screen size
        width_percentage = 0.75  # Use 75% of screen width
        height_percentage = 0.80  # Use 80% of screen height

        # Calculate initial size based on screen percentage
        target_width = int(screen_width * width_percentage)
        target_height = int(screen_height * height_percentage)

        # Adjust for different aspect ratios
        if screen_aspect >= 2.3:  # Ultrawide (21:9 or wider)
            target_width = int(screen_width * 0.65)
            target_height = int(screen_height * 0.85)
        elif screen_aspect >= 1.7:  # Widescreen (16:9, 16:10)
            pass  # Use calculated values
        elif screen_aspect <= 1.4:  # 4:3 or close
            target_width = int(screen_width * 0.92)
            target_height = int(screen_height * 0.85)

        # Ensure minimum constraints
        target_width = max(target_width, WINDOW_MIN_WIDTH)
        target_height = max(target_height, WINDOW_MIN_HEIGHT)

        # Ensure maximum reasonable size
        max_width = max(WINDOW_WIDTH, 1600)
        max_height = max(WINDOW_HEIGHT, 1200)
        target_width = min(target_width, max_width)
        target_height = min(target_height, max_height)

        optimal_size = QSize(target_width, target_height)

        logger.debug(
            "Calculated optimal window size: %dx%d",
            target_width,
            target_height,
            extra={"dev_only": True},
        )
        return optimal_size
