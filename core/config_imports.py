"""
Module: config_imports.py

Author: Michael Economou
Date: 2025-05-31

config_imports.py
Centralized config imports to reduce clutter in main files.
Re-exports commonly used configuration constants.
"""

from config import (
    APP_NAME,
    APP_VERSION,
    APP_AUTHOR,
    LOG_LEVEL,
    LOG_FORMAT,
    DIALOG_PATHS,
    FILE_TABLE_COLUMN_CONFIG,
    MAIN_WINDOW_GEOMETRY,
    MAIN_WINDOW_STATE,
    TOP_BOTTOM_SPLIT_RATIO,
    LEFT_CENTER_RIGHT_SPLIT_RATIO,
)

# Re-export all config constants
__all__ = [
    'APP_NAME',
    'APP_VERSION',
    'APP_AUTHOR',
    'LOG_LEVEL',
    'LOG_FORMAT',
    'DIALOG_PATHS',
    'FILE_TABLE_COLUMN_CONFIG',
    'MAIN_WINDOW_GEOMETRY',
    'MAIN_WINDOW_STATE',
    'TOP_BOTTOM_SPLIT_RATIO',
    'LEFT_CENTER_RIGHT_SPLIT_RATIO',
]
