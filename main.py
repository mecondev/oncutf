#!/usr/bin/env python3
"""Module: main.py.

Author: Michael Economou
Date: 2025-05-01

This module serves as the entry point for the oncutf application.
It sets up logging, initializes the Qt application with a stylesheet, creates
and displays the main window, and starts the application's main event loop.

Functions:
    main: Initializes and runs the Batch File Renamer application.
"""

import atexit
import logging
import os
import platform
import signal
import sys
import time
from pathlib import Path
from typing import Any

# Add the project root to the path FIRST - before any local imports
# Use pathlib for path manipulation
project_root = str(Path(__file__).resolve().parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from oncutf.config import SPLASH_SCREEN_DURATION, WAIT_CURSOR_SUPPRESS_AFTER_SPLASH_MS
from oncutf.ui.helpers.fonts import _get_inter_fonts, _get_jetbrains_fonts
from oncutf.ui.main_window import MainWindow
from oncutf.ui.theme_manager import get_theme_manager
from oncutf.ui.widgets.custom_splash_screen import CustomSplashScreen
from oncutf.utils.logging.logger_setup import ConfigureLogger
from oncutf.utils.paths import AppPaths

# Configure logging to use centralized user data directory
logs_dir = str(AppPaths.get_logs_dir())
ConfigureLogger(log_name="oncutf", log_dir=logs_dir)

logger = logging.getLogger()

# Log application start with current date/time
now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
logger.info("[App] Application started at %s", now)

logger_effective_level = logger.getEffectiveLevel()
logger.debug("Effective logging level: %d", logger_effective_level, extra={"dev_only": True})

# Flag to prevent double cleanup
_cleanup_done = False
_app_quit_called = False


def cleanup_on_exit() -> None:
    """Cleanup function to run on application exit or signal."""
    global _cleanup_done
    if _cleanup_done:
        return
    _cleanup_done = True

    try:
        # Save configuration immediately before exit
        from oncutf.utils.shared.json_config_manager import get_app_config_manager

        get_app_config_manager().save_immediate()
        logger.info("[App] Configuration saved immediately before exit")
    except Exception as e:
        logger.warning("[App] Error saving configuration during cleanup: %s", e)

    try:
        from oncutf.infra.external.exiftool_wrapper import ExifToolWrapper

        ExifToolWrapper.force_cleanup_all_exiftool_processes()
        logger.info("[App] Emergency ExifTool cleanup completed")
    except Exception as e:
        logger.warning("[App] Error in emergency ExifTool cleanup: %s", e)

    try:
        from oncutf.core.thumbnail.providers import VideoThumbnailProvider

        VideoThumbnailProvider.force_cleanup_all_ffmpeg_processes()
        logger.info("[App] Emergency FFmpeg cleanup completed")
    except Exception as e:
        logger.warning("[App] Error in emergency FFmpeg cleanup: %s", e)


def signal_handler(signum, _frame) -> None:
    """Handle signals for graceful shutdown."""
    logger.info("[App] Received signal %d, performing cleanup...", signum)
    cleanup_on_exit()
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# Register atexit cleanup
atexit.register(cleanup_on_exit)


def global_exception_handler(exc_type, exc_value, exc_tb) -> None:
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
    except Exception as cleanup_error:
        logger.exception("Error during exception cleanup: %s", cleanup_error)


# Install global exception handler
sys.excepthook = global_exception_handler


def main() -> int:
    """Entry point for the Batch File Renamer application.

    Initializes logging, creates a Qt application and stylesheet, creates a
    MainWindow and shows it, and enters the application's main loop.
    """
    try:
        # CRITICAL: Set working directory to project root first
        # This ensures all relative paths work correctly regardless of where script is run from
        os.chdir(project_root)
        logger.info("[App] Working directory set to: %s", Path.cwd())

        # Log platform information for debugging
        logger.info("[App] Platform: %s %s", platform.system(), platform.release())
        logger.info("[App] Python version: %s", sys.version)
        logger.debug("Project root: %s", project_root, extra={"dev_only": True})

        # Log Windows-specific info
        if platform.system() == "Windows":
            logger.info("[App] Windows version: %s", platform.win32_ver())
            import locale

            logger.info("[App] System locale: %s", locale.getdefaultlocale())
            logger.info("[App] File system encoding: %s", sys.getfilesystemencoding())

        # Enable High DPI support before creating QApplication
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        # Create application
        app = QApplication(sys.argv)

        # Log locale information (important for date/time formatting)
        try:
            import locale

            current_locale = locale.getlocale()
            logger.debug("Current locale: %s", current_locale, extra={"dev_only": True})
        except Exception as e:
            logger.warning("Could not get locale: %s", e)

        # Initialize DPI helper early
        from oncutf.ui.helpers.dpi_helper import get_dpi_helper, log_dpi_info

        get_dpi_helper()  # Initialize but don't store
        log_dpi_info()

        # Log font sizes for debugging
        try:
            from oncutf.ui.helpers.theme_font_generator import get_ui_font_sizes

            font_sizes = get_ui_font_sizes()
            logger.debug("Applied font sizes: %s", font_sizes, extra={"dev_only": True})
        except ImportError:
            logger.warning("Could not get font sizes - DPI helper not available")

        # Set Fusion style for consistent cross-platform rendering
        # This ensures proper alternating row colors and theme consistency
        app.setStyle("Fusion")
        logger.debug(
            "Applied Fusion style for cross-platform consistency",
            extra={"dev_only": True},
        )

        # Load Inter fonts
        logger.debug("Initializing Inter fonts...", extra={"dev_only": True})
        _get_inter_fonts()

        # Load JetBrains Mono fonts
        logger.debug("Initializing JetBrains Mono fonts...", extra={"dev_only": True})
        _get_jetbrains_fonts()

        # Initialize theme manager (singleton)
        theme_manager = get_theme_manager()
        logger.debug(
            "ThemeManager initialized with theme: %s",
            theme_manager.get_current_theme(),
            extra={"dev_only": True},
        )

        # Configure default services for dependency injection
        logger.debug("Configuring default services...", extra={"dev_only": True})
        from oncutf.app.ports import configure_default_services

        configure_default_services()
        logger.info("[App] Default services configured")

        # Create custom splash screen
        from oncutf.utils.filesystem.path_utils import get_images_dir

        splash_path = get_images_dir() / "splash.png"
        logger.debug("Loading splash screen from: %s", splash_path, extra={"dev_only": True})

        try:
            # Create and show splash screen immediately (responsive from start)
            splash = CustomSplashScreen(str(splash_path))
            splash.show()
            splash.raise_()
            splash.activateWindow()
            # Process events multiple times to ensure splash is fully rendered
            for _ in range(3):
                app.processEvents()

            logger.info(
                "[App] Splash screen displayed (size: %dx%d)",
                splash.splash_width,
                splash.splash_height,
            )

            # Initialize state for dual-flag synchronization
            init_state: dict[str, Any] = {
                "worker_ready": False,
                "min_time_elapsed": False,
                "worker_results": None,
                "worker_error": None,
                "window": None,
            }

            # Start background initialization worker
            from PyQt5.QtCore import QThread

            from oncutf.ui.boot.bootstrap_worker import BootstrapWorker

            worker = BootstrapWorker()
            worker_thread = QThread()
            worker.moveToThread(worker_thread)

            # Connect signals for thread-safe communication
            def on_worker_progress(percentage: int, status: str):
                """Update splash status (runs in main thread via signal)."""
                logger.debug("[Init] %d%% - %s", percentage, status, extra={"dev_only": True})
                # Future: could update splash status text here

            def on_worker_finished(results: dict):
                """Handle worker completion (runs in main thread via signal)."""
                logger.info(
                    "[Init] Background initialization completed in %.0fms",
                    results.get("duration_ms", 0),
                )
                init_state["worker_ready"] = True
                init_state["worker_results"] = results
                check_and_show_main()

            def on_worker_error(error_msg: str):
                """Handle worker failure (runs in main thread via signal)."""
                logger.error("[Init] Background initialization failed: %s", error_msg)
                init_state["worker_ready"] = True
                init_state["worker_error"] = error_msg
                check_and_show_main()

            def on_min_time_elapsed():
                """Handle minimum splash time expiration (runs in main thread via timer)."""
                logger.debug("[Init] Minimum splash time elapsed", extra={"dev_only": True})
                init_state["min_time_elapsed"] = True
                check_and_show_main()

            def _apply_theme_to_app(qapp, theme_manager, win):
                """Apply theme to application and window (called before updates enabled)."""
                # Apply complete theme (programmatic + QSS template)
                theme_manager.apply_complete_theme(qapp, win)
                logger.debug(
                    "[Theme] Applied complete theme (%s)",
                    theme_manager.get_current_theme(),
                    extra={"dev_only": True},
                )

            def check_and_show_main():
                """Show MainWindow when both worker and min time are ready."""
                if not (init_state["worker_ready"] and init_state["min_time_elapsed"]):
                    return  # Wait for both conditions

                logger.info("[Init] All initialization complete, showing main window")

                try:
                    # Suppress wait cursor during MainWindow construction so any
                    # early wait_cursor usage inside init does not flicker.
                    try:
                        from oncutf.ui.helpers.cursor_helper import (
                            suppress_wait_cursor_for,
                        )

                        suppress_wait_cursor_for(5.0)
                    except Exception:
                        pass

                    # Create MainWindow with theme callback (must be in main thread)
                    window = MainWindow(
                        theme_callback=lambda w: _apply_theme_to_app(app, theme_manager, w)
                    )
                    init_state["window"] = window

                    # Show main window and close splash
                    splash.finish(window)

                    # Startup polish: delay wait-cursor usage for 1s after splash closes.
                    # This prevents cursor flicker during immediate post-splash init work.
                    try:
                        import time

                        from oncutf.ui.helpers.cursor_helper import (
                            set_wait_cursor_suppressed_until,
                        )

                        set_wait_cursor_suppressed_until(
                            time.monotonic() + (WAIT_CURSOR_SUPPRESS_AFTER_SPLASH_MS / 1000.0)
                        )
                    except Exception:
                        pass

                    window.show()
                    window.raise_()
                    window.activateWindow()
                    app.processEvents()

                    # Cleanup worker thread
                    worker_thread.quit()
                    worker_thread.wait(1000)  # Wait max 1 second

                except Exception as e:
                    logger.exception("[Init] Error creating MainWindow: %s", e)
                    splash.close()
                    raise

            # Connect worker signals
            worker.progress.connect(on_worker_progress)
            worker.finished.connect(on_worker_finished)
            worker.error.connect(on_worker_error)

            # Connect worker to thread start
            worker_thread.started.connect(worker.run)

            # Start worker thread
            worker_thread.start()
            logger.debug("[Init] Background worker thread started", extra={"dev_only": True})

            # Schedule minimum splash time callback
            from oncutf.utils.shared.timer_manager import TimerType, get_timer_manager

            get_timer_manager().schedule(
                on_min_time_elapsed,
                delay=SPLASH_SCREEN_DURATION,
                timer_type=TimerType.GENERIC,
            )

            # Add timeout safety fallback (10 seconds)
            def timeout_fallback():
                """Emergency fallback if initialization hangs."""
                if not init_state["window"]:
                    logger.error("[Init] Initialization timeout - forcing MainWindow creation")
                    init_state["worker_ready"] = True
                    init_state["min_time_elapsed"] = True
                    check_and_show_main()

            get_timer_manager().schedule(
                timeout_fallback,
                delay=10000,  # 10 seconds
                timer_type=TimerType.GENERIC,
            )

        except Exception as e:
            logger.exception("Error creating splash screen: %s", e)
            # Fallback: Initialize app without splash
            app.restoreOverrideCursor()
            window = MainWindow()
            window.show()
            window.raise_()
            window.activateWindow()

        # Run the app
        exit_code = app.exec_()

        # Clean up before exit
        logger.info("[App] Application shutting down with exit code: %d", exit_code)

        # Force cleanup any remaining ExifTool processes
        global _cleanup_done, _app_quit_called
        try:
            from oncutf.infra.external.exiftool_wrapper import ExifToolWrapper

            ExifToolWrapper.force_cleanup_all_exiftool_processes()
            _cleanup_done = True  # Mark cleanup as done to prevent atexit duplicate
            logger.info("[App] ExifTool processes cleaned up")
        except Exception as e:
            logger.warning("[App] Error cleaning up ExifTool processes: %s", e)

        # Windows-specific: Process pending deleteLater events before quit
        if platform.system() == "Windows":
            try:
                import contextlib

                with contextlib.suppress(RuntimeError):
                    app.processEvents()
                    # Short delay for Windows to clean up handles
                    import time as time_module

                    time_module.sleep(0.1)
            except Exception as win_cleanup_error:
                logger.warning("Windows cleanup delay failed: %s", win_cleanup_error)

        # Extra defensive UI cleanup: close windows, run event loop cycles and force GC
        try:
            import gc

            # Ensure top-level windows are closed so Qt can release native resources
            with __import__("contextlib").suppress(Exception):
                app.closeAllWindows()

            # Run several small event-loop cycles and force garbage collection
            for _ in range(8):
                with __import__("contextlib").suppress(Exception):
                    app.processEvents()
                time.sleep(0.05)
                with __import__("contextlib").suppress(Exception):
                    gc.collect()

            # Extra short wait to allow native handles to be released
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

    except Exception as e:
        logger.exception("Fatal error in main: %s", str(e))
        # Emergency cleanup on crash
        try:
            from oncutf.infra.external.exiftool_wrapper import ExifToolWrapper

            ExifToolWrapper.force_cleanup_all_exiftool_processes()
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
