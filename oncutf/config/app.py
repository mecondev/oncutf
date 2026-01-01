"""Module: oncutf.config.app

Author: Michael Economou
Date: 2026-01-01

Application-level configuration: app info, debug flags, logging settings.
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

APP_NAME = "oncutf"
APP_VERSION = "1.3"
APP_AUTHOR = "Michael Economou"

# Window
WINDOW_TITLE = "Batch File Renamer"

# =====================================
# LOGGING CONFIGURATION
# =====================================

LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Console logging
LOG_TO_CONSOLE = True
LOG_CONSOLE_LEVEL = "INFO"

# File logging
LOG_TO_FILE = True
LOG_FILE_LEVEL = "INFO"
LOG_FILE_MAX_BYTES = 10_000_000  # 10MB per file
LOG_FILE_BACKUP_COUNT = 5  # Keep 5 backup files

# Debug file logging
LOG_DEBUG_FILE_ENABLED = True
LOG_DEBUG_FILE_LEVEL = "DEBUG"
LOG_DEBUG_FILE_MAX_BYTES = 20_000_000  # 20MB per debug file
LOG_DEBUG_FILE_BACKUP_COUNT = 3

# Development logging settings
SHOW_DEV_ONLY_IN_CONSOLE = False
ENABLE_DEBUG_LOG_FILE = LOG_DEBUG_FILE_ENABLED

# =====================================
# DATABASE BACKUP SETTINGS
# =====================================

DEFAULT_BACKUP_COUNT = 2
DEFAULT_BACKUP_INTERVAL = 900  # 15 minutes
BACKUP_FILENAME_FORMAT = "{basename}_{timestamp}.db.bak"
BACKUP_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"
DEFAULT_PERIODIC_BACKUP_ENABLED = True

# =====================================
# CONFIG SAVE OPTIMIZATION
# =====================================

CONFIG_AUTO_SAVE_ENABLED = True
CONFIG_AUTO_SAVE_DELAY = 600  # 10 minutes
CONFIG_SAVE_ON_EXIT = True
CONFIG_SAVE_ON_DIALOG_CLOSE = True
CONFIG_CACHE_ENABLED = True
CONFIG_CACHE_FLUSH_ON_SAVE = True

# =====================================
# EXPORT SETTINGS
# =====================================

EXPORT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# =====================================
# DIALOG PATHS
# =====================================

DIALOG_PATHS = {"last_used": ""}

# =====================================
# WINDOW GEOMETRY AND STATE
# =====================================

MAIN_WINDOW_GEOMETRY = None
MAIN_WINDOW_STATE = None
