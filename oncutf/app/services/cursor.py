"""Cursor management service - Application layer facade.

Provides Qt-independent cursor operations for core modules. Delegates to
CursorPort implementations registered in ApplicationContext.

This module breaks core→ui dependency cycles by inverting control:
- core/ imports this (app layer, no Qt)
- ui/ provides concrete implementations via ports

Author: Michael Economou
Date: 2026-01-22
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator

    from oncutf.app.ports.user_interaction import CursorPort


def get_cursor_adapter() -> CursorPort | None:
    """Get the registered CursorPort adapter.

    Returns:
        The registered adapter or None if not registered yet.

    """
    from oncutf.core.application_context import ApplicationContext

    try:
        ctx = ApplicationContext.get_instance()
        return ctx.get_manager("cursor") if ctx.has_manager("cursor") else None
    except RuntimeError:
        # ApplicationContext not initialized (e.g., in tests)
        return None


@contextlib.contextmanager
def wait_cursor(restore_after: bool = True) -> Generator[None, None, None]:
    """Context manager for wait cursor without Qt dependencies.

    Args:
        restore_after: If True, restore cursor after context (default).
                      If False, leave cursor as wait cursor.

    Example:
        with wait_cursor():
            # Long operation
            process_files()

    """
    adapter = get_cursor_adapter()

    if adapter:
        adapter.set_wait_cursor()
        try:
            yield
        finally:
            if restore_after:
                adapter.restore_cursor()
    else:
        # Fallback: direct Qt import (legacy behavior)
        from oncutf.utils.ui.cursor_helper import wait_cursor as legacy_wait_cursor

        with legacy_wait_cursor(restore_after=restore_after):
            yield


def force_restore_cursor() -> None:
    """Force restore cursor to normal state (emergency cleanup).

    This is used in error handlers and cleanup code to ensure cursor
    doesn't get stuck in wait state.
    """
    adapter = get_cursor_adapter()

    if adapter:
        adapter.force_restore_cursor()
    else:
        # Fallback: direct Qt import (legacy behavior)
        from oncutf.utils.ui.cursor_helper import force_restore_cursor as legacy_force_restore

        legacy_force_restore()
