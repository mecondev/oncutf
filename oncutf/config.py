"""Module: config.py

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

# =====================================
# DEBUG SETTINGS
# =====================================

# Database reset - if True, deletes database on startup
DEBUG_RESET_DATABASE = False

# Config reset - if True, deletes config.json on startup
DEBUG_RESET_CONFIG = False

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

# Console logging
LOG_TO_CONSOLE = True  # Enable/disable console output
LOG_CONSOLE_LEVEL = "INFO"  # Console log level (INFO, DEBUG, WARNING, ERROR)

# File logging
LOG_TO_FILE = True  # Enable/disable file logging
LOG_FILE_LEVEL = "INFO"  # Main log file level (INFO and above)
LOG_FILE_MAX_BYTES = 10_000_000  # 10MB per file (rotation trigger)
LOG_FILE_BACKUP_COUNT = 5  # Keep 5 backup files (total: 60MB max)

# Debug file logging
LOG_DEBUG_FILE_ENABLED = True  # Enable separate debug log file
LOG_DEBUG_FILE_LEVEL = "DEBUG"  # Debug log file level
LOG_DEBUG_FILE_MAX_BYTES = 20_000_000  # 20MB per debug file
LOG_DEBUG_FILE_BACKUP_COUNT = 3  # Keep 3 debug backups (total: 80MB max)

# Development logging settings
SHOW_DEV_ONLY_IN_CONSOLE = False  # Show dev-only logs in console
ENABLE_DEBUG_LOG_FILE = LOG_DEBUG_FILE_ENABLED  # Use new config system

# =====================================
# EXTERNAL TOOLS CONFIGURATION
# =====================================


# Tool availability and feature flags
# Dynamically updated by external_tools.py at runtime
class FeatureAvailability:
    """Runtime feature availability based on external tool detection.

    This class tracks which external tools are available and enables/disables
    features accordingly. It provides graceful degradation when tools are missing.

    Updated automatically by oncutf.utils.external_tools module during initialization.

    Attributes:
        exiftool_available: Whether ExifTool is detected and usable
        ffmpeg_available: Whether FFmpeg is detected and usable
        metadata_features_enabled: Whether EXIF/metadata features are active
        video_features_enabled: Whether video processing features are active

    """

    # Tool availability (updated at runtime)
    exiftool_available: bool = False
    ffmpeg_available: bool = False

    # Feature flags (derived from tool availability)
    @classmethod
    def metadata_features_enabled(cls) -> bool:
        """Whether metadata/EXIF features are enabled (requires ExifTool)."""
        return cls.exiftool_available

    @classmethod
    def video_features_enabled(cls) -> bool:
        """Whether video processing features are enabled (requires FFmpeg)."""
        return cls.ffmpeg_available

    @classmethod
    def update_availability(cls, exiftool: bool = False, ffmpeg: bool = False) -> None:
        """Update tool availability flags.

        Called by external_tools module during application initialization.

        Args:
            exiftool: Whether ExifTool is available
            ffmpeg: Whether FFmpeg is available

        """
        cls.exiftool_available = exiftool
        cls.ffmpeg_available = ffmpeg


# =====================================
# EXIFTOOL TIMEOUT SETTINGS
# =====================================

# ExifTool operation timeouts (in seconds)
EXIFTOOL_TIMEOUT_FAST = 60  # Fast metadata read (single file, no extended data)
EXIFTOOL_TIMEOUT_EXTENDED = (
    240  # Extended metadata read with -ee flag (can be slow for large video files)
)
EXIFTOOL_TIMEOUT_WRITE = 10  # Metadata write operations
EXIFTOOL_TIMEOUT_BATCH_BASE = 60  # Base timeout for batch operations
EXIFTOOL_TIMEOUT_BATCH_PER_FILE = 0.5  # Additional timeout per file in batch (seconds)

# =====================================
# HASH CALCULATION PERFORMANCE
# =====================================

# Parallel hash worker settings
USE_PARALLEL_HASH_WORKER = True  # Use parallel ThreadPoolExecutor (True) or serial QThread (False)
PARALLEL_HASH_MAX_WORKERS = None  # None = auto-detect optimal count (2x CPU cores, max 8)

# =====================================
# CONFIG SAVE OPTIMIZATION
# =====================================

# Auto-save settings (reduces disk I/O)
CONFIG_AUTO_SAVE_ENABLED = True  # Enable debounced auto-save
CONFIG_AUTO_SAVE_DELAY = 600  # Seconds (10 minutes) - time to wait before saving
CONFIG_SAVE_ON_EXIT = True  # Force immediate save on application exit
CONFIG_SAVE_ON_DIALOG_CLOSE = True  # Force immediate save when dialogs close

# Cache settings (in-memory cache for non-critical settings)
CONFIG_CACHE_ENABLED = True  # Enable in-memory cache layer
CONFIG_CACHE_FLUSH_ON_SAVE = True  # Flush cache to disk on save

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
    "mxf",
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
    # Companion/Sidecar file formats
    "xmp",
    "srt",
    "vtt",
    "ass",
    "ssa",
    "sub",
    "idx",
    "cube",
    "3dl",
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

# =====================================
# COMPANION FILES SETTINGS
# =====================================

# Whether to automatically detect and handle companion files
COMPANION_FILES_ENABLED = True

# Whether to show companion files in the file table or hide them
SHOW_COMPANION_FILES_IN_TABLE = False

# Whether to automatically rename companion files when main file is renamed
AUTO_RENAME_COMPANION_FILES = True

# Whether to load metadata from companion files (like Sony XML)
LOAD_COMPANION_METADATA = True

# How to handle companion files during operations
CompanionFileMode = {
    "HIDE": "hide",  # Hide companion files from user (default)
    "SHOW": "show",  # Show companion files in table
    "SHOW_GROUPED": "grouped",  # Show but grouped with main file
}

# Default companion file handling mode
DEFAULT_COMPANION_FILE_MODE = CompanionFileMode["HIDE"]

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
# ICON SIZE SETTINGS
# =====================================

# Icon Size Settings
ICON_SIZES = {
    "SMALL": 16,  # Small icons (menu items, tree view)
    "MEDIUM": 24,  # Medium icons (toolbars, buttons)
    "LARGE": 32,  # Large icons (dialogs, headers)
    "EXTRA_LARGE": 48,  # Extra large icons (splash, about)
    "PREVIEW": 48,  # Preview table icons (configurable)
}

# Default preview icon size (can be adjusted by user)
DEFAULT_PREVIEW_ICON_SIZE = 48

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

# Toggle metadata proxy usage (set False to bypass proxy for debugging)
METADATA_TREE_USE_PROXY = True

# Toggle custom delegate for metadata tree (set False to use default delegate)
METADATA_TREE_USE_CUSTOM_DELEGATE = True

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
PREVIEW_INDICATOR_SIZE = (14, 14)
PREVIEW_INDICATOR_BORDER = {"color": "#222222", "thickness": 1}

# =====================================
# PROGRESS DIALOG COLORS
# =====================================

# Save Operation Settings
SAVE_OPERATION_SETTINGS = {
    # Allow ESC to cancel normal/manual saves (NOT for exit saves)
    # WARNING: Enabling this may result in incomplete save operations
    # Exit saves (save-on-quit) are ALWAYS protected and cannot be cancelled
    "ALLOW_CANCEL_NORMAL_SAVE": True,  # Default: disabled for data safety
}

# Progress Dialog Colors
FAST_METADATA_COLOR = "#64b5f6"
FAST_METADATA_BG_COLOR = "#0a1a2a"

EXTENDED_METADATA_COLOR = "#fabf65"
EXTENDED_METADATA_BG_COLOR = "#2c1810"

FILE_LOADING_COLOR = "#64b5f6"
FILE_LOADING_BG_COLOR = "#0a1a2a"

HASH_CALCULATION_COLOR = "#a256af"
HASH_CALCULATION_BG_COLOR = "#2a1a2a"

SAVE_COLOR = "#64b5f6"
SAVE_BG_COLOR = "#0a1a2a"

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
# Duration in milliseconds (reduced from 3000 to improve UX)
SPLASH_SCREEN_DURATION = 2000

# =====================================
# SPLITTER SIZES
# =====================================

# Splitter sizes
TOP_BOTTOM_SPLIT_RATIO = [500, 400]
LEFT_CENTER_RIGHT_SPLIT_RATIO = [250, 674, 250]

# =====================================
# STATUS BAR SETTINGS
# =====================================

# Status Bar Auto-Reset Settings
STATUS_AUTO_RESET_DELAY = 3000  # Duration in milliseconds before status auto-resets (3 seconds)

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
# THEME_NAME = "light"

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
# CONTEXT MENU COLORS
# =====================================

# Context Menu Colors (Dark Theme)
# Used for styling QMenu in file table context menu and other context menus
CONTEXT_MENU_COLORS = {
    "background": "#232323",
    "text": "#f0ebd8",
    "selected_bg": "#748cab",
    "selected_text": "#0d1321",
    "disabled_text": "#888888",
    "separator": "#5a5a5a",
}

# =====================================
# CENTRALIZED THEME TOKENS
# =====================================

# Complete theme color token definitions for dark and light themes
# Used by ThemeManager for centralized color management and theme switching
# Tokens organized by category for easy maintenance
THEME_TOKENS = {
    "dark": {
        # ===== Base Colors =====
        "background": "#181818",
        "background_alternate": "#232323",
        "background_lighter": "#2a2a2a",
        "background_elevated": "#1e1e1e",  # Dialogs, elevated surfaces
        "text": "#f0ebd8",  # Main text color
        "text_secondary": "#888888",
        "text_tertiary": "#666666",
        "text_disabled": "#555555",
        "text_muted": "#888888",  # Muted UI text (companion files, etc.)
        "metadata_group_text": "#ddd6ba",  # Metadata tree root group headers (dimmed for hierarchy)
        # ===== Interactive States =====
        "hover": "#3e5c76",
        "selected": "#748cab",
        "selected_text": "#0d1321",
        "selected_hover": "#8a9bb4",  # Slightly lighter than selected
        "pressed": "#5a7fa0",
        # ===== Borders & Separators =====
        "border": "#3a3b40",
        "border_light": "#4a4b50",
        "separator": "#5a5a5a",
        "outline": "#748cab",
        # ===== Semantic/Status Colors =====
        "success": "#4ade80",
        "warning": "#fbbf24",
        "error": "#ff6b6b",
        "info": "#60a5fa",
        "neutral": "#94a3b8",
        # ===== Component-Specific: Menus =====
        "menu_background": "#232323",
        "menu_text": "#f0ebd8",
        "menu_selected_bg": "#748cab",
        "menu_selected_text": "#0d1321",
        "menu_disabled_text": "#888888",
        "menu_separator": "#5a5a5a",
        # ===== Component-Specific: Tables =====
        "table_background": "#181818",
        "table_alternate": "#232323",
        "table_header_bg": "#2a2a2a",
        "table_header_text": "#f0ebd8",
        "table_selection_bg": "#748cab",
        "table_selection_text": "#0d1321",
        "table_hover_bg": "#3e5c76",
        "table_grid": "#3a3b40",
        # ===== Component-Specific: Dialogs =====
        "dialog_background": "#1e1e1e",
        "dialog_title_bg": "#252525",
        "dialog_border": "#3a3b40",
        # ===== Component-Specific: Buttons =====
        "button_bg": "#2a2a2a",
        "button_text": "#f0ebd8",
        "button_hover_bg": "#3e5c76",
        "button_hover_text": "#f0ebd8",
        "button_pressed_bg": "#748cab",
        "button_pressed_text": "#0d1321",
        "button_disabled_bg": "#1a1a1a",
        "button_disabled_text": "#555555",
        # ===== Component-Specific: ComboBoxes =====
        "combo_dropdown_background": "#181818",
        "combo_item_background_hover": "#3e5c76",
        "combo_item_background_selected": "#748cab",
        # ===== Component-Specific: Inputs =====
        "input_bg": "#2a2a2a",
        "input_text": "#f0ebd8",
        "input_border": "#3a3b40",
        "input_focus_border": "#748cab",
        "input_placeholder": "#666666",
        "input_hover_bg": "#1f1f1f",
        "input_focus_bg": "#1a1a1a",
        "border_hover": "#555555",
        "border_muted": "#808080",
        "accent": "#748cab",
        # ===== Component-Specific: Scrollbars =====
        "scrollbar_bg": "#1e1e1e",
        "scrollbar_handle": "#4a4a4a",
        "scrollbar_handle_hover": "#5a5a5a",
        # ===== Component-Specific: TreeView =====
        "tree_branch": "#3a3b40",
        "tree_indicator": "#748cab",
        # ===== Component-Specific: Results & Hash List =====
        "results_header_bg": "#2d2d2d",
        "results_row_hover": "#3a3a3a",
        "results_footer_bg": "#2a2a2a",
        # ===== Component-Specific: Preview =====
        "preview_bg": "#232323",
        "preview_border": "#3a3b40",
        # ===== Component-Specific: Rename Modules =====
        "module_plate_bg": "#2a2a2a",
        "module_plate_border": "#3a3b40",
        "module_drag_handle": "#4a4a4a",
        "module_drag_hover": "#748cab",
        # ===== Component-Specific: Companion Files =====
        "companion_info_text": "#888888",
        "companion_note_text": "#888888",
        # ===== Component-Specific: Metadata Edit =====
        "edit_info_text": "#888888",
        "edit_error_text": "#ff6b6b",
        # ===== Component-Specific: History Dialog =====
        "history_title_text": "#f0ebd8",
        "history_info_text": "#888888",
        # ===== Component-Specific: Tooltips =====
        "tooltip_bg": "#2b2b2b",
        "tooltip_text": "#f0ebd8",
        "tooltip_border": "#555555",
        "tooltip_error_bg": "#3d1e1e",
        "tooltip_error_text": "#ffaaaa",
        "tooltip_error_border": "#cc4444",
        "tooltip_warning_bg": "#3d3d1e",
        "tooltip_warning_text": "#ffffaa",
        "tooltip_warning_border": "#cccc44",
        "tooltip_info_bg": "#1e2d3d",
        "tooltip_info_text": "#aaccff",
        "tooltip_info_border": "#4488cc",
        "tooltip_success_bg": "#1e3d1e",
        "tooltip_success_text": "#aaffaa",
        "tooltip_success_border": "#44cc44",
        # ===== Layout & Spacing Constants (numeric) =====
        # These are stored as strings for now, will be accessed via get_constant()
        "table_row_height": "22",
        "button_height": "24",
        "combo_height": "22",
    },
    "light": {
        # Placeholder for light theme - to be implemented later
        # Mirror structure of dark theme with appropriate light colors
        "background": "#ffffff",
        "background_alternate": "#f8f8f8",
        "text": "#212121",
        "text_secondary": "#666666",
        "text_muted": "#999999",  # Muted UI text for light theme
        "metadata_group_text": "#6b6b6b",  # Metadata tree root groups (darker for light theme hierarchy)
        # ... (rest will be filled when implementing light theme)
    },
}

# =====================================
# TOOLTIP SETTINGS
# =====================================

# Tooltip Settings
TOOLTIP_DURATION = 2500  # Duration in milliseconds (2.5 seconds)
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
    "REDO_SHORTCUT": "Ctrl+Shift+Z",  # Changed from Ctrl+R to standard Ctrl+Shift+Z
    "HISTORY_SHORTCUT": "Ctrl+Y",  # Changed from Ctrl+Shift+Z to Ctrl+Y
    "RESULTS_HASH_LIST_SHORTCUT": "Ctrl+L",
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
# KEYBOARD SHORTCUTS CONFIGURATION
# =====================================
# All shortcuts are centralized here for easy customization.
# Widget-specific shortcuts only work when that widget has focus.
# Global shortcuts work regardless of which widget has focus.

# Common refresh key used by multiple widgets (widget-dependent behavior)
REFRESH_KEY = "F5"

# File Table shortcuts (work when FileTableView has focus)
FILE_TABLE_SHORTCUTS = {
    "SELECT_ALL": "Ctrl+A",
    "CLEAR_SELECTION": "Ctrl+Shift+A",
    "INVERT_SELECTION": "Ctrl+I",
    "LOAD_METADATA": "Ctrl+M",
    "LOAD_EXTENDED_METADATA": "Ctrl+Shift+M",
    "CALCULATE_HASH": "Ctrl+H",
    "REFRESH": REFRESH_KEY,  # Reload files from current folder
}

# File Tree shortcuts (work when FileTreeView has focus)
FILE_TREE_SHORTCUTS = {
    "REFRESH": REFRESH_KEY,  # Refresh file tree view
}

# Metadata Tree shortcuts (work when MetadataTreeView has focus)
METADATA_TREE_SHORTCUTS = {
    "REFRESH": REFRESH_KEY,  # Reload metadata from current selection
}

# Preview shortcuts (work when PreviewTablesView has focus)
PREVIEW_SHORTCUTS = {
    "REFRESH": REFRESH_KEY,  # Refresh preview tables
}

# Global shortcuts (work regardless of which widget has focus)
GLOBAL_SHORTCUTS = {
    "BROWSE_FOLDER": "Ctrl+O",  # Browse dialog affects whole app
    "SAVE_METADATA": "Ctrl+S",  # Standard Save convention
    "CANCEL_DRAG": "Escape",  # Cancel drag in any widget (file_table, file_tree, metadata_tree)
    "CLEAR_FILE_TABLE": "Shift+Escape",  # Clear all files
    "UNDO": "Ctrl+Z",  # Global undo (all operations: rename, metadata, etc)
    "REDO": "Ctrl+Shift+Z",  # Global redo (standard convention)
    "SHOW_HISTORY": "Ctrl+Y",  # Show command history dialog
}

# =====================================
# FILE TABLE SETTINGS
# =====================================

# File Table Settings
MAX_LABEL_LENGTH = 30

# File Table Column Configuration for Context Menu
FILE_TABLE_COLUMN_CONFIG = {
    "color": {
        "title": "Color",
        "key": "color",
        "default_visible": True,
        "removable": True,
        "resizable": False,  # Non-resizable, fixed width
        "width": 50,
        "alignment": "center",
        "min_width": 50,
    },
    "filename": {
        "title": "Filename",
        "key": "filename",
        "default_visible": True,
        "removable": False,  # Always visible
        "resizable": True,
        "width": 524,
        "alignment": "left",
        "min_width": 80,
    },
    "file_size": {
        "title": "File Size",
        "key": "file_size",
        "default_visible": True,
        "removable": True,
        "resizable": True,
        "width": 75,
        "alignment": "right",
        "min_width": 40,
    },
    "type": {
        "title": "Type",
        "key": "type",
        "default_visible": True,
        "removable": True,
        "resizable": True,
        "width": 50,
        "alignment": "left",
        "min_width": 30,
    },
    "modified": {
        "title": "Modified",
        "key": "modified",
        "default_visible": True,
        "removable": True,
        "resizable": True,
        "width": 134,
        "alignment": "left",
        "min_width": 70,
    },
    "rotation": {
        "title": "Rotation",
        "key": "rotation",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 80,
        "alignment": "left",
        "min_width": 60,
    },
    "duration": {
        "title": "Duration",
        "key": "duration",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 80,
        "alignment": "left",
        "min_width": 60,
    },
    "audio_channels": {
        "title": "Audio Channels",
        "key": "audio_channels",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 100,
        "alignment": "left",
        "min_width": 80,
    },
    "audio_format": {
        "title": "Audio Format",
        "key": "audio_format",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 100,
        "alignment": "left",
        "min_width": 80,
    },
    "aperture": {
        "title": "Aperture",
        "key": "aperture",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 80,
        "alignment": "left",
        "min_width": 60,
    },
    "iso": {
        "title": "ISO",
        "key": "iso",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 60,
        "alignment": "left",
        "min_width": 50,
    },
    "shutter_speed": {
        "title": "Shutter Speed",
        "key": "shutter_speed",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 100,
        "alignment": "left",
        "min_width": 80,
    },
    "white_balance": {
        "title": "White Balance",
        "key": "white_balance",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 100,
        "alignment": "left",
        "min_width": 80,
    },
    "image_size": {
        "title": "Image Size",
        "key": "image_size",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 100,
        "alignment": "left",
        "min_width": 80,
    },
    "compression": {
        "title": "Compression",
        "key": "compression",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 100,
        "alignment": "left",
        "min_width": 80,
    },
    "device_model": {
        "title": "Device Model",
        "key": "device_model",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 120,
        "alignment": "left",
        "min_width": 100,
    },
    "device_serial_no": {
        "title": "Device Serial No",
        "key": "device_serial_no",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 140,
        "alignment": "left",
        "min_width": 100,
    },
    "video_fps": {
        "title": "Video FPS",
        "key": "video_fps",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 80,
        "alignment": "left",
        "min_width": 60,
    },
    "video_avg_bitrate": {
        "title": "Video Avg. Bitrate",
        "key": "video_avg_bitrate",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 120,
        "alignment": "left",
        "min_width": 100,
    },
    "video_codec": {
        "title": "Video Codec",
        "key": "video_codec",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 100,
        "alignment": "left",
        "min_width": 80,
    },
    "video_format": {
        "title": "Video Format",
        "key": "video_format",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 100,
        "alignment": "left",
        "min_width": 80,
    },
    "device_manufacturer": {
        "title": "Device Manufacturer",
        "key": "device_manufacturer",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 120,
        "alignment": "left",
        "min_width": 100,
    },
    "target_umid": {
        "title": "Target UMID",
        "key": "target_umid",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 400,
        "alignment": "left",
        "min_width": 200,
    },
    "file_hash": {
        "title": "File Hash",
        "key": "file_hash",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 90,
        "alignment": "left",
        "min_width": 70,
    },
}

# =====================================
# COLUMN MANAGEMENT SETTINGS
# =====================================

# Global minimum column width (applies to all columns)
GLOBAL_MIN_COLUMN_WIDTH = 50

# Keyboard shortcuts for column operations
COLUMN_SHORTCUTS = {
    "AUTO_FIT_CONTENT": "Ctrl+T",  # Auto-fit columns to content
    "RESET_TO_DEFAULT": "Ctrl+Shift+T",  # Reset column widths to default
}

# Column resizing behavior
COLUMN_RESIZE_BEHAVIOR = {
    "ENABLE_HORIZONTAL_SCROLLBAR": True,  # Always show horizontal scrollbar when needed
    "AUTO_ADJUST_FILENAME": False,  # Disable complex filename auto-adjustment
    "PRESERVE_USER_WIDTHS": True,  # Save user-adjusted widths to config.json
    "ENABLE_COLUMN_REORDERING": True,  # Allow drag & drop column reordering
}

# =====================================
# RESULTS TABLE DIALOG SETTINGS
# =====================================

# Results Table Dialog - Default dimensions
RESULTS_TABLE_DEFAULT_WIDTH = 700
RESULTS_TABLE_DEFAULT_HEIGHT = 400
# Minimum width for results dialog
RESULTS_TABLE_MIN_WIDTH = 350
# Minimum / Maximum height for results dialog
RESULTS_TABLE_MIN_HEIGHT = 250
RESULTS_TABLE_MAX_HEIGHT = 1000

# Results Table Dialog - Default column widths
RESULTS_TABLE_LEFT_COLUMN_WIDTH = 400  # Filename column (wider)
RESULTS_TABLE_RIGHT_COLUMN_WIDTH = 100  # Hash/value column (narrower)

# Default row height for hash/results lists (pixels). Matches file table row height.
HASH_LIST_ROW_HEIGHT = 22

# =====================================
# HASH / RESULTS LIST (UI) SETTINGS
# =====================================

# Window defaults & constraints (persisted by UI into config.json)
HASH_LIST_WINDOW_DEFAULT_WIDTH = RESULTS_TABLE_DEFAULT_WIDTH
HASH_LIST_WINDOW_DEFAULT_HEIGHT = RESULTS_TABLE_DEFAULT_HEIGHT
HASH_LIST_WINDOW_MIN_HEIGHT = RESULTS_TABLE_MIN_HEIGHT
HASH_LIST_WINDOW_MAX_HEIGHT = RESULTS_TABLE_MAX_HEIGHT

# Use same margins/padding as main content
HASH_LIST_CONTENT_MARGINS = CONTENT_MARGINS

# Font / row sizing: None = inherit defaults from File Table / main UI
# If UI finds a concrete value in config.json it should prefer that.
HASH_LIST_FONT_SIZE = None
# Use same row height as file table (22px) for consistency
# HASH_LIST_ROW_HEIGHT = None  # Disabled: using explicit 22px instead

# Header / label styling
HASH_LIST_HEADER_ALIGNMENT = "left"
# Empty string means no background color (use main window styling)
HASH_LIST_LABEL_BACKGROUND = ""

# Column configuration for the hash/list view
# 'width' = None will be treated as 'auto / stretch' by the dialog UI
HASH_LIST_COLUMN_CONFIG = {
    "filename": {
        "title": "Filename",
        "key": "filename",
        "default_visible": True,
        "removable": False,
        # None -> smart-fill / stretch behavior handled by UI; use min_width as lower bound
        "width": None,
        "alignment": "left",
        # reuse file table filename min width for consistency
        "min_width": FILE_TABLE_COLUMN_CONFIG["filename"]["min_width"],
    },
    "hash": {
        "title": "Hash",
        "key": "hash",
        "default_visible": True,
        "removable": True,
        "width": RESULTS_TABLE_RIGHT_COLUMN_WIDTH,
        "alignment": "left",
        "min_width": 70,
    },
}

# =====================================
# COLOR COLUMN CONFIGURATION
# =====================================

# File tag color array for file tagging/organization
# 36 colors arranged in 4 rows x 9 columns
FILE_TAG_COLOR_ARRAY = [
    # Row 1 (Light colors)
    "#ffb86a",
    "#ffdf20",
    "#7bf1a8",
    "#46ecd5",
    "#74d4ff",
    "#a3b3ff",
    "#dab2ff",
    "#fda5d5",
    "#cccccc",
    # Row 2
    "#ff6900",
    "#f0b100",
    "#00c950",
    "#00bba7",
    "#00a6f4",
    "#615fff",
    "#ad46ff",
    "#f6339a",
    "#888888",
    # Row 3
    "#ca3500",
    "#a65f00",
    "#008236",
    "#00786f",
    "#0069a8",
    "#432dd7",
    "#8200db",
    "#c6005c",
    "#444444",
    # Row 4 (Dark colors)
    "#7e2a0c",
    "#733e0a",
    "#0d542b",
    "#0b4f4a",
    "#024a70",
    "#312c85",
    "#59168b",
    "#861043",
    "#000000",
]

# Color grid layout configuration
COLOR_GRID_ROWS = 4
COLOR_GRID_COLS = 9
COLOR_SWATCH_SIZE = 16  # Size of each color button in pixels
COLOR_PICKER_IMAGE = "resources/images/color_range.jpg"

# =====================================
# AUTO-COLOR FOLDERS CONFIGURATION
# =====================================

# Manual auto-color action for organizing files by folder
AUTO_COLOR_FOLDERS_ENABLED = True  # Feature flag to enable/disable the action
AUTO_COLOR_FOLDERS_SHORTCUT = "Ctrl+Shift+C"  # Keyboard shortcut for auto-color command
AUTO_COLOR_MIN_BRIGHTNESS = 32  # Minimum value for each RGB component (0-255)
AUTO_COLOR_MAX_RETRIES = 100  # Maximum attempts to find unique color

# =====================================
# METADATA STATUS ICON COLORS
# =====================================

# Metadata Status Icon Colors
METADATA_ICON_COLORS = {
    "basic": "#e8f4fd",  # Light blue for basic metadata
    "extended": EXTENDED_METADATA_COLOR,  # Orange for extended metadata
    "invalid": "#ff6b6b",  # Red for invalid metadata
    "loaded": "#51cf66",  # Green for loaded metadata (fast/basic)
    "modified": "#fffd9c",  # Yellow for modified metadata
    "partial": "#ffd139",  # Yellow for partial metadata
    "hash": "#ce93d8",  # Light purple for hash (brighter than before)
    "none": "#404040",  # Dark gray for no metadata/hash (grayout)
}
