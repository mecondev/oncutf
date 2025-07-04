#!/usr/bin/env python3
"""
Module: main.py

Author: Michael Economou
Date: 2025-05-01

This module serves as the entry point for the oncutf application.
It sets up logging, initializes the Qt application with a stylesheet, creates
and displays the main window, and starts the application's main event loop.

Functions:
    main: Initializes and runs the Batch File Renamer application.
"""

import logging
import platform
import sys
import time
from pathlib import Path

from core.qt_imports import Qt, QTimer, QApplication, QStyleFactory

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import SPLASH_SCREEN_DURATION
from main_window import MainWindow
from utils.fonts import _get_inter_fonts
from utils.logger_setup import ConfigureLogger
from utils.theme_engine import ThemeEngine
from widgets.custom_splash_screen import CustomSplashScreen

# Configure logging first
ConfigureLogger(log_name="oncutf")

logger = logging.getLogger()

# Log application start with current date/time
now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
logger.info(f"Application started at {now}")

logger_effective_level =logger.getEffectiveLevel()
logger.debug(f"Effective logging level: {logger_effective_level}", extra={"dev_only": True})

def main() -> int:
    """
    Entry point for the Batch File Renamer application.

    Initializes logging, creates a Qt application and stylesheet, creates a
    MainWindow and shows it, and enters the application's main loop.
    """
    try:
        # Enable High DPI support before creating QApplication
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)  # type: ignore[attr-defined]
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)  # type: ignore[attr-defined]

        # Create application
        app = QApplication(sys.argv)

        # Initialize DPI helper early
        from utils.dpi_helper import get_dpi_helper, log_dpi_info
        dpi_helper = get_dpi_helper()
        log_dpi_info()

        # Log font sizes for debugging
        try:
            from utils.theme_font_generator import get_ui_font_sizes
            font_sizes = get_ui_font_sizes()
            logger.info(f"[DPI] Applied font sizes: {font_sizes}")
        except ImportError:
            logger.warning("[DPI] Could not get font sizes - DPI helper not available")

        # Set native style for better system integration
        system = platform.system()
        if system == "Windows":
            available_styles = QStyleFactory.keys()
            if "windowsvista" in available_styles:
                app.setStyle("windowsvista")
        elif system == "Linux":
            available_styles = QStyleFactory.keys()
            for style in available_styles:
                if "gtk" in style.lower():
                    app.setStyle(style)
                    break

        # Load Inter fonts
        logger.debug("Initializing Inter fonts...", extra={"dev_only": True})
        _get_inter_fonts()

        # Initialize theme engine
        theme_manager = ThemeEngine()

        # We'll apply the theme after creating the main window

        # Create custom splash screen
        from utils.path_utils import get_images_dir
        splash_path = get_images_dir() / "splash.png"
        logger.debug(f"Loading custom splash screen from: {splash_path}", extra={"dev_only": True})

        # Set application-wide wait cursor
        app.setOverrideCursor(Qt.WaitCursor) # type: ignore[attr-defined]

        try:
            # Create custom splash screen
            splash = CustomSplashScreen(str(splash_path))
            splash.show()
            splash.raise_()  # Bring to front
            splash.activateWindow()  # Activate the window
            app.processEvents()  # Force paint of splash

            logger.debug(f"Custom splash screen displayed (size: {splash.splash_width}x{splash.splash_height})", extra={"dev_only": True})

            # Initialize app
            window = MainWindow()

            # Apply programmatic theme to the entire application
            theme_manager.apply_complete_theme(app, window)

            # Show main window and close splash
            def show_main():
                logger.debug("Hiding splash screen and showing main window", extra={"dev_only": True})
                splash.finish(window)
                window.show()
                window.raise_()  # Bring main window to front
                window.activateWindow()  # Activate the main window
                app.processEvents()  # Force UI update
                # Restore normal cursor
                app.restoreOverrideCursor()

            # Use configurable delay for splash screen with timer manager
            from utils.timer_manager import get_timer_manager, TimerType
            get_timer_manager().schedule(
                show_main,
                delay=SPLASH_SCREEN_DURATION,
                timer_type=TimerType.GENERIC
            )

        except Exception as e:
            logger.error(f"Error creating custom splash screen: {e}")
            # Fallback: Initialize app without splash
            app.restoreOverrideCursor()
            window = MainWindow()
            window.show()
            window.raise_()  # Bring main window to front
            window.activateWindow()  # Activate the main window

        # Run the app
        exit_code = app.exec_()

        # Clean up before exit
        logger.info("Application shutting down with exit code: %d", exit_code)

        # Force quit any remaining processes
        app.quit()

        return exit_code

    except Exception as e:
        logger.critical("Fatal error in main: %s", str(e), exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())


