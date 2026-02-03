"""Module: process_cleanup.py.

Author: Michael Economou
Date: 2026-02-03

Utility functions for cleaning up orphaned processes during shutdown.
"""

from __future__ import annotations

import contextlib
import logging
import time

logger = logging.getLogger(__name__)


def force_cleanup_ffmpeg_processes(
    *,
    max_scan_s: float = 0.5,
    graceful_wait_s: float = 0.5,
) -> None:
    """Force cleanup all FFmpeg processes system-wide.

    Similar to ExifToolWrapper.force_cleanup_all_exiftool_processes().
    This runs during app shutdown to prevent orphan ffmpeg processes.

    Args:
        max_scan_s: Maximum time to spend scanning processes
        graceful_wait_s: Maximum time to wait for terminate() before kill()

    """
    try:
        import psutil

        ffmpeg_processes = []
        scan_start = time.perf_counter()
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                if (time.perf_counter() - scan_start) > max_scan_s:
                    logger.debug(
                        "[ProcessCleanup] FFmpeg scan time limit reached (%.2fs)",
                        max_scan_s,
                    )
                    break
                if proc.info["name"] and "ffmpeg" in proc.info["name"].lower():
                    ffmpeg_processes.append(proc)
                elif proc.info["cmdline"]:
                    cmdline = " ".join(proc.info["cmdline"]).lower()
                    if "ffmpeg" in cmdline:
                        ffmpeg_processes.append(proc)
            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess,
            ):
                pass

        if not ffmpeg_processes:
            logger.debug("[ProcessCleanup] No orphaned FFmpeg processes found")
            return

        logger.warning(
            "[ProcessCleanup] Found %d orphaned FFmpeg processes",
            len(ffmpeg_processes),
        )

        # Try to terminate gracefully first
        for proc in ffmpeg_processes:
            with contextlib.suppress(psutil.NoSuchProcess):
                proc.terminate()

        # Wait briefly for graceful termination (bounded)
        wait_deadline = time.perf_counter() + max(0.0, graceful_wait_s)
        while time.perf_counter() < wait_deadline:
            remaining_count = 0
            for proc in ffmpeg_processes:
                try:
                    if proc.is_running():
                        remaining_count += 1
                except psutil.NoSuchProcess:
                    pass
            if remaining_count == 0:
                break
            time.sleep(0.05)

        # Force kill any remaining processes
        for proc in ffmpeg_processes:
            with contextlib.suppress(psutil.NoSuchProcess):
                if proc.is_running():
                    logger.warning(
                        "[ProcessCleanup] Force-killing FFmpeg process PID %d",
                        proc.pid,
                    )
                    proc.kill()

        logger.info("[ProcessCleanup] FFmpeg process cleanup complete")

    except ImportError:
        logger.debug("[ProcessCleanup] psutil not available - skipping FFmpeg cleanup")
    except Exception:
        logger.exception("[ProcessCleanup] Error during FFmpeg cleanup")
