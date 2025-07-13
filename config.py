"""
Module: config.py

Author: Michael Economou
Date: 2025-05-01

This module defines global configuration constants and settings used
throughout the oncutf application. It centralizes UI defaults, file
filters, path definitions, and other shared parameters.

Contains:
- Debug settings (for development and troubleshooting)
- Default UI settings
- File extension filters
- Paths to resources and stylesheets
"""

from core.pyqt_imports import Qt

# =====================================
# DEBUG SETTINGS
# =====================================

# Database reset - if True, deletes database on startup
DEBUG_RESET_DATABASE = False

# Config reset - if True, deletes config.json on startup
DEBUG_RESET_CONFIG = False

# Development logging settings
SHOW_DEV_ONLY_IN_CONSOLE = False
ENABLE_DEBUG_LOG_FILE = True

# Development/Testing Settings
DEV_SIMULATE_SCREEN = False

# Simulated screen dimensions (only used when DEV_SIMULATE_SCREEN is True)
DEV_SIMULATED_SCREEN = {"width": 1280, "height": 1024, "name": "Simulated Screen"}

# =====================================
# APPLICATION INFORMATION
# =====================================

# App info
APP_NAME = "oncutf"
APP_VERSION = "1.3"
APP_AUTHOR = "Michael Economou"

# Window
WINDOW_TITLE = "Batch File Renamer"

# =====================================
# LOGGING CONFIGURATION
# =====================================

# Logging settings
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# =====================================
# DIALOG PATHS
# =====================================

# Dialog paths
DIALOG_PATHS = {"last_used": ""}

# =====================================
# WINDOW GEOMETRY AND STATE
# =====================================

# Main window geometry and state (will be loaded from config.json)
MAIN_WINDOW_GEOMETRY = None
MAIN_WINDOW_STATE = None



# =====================================
# ALLOWED FILE EXTENSIONS
# =====================================

# Allowed file extensions - organized by category
ALLOWED_EXTENSIONS = {
    # Image formats
    "jpg",
    "jpeg",
    "png",
    "tiff",
    "tif",
    "bmp",
    "gif",
    "webp",
    "svg",
    "heic",
    "heif",
    # RAW image formats
    "nef",
    "raw",
    "rw2",
    "arw",
    "cr2",
    "cr3",
    "dng",
    "orf",
    # Audio formats
    "mp3",
    "wav",
    "flac",
    "aac",
    "ogg",
    "m4a",
    "wma",
    "aiff",
    # Video formats
    "mp4",
    "mov",
    "mts",
    "avi",
    "mkv",
    "wmv",
    "flv",
    "webm",
    "m4v",
    "3gp",
    "ts",
    "vob",
    # Document formats
    "txt",
    "csv",
    "xml",
    "json",
    "rtf",
    "pdf",
    # Thumbnail formats
    "tmp",
}

# =====================================
# DATABASE BACKUP SETTINGS
# =====================================

# Backup count (how many backup files to keep)
DEFAULT_BACKUP_COUNT = 2  # Keep 2 backup files by default

# Periodic backup interval in seconds (15 minutes = 900 seconds)
DEFAULT_BACKUP_INTERVAL = 900  # 15 minutes

# Backup filename format: oncutf_YYYYMMDD_HHMMSS.db.bak
BACKUP_FILENAME_FORMAT = "{basename}_{timestamp}.db.bak"
BACKUP_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"

# Whether periodic backups are enabled by default
DEFAULT_PERIODIC_BACKUP_ENABLED = True

# =====================================
# EXPORT SETTINGS
# =====================================

EXPORT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# =====================================
# FILE HANDLING SETTINGS
# =====================================

USE_PREVIEW_BACKGROUND = False
LARGE_FOLDER_WARNING_THRESHOLD = 150
EXTENDED_METADATA_SIZE_LIMIT_MB = 500

# Regex pattern for Windows-safe names
ALLOWED_FILENAME_CHARS = r"^[^\\/:*?\"<>|]+$"

# Invalid filename characters for input filtering
INVALID_FILENAME_CHARS = '<>:"/\\|?*'
# Characters that shouldn't be at the end of filename (before extension)
INVALID_TRAILING_CHARS = " ."
# Validation error marker (unique string that users won't intentionally use)
INVALID_FILENAME_MARKER = "__VALIDATION_ERROR__"

