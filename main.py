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

import atexit
import logging
import locale
import os
import platform
import signal
import sys
import time

# Add the project root to the path FIRST - before any local imports
# Normalize the path for Windows compatibility
project_root = os.path.normpath(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.pyqt_imports import QApplication, QStyleFactory, Qt

from config import SPLASH_SCREEN_DURATION
from main_window import MainWindow
from utils.fonts import _get_inter_fonts
from utils.logger_setup import ConfigureLogger
from utils.theme_engine import ThemeEngine
from widgets.custom_splash_screen import CustomSplashScreen


# Calculate the user config directory for logs
def get_user_config_dir(app_name: str = "oncutf") -> str:
    """Get user configuration directory based on OS."""
    if os.name == "nt":
        base_dir = os.environ.get("APPDATA", os.path.expanduser("~"))
        return os.path.join(base_dir, app_name)
    else:
        base_dir = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
        return os.path.join(base_dir, app_name)


# Configure logging to use user config directory
config_dir = get_user_config_dir()
logs_dir = os.path.join(config_dir, "logs")
ConfigureLogger(log_name="oncutf", log_dir=logs_dir)

logger = logging.getLogger()

# Log application start with current date/time
now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
logger.info(f"Application started at {now}")

logger_effective_level = logger.getEffectiveLevel()
logger.debug(f"Effective logging level: {logger_effective_level}", extra={"dev_only": True})


def cleanup_on_exit():
    """Cleanup function to run on application exit or signal."""
    try:
        from utils.exiftool_wrapper import ExifToolWrapper

        ExifToolWrapper.force_cleanup_all_exiftool_processes()
        logger.info("Emergency ExifTool cleanup completed")
    except Exception as e:
        logger.warning(f"Error in emergency cleanup: {e}")


def signal_handler(signum, _frame):
    """Handle signals for graceful shutdown."""
    logger.info(f"Received signal {signum}, performing cleanup...")
    cleanup_on_exit()
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# Register atexit cleanup
atexit.register(cleanup_on_exit)


def main() -> int:
    """
    Entry point for the Batch File Renamer application.

    Initializes logging, creates a Qt application and stylesheet, creates a
    MainWindow and shows it, and enters the application's main loop.
    """
    try:
        # Log platform information for debugging
        logger.info(f"Platform: {platform.system()} {platform.release()}")
        logger.info(f"Python version: {sys.version}")
        logger.debug(f"Project root: {project_root}", extra={"dev_only": True})
        
        # Log Windows-specific info
        if platform.system() == "Windows":
            logger.info(f"Windows version: {platform.win32_ver()}")
            import locale
            logger.info(f"System locale: {locale.getdefaultlocale()}")
            logger.info(f"File system encoding: {sys.getfilesystemencoding()}")
        
        # Enable High DPI support before creating QApplication
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)  # type: ignore[attr-defined]
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)  # type: ignore[attr-defined]

        # Create application
        app = QApplication(sys.argv)
        
        # Log locale information (important for date/time formatting)
        try:
            current_locale = locale.getlocale()
            logger.debug(f"Current locale: {current_locale}", extra={"dev_only": True})
        except Exception as e:
            logger.warning(f"Could not get locale: {e}")

        # Initialize DPI helper early
        from utils.dpi_helper import get_dpi_helper, log_dpi_info

        get_dpi_helper()  # Initialize but don't store
        log_dpi_info()

        # Log font sizes for debugging
        try:
            from utils.theme_font_generator import get_ui_font_sizes

            font_sizes = get_ui_font_sizes()
            logger.debug(f"Applied font sizes: {font_sizes}", extra={"dev_only": True})
        except ImportError:
            logger.warning("Could not get font sizes - DPI helper not available")

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

        # Create custom splash screen
        from utils.path_utils import get_images_dir

        splash_path = get_images_dir() / "splash.png"
        logger.debug(f"Loading splash screen from: {splash_path}", extra={"dev_only": True})

        # Set application-wide wait cursor
        app.setOverrideCursor(Qt.WaitCursor)  # type: ignore[attr-defined]

        try:
            # Create custom splash screen
            splash = CustomSplashScreen(str(splash_path))
            splash.show()
            splash.raise_()
            splash.activateWindow()
            app.processEvents()

            logger.debug(
                f"Splash screen displayed (size: {splash.splash_width}x{splash.splash_height})",
                extra={"dev_only": True},
            )

            # Initialize app
            window = MainWindow()

            # Apply programmatic theme to the entire application
            theme_manager.apply_complete_theme(app, window)

            # Show main window and close splash
            def show_main():
                logger.debug("Showing main window", extra={"dev_only": True})
                splash.finish(window)
                window.show()
                window.raise_()
                window.activateWindow()
                app.processEvents()
                app.restoreOverrideCursor()

            # Use configurable delay for splash screen with timer manager
            from utils.timer_manager import TimerType, get_timer_manager

            get_timer_manager().schedule(
                show_main, delay=SPLASH_SCREEN_DURATION, timer_type=TimerType.GENERIC
            )

        except Exception as e:
            logger.error(f"Error creating splash screen: {e}")
            # Fallback: Initialize app without splash
            app.restoreOverrideCursor()
            window = MainWindow()
            window.show()
            window.raise_()
            window.activateWindow()

        # Run the app
        exit_code = app.exec_()

        # Clean up before exit
        logger.info("Application shutting down with exit code: %d", exit_code)

        # Force cleanup any remaining ExifTool processes
        try:
            from utils.exiftool_wrapper import ExifToolWrapper

            ExifToolWrapper.force_cleanup_all_exiftool_processes()
            logger.info("ExifTool processes cleaned up")
        except Exception as e:
            logger.warning(f"Error cleaning up ExifTool processes: {e}")

        # Force quit any remaining processes
        app.quit()

        return exit_code

    except Exception as e:
        logger.critical("Fatal error in main: %s", str(e), exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
