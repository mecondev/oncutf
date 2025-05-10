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

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from main_window import MainWindow
from utils.theme import load_stylesheet

from logger_setup import ConfigureLogger
from logger_helper import get_logger

# Initialize logging system
ConfigureLogger(log_name="oncutf")

# Logger for this module
logger = get_logger(__name__)

logger.info("Application started")


def main() -> None:
    # Setup logging
    """
    Entry point for the Batch File Renamer application.

    Initializes logging, creates a Qt application and stylesheet, creates a
    MainWindow and shows it, and enters the application's main loop.
    """

    # Create application
    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app.setStyleSheet(load_stylesheet())

    # Create and show main window
    window = MainWindow()
    window.show()

    # Run the app
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
