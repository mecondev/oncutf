"""Module: oncutf.config.features.

Author: Michael Economou
Date: 2026-01-01

Feature flags, external tools, performance limits.
"""

# =====================================
# EXTERNAL TOOLS CONFIGURATION
# =====================================


class FeatureAvailability:
    """Runtime feature availability based on external tool detection.

    This class tracks which external tools are available and enables/disables
    features accordingly. It provides graceful degradation when tools are missing.

    Updated automatically by oncutf.utils.shared.external_tools module during initialization.
    """

    exiftool_available: bool = False
    ffmpeg_available: bool = False

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
        """Update tool availability flags."""
        cls.exiftool_available = exiftool
        cls.ffmpeg_available = ffmpeg


# =====================================
# EXIFTOOL TIMEOUT SETTINGS
# =====================================

EXIFTOOL_TIMEOUT_FAST = 60
EXIFTOOL_TIMEOUT_EXTENDED = 240
EXIFTOOL_TIMEOUT_WRITE = 10
EXIFTOOL_TIMEOUT_BATCH_BASE = 60
EXIFTOOL_TIMEOUT_BATCH_PER_FILE = 0.5

# =====================================
# HASH CALCULATION PERFORMANCE
# =====================================

USE_PARALLEL_HASH_WORKER = True
PARALLEL_HASH_MAX_WORKERS = None  # Auto-detect optimal count

# =====================================
# FILE HANDLING LIMITS
# =====================================

USE_PREVIEW_BACKGROUND = False
LARGE_FOLDER_WARNING_THRESHOLD = 150
EXTENDED_METADATA_SIZE_LIMIT_MB = 500

# =====================================
# UNDO/REDO SYSTEM SETTINGS
# =====================================

UNDO_REDO_SETTINGS = {
    "MAX_UNDO_STEPS": 300,
    "UNDO_SHORTCUT": "Ctrl+Z",
    "REDO_SHORTCUT": "Ctrl+Shift+Z",
    "HISTORY_SHORTCUT": "Ctrl+Y",
    "RESULTS_HASH_LIST_SHORTCUT": "Ctrl+L",
    "COMMAND_GROUPING_TIMEOUT": 1000,
    "PERSIST_UNDO_HISTORY": False,
    "UNDO_AVAILABLE_COLOR": "#51cf66",
    "REDO_AVAILABLE_COLOR": "#74c0fc",
    "UNAVAILABLE_COLOR": "#6c757d",
    "HISTORY_DIALOG_WIDTH": 900,
    "HISTORY_DIALOG_HEIGHT": 700,
    "HISTORY_ITEMS_PER_PAGE": 50,
}

COMMAND_TYPES = {
    "METADATA_EDIT": "metadata_edit",
    "METADATA_RESET": "metadata_reset",
    "METADATA_SAVE": "metadata_save",
    "RENAME_OPERATION": "rename_operation",
    "BATCH_OPERATION": "batch_operation",
}

# =====================================
# SAVE OPERATION SETTINGS
# =====================================

SAVE_OPERATION_SETTINGS = {
    "ALLOW_CANCEL_NORMAL_SAVE": True,
}

# =====================================
# AUTO-COLOR FOLDERS CONFIGURATION
# =====================================

AUTO_COLOR_FOLDERS_ENABLED = True
AUTO_COLOR_FOLDERS_SHORTCUT = "Ctrl+Shift+C"
AUTO_COLOR_MIN_BRIGHTNESS = 32
AUTO_COLOR_MAX_RETRIES = 100
