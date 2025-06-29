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
from core.qt_imports import Qt

# Debugging Set to False to disable debug.log output
SHOW_DEV_ONLY_IN_CONSOLE = False  # Disabled for performance
ENABLE_DEBUG_LOG_FILE = True

# Which key skips the metadata scan when held down
SKIP_METADATA_MODIFIER = Qt.ControlModifier # type: ignore
DEFAULT_SKIP_METADATA = True

# App info
APP_NAME = "oncutf"
APP_VERSION = "1.3"

# Export settings
EXPORT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"  # Format for export timestamps

# Splash Screen Settings
SPLASH_SCREEN_DURATION = 3000  # Duration in milliseconds (3 seconds)

# Window
WINDOW_TITLE = "Batch File Renamer"
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 900
WINDOW_MIN_WIDTH = 800
WINDOW_MIN_HEIGHT = 500

# Smart Window Sizing Configuration
# Screen size breakpoints (in pixels) - defines the categories
SCREEN_SIZE_BREAKPOINTS = {
    "large_4k": 2560,      # 4K screens and above
    "full_hd": 1920,       # Full HD screens and above
    "laptop": 1366,        # Common laptop resolution and above
    # Everything below 1366px is considered "small"
}

# Window sizing percentages for each screen category (separate width/height control)
SCREEN_SIZE_PERCENTAGES = {
    "large_4k": {"width": 0.75, "height": 0.75},      # 4K screens: 75% of screen
    "full_hd": {"width": 0.80, "height": 0.80},       # Full HD screens: 80% of screen
    "laptop": {"width": 0.85, "height": 0.85},        # Laptop screens: 85% of screen
    "small": {"width": 0.90, "height": 0.90}          # Small screens: 90% of screen
}

# Minimum window dimensions for usability
WINDOW_MIN_SMART_WIDTH = 1000
WINDOW_MIN_SMART_HEIGHT = 700

# Minimum dimensions for large screens
LARGE_SCREEN_MIN_WIDTH = 1400
LARGE_SCREEN_MIN_HEIGHT = 900

# ----------------------------
# Development/Testing Settings
# ----------------------------
# Set to True to simulate different screen sizes for testing (DEV ONLY)
DEV_SIMULATE_SCREEN = True

# Simulated screen dimensions (only used when DEV_SIMULATE_SCREEN is True)
DEV_SIMULATED_SCREEN = {
    "width": 1280,
    "height": 1024,
    "name": "Simulated 4K Screen"
}

# Common screen sizes for quick testing:
# 4K: {"width": 2560, "height": 1440, "name": "Simulated 4K"}
# Full HD: {"width": 1920, "height": 1080, "name": "Simulated Full HD"}
# Laptop: {"width": 1366, "height": 768, "name": "Simulated Laptop"}
# Small: {"width": 1024, "height": 768, "name": "Simulated Small"}
# Ultrawide: {"width": 3440, "height": 1440, "name": "Simulated Ultrawide"}

# Splitter sizes
TOP_BOTTOM_SPLIT_RATIO = [500, 400]
LEFT_CENTER_RIGHT_SPLIT_RATIO = [250, 674, 250]

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

# Allowed file extensions - organized by category for better maintenance
ALLOWED_EXTENSIONS = {
    # Image formats
    "jpg", "jpeg", "png", "tiff", "tif", "bmp", "gif", "webp", "svg",
    "heic", "heif",  # Apple formats

    # RAW image formats
    "nef", "raw", "rw2", "arw", "cr2", "cr3", "dng", "orf",

    # Audio formats
    "mp3", "wav", "flac", "aac", "ogg", "m4a", "wma", "aiff",

    # Video formats
    "mp4", "mov", "mts", "avi", "mkv", "wmv", "flv", "webm", "m4v", "3gp", "ts", "vob",

        # Document formats
    "txt", "csv", "xml", "json", "rtf",
    "pdf",

    # Thumbnail formats
    "tmp"
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
# Metadata Status Icon Colors (SVG-based system)
# ----------------------------
METADATA_ICON_COLORS = {
    'basic': '#e8f4fd',        # Almost white with slight blue tint
    'extended': EXTENDED_METADATA_COLOR,  # Orange like progress bar (#ffb74d)
    'invalid': '#ff6b6b',      # Light red
    'loaded': '#51cf66',       # Light green
    'modified': '#ffd755',     # Yellow
    'partial': '#888888',      # Gray
    'hash': HASH_CALCULATION_COLOR,  # Purple like progress bar (#9c27b0)
}

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
    "STATUS_COLUMN": 40,     # Column 0: Status/info icon column (increased for metadata + hash icons)
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
    # Basic status states
    "ready": "",                    # Default color (no override)
    "error": "#ff6b6b",            # Light red
    "success": "#51cf66",          # Light green
    "warning": "#ffa726",          # Light orange
    "info": "#74c0fc",             # Light blue/cyan
    "loading": "#adb5bd",          # Light gray

    # Metadata specific
    "metadata_skipped": "#adb5bd", # Light gray for skipped metadata
    "metadata_extended": "#ff8a65", # Light orange-red for extended metadata
    "metadata_basic": "#74c0fc",   # Light blue/cyan for basic metadata

    # Action categories (pale and bright colors)
    "action_completed": "#87ceeb", # Pale bright blue - for completed actions like clearing table
    "neutral_info": "#d3d3d3",     # Pale bright gray - for neutral information
    "operation_success": "#90ee90", # Pale bright green - for successful operations
    "alert_notice": "#ffd700",     # Pale bright orange/yellow - for alerts and notices
    "critical_error": "#ffb6c1",   # Pale bright red - for critical errors

    # Specific use cases
    "file_cleared": "#87ceeb",     # Pale blue for file table cleared
    "no_action": "#d3d3d3",        # Pale gray for "no files to clear" etc
    "rename_success": "#90ee90",   # Pale green for successful renames
    "validation_error": "#ffb6c1", # Pale red for validation errors
    "drag_action": "#87ceeb",      # Pale blue for drag operations
    "hash_success": "#90ee90",     # Pale green for hash operations
    "duplicate_found": "#ffd700",  # Pale yellow for duplicate warnings
    "metadata_success": "#90ee90", # Pale green for metadata operations
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
# Database Backup Settings
# ----------------------------
# Backup count (how many backup files to keep)
DEFAULT_BACKUP_COUNT = 2  # Keep 2 backup files by default

# Periodic backup interval in seconds (15 minutes = 900 seconds)
DEFAULT_BACKUP_INTERVAL = 900  # 15 minutes

# Backup filename format: oncutf_YYYYMMDD_HHMMSS.db.bak
BACKUP_FILENAME_FORMAT = "{basename}_{timestamp}.db.bak"
BACKUP_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"

# Whether periodic backups are enabled by default
DEFAULT_PERIODIC_BACKUP_ENABLED = True

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