# File Size Formatting Settings
# Use SI decimal units (1000) vs Binary units (1024)
USE_BINARY_UNITS = False  # False = SI units (1000), True = Binary units (1024)
# Auto-detect locale for decimal separator (. vs ,)
USE_LOCALE_DECIMAL_SEPARATOR = True

# =====================================
# FONT CONFIGURATION
# =====================================

# Font Configuration
USE_EMBEDDED_FONTS = False

# =====================================
# LAYOUT MARGINS
# =====================================

# Layout Margins
CONTENT_MARGINS = {
    "top": 8,
    "bottom": 8,
    "left": 8,
    "right": 8,
}

# =====================================
# METADATA DISPLAY LEVEL SETTINGS
# =====================================

# Metadata Display Level Settings


# =====================================
# METADATA TREE VIEW SETTINGS
# =====================================

# Metadata Tree View Settings
METADATA_TREE_COLUMN_WIDTHS = {
    "PLACEHOLDER_KEY_WIDTH": 140,
    "PLACEHOLDER_VALUE_WIDTH": 250,
    "NORMAL_KEY_INITIAL_WIDTH": 140,
    "NORMAL_VALUE_INITIAL_WIDTH": 600,
    "KEY_MIN_WIDTH": 80,
    "KEY_MAX_WIDTH": 800,
    "VALUE_MIN_WIDTH": 250,
}

# Metadata Tree Column Configuration (dictionary-based, similar to FILE_TABLE_COLUMN_CONFIG)
METADATA_TREE_COLUMN_CONFIG = {
    "key": {
        "title": "Key",
        "key": "key",
        "default_visible": True,
        "removable": False,  # Always visible
        "width": 140,
        "alignment": "left",
        "min_width": 80,
    },
    "value": {
        "title": "Value",
        "key": "value",
        "default_visible": True,
        "removable": False,  # Always visible
        "width": 600,
        "alignment": "left",
        "min_width": 250,
    },
}

# =====================================
# PANEL SIZE CONSTRAINTS
# =====================================

# Panel size constraints for SplitterManager
LEFT_PANEL_MIN_WIDTH = 200
LEFT_PANEL_MAX_WIDTH = 350
RIGHT_PANEL_MIN_WIDTH = 200
RIGHT_PANEL_MAX_WIDTH = 450

# Screen size thresholds for adaptive splitter sizing
WIDE_SCREEN_THRESHOLD = 1920
ULTRA_WIDE_SCREEN_THRESHOLD = 2560

# Preview columns
PREVIEW_COLUMN_WIDTH = 350
PREVIEW_MIN_WIDTH = 250

# =====================================
# PREVIEW INDICATOR SETTINGS
# =====================================

# Preview Indicator Settings
PREVIEW_COLORS = {
    "valid": "#2ecc71",
    "duplicate": "#e67e22",
    "invalid": "#c0392b",
    "unchanged": "#777777",
}

PREVIEW_INDICATOR_SHAPE = "circle"
PREVIEW_INDICATOR_SIZE = (10, 10)
PREVIEW_INDICATOR_BORDER = {"color": "#222222", "thickness": 1}

# =====================================
# PROGRESS DIALOG COLORS
# =====================================

# Progress Dialog Colors
FAST_METADATA_COLOR = "#64b5f6"
FAST_METADATA_BG_COLOR = "#0a1a2a"

EXTENDED_METADATA_COLOR = "#ffb74d"
EXTENDED_METADATA_BG_COLOR = "#2c1810"

FILE_LOADING_COLOR = "#64b5f6"
FILE_LOADING_BG_COLOR = "#0a1a2a"

HASH_CALCULATION_COLOR = "#9c27b0"
HASH_CALCULATION_BG_COLOR = "#2a1a2a"

# =====================================
# QLABEL TEXT COLORS
# =====================================

# QLabel Text Colors
# Progress Widget Colors
QLABEL_PRIMARY_TEXT = "#f0ebd8"  # Primary text color (status labels)
QLABEL_SECONDARY_TEXT = "#90a4ae"  # Secondary text color (count, percentage)
QLABEL_TERTIARY_TEXT = "#b0bec5"  # Tertiary text color (filename, info)
QLABEL_MUTED_TEXT = "#888888"  # Muted text color (info labels)

