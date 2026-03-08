"""Application lifecycle handlers -- signals, atexit, exception handling, shutdown.

Centralises all process lifecycle concerns that were previously scattered
across module-level code in main.py:

- Emergency cleanup (atexit / signal / unhandled-exception)
- Signal registration (SIGTERM, SIGINT)
- Global exception handler (sys.excepthook)
- Graceful post-exec shutdown sequence
- Emergency crash cleanup

Author: Michael Economou
Date: 2026-03-08
"""

from __future__ import annotations

import atexit
import contextlib
import gc
import platform
import signal
import sys
import time
from typing import TYPE_CHECKING

from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    import types

    from PyQt5.QtWidgets import QApplication

logger = get_cached_logger(__name__)

# Flags to prevent double cleanup
_cleanup_done = False
_app_quit_called = False


def cleanup_on_exit() -> None:
    """Cleanup function to run on application exit or signal."""
    global _cleanup_done
    if _cleanup_done:
        return
    _cleanup_done = True

    logger.info("=" * 70)
    logger.info("[CLEANUP] Emergency cleanup handler triggered (atexit/signal)")
    logger.info("=" * 70)

    try:
        from oncutf.utils.shared.json_config_manager import get_app_config_manager

        get_app_config_manager().save_immediate()
        logger.info("[CLEANUP] Configuration saved successfully")
    except Exception as e:
        logger.warning("[CLEANUP] Error saving configuration: %s", e)

    try:
        from oncutf.infra.external.exiftool_wrapper import ExifToolWrapper

        cleaned_count = ExifToolWrapper.force_cleanup_all_exiftool_processes()
        if cleaned_count > 0:
            logger.info("[CLEANUP] ExifTool processes terminated (%d)", cleaned_count)
    except Exception as e:
        logger.warning("[CLEANUP] Error terminating ExifTool processes: %s", e)

    try:
        from oncutf.ui.thumbnail.providers import VideoThumbnailProvider

        VideoThumbnailProvider.force_cleanup_all_ffmpeg_processes()
        logger.info("[CLEANUP] FFmpeg processes terminated")
    except Exception as e:
        logger.warning("[CLEANUP] Error terminating FFmpeg processes: %s", e)

    try:
        from oncutf.utils.lock_file import release_lock

        release_lock()
        logger.info("[CLEANUP] Lock file released")
    except Exception as e:
        logger.warning("[CLEANUP] Error releasing lock file: %s", e)


def _signal_handler(signum: int, _frame: types.FrameType | None) -> None:
    """Handle signals for graceful shutdown."""
    global _app_quit_called
    logger.info("[App] Received signal %d, performing cleanup...", signum)
    cleanup_on_exit()

    # Ensure QApplication exits cleanly without abrupt sys.exit
    try:
        from PyQt5.QtCore import QTimer
        from PyQt5.QtWidgets import QApplication as _QApp
    except Exception:
        sys.exit(0)

    app = _QApp.instance()
    if app:
        if not _app_quit_called:
            _app_quit_called = True
            QTimer.singleShot(0, app.quit)
        return

    sys.exit(0)


def _global_exception_handler(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_tb: types.TracebackType | None,
) -> None:
    """Global exception handler for unhandled exceptions.

    Logs the exception with full traceback and attempts graceful recovery.
    This prevents silent crashes and ensures all errors are logged.
    """
    # Don't intercept KeyboardInterrupt
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return

    # Log the exception with full traceback
    logger.critical("Unhandled exception occurred", exc_info=(exc_type, exc_value, exc_tb))

    # Attempt cleanup
    try:
        cleanup_on_exit()
    except Exception:
        logger.exception("Error during exception cleanup")


def setup_lifecycle_handlers() -> None:
    """Register signal handlers, atexit cleanup, and global exception handler."""
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)
    atexit.register(cleanup_on_exit)
    sys.excepthook = _global_exception_handler


def perform_graceful_shutdown(app: QApplication, exit_code: int) -> int:
    """Perform graceful shutdown after the Qt event loop exits.

    Args:
        app: The QApplication instance.
        exit_code: The exit code from app.exec_().

    Returns:
        The exit code to pass to sys.exit().

    """
    global _cleanup_done, _app_quit_called
    logger.info("[App] Application shutting down with exit code: %d", exit_code)

    # Force cleanup any remaining ExifTool processes
    try:
        from oncutf.infra.external.exiftool_wrapper import ExifToolWrapper

        cleaned_count = ExifToolWrapper.force_cleanup_all_exiftool_processes()
        _cleanup_done = True  # Mark cleanup as done to prevent atexit duplicate
        if cleaned_count > 0:
            logger.info("[App] ExifTool processes cleaned up (%d)", cleaned_count)
    except Exception as e:
        logger.warning("[App] Error cleaning up ExifTool processes: %s", e)

    # Windows-specific: Process pending deleteLater events before quit
    if platform.system() == "Windows":
        try:
            with contextlib.suppress(RuntimeError):
                app.processEvents()
                time.sleep(0.1)
        except Exception as win_cleanup_error:
            logger.warning("Windows cleanup delay failed: %s", win_cleanup_error)

    # Extra defensive UI cleanup: close windows, run event loop cycles and force GC
    try:
        with contextlib.suppress(Exception):
            app.closeAllWindows()

        for _ in range(8):
            with contextlib.suppress(Exception):
                app.processEvents()
            time.sleep(0.05)
            with contextlib.suppress(Exception):
                gc.collect()

        time.sleep(0.2)
    except Exception as extra_cleanup_error:
        logger.warning("Extra UI cleanup failed: %s", extra_cleanup_error)

    # Only call quit once to prevent runtime errors on Windows
    if not _app_quit_called:
        _app_quit_called = True
        try:
            app.quit()
        except RuntimeError as e:
            logger.debug("QApplication.quit() error (expected): %s", e)

    return exit_code


def perform_emergency_cleanup() -> None:
    """Emergency cleanup on fatal crash (ExifTool + lock file)."""
    try:
        from oncutf.infra.external.exiftool_wrapper import ExifToolWrapper

        ExifToolWrapper.force_cleanup_all_exiftool_processes()
    except Exception:
        pass
    try:
        from oncutf.utils.lock_file import release_lock

        release_lock()
    except Exception:
        pass
