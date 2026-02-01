"""Module: shutdown_coordinator.py.

Author: Michael Economou
Date: 2025-11-21

Shutdown Coordinator Module

Provides centralized, ordered shutdown coordination for all concurrent components
in oncutf. Ensures safe, graceful termination with health checks and timeout handling.

Features:
- Ordered shutdown phases (timers → async → threads → database → exiftool)
- Health checks before shutdown
- Timeout handling per phase
- Progress callbacks for UI updates
- Emergency shutdown fallback
- Comprehensive logging
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, ClassVar

from PyQt5.QtCore import QObject, QTimer, pyqtSignal

logger = logging.getLogger(__name__)


class ShutdownPhase(Enum):
    """Shutdown phases in execution order."""

    TIMERS = "timers"
    THREAD_POOL = "thread_pool"
    THUMBNAILS = "thumbnails"  # Must shutdown before database
    DATABASE = "database"
    EXIFTOOL = "exiftool"
    FINALIZE = "finalize"


@dataclass
class ShutdownResult:
    """Result of a shutdown phase."""

    phase: ShutdownPhase
    success: bool
    duration: float
    error: str | None = None
    warning: str | None = None
    health_before: dict[str, Any] | None = None


class ShutdownCoordinator(QObject):
    """Coordinates graceful shutdown of all concurrent components.

    Manages ordered shutdown sequence with health checks, timeouts,
    and progress reporting.

    Signals:
        phase_started: Emitted when a shutdown phase starts
        phase_completed: Emitted when a shutdown phase completes
        shutdown_completed: Emitted when entire shutdown is complete
    """

    # Signals
    phase_started = pyqtSignal(str)  # phase_name
    phase_completed = pyqtSignal(str, bool)  # phase_name, success
    shutdown_completed = pyqtSignal(bool)  # overall_success

    # Default timeouts per phase (seconds)
    # Keep these reasonably short to avoid Windows "Not Responding" dialog,
    # but not so short that shutdown skips meaningful work during diagnostics.
    DEFAULT_TIMEOUTS: ClassVar[dict["ShutdownPhase", float]] = {
        ShutdownPhase.TIMERS: 0.5,
        ShutdownPhase.THREAD_POOL: 2.0,
        ShutdownPhase.THUMBNAILS: 2.0,  # Increased from 1.0s (can take 1.3s+ on busy systems)
        ShutdownPhase.DATABASE: 1.0,
        ShutdownPhase.EXIFTOOL: 0.5,
        ShutdownPhase.FINALIZE: 0.5,
    }
    # Total worst-case: 6.0 seconds

    def __init__(self, parent: Any = None) -> None:
        """Initialize shutdown coordinator.

        Args:
            parent: Optional parent QObject

        """
        super().__init__(parent)

        # Phase timeouts (can be customized)
        self.phase_timeouts = self.DEFAULT_TIMEOUTS.copy()

        # Results tracking
        self._results: list[ShutdownResult] = []
        self._shutdown_in_progress = False
        self._emergency_mode = False

        # Component references (set via register methods)
        self._timer_manager: Any | None = None
        self._thumbnail_manager: Any | None = None
        self._thread_pool_manager: Any | None = None
        self._database_manager: Any | None = None
        self._exiftool_wrapper: Any | None = None

        # Async shutdown state
        self._async_phases: list[tuple[ShutdownPhase, Callable[[], tuple[bool, str | None]]]] = []
        self._async_index: int = 0
        self._async_start_time: float = 0.0
        self._async_overall_success: bool = True
        self._async_progress_callback: Callable[[str, float], None] | None = None

        logger.info("[ShutdownCoordinator] Initialized")

    def register_timer_manager(self, timer_manager: Any) -> None:
        """Register timer manager for shutdown."""
        self._timer_manager = timer_manager
        logger.debug("[ShutdownCoordinator] Timer manager registered")

    def register_thread_pool_manager(self, thread_pool_manager: Any) -> None:
        """Register thread pool manager for shutdown."""
        self._thread_pool_manager = thread_pool_manager
        logger.debug("[ShutdownCoordinator] Thread pool manager registered")

    def register_thumbnail_manager(self, thumbnail_manager: Any) -> None:
        """Register thumbnail manager for shutdown."""
        self._thumbnail_manager = thumbnail_manager
        logger.debug("[ShutdownCoordinator] Thumbnail manager registered")

    def register_database_manager(self, database_manager: Any) -> None:
        """Register database manager for shutdown."""
        self._database_manager = database_manager
        logger.debug("[ShutdownCoordinator] Database manager registered")
        logger.debug("[ShutdownCoordinator] Database manager registered")

    def register_exiftool_wrapper(self, exiftool_wrapper: Any) -> None:
        """Register ExifTool wrapper for shutdown."""
        self._exiftool_wrapper = exiftool_wrapper
        logger.debug("[ShutdownCoordinator] ExifTool wrapper registered")

    def set_phase_timeout(self, phase: ShutdownPhase, timeout: float) -> None:
        """Set custom timeout for a specific phase.

        Args:
            phase: Shutdown phase
            timeout: Timeout in seconds

        """
        self.phase_timeouts[phase] = timeout
        logger.debug("[ShutdownCoordinator] %s timeout set to %ss", phase.value, timeout)

    def execute_shutdown(
        self,
        progress_callback: Callable[[str, float], None] | None = None,
        emergency: bool = False,
    ) -> bool:
        """Execute coordinated shutdown of all components.

        Args:
            progress_callback: Optional callback for progress updates (message, progress)
            emergency: If True, use shorter timeouts and skip health checks

        Returns:
            True if all phases completed successfully

        """
        if self._shutdown_in_progress:
            logger.warning("[ShutdownCoordinator] Shutdown already in progress")
            return False

        self._shutdown_in_progress = True
        self._emergency_mode = emergency
        self._results.clear()

        logger.info(
            "[ShutdownCoordinator] Starting %s shutdown",
            "EMERGENCY" if emergency else "GRACEFUL",
        )

        start_time = time.time()
        overall_success = True

        # Define shutdown phases in order
        phases = [
            (ShutdownPhase.TIMERS, self._shutdown_timers),
            (ShutdownPhase.THREAD_POOL, self._shutdown_thread_pool),
            (ShutdownPhase.DATABASE, self._shutdown_database),
            (ShutdownPhase.EXIFTOOL, self._shutdown_exiftool),
            (ShutdownPhase.FINALIZE, self._shutdown_finalize),
        ]

        total_phases = len(phases)

        for idx, (phase, shutdown_func) in enumerate(phases):
            # Calculate progress
            progress = idx / total_phases
            phase_name = phase.value

            # Emit phase started signal
            self.phase_started.emit(phase_name)

            # Call progress callback if provided
            if progress_callback:
                progress_callback(f"Shutting down {phase_name}...", progress)

            # Execute phase
            result = self._execute_phase(phase, shutdown_func)
            self._results.append(result)

            # Emit phase completed signal
            self.phase_completed.emit(phase_name, result.success)

            # Track overall success
            if not result.success:
                overall_success = False
                logger.error(
                    "[ShutdownCoordinator] Phase %s failed: %s",
                    phase_name,
                    result.error,
                )

            # Log result (use ASCII-safe characters for Windows console compatibility)
            status = "[OK]" if result.success else "[FAIL]"
            logger.info(
                "[ShutdownCoordinator] %s %s (%.2fs)",
                status,
                phase_name,
                result.duration,
            )

        # Final progress update
        if progress_callback:
            progress_callback("Shutdown complete", 1.0)

        # Calculate total duration
        total_duration = time.time() - start_time

        # Log summary
        logger.info(
            "[ShutdownCoordinator] Shutdown %s in %.2fs",
            "succeeded" if overall_success else "completed with errors",
            total_duration,
        )

        # Emit completion signal
        self.shutdown_completed.emit(overall_success)

        self._shutdown_in_progress = False

        return overall_success

    def execute_shutdown_async(
        self,
        progress_callback: Callable[[str, float], None] | None = None,
        emergency: bool = False,
    ) -> bool:
        """Start coordinated shutdown without blocking the Qt event loop.

        This schedules each shutdown phase on subsequent Qt ticks (via QTimer),
        keeping the UI message pump responsive to avoid Windows "Not Responding"
        during close.

        Returns:
            True if shutdown was started, False if already in progress.

        """
        if self._shutdown_in_progress:
            logger.warning("[ShutdownCoordinator] Shutdown already in progress")
            return False

        self._shutdown_in_progress = True
        self._emergency_mode = emergency
        self._results.clear()
        self._async_progress_callback = progress_callback
        self._async_start_time = time.time()
        self._async_overall_success = True

        logger.info(
            "[ShutdownCoordinator] Starting %s shutdown (async)",
            "EMERGENCY" if emergency else "GRACEFUL",
        )

        self._async_phases = [
            (ShutdownPhase.TIMERS, self._shutdown_timers),
            (ShutdownPhase.THREAD_POOL, self._shutdown_thread_pool),
            (ShutdownPhase.THUMBNAILS, self._shutdown_thumbnails),
            (ShutdownPhase.DATABASE, self._shutdown_database),
            (ShutdownPhase.EXIFTOOL, self._shutdown_exiftool),
            (ShutdownPhase.FINALIZE, self._shutdown_finalize),
        ]
        self._async_index = 0

        QTimer.singleShot(0, self._execute_next_phase_async)
        return True

    def _execute_next_phase_async(self) -> None:
        """Execute the next shutdown phase (scheduled via QTimer)."""
        try:
            if self._async_index >= len(self._async_phases):
                total_duration = time.time() - self._async_start_time
                logger.info(
                    "[ShutdownCoordinator] Shutdown %s in %.2fs (async)",
                    "succeeded" if self._async_overall_success else "completed with errors",
                    total_duration,
                )
                self.shutdown_completed.emit(self._async_overall_success)
                self._shutdown_in_progress = False
                return

            total_phases = len(self._async_phases)
            phase, shutdown_func = self._async_phases[self._async_index]
            phase_name = phase.value
            progress = self._async_index / total_phases

            self.phase_started.emit(phase_name)
            if self._async_progress_callback:
                self._async_progress_callback(f"Shutting down {phase_name}...", progress)

            result = self._execute_phase(phase, shutdown_func)
            self._results.append(result)

            self.phase_completed.emit(phase_name, result.success)
            if not result.success:
                self._async_overall_success = False
                logger.error(
                    "[ShutdownCoordinator] Phase %s failed: %s",
                    phase_name,
                    result.error,
                )

            status = "[OK]" if result.success else "[FAIL]"
            logger.info(
                "[ShutdownCoordinator] %s %s (%.2fs)",
                status,
                phase_name,
                result.duration,
            )

            self._async_index += 1
            QTimer.singleShot(0, self._execute_next_phase_async)

        except Exception as e:
            logger.exception("[ShutdownCoordinator] Async shutdown error")
            self._async_overall_success = False
            self.shutdown_completed.emit(False)
            self._shutdown_in_progress = False

    def _execute_phase(
        self, phase: ShutdownPhase, shutdown_func: Callable[[], tuple[bool, str | None]]
    ) -> ShutdownResult:
        """Execute a single shutdown phase with timeout handling.

        Args:
            phase: Shutdown phase
            shutdown_func: Function to execute for this phase

        Returns:
            ShutdownResult with phase outcome

        """
        phase_start = time.time()
        timeout = self.phase_timeouts[phase]

        # In emergency mode, use half the normal timeout
        if self._emergency_mode:
            timeout = timeout / 2

        logger.debug(
            "[ShutdownCoordinator] Starting phase %s (timeout: %ss, emergency: %s)",
            phase.value,
            timeout,
            self._emergency_mode,
        )

        # Get health check before shutdown (if not emergency mode)
        health_before = None
        if not self._emergency_mode:
            health_before = self._get_component_health(phase)
            if health_before and not health_before.get("healthy", True):
                logger.warning(
                    "[ShutdownCoordinator] Component for %s reports unhealthy: %s",
                    phase.value,
                    health_before,
                )

        try:
            # Execute shutdown function with timeout awareness
            success, error = shutdown_func()

            duration = time.time() - phase_start

            # Check if we exceeded timeout (soft warning)
            if duration > timeout:
                warning = f"Phase exceeded timeout ({duration:.2f}s > {timeout}s)"
                logger.warning("[ShutdownCoordinator] %s", warning)
                return ShutdownResult(
                    phase=phase,
                    success=success,
                    duration=duration,
                    error=error,
                    warning=warning,
                    health_before=health_before,
                )

            return ShutdownResult(
                phase=phase,
                success=success,
                duration=duration,
                error=error,
                health_before=health_before,
            )

        except Exception as e:
            duration = time.time() - phase_start
            error_msg = f"Exception during shutdown: {e}"
            logger.exception("[ShutdownCoordinator] %s", error_msg)

            return ShutdownResult(
                phase=phase,
                success=False,
                duration=duration,
                error=error_msg,
                health_before=health_before,
            )

    def _get_component_health(self, phase: ShutdownPhase) -> dict[str, Any] | None:
        """Get health check for component corresponding to phase.

        Args:
            phase: Shutdown phase

        Returns:
            Health check dictionary or None if not available

        """
        try:
            if phase == ShutdownPhase.TIMERS and self._timer_manager:
                if hasattr(self._timer_manager, "health_check"):
                    return self._timer_manager.health_check()

            elif phase == ShutdownPhase.THREAD_POOL and self._thread_pool_manager:
                if hasattr(self._thread_pool_manager, "health_check"):
                    return self._thread_pool_manager.health_check()

            elif (
                phase == ShutdownPhase.EXIFTOOL
                and self._exiftool_wrapper
                and hasattr(self._exiftool_wrapper, "health_check")
            ):
                return self._exiftool_wrapper.health_check()

        except Exception as e:
            logger.warning("[ShutdownCoordinator] Error getting health for %s: %s", phase.value, e)

        return None

    def _shutdown_timers(self) -> tuple[bool, str | None]:
        """Shutdown timer manager."""
        if not self._timer_manager:
            return True, None

        try:
            if hasattr(self._timer_manager, "cleanup_all"):
                cancelled = self._timer_manager.cleanup_all()
                logger.debug("[ShutdownCoordinator] Cleaned up %d timers", cancelled)
            return True, None
        except Exception as e:
            return False, f"Timer shutdown failed: {e}"

    def _shutdown_thread_pool(self) -> tuple[bool, str | None]:
        """Shutdown thread pool manager with defensive cleanup."""
        import contextlib

        if not self._thread_pool_manager:
            return True, None

        try:
            # Disconnect any signals to prevent crashes during cleanup
            with contextlib.suppress(RuntimeError, TypeError, AttributeError):
                if hasattr(self._thread_pool_manager, "disconnect"):
                    self._thread_pool_manager.disconnect()

            # Shutdown thread pool
            if hasattr(self._thread_pool_manager, "shutdown"):
                # Keep this very short to avoid freezing the UI thread during app close.
                # The ThreadPoolManager supports bounded shutdown parameters.
                try:
                    self._thread_pool_manager.shutdown(worker_wait_ms=200, terminate_wait_ms=50)
                except TypeError:
                    # Backward compatibility if signature doesn't accept kwargs
                    self._thread_pool_manager.shutdown()

            return True, None
        except Exception as e:
            logger.exception("Thread pool shutdown failed")
            return False, f"Thread pool shutdown failed: {e}"

    def _shutdown_thumbnails(self) -> tuple[bool, str | None]:
        """Shutdown thumbnail manager (must run before database)."""
        import threading

        if not self._thumbnail_manager:
            # Still do force cleanup even if no manager registered
            try:
                from oncutf.core.thumbnail.providers import VideoThumbnailProvider

                threading.Thread(
                    target=VideoThumbnailProvider.force_cleanup_all_ffmpeg_processes,
                    kwargs={"max_scan_s": 0.15, "graceful_wait_s": 0.05},
                    daemon=True,
                    name="FFmpegForceCleanup",
                ).start()
            except Exception:
                pass
            return True, None

        try:
            if hasattr(self._thumbnail_manager, "shutdown"):
                self._thumbnail_manager.shutdown()

            # Force cleanup all FFmpeg processes (like ExifTool)
            # This is critical to prevent zombie ffmpeg processes
            from oncutf.core.thumbnail.providers import VideoThumbnailProvider

            # Run in background thread to avoid UI freezes
            threading.Thread(
                target=VideoThumbnailProvider.force_cleanup_all_ffmpeg_processes,
                kwargs={"max_scan_s": 0.15, "graceful_wait_s": 0.05},
                daemon=True,
                name="FFmpegForceCleanup",
            ).start()

            return True, None
        except Exception as e:
            logger.exception("Thumbnail manager shutdown failed")
            # Even on error, try force cleanup
            try:
                from oncutf.core.thumbnail.providers import VideoThumbnailProvider

                threading.Thread(
                    target=VideoThumbnailProvider.force_cleanup_all_ffmpeg_processes,
                    kwargs={"max_scan_s": 0.15, "graceful_wait_s": 0.05},
                    daemon=True,
                    name="FFmpegForceCleanup",
                ).start()
            except Exception:
                pass
            return False, f"Thumbnail manager shutdown failed: {e}"

    def _shutdown_database(self) -> tuple[bool, str | None]:
        """Shutdown database manager with proper connection closure."""
        import contextlib

        if not self._database_manager:
            return True, None

        try:
            # Close database connection
            if hasattr(self._database_manager, "close"):
                self._database_manager.close()

            # Additional cleanup for SQLite on Windows
            import platform

            if platform.system() == "Windows":
                # Force commit any pending transactions
                with contextlib.suppress(Exception):
                    if hasattr(self._database_manager, "commit"):
                        self._database_manager.commit()

            return True, None
        except Exception as e:
            logger.exception("Database shutdown failed")
            return False, f"Database shutdown failed: {e}"

    def _shutdown_exiftool(self) -> tuple[bool, str | None]:
        """Shutdown ExifTool wrapper with aggressive cleanup for Windows."""
        import contextlib
        import threading

        if not self._exiftool_wrapper:
            # Still do force cleanup even if no wrapper registered
            try:
                from oncutf.infra.external.exiftool_wrapper import ExifToolWrapper

                threading.Thread(
                    target=ExifToolWrapper.force_cleanup_all_exiftool_processes,
                    kwargs={"max_scan_s": 0.15, "graceful_wait_s": 0.05},
                    daemon=True,
                    name="ExifToolForceCleanup",
                ).start()
            except Exception:
                pass
            return True, None

        try:
            # Stop/close the wrapper first (close is the common API).
            if hasattr(self._exiftool_wrapper, "stop"):
                with contextlib.suppress(Exception):
                    self._exiftool_wrapper.stop()
            if hasattr(self._exiftool_wrapper, "close"):
                # Keep this bounded to avoid UI freezes during app close.
                with contextlib.suppress(Exception):
                    try:
                        self._exiftool_wrapper.close(
                            try_graceful=False,
                            graceful_wait_s=0.0,
                            terminate_wait_s=0.2,
                            kill_wait_s=0.1,
                        )
                    except TypeError:
                        # Backward compatibility if signature doesn't accept kwargs
                        self._exiftool_wrapper.close()

            # Force cleanup all ExifTool processes
            # This is critical on Windows to prevent zombie processes
            from oncutf.infra.external.exiftool_wrapper import ExifToolWrapper

            # IMPORTANT: Do this in background; psutil.process_iter() can occasionally
            # block on Windows and would freeze the UI thread during close.
            threading.Thread(
                target=ExifToolWrapper.force_cleanup_all_exiftool_processes,
                kwargs={"max_scan_s": 0.15, "graceful_wait_s": 0.05},
                daemon=True,
                name="ExifToolForceCleanup",
            ).start()

            return True, None
        except Exception as e:
            logger.exception("ExifTool shutdown failed")
            # Even on error, try force cleanup one more time
            try:
                from oncutf.infra.external.exiftool_wrapper import ExifToolWrapper

                threading.Thread(
                    target=ExifToolWrapper.force_cleanup_all_exiftool_processes,
                    kwargs={"max_scan_s": 0.15, "graceful_wait_s": 0.05},
                    daemon=True,
                    name="ExifToolForceCleanup",
                ).start()
            except Exception:
                pass
            return False, f"ExifTool shutdown failed: {e}"

    def _shutdown_finalize(self) -> tuple[bool, str | None]:
        """Finalize shutdown - cleanup any remaining resources."""
        try:
            # Any final cleanup operations can go here
            logger.debug("[ShutdownCoordinator] Finalization complete")
            return True, None
        except Exception as e:
            return False, f"Finalization failed: {e}"

    def get_results(self) -> list[ShutdownResult]:
        """Get results from last shutdown execution.

        Returns:
            List of ShutdownResult objects

        """
        return self._results.copy()

    def get_summary(self) -> dict[str, Any]:
        """Get summary of last shutdown execution.

        Returns:
            Dictionary with shutdown statistics

        """
        if not self._results:
            return {"executed": False}

        total_duration = sum(r.duration for r in self._results)
        successful_phases = sum(1 for r in self._results if r.success)
        failed_phases = sum(1 for r in self._results if not r.success)

        return {
            "executed": True,
            "total_phases": len(self._results),
            "successful_phases": successful_phases,
            "failed_phases": failed_phases,
            "total_duration": total_duration,
            "emergency_mode": self._emergency_mode,
            "phases": [
                {
                    "phase": r.phase.value,
                    "success": r.success,
                    "duration": r.duration,
                    "error": r.error,
                    "warning": r.warning,
                }
                for r in self._results
            ],
        }


# Global instance
_shutdown_coordinator_instance: ShutdownCoordinator | None = None


def get_shutdown_coordinator() -> ShutdownCoordinator:
    """Get the global shutdown coordinator instance.

    Returns:
        ShutdownCoordinator singleton instance

    """
    global _shutdown_coordinator_instance
    if _shutdown_coordinator_instance is None:
        _shutdown_coordinator_instance = ShutdownCoordinator()
    return _shutdown_coordinator_instance
