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
from PyQt5.QtCore import Qt

# Debugging Set to False to disable debug.log output
SHOW_DEV_ONLY_IN_CONSOLE = False
ENABLE_DEBUG_LOG_FILE = True

# Which key skips the metadata scan when held down
SKIP_METADATA_MODIFIER = Qt.ControlModifier
DEFAULT_SKIP_METADATA = True

# App info
APP_NAME = "oncutf"
APP_VERSION = "1.1"

# Window
WINDOW_TITLE = "Batch File Renamer"
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 900
WINDOW_MIN_WIDTH = 800
WINDOW_MIN_HEIGHT = 500

# Splitter sizes
TOP_BOTTOM_SPLIT_RATIO = [500, 300]
LEFT_CENTER_RIGHT_SPLIT_RATIO = [180, 565, 240]
# BOTTOM_MODULE_PREVIEW_RATIO = [450, 750]

# Preview columns
PREVIEW_COLUMN_WIDTH = 350
PREVIEW_MIN_WIDTH = 250

# Layout Margins (used in window, layout spacing, etc.)
CONTENT_MARGINS = {
    "top": 8,
    "bottom": 8,
    "left": 8,
    "right": 8,
}

# Allowed file extensions
ALLOWED_EXTENSIONS = {
    "jpg", "jpeg", "png", "mp3", "mp4", "mov", "mts", "nef", "raw", "arw", "cr2", "cr3",
    "wav", "txt", "csv", "xml", "pdf", "doc", "docx", "xls", "xlsx"
}

# Regex pattern for Windows-safe names
ALLOWED_FILENAME_CHARS = r"^[^\\/:*?\"<>|]+$"

# Theme
THEME_NAME = "dark"

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

# ----------------------------
# File Handling Settings
# ----------------------------
USE_PREVIEW_BACKGROUND = False  # Whether to apply background color in tables
LARGE_FOLDER_WARNING_THRESHOLD = 150 # Number when to prompt QuestionDialog to load large folder
EXTENDED_METADATA_SIZE_LIMIT_MB = 500  # Over this size, warn user before attempting extended scan

# ----------------------------
# Metadata Settings
# ----------------------------
EXTENDED_METADATA_COLOR = "#e67e22"  # orange (same as extended info icon)
EXTENDED_METADATA_BG_COLOR = "#4a2a00"  # dark orange for progress bar bg
FAST_METADATA_COLOR = "#4a90e2"  # blue (ίδιο με selection-background-color στο QSS)
FAST_METADATA_BG_COLOR = "#102040"  # dark blue for progress bar bg

# ----------------------------
# File Table Settings
# ----------------------------
MAX_LABEL_LENGTH = 30
