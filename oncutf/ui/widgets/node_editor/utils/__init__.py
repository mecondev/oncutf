from .ulid import is_ulid, new_ulid

__all__ = [
    "is_ulid",
    "new_ulid",
]
"""Utility functions and helpers for the node editor.

This module provides common utility functions used throughout the
node editor framework, including stylesheet loading, exception handling,
and logging configuration.

Functions:
    loadStylesheet: Load a single QSS stylesheet to QApplication.
    loadStylesheets: Load and concatenate multiple QSS stylesheets.
    is_ctrl_pressed: Check if Control modifier is active.
    is_shift_pressed: Check if Shift modifier is active.
    is_alt_pressed: Check if Alt modifier is active.
    dump_exception: Print exception with traceback for debugging.
    pp: Pretty-print objects to console.
    setup_logging: Configure application-wide logging handlers.
    get_logger: Get a named logger instance.

Author:
    Michael Economou

Date:
    2025-12-11
"""

from oncutf.ui.widgets.node_editor.utils.helpers import dump_exception, pp
from oncutf.ui.widgets.node_editor.utils.logging_config import get_logger, setup_logging
from oncutf.ui.widgets.node_editor.utils.qt_helpers import (
    is_alt_pressed,
    is_ctrl_pressed,
    is_shift_pressed,
    loadStylesheet,
    loadStylesheets,
)

__all__ = [
    "dump_exception",
    "pp",
    "loadStylesheet",
    "loadStylesheets",
    "is_ctrl_pressed",
    "is_shift_pressed",
    "is_alt_pressed",
    "setup_logging",
    "get_logger",
]