# Widget Colors
QLABEL_INFO_TEXT = "#bbbbbb"  # Info text color
QLABEL_ERROR_TEXT = "#ff4444"  # Error text color
QLABEL_WHITE_TEXT = "white"  # White text color

# Background Colors
QLABEL_BORDER_GRAY = "#3a3a3a"  # Gray border color
QLABEL_DARK_BORDER = "#555555"  # Dark border color
QLABEL_ERROR_BG = "#3a2222"  # Error background color
QLABEL_DARK_BG = "#181818"  # Dark background color

# =====================================
# SMART WINDOW SIZING CONFIGURATION
# =====================================

# Smart Window Sizing Configuration
SCREEN_SIZE_BREAKPOINTS = {
    "large_4k": 2560,
    "full_hd": 1920,
    "laptop": 1366,
}

SCREEN_SIZE_PERCENTAGES = {
    "large_4k": {"width": 0.75, "height": 0.75},
    "full_hd": {"width": 0.80, "height": 0.80},
    "laptop": {"width": 0.85, "height": 0.85},
    "small": {"width": 0.90, "height": 0.90},
}

# Minimum window dimensions
WINDOW_MIN_SMART_WIDTH = 1000
WINDOW_MIN_SMART_HEIGHT = 700

# Minimum dimensions for large screens
LARGE_SCREEN_MIN_WIDTH = 1400
LARGE_SCREEN_MIN_HEIGHT = 900

WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 900
WINDOW_MIN_WIDTH = 800
WINDOW_MIN_HEIGHT = 500

# =====================================
# SPLASH SCREEN SETTINGS
# =====================================

# Splash Screen Settings
SPLASH_SCREEN_DURATION = 3000  # Duration in milliseconds

# =====================================
# SPLITTER SIZES
# =====================================

# Splitter sizes
TOP_BOTTOM_SPLIT_RATIO = [500, 400]
LEFT_CENTER_RIGHT_SPLIT_RATIO = [250, 674, 250]

# =====================================
# STATUS LABEL COLORS
# =====================================

# Status Label Colors
STATUS_COLORS = {
    # Basic status states
    "ready": "",  # Default color (no override)
    "error": "#ff6b6b",  # Light red
    "success": "#51cf66",  # Light green
    "warning": "#ffa726",  # Light orange
    "info": "#74c0fc",  # Light blue/cyan
    "loading": "#adb5bd",  # Light gray
    # Metadata specific
    "metadata_skipped": "#adb5bd",  # Light gray for skipped metadata
    "metadata_extended": "#ff8a65",  # Light orange-red for extended metadata
    "metadata_basic": "#74c0fc",  # Light blue/cyan for basic metadata
    # Action categories (pale and bright colors)
    "action_completed": "#87ceeb",  # Pale bright blue - for completed actions like clearing table
    "neutral_info": "#d3d3d3",  # Pale bright gray - for neutral information
    "operation_success": "#90ee90",  # Pale bright green - for successful operations
    "alert_notice": "#ffd700",  # Pale bright orange/yellow - for alerts and notices
    "critical_error": "#ffb6c1",  # Pale bright red - for critical errors
    # Specific use cases
    "file_cleared": "#87ceeb",  # Pale blue for file table cleared
    "no_action": "#d3d3d3",  # Pale gray for "no files to clear" etc
    "rename_success": "#90ee90",  # Pale green for successful renames
    "validation_error": "#ffb6c1",  # Pale red for validation errors
    "drag_action": "#87ceeb",  # Pale blue for drag operations
    "hash_success": "#90ee90",  # Pale green for hash operations
    "duplicate_found": "#ffd700",  # Pale yellow for duplicate warnings
    "metadata_success": "#90ee90",  # Pale green for metadata operations
}

# =====================================
# THEME COLORS (DARK THEME)
# =====================================

# Theme
THEME_NAME = "dark"

# Theme Colors (Dark Theme)
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
    },
}

# =====================================
# TOOLTIP SETTINGS
# =====================================

# Tooltip Settings
TOOLTIP_DURATION = 2000  # Duration in milliseconds (2 seconds)
TOOLTIP_POSITION_OFFSET = (
    25,
    -35,
)  # (x, y) offset from widget position - positioned above and to the right

