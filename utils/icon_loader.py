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

def load_metadata_icons(base_dir: str = "resources/icons") -> dict[str, QPixmap]:
    return {
        'loaded': QPixmap(f"{base_dir}/info_green.png"),
        'extended': QPixmap(f"{base_dir}/info_orange.png"),
        'partial': QPixmap(f"{base_dir}/info_gray.png"),
        'invalid': QPixmap(f"{base_dir}/info_red.png"),
    }
