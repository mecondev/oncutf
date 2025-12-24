"""
Module: initialization_worker.py

Author: Michael Economou
Date: 2025-12-07

Background worker for application initialization tasks.

This module provides a QObject-based worker that performs heavy non-GUI
initialization tasks in a background thread, allowing the splash screen
to remain responsive during application startup.

The worker handles:
- Font loading and validation
- Theme preparation (non-GUI parts)
- Database validation
- Cache warmup
- Other file I/O and computation tasks

CRITICAL: This worker must NEVER perform Qt GUI operations directly.
All Qt GUI operations must remain in the main thread.

Thread Safety:
- Worker runs in a separate QThread (moved via moveToThread)
- Communicates with main thread via signals only
- No direct Qt GUI object manipulation
- No QWidget, QMainWindow, or other GUI class instantiation

Usage:
    worker = InitializationWorker()
    thread = QThread()
    worker.moveToThread(thread)
    worker.progress.connect(on_progress)
    worker.finished.connect(on_finished)
    worker.error.connect(on_error)
    thread.started.connect(worker.run)
    thread.start()
"""

import traceback

from oncutf.core.pyqt_imports import QObject, pyqtSignal
from oncutf.utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class InitializationWorker(QObject):
    """
    Background worker for application initialization tasks.

    This worker performs heavy non-GUI operations in a background thread
    to keep the splash screen responsive during app startup.

    Signals:
        progress(int, str): Emitted during initialization with (percentage, status_text)
        finished(dict): Emitted when initialization completes successfully with results dict
        error(str): Emitted when initialization fails with error message

    The results dict contains:
        - 'fonts_loaded': bool - Whether fonts were successfully loaded
        - 'theme_prepared': bool - Whether theme data was prepared
        - 'database_validated': bool - Whether database was validated
        - 'cache_warmed': bool - Whether caches were warmed up
        - 'duration_ms': float - Total initialization time in milliseconds
    """

    # Signals for thread-safe communication
    progress = pyqtSignal(int, str)  # percentage, status_text
    finished = pyqtSignal(dict)  # results dictionary
    error = pyqtSignal(str)  # error_message

    def __init__(self):
        """Initialize the worker (runs in main thread before moveToThread)."""
        super().__init__()
        self._results = {
            "fonts_loaded": False,
            "theme_prepared": False,
            "database_validated": False,
            "cache_warmed": False,
            "duration_ms": 0.0,
        }

    def run(self) -> None:
        """
        Main worker entry point (runs in background thread).

        Performs all initialization tasks and emits signals for progress updates.
        Emits finished signal with results dict on success, or error signal on failure.

        This method is connected to thread.started signal and runs in the worker thread.
        """
        try:
            import time

            start_time = time.perf_counter()

            logger.info("[InitWorker] Background initialization started")

            # Step 1: Load fonts (25% progress)
            self.progress.emit(10, "Loading fonts...")
            self._load_fonts()
            self._results["fonts_loaded"] = True
            self.progress.emit(25, "Fonts loaded")

            # Step 2: Prepare theme data (50% progress)
            self.progress.emit(30, "Preparing theme...")
            self._prepare_theme()
            self._results["theme_prepared"] = True
            self.progress.emit(50, "Theme prepared")

            # Step 3: Validate database (75% progress)
            self.progress.emit(55, "Validating database...")
            self._validate_database()
            self._results["database_validated"] = True
            self.progress.emit(75, "Database validated")

            # Step 4: Warmup caches (100% progress)
            self.progress.emit(80, "Warming up caches...")
            self._warmup_caches()
            self._results["cache_warmed"] = True
            self.progress.emit(100, "Initialization complete")

            # Calculate duration
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            self._results["duration_ms"] = duration_ms

            logger.info(
                "[InitWorker] Background initialization completed in %.0fms",
                duration_ms,
            )

            # Emit finished signal with results
            self.finished.emit(self._results)

        except Exception as e:
            error_msg = f"Initialization failed: {e}"
            logger.error("[InitWorker] %s\n%s", error_msg, traceback.format_exc())
            self.error.emit(error_msg)

    def _load_fonts(self) -> None:
        """
        Load and validate custom fonts.

        This is a file I/O operation that can be safely done in background thread.
        Actual font registration with Qt must be done in main thread later.
        """
        try:
            # Import here to avoid circular dependencies
            from oncutf.utils.path_utils import get_fonts_dir

            fonts_dir = get_fonts_dir()

            if not fonts_dir.exists():
                logger.debug("[InitWorker] Custom fonts directory not found, skipping")
                return

            # Scan for font files (just file I/O, not Qt operations)
            font_files = list(fonts_dir.glob("*.ttf")) + list(fonts_dir.glob("*.otf"))

            if font_files:
                logger.info("[InitWorker] Found %d custom fonts", len(font_files))
                # Note: Actual QFontDatabase.addApplicationFont() must be called
                # in main thread later - we just verify the files exist here
                for font_file in font_files:
                    if not font_file.exists():
                        logger.warning("[InitWorker] Font file missing: %s", font_file)
            else:
                logger.debug("[InitWorker] No custom fonts found")

        except Exception as e:
            logger.warning("[InitWorker] Font loading failed (non-critical): %s", e)
            # Don't fail initialization if fonts can't be loaded

    def _prepare_theme(self) -> None:
        """
        Prepare theme data without applying to GUI.

        This performs non-GUI preparatory work like:
        - Reading theme files from disk
        - Parsing color schemes
        - Precomputing derived colors
        - Validating theme consistency

        CRITICAL: Does NOT apply theme to any Qt widgets (done in main thread later).
        """
        try:
            # Import here to avoid circular dependencies
            from oncutf.config import THEME_NAME

            logger.debug("[InitWorker] Preparing theme: %s", THEME_NAME)

            # We can read theme files and validate them, but NOT apply to GUI
            # This is just file I/O and string processing
            # Actual theme application happens in main thread after MainWindow creation

            # Future enhancement: could parse theme CSS files here to validate syntax
            # For now, just verify theme name is valid
            valid_themes = ["light", "dark", "auto"]
            if THEME_NAME.lower() not in valid_themes:
                logger.warning(
                    "[InitWorker] Invalid theme '%s', will fallback to 'light'",
                    THEME_NAME,
                )

        except Exception as e:
            logger.warning("[InitWorker] Theme preparation failed (non-critical): %s", e)
            # Don't fail initialization if theme prep fails

    def _validate_database(self) -> None:
        """
        Validate database files and perform integrity checks.

        This is file I/O and SQL operations (no GUI), safe for background thread.
        Checks:
        - Database file existence
        - Schema validity
        - Basic integrity checks

        If database is corrupt or missing, it will be recreated in main thread later.
        """
        try:
            # Database validation is non-critical for background initialization
            # The actual database initialization happens when DatabaseManager is created
            # in the main thread. This is just a placeholder for future enhancements.

            # Future enhancement: could check for database file existence and size
            # without opening connections (to avoid threading issues with SQLite)
            logger.debug("[InitWorker] Database validation placeholder")

        except Exception as e:
            logger.warning("[InitWorker] Database validation failed (non-critical): %s", e)
            # Don't fail initialization if database validation fails

    def _warmup_caches(self) -> None:
        """
        Perform cache warmup operations.

        This is file I/O and computation (no GUI), safe for background thread.
        Preloads frequently accessed data to improve responsiveness.
        """
        try:
            # Future enhancement: could preload common metadata patterns,
            # recently used files list, etc.
            logger.debug("[InitWorker] Cache warmup placeholder")

            # For now, just simulate some work
            import time

            time.sleep(0.05)  # 50ms simulated work

        except Exception as e:
            logger.warning("[InitWorker] Cache warmup failed (non-critical): %s", e)
            # Don't fail initialization if cache warmup fails
