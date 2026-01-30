"""Module: cursor_helper.py.

Author: Michael Economou
Date: 2026-01-04

Delegator module for cursor helpers.

This module exists to provide a stable import path:

    from oncutf.utils.cursor_helper import wait_cursor

The implementation lives in oncutf.ui.helpers.cursor_helper.
"""

from oncutf.ui.helpers.cursor_helper import (
    emergency_cursor_cleanup,
    force_restore_cursor,
    get_current_cursor_info,
    wait_cursor,
)

__all__ = [
    "emergency_cursor_cleanup",
    "force_restore_cursor",
    "get_current_cursor_info",
    "wait_cursor",
]
