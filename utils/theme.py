"""
Module: theme.py

Author: Michael Economou
Date: 2025-05-01

This utility module is responsible for loading the application's stylesheet
from external `.qss` files. It provides helper functions to apply consistent
theming across all UI components of oncutf.

Typically used during application startup to apply a dark or light theme.

Supports:
- Loading QSS from file path or resource
- Applying styles to QApplication instance
"""

import os

# Initialize Logger
from utils.logger_helper import get_logger
logger = get_logger(__name__)

def load_stylesheet() -> str:
    """
    Loads the global QSS stylesheet from file.

    Returns:
        str: The contents of the stylesheet, or empty string if not found.
    """
    qss_path = os.path.join(os.path.dirname(__file__), "dark_theme.qss")

    if os.path.exists(qss_path):
        with open(qss_path, "r", encoding="utf-8") as file:
            return file.read()
    return ""
