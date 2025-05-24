"""
icon_loader.py

Author: Michael Economou
Date: 2025-05-20

This utility provides a helper function to load metadata status icons
for use in the metadata icon delegate (ℹ️ icons in column 0).

Each status ('loaded', 'missing', etc.) maps to a colored info icon.

Usage:
    from utils.icon_loader import load_metadata_icons
    icon_map = load_metadata_icons()
"""

from PyQt5.QtGui import QPixmap
import os
import logging

logger = logging.getLogger(__name__)

def load_metadata_icons(base_dir: str = "resources/icons") -> dict[str, QPixmap]:
    icon_files = {
        'loaded': "info_green.png",
        'extended': "info_orange.png",
        'partial': "info_gray.png",
        'invalid': "info_red.png",
    }

    icon_map = {}
    for status, filename in icon_files.items():
        path = os.path.join(base_dir, filename)
        pixmap = QPixmap(path)
        if pixmap.isNull():
            logger.warning(f"[IconLoader] Failed to load icon for '{status}' from {path}")
        icon_map[status] = pixmap

    return icon_map
