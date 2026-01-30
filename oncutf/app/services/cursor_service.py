"""Cursor management service - Application layer facade.

Provides Qt-independent cursor operations for core modules. Delegates to
CursorPort implementations registered in QtAppContext.

This module breaks core->ui dependency cycles by inverting control:
- core/ imports this (app layer, no Qt)
- ui/ provides concrete implementations via ports

Author: Michael Economou
Date: 2026-01-22
Moved to app layer: 2026-01-30
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from collections.abc import Generator

    from oncutf.app.ports.user_interaction import CursorPort

logger = get_cached_logger(__name__)


def get_cursor_adapter() -> CursorPort | None:
    """Get the registered CursorPort adapter.

    Returns:
        The registered adapter or None if not registered yet.

    """
    from oncutf.app.state.context import AppContext

    try:
        ctx = AppContext.get_instance()
        return ctx.get_manager("cursor") if ctx.has_manager("cursor") else None
    except RuntimeError:
        # AppContext not initialized (e.g., in tests)
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
        # No adapter registered - just yield (no-op)
        logger.debug(
            "[cursor_service] No cursor adapter registered, cursor operations skipped",
            extra={"dev_only": True},
        )
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
        logger.debug(
            "[cursor_service] No cursor adapter registered, force_restore skipped",
            extra={"dev_only": True},
        )