# =====================================
# UNDO/REDO SYSTEM SETTINGS
# =====================================

# Undo/Redo System Settings
UNDO_REDO_SETTINGS = {
    # Maximum number of undo steps to keep in memory
    "MAX_UNDO_STEPS": 300,
    # Keyboard shortcuts
    "UNDO_SHORTCUT": "Ctrl+Z",
    "REDO_SHORTCUT": "Ctrl+Shift+Z",
    "HISTORY_SHORTCUT": "Ctrl+L",
    # Command grouping timeout (milliseconds)
    # Commands within this time window may be grouped together
    "COMMAND_GROUPING_TIMEOUT": 1000,
    # Whether to persist undo history between sessions
    "PERSIST_UNDO_HISTORY": False,
    # Colors for undo/redo UI elements
    "UNDO_AVAILABLE_COLOR": "#51cf66",  # Green when undo is available
    "REDO_AVAILABLE_COLOR": "#74c0fc",  # Blue when redo is available
    "UNAVAILABLE_COLOR": "#6c757d",  # Gray when unavailable
    # History dialog settings
    "HISTORY_DIALOG_WIDTH": 900,
    "HISTORY_DIALOG_HEIGHT": 700,
    "HISTORY_ITEMS_PER_PAGE": 50,
}

# Command Types for Undo/Redo System
COMMAND_TYPES = {
    "METADATA_EDIT": "metadata_edit",
    "METADATA_RESET": "metadata_reset",
    "METADATA_SAVE": "metadata_save",
    "RENAME_OPERATION": "rename_operation",
    "BATCH_OPERATION": "batch_operation",
}

# =====================================
# FILE TABLE SETTINGS
# =====================================

# File Table Settings
MAX_LABEL_LENGTH = 30

