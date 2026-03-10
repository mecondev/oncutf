#!/usr/bin/env python3
"""Module: main.py.

Author: Michael Economou
Date: 2025-05-01

Thin entry point for the oncutf application.  Lifecycle handlers, splash-screen
orchestration, and shutdown logic live in ``oncutf.boot.lifecycle`` and
``oncutf.boot.startup_orchestrator`` respectively.
"""

import logging
import os
import platform
import sys
import time
from pathlib import Path

# Add the project root to the path FIRST - before any local imports
project_root = str(Path(__file__).resolve().parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from oncutf.boot.lifecycle import (
    perform_emergency_cleanup,
    perform_graceful_shutdown,
    setup_lifecycle_handlers,
)
from oncutf.boot.startup_orchestrator import run_startup
from oncutf.ui.helpers.fonts import _get_inter_fonts, _get_jetbrains_fonts
from oncutf.ui.theme_manager import get_theme_manager
from oncutf.utils.logging.logger_setup import ConfigureLogger
from oncutf.utils.paths import AppPaths

# Configure logging to use centralized user data directory
logs_dir = str(AppPaths.get_logs_dir())
ConfigureLogger(log_name="oncutf", log_dir=logs_dir)

logger = logging.getLogger()

# Log application start with current date/time
now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
logger.info("[App] Application started at %s", now)

logger_effective_level = logger.getEffectiveLevel()
logger.debug("Effective logging level: %d", logger_effective_level, extra={"dev_only": True})

# Register signal handlers, atexit cleanup, and global exception handler
setup_lifecycle_handlers()


def main() -> int:
    """Entry point for the oncutf application."""
    try:
        # CRITICAL: Set working directory to project root first
        os.chdir(project_root)
        logger.info("[App] Working directory set to: %s", Path.cwd())

        # Log platform information for debugging
        logger.info("[App] Platform: %s %s", platform.system(), platform.release())
        logger.info("[App] Python version: %s", sys.version)
        logger.debug("Project root: %s", project_root, extra={"dev_only": True})

        # Log Windows-specific info
        if platform.system() == "Windows":
            logger.info("[App] Windows version: %s", platform.win32_ver())
            import locale

            logger.info("[App] System locale: %s", locale.getlocale())
            logger.info("[App] File system encoding: %s", sys.getfilesystemencoding())

        # Enable High DPI support before creating QApplication
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        # Acquire lock file to prevent multiple instances
        from oncutf.utils.lock_file import acquire_lock

        if not acquire_lock():
            logger.error("[App] Another instance is already running. Exiting.")
            print("ERROR: Another instance of oncutf is already running.")
            print("Please close the other instance first.")
            return 1

        # Create application
        app = QApplication(sys.argv)
        logger.info("[App] QApplication created")

        # Show splash screen IMMEDIATELY for responsiveness (simple version first)
        splash = None
        try:
            from oncutf.ui.widgets.custom_splash_screen import CustomSplashScreen
            from oncutf.utils.filesystem.path_utils import get_images_dir

            splash_path = get_images_dir() / "splash.png"
            if splash_path.exists():
                splash = CustomSplashScreen(str(splash_path))
                splash.show()
                splash.raise_()
                splash.activateWindow()
                app.processEvents()
                logger.info("[App] Splash screen shown immediately at startup")
        except Exception as e:
            logger.warning("[App] Could not show splash screen: %s", e)
            splash = None

        # Set wait cursor for responsiveness while initializing
        try:
            from oncutf.ui.helpers.cursor_helper import wait_cursor
            wait_cursor(show=True)
        except Exception:
            pass

        # Continue with remaining initialization while splash is visible
        # Initialize theme manager early (needed for splash screen updates)
        theme_manager = get_theme_manager()
        logger.debug(
            "ThemeManager initialized with theme: %s",
            theme_manager.get_current_theme(),
            extra={"dev_only": True},
        )

        # Log locale information (important for date/time formatting)
        try:
            import locale

            current_locale = locale.getlocale()
            logger.debug("Current locale: %s", current_locale, extra={"dev_only": True})
        except Exception as e:
            logger.warning("Could not get locale: %s", e)

        # Initialize DPI helper early
        from oncutf.ui.helpers.dpi_helper import get_dpi_helper, log_dpi_info

        get_dpi_helper()  # Initialize but don't store
        log_dpi_info()

        # Log font sizes for debugging
        try:
            from oncutf.ui.helpers.theme_font_generator import get_ui_font_sizes

            font_sizes = get_ui_font_sizes()
            logger.debug("Applied font sizes: %s", font_sizes, extra={"dev_only": True})
        except ImportError:
            logger.warning("Could not get font sizes - DPI helper not available")

        # Set Fusion style for consistent cross-platform rendering
        app.setStyle("Fusion")
        logger.debug(
            "Applied Fusion style for cross-platform consistency",
            extra={"dev_only": True},
        )

        # Load Inter fonts
        logger.debug("Initializing Inter fonts...", extra={"dev_only": True})
        _get_inter_fonts()

        # Load JetBrains Mono fonts
        logger.debug("Initializing JetBrains Mono fonts...", extra={"dev_only": True})
        _get_jetbrains_fonts()

        # Configure default services for dependency injection
        logger.debug("Configuring default services...", extra={"dev_only": True})
        from oncutf.app.ports import configure_default_services

        configure_default_services()
        logger.info("[App] Default services configured")

        # Boot worker + MainWindow initialization (splash already visible)
        run_startup(app, theme_manager, splash=splash)

        # Run the Qt event loop
        exit_code = app.exec_()

        return perform_graceful_shutdown(app, exit_code)

    except Exception:
        logger.exception("Fatal error in main")
        perform_emergency_cleanup()
        return 1


if __name__ == "__main__":
    sys.exit(main())
