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
LEFT_CENTER_RIGHT_SPLIT_RATIO = [220, 515, 220]
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
    "jpg", "jpeg", "png", "mp3", "mp4", "mov", "mts", "nef", "raw", "rw2", "thm", "arw", "cr2", "cr3",
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

# ----------------------------
# Tree View Expand/Collapse Mode
# ----------------------------
TREE_EXPAND_MODE = "double"  # Επιλογές: "single" ή "double". Default: double click για expand/collapse

# ----------------------------
# File Table Column Widths
# ----------------------------
FILE_TABLE_COLUMN_WIDTHS = {
    "STATUS_COLUMN": 23,     # Column 0: Status/info icon column
    "FILENAME_COLUMN": 330,  # Column 1: Filename column
    "FILESIZE_COLUMN": 80,   # Column 2: File size column
    "EXTENSION_COLUMN": 60,  # Column 3: File extension column
    "DATE_COLUMN": 100       # Column 4: Modified date column
}

# ----------------------------
# Theme Colors (Dark Theme)
# ----------------------------
THEME_COLORS = {
    "dark": {
        # Table/Tree view colors
        "background": "#181818",
        "text": "#f0ebd8",
        "text_selected": "#0d1321",
        "alternate_row": "#232323",

        # Interactive states
        "hover": "#3e5c76",
        "selected": "#748cab",
        "selected_hover": "#8a9bb4",  # Slightly lighter than selected

        # UI elements
        "button_bg": "#2a2a2a",
        "button_hover": "#4a6fa5",
        "border": "#3a3b40",
    },
    "light": {
        # Table/Tree view colors
        "background": "#ffffff",
        "text": "#212121",
        "text_selected": "#ffffff",
        "alternate_row": "#f8f8f8",

        # Interactive states
        "hover": "#e3f2fd",
        "selected": "#1976d2",
        "selected_hover": "#42a5f5",  # Slightly lighter than selected

        # UI elements
        "button_bg": "#f5f5f5",
        "button_hover": "#e3f2fd",
        "border": "#cccccc",
    }
}