# File Table Column Configuration for Context Menu
FILE_TABLE_COLUMN_CONFIG = {
    "filename": {
        "title": "Filename",
        "key": "filename",
        "default_visible": True,
        "removable": False,  # Always visible
        "width": 524,
        "alignment": "left",
        "min_width": 150,
    },
    "file_size": {
        "title": "File Size",
        "key": "file_size",
        "default_visible": True,
        "removable": True,
        "width": 75,
        "alignment": "right",  # Numbers align right
        "min_width": 60,
    },
    "type": {
        "title": "Type",
        "key": "type",
        "default_visible": True,
        "removable": True,
        "width": 50,
        "alignment": "left",
        "min_width": 40,
    },
    "modified": {
        "title": "Modified",
        "key": "modified",
        "default_visible": True,
        "removable": True,
        "width": 134,
        "alignment": "center",  # Dates look good centered
        "min_width": 100,
    },
    "rotation": {
        "title": "Rotation",
        "key": "rotation",
        "default_visible": False,
        "removable": True,
        "width": 80,
        "alignment": "right",  # Numbers align right
        "min_width": 60,
    },
    "duration": {
        "title": "Duration",
        "key": "duration",
        "default_visible": False,
        "removable": True,
        "width": 80,
        "alignment": "right",  # Time values align right
        "min_width": 60,
    },
    "audio_channels": {
        "title": "Audio Channels",
        "key": "audio_channels",
        "default_visible": False,
        "removable": True,
        "width": 100,
        "alignment": "right",  # Numbers align right
        "min_width": 80,
    },
    "audio_format": {
        "title": "Audio Format",
        "key": "audio_format",
        "default_visible": False,
        "removable": True,
        "width": 100,
        "alignment": "left",
        "min_width": 80,
    },
    "aperture": {
        "title": "Aperture",
        "key": "aperture",
        "default_visible": False,
        "removable": True,
        "width": 80,
        "alignment": "right",  # Camera values align right
        "min_width": 60,
    },
    "iso": {
        "title": "ISO",
        "key": "iso",
        "default_visible": False,
        "removable": True,
        "width": 60,
        "alignment": "right",  # Numbers align right
        "min_width": 50,
    },
    "shutter_speed": {
        "title": "Shutter Speed",
        "key": "shutter_speed",
        "default_visible": False,
        "removable": True,
        "width": 100,
        "alignment": "right",  # Camera values align right
        "min_width": 80,
    },
    "white_balance": {
        "title": "White Balance",
        "key": "white_balance",
        "default_visible": False,
        "removable": True,
        "width": 100,
        "alignment": "left",
        "min_width": 80,
    },
    "image_size": {
        "title": "Image Size",
        "key": "image_size",
        "default_visible": False,
        "removable": True,
        "width": 100,
        "alignment": "right",  # Dimensions align right
        "min_width": 80,
    },
    "compression": {
        "title": "Compression",
        "key": "compression",
        "default_visible": False,
        "removable": True,
        "width": 100,
        "alignment": "left",
        "min_width": 80,
    },
    "device_model": {
        "title": "Device Model",
        "key": "device_model",
        "default_visible": False,
        "removable": True,
        "width": 120,
        "alignment": "left",
        "min_width": 100,
    },
    "device_serial_no": {
        "title": "Device Serial No",
        "key": "device_serial_no",
        "default_visible": False,
        "removable": True,
        "width": 120,
        "alignment": "left",  # Serial numbers align left
        "min_width": 100,
    },
    "video_fps": {
        "title": "Video FPS",
        "key": "video_fps",
        "default_visible": False,
        "removable": True,
        "width": 80,
        "alignment": "right",  # Numbers align right
        "min_width": 60,
    },
    "video_avg_bitrate": {
        "title": "Video Avg. Bitrate",
        "key": "video_avg_bitrate",
        "default_visible": False,
        "removable": True,
        "width": 120,
        "alignment": "right",  # Numbers align right
        "min_width": 100,
    },
    "video_codec": {
        "title": "Video Codec",
        "key": "video_codec",
        "default_visible": False,
        "removable": True,
        "width": 100,
        "alignment": "left",
        "min_width": 80,
    },
    "video_format": {
        "title": "Video Format",
        "key": "video_format",
        "default_visible": False,
        "removable": True,
        "width": 100,
        "alignment": "left",
        "min_width": 80,
    },
    "device_manufacturer": {
        "title": "Device Manufacturer",
        "key": "device_manufacturer",
        "default_visible": False,
        "removable": True,
        "width": 120,
        "alignment": "left",
        "min_width": 100,
    },
    "target_umid": {
        "title": "Target UMID",
        "key": "target_umid",
        "default_visible": False,
        "removable": True,
        "width": 120,
        "alignment": "left",
        "min_width": 100,
    },
    "file_hash": {
        "title": "File Hash",
        "key": "file_hash",
        "default_visible": False,
        "removable": True,
        "width": 90,  # Reduced from 200 to 90 (45% of original)
        "alignment": "left",  # Hash values align left
        "min_width": 70,  # Reduced min_width proportionally
    },
}

# =====================================
# COLUMN MANAGEMENT SETTINGS
# =====================================

# Global minimum column width (applies to all columns)
GLOBAL_MIN_COLUMN_WIDTH = 50

# Keyboard shortcuts for column operations
COLUMN_SHORTCUTS = {
    "RESET_TO_DEFAULT": "Ctrl+T",  # Reset column widths to default
    "AUTO_FIT_CONTENT": "Ctrl+Shift+T",  # Auto-fit columns to content
}

# Column resizing behavior
COLUMN_RESIZE_BEHAVIOR = {
    "ENABLE_HORIZONTAL_SCROLLBAR": True,  # Always show horizontal scrollbar when needed
    "AUTO_ADJUST_FILENAME": False,  # Disable complex filename auto-adjustment
    "PRESERVE_USER_WIDTHS": True,  # Save user-adjusted widths to config.json
    "ENABLE_COLUMN_REORDERING": True,  # Allow drag & drop column reordering
}

# =====================================
# METADATA STATUS ICON COLORS
# =====================================

# Metadata Status Icon Colors
METADATA_ICON_COLORS = {
    "basic": "#e8f4fd",  # Light blue for basic metadata
    "extended": EXTENDED_METADATA_COLOR,  # Orange for extended metadata
    "invalid": "#ff6b6b",  # Red for invalid metadata
    "loaded": "#51cf66",  # Green for loaded metadata (fast/basic)
    "modified": "#ffa726",  # Orange for modified metadata
    "partial": "#ffeb3b",  # Yellow for partial metadata
    "hash": "#ce93d8",  # Light purple for hash (brighter than before)
    "none": "#404040",  # Dark gray for no metadata/hash (grayout)
}
