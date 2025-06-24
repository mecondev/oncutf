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
        """Center the splash screen on the screen."""
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()

        # Calculate center position
        x = (screen_geometry.width() - self.splash_width) // 2
        y = (screen_geometry.height() - self.splash_height) // 2

        self.move(x, y)

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
