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
SHOW_DEV_ONLY_IN_CONSOLE = True
ENABLE_DEBUG_LOG_FILE = True

# Which key skips the metadata scan when held down
SKIP_METADATA_MODIFIER = Qt.ControlModifier
DEFAULT_SKIP_METADATA = True

# App info
APP_NAME = "oncutf"
APP_VERSION = "1.1"

# Splash Screen Settings
SPLASH_SCREEN_DURATION = 3000  # Duration in milliseconds (3 seconds)

# Window
WINDOW_TITLE = "Batch File Renamer"
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 900
WINDOW_MIN_WIDTH = 800
WINDOW_MIN_HEIGHT = 500

# Splitter sizes
TOP_BOTTOM_SPLIT_RATIO = [500, 300]
LEFT_CENTER_RIGHT_SPLIT_RATIO = [250, 674, 250]
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
    "wav", "txt", "csv", "xml", "pdf", "doc", "docx", "xls", "xlsx", "avi", "mkv"
}

# Regex pattern for Windows-safe names
ALLOWED_FILENAME_CHARS = r"^[^\\/:*?\"<>|]+$"

# Theme
THEME_NAME = "dark"

# ----------------------------
# Font Configuration
# ----------------------------
USE_EMBEDDED_FONTS = False  # Set to True to use QRC embedded fonts instead of filesystem

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
# Progress Dialog Colors
# ----------------------------
# Metadata colors (basic/fast metadata operations)
FAST_METADATA_COLOR = "#64b5f6"        # Pale blue
FAST_METADATA_BG_COLOR = "#0a1a2a"     # Darker blue bg

# Metadata colors (extended metadata operations)
EXTENDED_METADATA_COLOR = "#ffb74d"    # Pale orange
EXTENDED_METADATA_BG_COLOR = "#2c1810" # Darker orange bg

# File loading colors
FILE_LOADING_COLOR = "#64b5f6"         # Blue
FILE_LOADING_BG_COLOR = "#0a1a2a"      # Darker blue bg

# Hash calculation colors
HASH_CALCULATION_COLOR = "#9c27b0"     # Purple
HASH_CALCULATION_BG_COLOR = "#2a1a2a"  # Darker purple bg

# ----------------------------
# File Table Settings
# ----------------------------
MAX_LABEL_LENGTH = 30

# ----------------------------
# Tree View Expand/Collapse Mode
# ----------------------------
TREE_EXPAND_MODE = "double"  # Options: "single" or "double". Default: double click for expand/collapse

# ----------------------------
# File Table Column Widths
# ----------------------------
FILE_TABLE_COLUMN_WIDTHS = {
    "STATUS_COLUMN": 23,     # Column 0: Status/info icon column
    "FILENAME_COLUMN": 345,  # Column 1: Filename column (set to 345px)
    "FILESIZE_COLUMN": 80,   # Column 2: File size column
    "EXTENSION_COLUMN": 60,  # Column 3: File extension column
    "DATE_COLUMN": 130       # Column 4: Modified date column
}

# ----------------------------
# Metadata Tree View Settings
# ----------------------------
METADATA_TREE_COLUMN_WIDTHS = {
    "PLACEHOLDER_KEY_WIDTH": 100,
    "PLACEHOLDER_VALUE_WIDTH": 250,
    "NORMAL_KEY_INITIAL_WIDTH": 180,
    "NORMAL_VALUE_INITIAL_WIDTH": 500,
    "KEY_MIN_WIDTH": 80,
    "KEY_MAX_WIDTH": 800,
    "VALUE_MIN_WIDTH": 250
}

# ----------------------------
# Status Label Colors
# ----------------------------
STATUS_COLORS = {
    "ready": "",                    # Default color (no override)
    "error": "#ff6b6b",            # Light red (was "red")
    "success": "#51cf66",          # Light green (was "green")
    "warning": "#ffa726",          # Light orange (was "orange")
    "info": "#74c0fc",             # Light blue/cyan (was "blue" - now more cyan/light blue)
    "loading": "#adb5bd",          # Light gray (was "gray")
    "metadata_skipped": "#adb5bd", # Light gray for skipped metadata
    "metadata_extended": "#ff8a65", # Light orange-red for extended metadata
    "metadata_basic": "#74c0fc"    # Light blue/cyan for basic metadata
}

# ----------------------------
# Tooltip Settings
# ----------------------------
TOOLTIP_DURATION = 2000  # Duration in milliseconds (2 seconds)
TOOLTIP_POSITION_OFFSET = (10, -25)  # (x, y) offset from widget position

# Invalid filename characters for input filtering
INVALID_FILENAME_CHARS = '<>:"/\\|?*'
# Characters that shouldn't be at the end of filename (before extension)
INVALID_TRAILING_CHARS = ' .'
# Validation error marker (unique string that users won't intentionally use)
INVALID_FILENAME_MARKER = "__VALIDATION_ERROR__"

# ----------------------------
# File Size Formatting Settings
# ----------------------------
# Use SI decimal units (1000) vs Binary units (1024)
USE_BINARY_UNITS = False  # False = SI units (1000), True = Binary units (1024)
# Auto-detect locale for decimal separator (. vs ,)
USE_LOCALE_DECIMAL_SEPARATOR = True

# ----------------------------
# QLabel Text Colors
# ----------------------------
# Progress Widget Colors
QLABEL_PRIMARY_TEXT = "#f0ebd8"      # Primary text color (status labels)
QLABEL_SECONDARY_TEXT = "#90a4ae"    # Secondary text color (count, percentage)
QLABEL_TERTIARY_TEXT = "#b0bec5"     # Tertiary text color (filename, info)
QLABEL_MUTED_TEXT = "#888888"        # Muted text color (info labels)

# Widget Colors
QLABEL_INFO_TEXT = "#bbbbbb"         # Info text color
QLABEL_ERROR_TEXT = "#ff4444"        # Error text color
QLABEL_WHITE_TEXT = "white"          # White text color

# Background Colors
QLABEL_BORDER_GRAY = "#3a3a3a"       # Gray border color
QLABEL_DARK_BORDER = "#555555"       # Dark border color
QLABEL_ERROR_BG = "#3a2222"          # Error background color
QLABEL_DARK_BG = "#3a3a3a"           # Dark background color

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

