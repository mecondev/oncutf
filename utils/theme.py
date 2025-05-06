# theme.py
# Author: Michael Economou
# Date: 2025-05-01
# Description: Utility to load the application stylesheet from file.

import os

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
