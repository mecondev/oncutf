"""Module: custom_splash_screen.py.

Author: Michael Economou
Date: 2025-06-23

custom_splash_screen.py
Custom splash screen widget for the oncutf application.
Features:
- Custom size (16:9 aspect ratio with 400px height)
- Version display in bottom left
- Initialize text in bottom center with animated dots
- Custom styling and positioning
- Blocks application interaction until closed
"""

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QFontMetrics, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import QApplication, QSplashScreen

from oncutf.config import APP_VERSION
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class CustomSplashScreen(QSplashScreen):
    """Custom splash screen with version info and animated initialize text.

    Size: 16:9 aspect ratio with 400px height (711x400)
    """

    def __init__(self, pixmap_path: str):
        """Initialize the custom splash screen.

        Args:
            pixmap_path: Path to the splash image

        """
        # Calculate 16:9 aspect ratio dimensions
        self.splash_height = 400
        self.splash_width = int(self.splash_height * 3 / 2)  # 600px

        # Animation state for dots
        self.dots_count = 0

        # Load and scale the pixmap
        original_pixmap = QPixmap(pixmap_path)
        if not original_pixmap.isNull():
            # Scale to our desired size
            scaled_pixmap = original_pixmap.scaled(
                self.splash_width, self.splash_height, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )

            # Create a new pixmap with exact dimensions if scaling didn't match
            if (
                scaled_pixmap.width() != self.splash_width
                or scaled_pixmap.height() != self.splash_height
            ):
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

            # Use our custom InterDisplay-SemiBold for title
            from oncutf.ui.helpers.fonts import get_default_ui_font, get_inter_font

            try:
                font = get_inter_font("titles", 24)  # Uses InterDisplay-SemiBold
            except (ImportError, AttributeError):
                font = get_default_ui_font(size=24, style="bold")  # Fallback
            painter.setFont(font)
            painter.drawText(fallback_pixmap.rect(), Qt.AlignCenter, "oncutf")
            painter.end()

            super().__init__(fallback_pixmap)

        # Set window properties to block interaction with main application
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.SplashScreen | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        # Make splash screen modal to block interaction with other windows
        self.setWindowModality(Qt.ApplicationModal)

        # Center on screen
        self._center_on_screen()

        # Timer for dots animation (must be after super().__init__())
        self.dots_timer = QTimer(self)
        self.dots_timer.timeout.connect(self._animate_dots)
        self.dots_timer.start(500)  # 500ms interval

        # Set cursor to wait cursor
        self.setCursor(Qt.WaitCursor)

    def _center_on_screen(self):
        """Center the splash screen on the screen, considering saved main window position and multi-monitor setup."""
        try:
            # Try to get the saved main window position from config
            from oncutf.utils.shared.json_config_manager import get_app_config_manager

            config_manager = get_app_config_manager()
            window_config = config_manager.get_category("window")

            target_screen = None
            target_x = None
            target_y = None

            if window_config:
                geometry = window_config.get("geometry")
                if geometry:
                    # Calculate center of the saved main window position
                    main_window_center_x = geometry["x"] + geometry["width"] // 2
                    main_window_center_y = geometry["y"] + geometry["height"] // 2

                    # Find which screen contains the main window center point
                    app = QApplication.instance()
                    if app:
                        for screen in app.screens():
                            screen_geometry = screen.geometry()
                            if (
                                screen_geometry.x()
                                <= main_window_center_x
                                <= screen_geometry.x() + screen_geometry.width()
                                and screen_geometry.y()
                                <= main_window_center_y
                                <= screen_geometry.y() + screen_geometry.height()
                            ):
                                target_screen = screen
                                logger.debug(
                                    "[Splash] Found target screen for saved main window position: %s",
                                    screen.name(),
                                )
                                break

                    if target_screen:
                        # Position splash screen at the center of where main window will appear
                        target_x = main_window_center_x - self.splash_width // 2
                        target_y = main_window_center_y - self.splash_height // 2

                        # Make sure splash screen stays within the target screen bounds
                        screen_geometry = target_screen.geometry()
                        target_x = max(
                            screen_geometry.x(),
                            min(
                                target_x,
                                screen_geometry.x() + screen_geometry.width() - self.splash_width,
                            ),
                        )
                        target_y = max(
                            screen_geometry.y(),
                            min(
                                target_y,
                                screen_geometry.y() + screen_geometry.height() - self.splash_height,
                            ),
                        )

                        self.move(target_x, target_y)
                        logger.debug(
                            "[Splash] Positioned on screen where main window will appear: %d, %d",
                            target_x,
                            target_y,
                        )
                        return

        except Exception as e:
            logger.debug("[Splash] Error positioning on target screen: %s", e)

        # Fallback: Try to position on primary screen or the screen containing the mouse cursor
        try:
            app = QApplication.instance()
            if app:
                # First try to get the primary screen (this should work better for dual monitor)
                target_screen = app.primaryScreen()
                logger.debug(
                    "[Splash] Using primary screen: %s",
                    target_screen.name() if target_screen else "None",
                )

                # If no primary screen found, try to get the screen containing the mouse cursor
                if not target_screen:
                    cursor_pos = (
                        app.desktop().cursor().pos()
                        if hasattr(app.desktop().cursor(), "pos")
                        else None
                    )
                    logger.debug("[Splash] Cursor position: %s", cursor_pos)

                    if cursor_pos:
                        for screen in app.screens():
                            screen_geometry = screen.geometry()
                            if (
                                screen_geometry.x()
                                <= cursor_pos.x()
                                <= screen_geometry.x() + screen_geometry.width()
                                and screen_geometry.y()
                                <= cursor_pos.y()
                                <= screen_geometry.y() + screen_geometry.height()
                            ):
                                target_screen = screen
                                logger.debug(
                                    "[Splash] Found screen containing cursor: %s",
                                    screen.name(),
                                )
                                break

                if target_screen:
                    screen_geometry = target_screen.availableGeometry()
                    logger.debug(
                        "[Splash] Target screen geometry: %d, %d, %dx%d",
                        screen_geometry.x(),
                        screen_geometry.y(),
                        screen_geometry.width(),
                        screen_geometry.height(),
                    )

                    # Calculate center position on the target screen
                    x = screen_geometry.x() + (screen_geometry.width() - self.splash_width) // 2
                    y = screen_geometry.y() + (screen_geometry.height() - self.splash_height) // 2

                    self.move(x, y)
                    logger.debug(
                        "[Splash] Positioned on screen %s: %d, %d",
                        target_screen.name(),
                        x,
                        y,
                    )
                    return

        except Exception as e:
            logger.debug("[Splash] Error with multi-screen positioning: %s", e)

        # Ultimate fallback: use modern QScreen API instead of deprecated QDesktopWidget
        try:
            app = QApplication.instance()
            if app and hasattr(app, "primaryScreen"):
                primary_screen = app.primaryScreen()
                if primary_screen:
                    screen_geometry = primary_screen.availableGeometry()

                    logger.debug(
                        "[Splash] Fallback using QScreen API primary screen: %dx%d",
                        screen_geometry.width(),
                        screen_geometry.height(),
                    )

                    # Calculate center position on primary screen
                    x = screen_geometry.x() + (screen_geometry.width() - self.splash_width) // 2
                    y = screen_geometry.y() + (screen_geometry.height() - self.splash_height) // 2

                    self.move(x, y)
                    logger.debug("[Splash] Positioned using QScreen API: %d, %d", x, y)
                    return

        except Exception as e:
            logger.debug("[Splash] Error with QScreen API positioning: %s", e)

        # Final fallback: fixed position
        logger.debug("[Splash] Using fixed fallback position")
        self.move(100, 100)

    def _animate_dots(self) -> None:
        """Animate the dots in the initialize text."""
        self.dots_count += 1
        self.repaint()  # Force repaint to show new dots

    def showMessage(
        self, message: str, alignment: int = Qt.AlignBottom | Qt.AlignCenter, color=None
    ):
        """Override showMessage to add custom text rendering.

        Args:
            message: Message to display
            alignment: Text alignment
            color: Text color (optional)

        """
        # Don't use the default showMessage, we'll handle text in drawContents

    def drawContents(self, painter: QPainter):
        """Custom drawing of splash screen contents.

        Args:
            painter: QPainter instance

        """
        painter.setRenderHint(QPainter.Antialiasing)

        # Set up fonts using our custom font system
        from oncutf.ui.helpers.fonts import get_default_ui_font, get_inter_font

        try:
            version_font = get_inter_font("base", 11)  # Uses Inter-Regular
            init_font = get_inter_font("base", 9)  # Uses Inter-Regular
        except (ImportError, AttributeError):
            # Fallback to default UI font
            version_font = get_default_ui_font(size=11)
            init_font = get_default_ui_font(size=9)

        # Draw version in bottom left
        painter.setFont(version_font)
        painter.setPen(QColor(255, 255, 255, 180))  # Semi-transparent white

        version_text = f"v{APP_VERSION}"
        QFontMetrics(version_font).boundingRect(version_text)

        version_x = 15  # 15px from left edge
        version_y = self.splash_height - 15  # 15px from bottom

        painter.drawText(version_x, version_y, version_text)

        # Draw "initialize" text in bottom center
        painter.setFont(init_font)
        painter.setPen(QPen(Qt.white))

        init_text = "initialize"

        # Add animated dots to the initialize text
        dots = "." * self.dots_count
        init_text_with_dots = f"{init_text}{dots}"

        # Calculate position to keep text centered based on base text width
        init_metrics = QFontMetrics(init_font)
        base_text_width = init_metrics.boundingRect(init_text).width()

        # Center based on the base text width (without dots)
        init_x = (self.splash_width - base_text_width) // 2
        init_y = self.splash_height - 25  # 25px from bottom

        painter.drawText(init_x, init_y, init_text_with_dots)

    def finish(self, widget):
        """Override finish to restore cursor and stop animation.

        Args:
            widget: Widget to finish splash for

        """
        # Stop the dots animation timer
        if hasattr(self, "dots_timer"):
            self.dots_timer.stop()

        # Restore cursor before finishing
        self.setCursor(Qt.ArrowCursor)
        QApplication.restoreOverrideCursor()
        super().finish(widget)

    def close(self):
        """Override close to restore cursor and stop animation."""
        # Stop the dots animation timer
        if hasattr(self, "dots_timer"):
            self.dots_timer.stop()

        self.setCursor(Qt.ArrowCursor)
        QApplication.restoreOverrideCursor()
        super().close()

    def mousePressEvent(self, event):
        """Override mouse press to prevent cursor changes."""
        # Ignore mouse events to keep wait cursor
        event.ignore()

    def mouseReleaseEvent(self, event):
        """Override mouse release to prevent cursor changes."""
        # Ignore mouse events to keep wait cursor
        event.ignore()

    def mouseMoveEvent(self, event):
        """Override mouse move to prevent cursor changes."""
        # Ignore mouse events to keep wait cursor
        event.ignore()
