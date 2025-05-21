"""
theme.py

Loads and combines modular QSS files for the selected application theme.
Supports expansion for light/dark themes and separates widget styles.

Current implementation loads the 'dark' theme from style/dark_theme/.

Author: Michael Economou
Date: 2025-05-21
"""

import os
from config import THEME_NAME

def load_stylesheet() -> str:
    """
    Loads the stylesheet based on THEME_NAME defined in config.py.
    """
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "style", f"{THEME_NAME}_theme"))
    qss_files = [
        "base.qss",
        "table_view.qss",
        "tree_view.qss",
        "combo_box.qss",
        "buttons.qss",
        "scrollbars.qss"
    ]

    full_style = ""
    for filename in qss_files:
        path = os.path.join(base_dir, filename)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                full_style += f.read() + "\n"

    return full_style
