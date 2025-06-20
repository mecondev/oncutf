#! /usr/bin/env python3
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

import datetime
import sys
import platform

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QStyleFactory

from main_window import MainWindow
from utils.fonts import _get_inter_fonts

# Initialize logging system
from utils.logger_setup import ConfigureLogger
from utils.theme import load_stylesheet

ConfigureLogger(log_name="oncutf")

import logging

logger = logging.getLogger()

# Log application start with current date/time
now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
        # Create application
        app = QApplication(sys.argv)
        # Qt.AA_UseHighDpiPixmaps is defined in PyQt5, but linter may not resolve C++-level attributes
        app.setAttribute(Qt.AA_UseHighDpiPixmaps) # type: ignore[attr-defined]

        # Set native style for proper system cursor integration (simplified logging)
        system = platform.system()
        available_styles = QStyleFactory.keys()

        if system == "Windows" and "windowsvista" in available_styles:
            app.setStyle("windowsvista")
            logger.debug("Using Windows Vista style", extra={"dev_only": True})
        elif system == "Windows" and "Windows" in available_styles:
            app.setStyle("Windows")
            logger.debug("Using Windows style", extra={"dev_only": True})
        elif system == "Darwin":  # macOS
            logger.debug("Using default macOS style", extra={"dev_only": True})
        elif system == "Linux":
            # Try to use native style if available
            for style in available_styles:
                if "gtk" in style.lower():
                    app.setStyle(style)
                    logger.debug(f"Using {style} style on Linux", extra={"dev_only": True})
                    break
            else:
                logger.debug("Using Fusion style on Linux", extra={"dev_only": True})

        logger.debug(f"Qt style: {app.style().objectName()}", extra={"dev_only": True}) # type: ignore

        # Load Inter fonts
        logger.debug("Initializing Inter fonts...", extra={"dev_only": True})
        _get_inter_fonts()

        app.setStyleSheet(load_stylesheet())

        # Create and show main window
        window = MainWindow()
        window.show()

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


