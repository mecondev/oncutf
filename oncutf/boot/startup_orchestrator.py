"""Startup orchestration -- splash screen, boot worker, dual-flag synchronization.

Encapsulates the splash-screen display, background BootstrapWorker thread,
and the dual-flag gate that creates and shows MainWindow once both the
worker finishes and the minimum splash duration elapses.

Author: Michael Economou
Date: 2026-03-08
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QApplication

    from oncutf.ui.theme_manager import ThemeManager

logger = get_cached_logger(__name__)


def run_startup(app: QApplication, theme_manager: ThemeManager) -> None:
    """Create splash screen, start boot worker, and set up dual-flag synchronization.

    When both the boot worker completes and the minimum splash time elapses,
    the MainWindow is created and shown.  If splash creation fails, MainWindow
    is created directly as a fallback.

    This function is non-blocking: it sets up Qt signals/timers and returns
    immediately.  The actual window creation happens asynchronously inside the
    Qt event loop.

    Args:
        app: The QApplication instance.
        theme_manager: The initialized ThemeManager.

    """
    from oncutf.config import SPLASH_SCREEN_DURATION, WAIT_CURSOR_SUPPRESS_AFTER_SPLASH_MS
    from oncutf.ui.main_window import MainWindow
    from oncutf.ui.widgets.custom_splash_screen import CustomSplashScreen
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

        # -- Callback closures (run in main thread via Qt signals) ---------

        def on_worker_progress(percentage: int, status: str) -> None:
            """Update splash status (runs in main thread via signal)."""
            logger.debug("[Init] %d%% - %s", percentage, status, extra={"dev_only": True})
            # Future: could update splash status text here

        def on_worker_finished(results: dict) -> None:
            """Handle worker completion (runs in main thread via signal)."""
            logger.info(
                "[Init] Background initialization completed in %.0fms",
                results.get("duration_ms", 0),
            )
            init_state["worker_ready"] = True
            init_state["worker_results"] = results
            check_and_show_main()

        def on_worker_error(error_msg: str) -> None:
            """Handle worker failure (runs in main thread via signal)."""
            logger.error("[Init] Background initialization failed: %s", error_msg)
            init_state["worker_ready"] = True
            init_state["worker_error"] = error_msg
            check_and_show_main()

        def on_min_time_elapsed() -> None:
            """Handle minimum splash time expiration (runs in main thread via timer)."""
            logger.debug("[Init] Minimum splash time elapsed", extra={"dev_only": True})
            init_state["min_time_elapsed"] = True
            check_and_show_main()

        def _apply_theme(qapp, tm, win) -> None:  # type: ignore[no-untyped-def]
            """Apply theme to application and window (called before updates enabled)."""
            tm.apply_complete_theme(qapp, win)
            logger.debug(
                "[Theme] Applied complete theme (%s)",
                tm.get_current_theme(),
                extra={"dev_only": True},
            )

        def check_and_show_main() -> None:
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
                window = MainWindow(theme_callback=lambda w: _apply_theme(app, theme_manager, w))
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

            except Exception:
                logger.exception("[Init] Error creating MainWindow")
                splash.close()
                raise

        # -- Wire signals and start ----------------------------------------

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
        def timeout_fallback() -> None:
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

    except Exception:
        logger.exception("Error creating splash screen")
        # Fallback: Initialize app without splash
        app.restoreOverrideCursor()
        window = MainWindow()
        window.show()
        window.raise_()
        window.activateWindow()
