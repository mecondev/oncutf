"""Module: oncutf.config.paths.

Author: Michael Economou
Date: 2026-01-01

File paths, extensions, and validation patterns.
"""

from oncutf.config.file_types import ALLOWED_EXTENSIONS  # re-export

# =====================================
# FILENAME VALIDATION
# =====================================

# Regex pattern for Windows-safe names
ALLOWED_FILENAME_CHARS = r"^[^\\/:*?\"<>|]+$"

# Invalid filename characters for input filtering
INVALID_FILENAME_CHARS = '<>:"/\\|?*'

# Characters that shouldn't be at the end of filename (before extension)
INVALID_TRAILING_CHARS = " ."

# Validation error marker (unique string that users won't intentionally use)
INVALID_FILENAME_MARKER = "__VALIDATION_ERROR__"

# =====================================
# COMPANION FILES SETTINGS
# =====================================

COMPANION_FILES_ENABLED = True
SHOW_COMPANION_FILES_IN_TABLE = False
AUTO_RENAME_COMPANION_FILES = True
LOAD_COMPANION_METADATA = True

CompanionFileMode = {
    "HIDE": "hide",
    "SHOW": "show",
    "SHOW_GROUPED": "grouped",
}

DEFAULT_COMPANION_FILE_MODE = CompanionFileMode["HIDE"]

# =====================================
# FILE SIZE FORMATTING
# =====================================

USE_BINARY_UNITS = False  # False = SI units (1000), True = Binary units (1024)
USE_LOCALE_DECIMAL_SEPARATOR = True
