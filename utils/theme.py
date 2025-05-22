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

# Initialize Logger
from utils.logger_helper import get_logger
logger = get_logger(__name__)

def load_stylesheet() -> str:
    """
    Loads the stylesheet based on THEME_NAME defined in config.py.
    """
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "style", f"{THEME_NAME}_theme"))
    qss_files = [
        "base.qss",
        "buttons.qss",
        #"combo_box.qss",
        "scrollbars.qss",
        "table_view.qss",
        "tree_view.qss"
    ]

    full_style = ""
    for filename in qss_files:
        path = os.path.join(base_dir, filename)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                qss = f.read()
                full_style += qss + "\n"
                logger.debug(f"[DEBUG] Loaded {filename} ({len(qss)} characters)")
        else:
            logger.warning(f"[WARNING] QSS file not found: {filename}")

    return full_style
