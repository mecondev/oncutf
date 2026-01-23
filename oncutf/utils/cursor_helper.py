"""Module: cursor_helper.py.

Author: Michael Economou
Date: 2026-01-04

Delegator module for cursor helpers.

This module exists to provide a stable import path:

    from oncutf.utils.cursor_helper import wait_cursor

The implementation lives in oncutf.utils.ui.cursor_helper.
"""

from oncutf.utils.ui.cursor_helper import (  # noqa: F401
    emergency_cursor_cleanup,
    force_restore_cursor,
    get_current_cursor_info,
    wait_cursor,
)
