#!/usr/bin/env python3
"""
Module: main.py

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

# Add the project root to the path FIRST - before any local imports
# Normalize the path for Windows compatibility
project_root = os.path.normpath(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from oncutf.config import SPLASH_SCREEN_DURATION
from oncutf.core.pyqt_imports import QApplication, Qt
from oncutf.core.theme_manager import get_theme_manager
from oncutf.ui.main_window import MainWindow
from oncutf.utils.fonts import _get_inter_fonts
from oncutf.utils.logger_setup import ConfigureLogger
from oncutf.utils.theme_engine import ThemeEngine
from oncutf.ui.widgets.custom_splash_screen import CustomSplashScreen


# Calculate the user config directory for logs
def get_user_config_dir(app_name: str = "oncutf") -> str:
    """Get user configuration directory based on OS."""
    if os.name == "nt":
        base_dir = os.environ.get("APPDATA", os.path.expanduser("~"))
        return os.path.join(base_dir, app_name)
    else:
        base_dir = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
        return os.path.join(base_dir, app_name)


# Configure logging to use user config directory
config_dir = get_user_config_dir()
logs_dir = os.path.join(config_dir, "logs")
ConfigureLogger(log_name="oncutf", log_dir=logs_dir)

logger = logging.getLogger()

# Log application start with current date/time
now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
logger.info(f"Application started at {now}")

logger_effective_level = logger.getEffectiveLevel()
logger.debug(f"Effective logging level: {logger_effective_level}", extra={"dev_only": True})

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
        from oncutf.utils.json_config_manager import get_app_config_manager

        get_app_config_manager().save_immediate()
        logger.info("Configuration saved immediately before exit")
    except Exception as e:
        logger.warning(f"Error saving configuration during cleanup: {e}")

    try:
        from oncutf.utils.exiftool_wrapper import ExifToolWrapper

        ExifToolWrapper.force_cleanup_all_exiftool_processes()
        logger.info("Emergency ExifTool cleanup completed")
    except Exception as e:
        logger.warning(f"Error in emergency cleanup: {e}")


def signal_handler(signum, _frame) -> None:
    """Handle signals for graceful shutdown."""
    logger.info(f"Received signal {signum}, performing cleanup...")
    cleanup_on_exit()
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# Register atexit cleanup
atexit.register(cleanup_on_exit)


def main() -> int:
    """
    Entry point for the Batch File Renamer application.

    Initializes logging, creates a Qt application and stylesheet, creates a
    MainWindow and shows it, and enters the application's main loop.
    """
    try:
        # CRITICAL: Set working directory to project root first
        # This ensures all relative paths work correctly regardless of where script is run from
        os.chdir(project_root)
        logger.info(f"Working directory set to: {os.getcwd()}")

        # Log platform information for debugging
        logger.info(f"Platform: {platform.system()} {platform.release()}")
        logger.info(f"Python version: {sys.version}")
        logger.debug(f"Project root: {project_root}", extra={"dev_only": True})

        # Log Windows-specific info
        if platform.system() == "Windows":
            logger.info(f"Windows version: {platform.win32_ver()}")
            import locale

            logger.info(f"System locale: {locale.getdefaultlocale()}")
            logger.info(f"File system encoding: {sys.getfilesystemencoding()}")

        # Enable High DPI support before creating QApplication
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)  # type: ignore[attr-defined]
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)  # type: ignore[attr-defined]

        # Create application
        app = QApplication(sys.argv)

        # Log locale information (important for date/time formatting)
        try:
            import locale
            current_locale = locale.getlocale()
            logger.debug(f"Current locale: {current_locale}", extra={"dev_only": True})
        except Exception as e:
            logger.warning(f"Could not get locale: {e}")

        # Initialize DPI helper early
        from oncutf.utils.dpi_helper import get_dpi_helper, log_dpi_info

        get_dpi_helper()  # Initialize but don't store
        log_dpi_info()

        # Log font sizes for debugging
        try:
            from oncutf.utils.theme_font_generator import get_ui_font_sizes

            font_sizes = get_ui_font_sizes()
            logger.debug(f"Applied font sizes: {font_sizes}", extra={"dev_only": True})
        except ImportError:
            logger.warning("Could not get font sizes - DPI helper not available")

        # Set Fusion style for consistent cross-platform rendering
        # This ensures proper alternating row colors and theme consistency
        app.setStyle("Fusion")
        logger.debug("Applied Fusion style for cross-platform consistency", extra={"dev_only": True})

        # Load Inter fonts
        logger.debug("Initializing Inter fonts...", extra={"dev_only": True})
        _get_inter_fonts()

        # Initialize theme manager (new token-based system)
        theme_mgr = get_theme_manager()
        logger.debug(
            f"ThemeManager initialized with theme: {theme_mgr.get_current_theme()}",
            extra={"dev_only": True}
        )

        # Initialize theme engine (legacy global stylesheet system)
        theme_manager = ThemeEngine()

        # Create custom splash screen
        from oncutf.utils.path_utils import get_images_dir

        splash_path = get_images_dir() / "splash.png"
        logger.debug(f"Loading splash screen from: {splash_path}", extra={"dev_only": True})

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
                f"Splash screen displayed (size: {splash.splash_width}x{splash.splash_height})"
            )

            # Initialize state for dual-flag synchronization
            init_state = {
                'worker_ready': False,
                'min_time_elapsed': False,
                'worker_results': None,
                'worker_error': None,
                'window': None
            }

            # Start background initialization worker
            from oncutf.core.initialization_worker import InitializationWorker
            from oncutf.core.pyqt_imports import QThread

            worker = InitializationWorker()
            worker_thread = QThread()
            worker.moveToThread(worker_thread)

            # Connect signals for thread-safe communication
            def on_worker_progress(percentage: int, status: str):
                """Update splash status (runs in main thread via signal)."""
                logger.debug(f"[Init] {percentage}% - {status}", extra={"dev_only": True})
                # Future: could update splash status text here

            def on_worker_finished(results: dict):
                """Handle worker completion (runs in main thread via signal)."""
                logger.info(
                    f"[Init] Background initialization completed in "
                    f"{results.get('duration_ms', 0):.0f}ms"
                )
                init_state['worker_ready'] = True
                init_state['worker_results'] = results
                check_and_show_main()

            def on_worker_error(error_msg: str):
                """Handle worker failure (runs in main thread via signal)."""
                logger.error(f"[Init] Background initialization failed: {error_msg}")
                init_state['worker_ready'] = True
                init_state['worker_error'] = error_msg
                check_and_show_main()

            def on_min_time_elapsed():
                """Handle minimum splash time expiration (runs in main thread via timer)."""
                logger.debug("[Init] Minimum splash time elapsed", extra={"dev_only": True})
                init_state['min_time_elapsed'] = True
                check_and_show_main()

            def _apply_theme_to_app(qapp, legacy_theme_manager, token_theme_manager, win):
                """Apply theme to application and window (called before updates enabled)."""
                # Apply programmatic theme (legacy system)
                legacy_theme_manager.apply_complete_theme(qapp, win)

                # Apply ThemeManager QSS template on top (new token-based system)
                qss_content = token_theme_manager.get_qss()
                current_style = qapp.styleSheet()
                combined_style = (
                    current_style + "\n\n/* ThemeManager Token-Based Styles */\n" + qss_content
                )
                qapp.setStyleSheet(combined_style)
                logger.debug(
                    f"[Theme] Applied theme ({len(qss_content)} chars QSS)",
                    extra={"dev_only": True}
                )

            def check_and_show_main():
                """Show MainWindow when both worker and min time are ready."""
                if not (init_state['worker_ready'] and init_state['min_time_elapsed']):
                    return  # Wait for both conditions

                logger.info("[Init] All initialization complete, showing main window")

                try:
                    # Create MainWindow with theme callback (must be in main thread)
                    window = MainWindow(
                        theme_callback=lambda w: _apply_theme_to_app(app, theme_manager, theme_mgr, w)
                    )
                    init_state['window'] = window

                    # Show main window and close splash
                    splash.finish(window)
                    window.show()
                    window.raise_()
                    window.activateWindow()
                    app.processEvents()

                    # Cleanup worker thread
                    worker_thread.quit()
                    worker_thread.wait(1000)  # Wait max 1 second

                except Exception as e:
                    logger.error(f"[Init] Error creating MainWindow: {e}")
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
            from oncutf.utils.timer_manager import TimerType, get_timer_manager

            get_timer_manager().schedule(
                on_min_time_elapsed,
                delay=SPLASH_SCREEN_DURATION,
                timer_type=TimerType.GENERIC
            )

            # Add timeout safety fallback (10 seconds)
            def timeout_fallback():
                """Emergency fallback if initialization hangs."""
                if not init_state['window']:
                    logger.error("[Init] Initialization timeout - forcing MainWindow creation")
                    init_state['worker_ready'] = True
                    init_state['min_time_elapsed'] = True
                    check_and_show_main()

            get_timer_manager().schedule(
                timeout_fallback,
                delay=10000,  # 10 seconds
                timer_type=TimerType.GENERIC
            )

        except Exception as e:
            logger.error(f"Error creating splash screen: {e}")
            # Fallback: Initialize app without splash
            app.restoreOverrideCursor()
            window = MainWindow()
            window.show()
            window.raise_()
            window.activateWindow()

        # Run the app
        exit_code = app.exec_()

        # Clean up before exit
        logger.info(f"Application shutting down with exit code: {exit_code}")

        # Force cleanup any remaining ExifTool processes
        global _cleanup_done, _app_quit_called
        try:
            from oncutf.utils.exiftool_wrapper import ExifToolWrapper

            ExifToolWrapper.force_cleanup_all_exiftool_processes()
            _cleanup_done = True  # Mark cleanup as done to prevent atexit duplicate
            logger.info("ExifTool processes cleaned up")
        except Exception as e:
            logger.warning(f"Error cleaning up ExifTool processes: {e}")

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
                logger.warning(f"Windows cleanup delay failed: {win_cleanup_error}")

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
            logger.warning(f"Extra UI cleanup failed: {extra_cleanup_error}")

        # Only call quit once to prevent runtime errors on Windows
        if not _app_quit_called:
            _app_quit_called = True
            try:
                app.quit()
            except RuntimeError as e:
                logger.debug(f"QApplication.quit() error (expected): {e}")

        return exit_code

    except Exception as e:
        logger.critical(f"Fatal error in main: {str(e)}", exc_info=True)
        # Emergency cleanup on crash
        try:
            from oncutf.utils.exiftool_wrapper import ExifToolWrapper
            ExifToolWrapper.force_cleanup_all_exiftool_processes()
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
