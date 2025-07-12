"""
Module: config_imports.py

Author: Michael Economou
Date: 2025-05-31

config_imports.py
Centralized config imports to reduce clutter in main files.
Re-exports commonly used configuration constants.
"""

from config import (
    app_name,
    app_version,
    app_author,
    log_level,
    log_format,
    log_file,
    dialog_paths,
    file_table_column_config,
    main_window_geometry,
    main_window_state,
    splitter_sizes,
)

# Re-export all config constants
__all__ = [
    'app_name',
    'app_version',
    'app_author',
    'log_level',
    'log_format',
    'log_file',
    'dialog_paths',
    'file_table_column_config',
    'main_window_geometry',
    'main_window_state',
    'splitter_sizes',
]
