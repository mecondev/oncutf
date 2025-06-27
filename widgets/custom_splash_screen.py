"""
custom_splash_screen.py

Author: Michael Economou
Date: 2025-06-23

Custom splash screen widget for the oncutf application.
Features:
- Custom size (16:9 aspect ratio with 400px height)
- Version display in bottom left
- Initialize text in bottom center
- Custom styling and positioning
"""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QFontMetrics, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import QApplication, QSplashScreen

from config import APP_VERSION
import logging

logger = logging.getLogger(__name__)


class CustomSplashScreen(QSplashScreen):
    """
    Custom splash screen with version info and initialize text.

    Size: 16:9 aspect ratio with 400px height (711x400)
    """

    def __init__(self, pixmap_path: str):
        """
        Initialize the custom splash screen.

        Args:
            pixmap_path: Path to the splash image
        """
        # Calculate 16:9 aspect ratio dimensions
        self.splash_height = 400
        self.splash_width = int(self.splash_height * 3 / 2)  # 600px

        # Load and scale the pixmap
        original_pixmap = QPixmap(pixmap_path)
        if not original_pixmap.isNull():
            # Scale to our desired size
            scaled_pixmap = original_pixmap.scaled(
                self.splash_width,
                self.splash_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

            # Create a new pixmap with exact dimensions if scaling didn't match
            if scaled_pixmap.width() != self.splash_width or scaled_pixmap.height() != self.splash_height:
                final_pixmap = QPixmap(self.splash_width, self.splash_height)
                final_pixmap.fill(Qt.black)  # Fill with black background

                painter = QPainter(final_pixmap)
                painter.setRenderHint(QPainter.Antialiasing)

                # Center the scaled image
                x = (self.splash_width - scaled_pixmap.width()) // 2
                y = (self.splash_height - scaled_pixmap.height()) // 2
                painter.drawPixmap(x, y, scaled_pixmap)
                painter.end()

                super().__init__(final_pixmap)
            else:
                super().__init__(scaled_pixmap)
        else:
            # Fallback: create a simple black pixmap with app name
            fallback_pixmap = QPixmap(self.splash_width, self.splash_height)
            fallback_pixmap.fill(Qt.black)

            painter = QPainter(fallback_pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(QPen(Qt.white))

            font = QFont("Inter", 24, QFont.Bold)
            painter.setFont(font)
            painter.drawText(
                fallback_pixmap.rect(),
                Qt.AlignCenter,
                "OnCutF"
            )
            painter.end()

            super().__init__(fallback_pixmap)

        # Set window properties
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.SplashScreen | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        # Center on screen
        self._center_on_screen()

        # Set cursor to wait cursor
        self.setCursor(Qt.WaitCursor)

    def _center_on_screen(self):
        """Center the splash screen on the screen, considering saved main window position and multi-monitor setup."""
        try:
            # Try to get the saved main window position from config
            from utils.json_config_manager import get_app_config_manager
            config_manager = get_app_config_manager()
            window_config = config_manager.get_category('window')

            target_screen = None
            target_x = None
            target_y = None

            if window_config:
                geometry = window_config.get('geometry')
                if geometry:
                    # Calculate center of the saved main window position
                    main_window_center_x = geometry['x'] + geometry['width'] // 2
                    main_window_center_y = geometry['y'] + geometry['height'] // 2

                    # Find which screen contains the main window center point
                    app = QApplication.instance()
                    if app:
                        for screen in app.screens():
                            screen_geometry = screen.geometry()
                            if (screen_geometry.x() <= main_window_center_x <= screen_geometry.x() + screen_geometry.width() and
                                screen_geometry.y() <= main_window_center_y <= screen_geometry.y() + screen_geometry.height()):
                                target_screen = screen
                                logger.debug(f"[Splash] Found target screen for saved main window position: {screen.name()}")
                                break

                    if target_screen:
                        # Position splash screen at the center of where main window will appear
                        target_x = main_window_center_x - self.splash_width // 2
                        target_y = main_window_center_y - self.splash_height // 2

                        # Make sure splash screen stays within the target screen bounds
                        screen_geometry = target_screen.geometry()
                        target_x = max(screen_geometry.x(),
                                     min(target_x, screen_geometry.x() + screen_geometry.width() - self.splash_width))
                        target_y = max(screen_geometry.y(),
                                     min(target_y, screen_geometry.y() + screen_geometry.height() - self.splash_height))

                        self.move(target_x, target_y)
                        logger.debug(f"[Splash] Positioned on screen where main window will appear: {target_x}, {target_y}")
                        return

        except Exception as e:
            logger.debug(f"[Splash] Error positioning on target screen: {e}")

        # Fallback: Try to position on primary screen or the screen containing the mouse cursor
        try:
            app = QApplication.instance()
            if app:
                # First try to get the primary screen (this should work better for dual monitor)
                target_screen = app.primaryScreen()
                logger.debug(f"[Splash] Using primary screen: {target_screen.name() if target_screen else 'None'}")

                # If no primary screen found, try to get the screen containing the mouse cursor
                if not target_screen:
                    cursor_pos = app.desktop().cursor().pos() if hasattr(app.desktop().cursor(), 'pos') else None
                    logger.debug(f"[Splash] Cursor position: {cursor_pos}")

                    if cursor_pos:
                        for screen in app.screens():
                            screen_geometry = screen.geometry()
                            if (screen_geometry.x() <= cursor_pos.x() <= screen_geometry.x() + screen_geometry.width() and
                                screen_geometry.y() <= cursor_pos.y() <= screen_geometry.y() + screen_geometry.height()):
                                target_screen = screen
                                logger.debug(f"[Splash] Found screen containing cursor: {screen.name()}")
                                break

                if target_screen:
                    screen_geometry = target_screen.availableGeometry()
                    logger.debug(f"[Splash] Target screen geometry: {screen_geometry.x()}, {screen_geometry.y()}, {screen_geometry.width()}x{screen_geometry.height()}")

                    # Calculate center position on the target screen
                    x = screen_geometry.x() + (screen_geometry.width() - self.splash_width) // 2
                    y = screen_geometry.y() + (screen_geometry.height() - self.splash_height) // 2

                    self.move(x, y)
                    logger.debug(f"[Splash] Positioned on screen {target_screen.name()}: {x}, {y}")
                    return

        except Exception as e:
            logger.debug(f"[Splash] Error with multi-screen positioning: {e}")

        # Ultimate fallback: use deprecated QDesktopWidget for older Qt versions
        try:
            from core.qt_imports import QDesktopWidget
            desktop = QDesktopWidget()

            # Try to get primary screen geometry instead of total desktop
            primary_screen = desktop.primaryScreen()
            screen_geometry = desktop.availableGeometry(primary_screen)

            logger.debug(f"[Splash] Fallback using QDesktopWidget primary screen: {screen_geometry.width()}x{screen_geometry.height()}")

            # Calculate center position on primary screen
            x = screen_geometry.x() + (screen_geometry.width() - self.splash_width) // 2
            y = screen_geometry.y() + (screen_geometry.height() - self.splash_height) // 2

            self.move(x, y)
            logger.debug(f"[Splash] Fallback positioning: {x}, {y}")

        except Exception as e:
            logger.warning(f"[Splash] All positioning methods failed: {e}")
            # Last resort: position at 100, 100
            self.move(100, 100)

    def showMessage(self, message: str, alignment: int = Qt.AlignBottom | Qt.AlignCenter, color=None):
        """
        Override showMessage to add custom text rendering.

        Args:
            message: Message to display
            alignment: Text alignment
            color: Text color (optional)
        """
        # Don't use the default showMessage, we'll handle text in drawContents
        pass

    def drawContents(self, painter: QPainter):
        """
        Custom drawing of splash screen contents.

        Args:
            painter: QPainter instance
        """
        painter.setRenderHint(QPainter.Antialiasing)

        # Set up fonts
        version_font = QFont("Inter", 11, QFont.Normal)
        init_font = QFont("Inter", 9, QFont.Normal)

        # Draw version in bottom left
        painter.setFont(version_font)
        painter.setPen(QPen(Qt.white))

        version_text = f"v{APP_VERSION}"
        QFontMetrics(version_font).boundingRect(version_text)

        version_x = 15  # 15px from left edge
        version_y = self.splash_height - 15  # 15px from bottom

        painter.drawText(version_x, version_y, version_text)

        # Draw "initialize" text in bottom center
        painter.setFont(init_font)
        painter.setPen(QPen(Qt.white))

        init_text = "initialize"
        init_metrics = QFontMetrics(init_font)
        init_rect = init_metrics.boundingRect(init_text)

        init_x = (self.splash_width - init_rect.width()) // 2
        init_y = self.splash_height - 25  # 25px from bottom

        painter.drawText(init_x, init_y, init_text)

    def finish(self, widget):
        """
        Override finish to restore cursor.

        Args:
            widget: Widget to finish splash for
        """
        # Restore cursor before finishing
        self.setCursor(Qt.ArrowCursor)
        QApplication.restoreOverrideCursor()
        super().finish(widget)

    def close(self):
        """Override close to restore cursor."""
        self.setCursor(Qt.ArrowCursor)
        QApplication.restoreOverrideCursor()
        super().close()
