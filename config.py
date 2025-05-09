"""
Module: config.py

Author: Michael Economou
Date: 2025-05-01

This module defines global configuration constants and settings used
throughout the oncutf application. It centralizes UI defaults, file
filters, path definitions, and other shared parameters.

Intended to be imported wherever consistent application-wide settings
are required.

Contains:
- Default UI settings
- File extension filters
- Paths to resources and stylesheets
"""


# Window
WINDOW_TITLE = "Batch File Renamer"
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 900
WINDOW_MIN_WIDTH = 800
WINDOW_MIN_HEIGHT = 500

# Splitter sizes
TOP_BOTTOM_SPLIT_RATIO = [550, 350]
LEFT_CENTER_RIGHT_SPLIT_RATIO = [220, 830, 200]
BOTTOM_MODULE_PREVIEW_RATIO = [450, 750]

# Preview columns
PREVIEW_COLUMN_WIDTH = 300
PREVIEW_MIN_WIDTH = 200

# Layout Margins (used in window, layout spacing, etc.)
CONTENT_MARGINS = {
    "top": 8,
    "bottom": 8,
    "left": 8,
    "right": 8,
}


# Allowed file extensions
ALLOWED_EXTENSIONS = {
    "jpg", "jpeg", "png", "mp3", "mp4", "mov", "mts", "nef", "raw", "arw", "cr2",
    "txt", "csv", "xml", "pdf", "doc", "docx", "xls", "xlsx"
}

# Regex pattern for Windows-safe names
ALLOWED_FILENAME_CHARS = r"^[^\\/:*?\"<>|]+$"

# Theme
DARK_THEME = "dark_theme.qss"
LIGHT_THEME = "light_theme.qss"

# ----------------------------
# Preview Indicator Settings
# ----------------------------
PREVIEW_COLORS = {
    "valid": "#2ecc71",     # Green
    "duplicate": "#e67e22",  # Orange
    "invalid": "#c0392b",    # Red
    "unchanged": "#777777"   # Gray
}

PREVIEW_INDICATOR_SHAPE = "circle"  # or "square"
PREVIEW_INDICATOR_SIZE = (10, 10)    # Width, Height in pixels
PREVIEW_INDICATOR_BORDER = {
    "color": "#222222",
    "thickness": 1
}

USE_PREVIEW_BACKGROUND = False  # Whether to apply background color in tables

