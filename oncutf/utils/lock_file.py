"""Module: lock_file.py.

Author: Michael Economou
Date: 2026-02-01

Single instance lock file management for oncutf application.

Prevents multiple instances from running simultaneously and corrupting shared data.
Uses PID-based lock file with stale lock detection.

Usage:
    from oncutf.utils.lock_file import acquire_lock, release_lock

    if not acquire_lock():
        print("Another instance is already running")
        sys.exit(1)

    # ... run application ...

    release_lock()
"""

import os
import platform
from pathlib import Path

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)

_lock_file_path: Path | None = None
_lock_acquired: bool = False


def _get_lock_file_path() -> Path:
    """Get the lock file path in user data directory.

    Returns:
        Path to .oncutf.lock file

    """
    from oncutf.utils.paths import AppPaths

    return AppPaths.get_user_data_dir() / ".oncutf.lock"


def _is_process_running(pid: int) -> bool:
    """Check if a process with given PID is running.

    Args:
        pid: Process ID to check

    Returns:
        True if process is running, False otherwise

    """
    if platform.system() == "Windows":
        import ctypes
        from ctypes import wintypes

        # Windows: Use kernel32.OpenProcess
        PROCESS_QUERY_INFORMATION = 0x0400
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION, 0, pid)
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return False

    # Linux/macOS: Use os.kill with signal 0
    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError):
        return False
    else:
        return True


def acquire_lock() -> bool:
    """Acquire application lock file.

    Creates a lock file with current PID. If lock file exists, checks if the
    process is still running. Removes stale locks automatically.

    Returns:
        True if lock acquired successfully, False if another instance is running

    """
    global _lock_file_path, _lock_acquired

    _lock_file_path = _get_lock_file_path()
    current_pid = os.getpid()

    # Check if lock file exists
    if _lock_file_path.exists():
        try:
            # Read PID from existing lock file
            lock_content = _lock_file_path.read_text(encoding="utf-8").strip()
            existing_pid = int(lock_content.split()[0])  # First token is PID

            # Check if process is still running
            if _is_process_running(existing_pid):
                logger.warning("[LockFile] Another instance is running (PID: %d)", existing_pid)
                return False

            # Stale lock - remove it
            logger.info("[LockFile] Removing stale lock file (PID: %d)", existing_pid)
            _lock_file_path.unlink()
        except (ValueError, FileNotFoundError, PermissionError) as e:
            logger.warning("[LockFile] Error reading existing lock file: %s", e)
            # Try to remove corrupted lock file
            import contextlib

            with contextlib.suppress(Exception):
                _lock_file_path.unlink()

    # Create lock file with current PID
    try:
        import socket
        from datetime import datetime

        hostname = socket.gethostname()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        lock_content = f"{current_pid} {hostname} {timestamp}\n"
        _lock_file_path.write_text(lock_content, encoding="utf-8")

        _lock_acquired = True
        logger.info("[LockFile] Lock acquired (PID: %d)", current_pid)
    except Exception:
        logger.exception("[LockFile] Failed to create lock file")
        return False
    else:
        return True


def release_lock() -> None:
    """Release application lock file.

    Removes the lock file if it was acquired by this process.
    """
    global _lock_file_path, _lock_acquired

    if not _lock_acquired or not _lock_file_path:
        return

    try:
        if _lock_file_path.exists():
            # Verify it's our lock file by checking PID
            lock_content = _lock_file_path.read_text(encoding="utf-8").strip()
            lock_pid = int(lock_content.split()[0])

            if lock_pid == os.getpid():
                _lock_file_path.unlink()
                logger.info("[LockFile] Lock released")
            else:
                logger.warning(
                    "[LockFile] Lock file PID mismatch (expected: %d, found: %d)",
                    os.getpid(),
                    lock_pid,
                )
    except Exception as e:
        logger.warning("[LockFile] Error releasing lock file: %s", e)
    finally:
        _lock_acquired = False
        _lock_file_path = None


def is_locked() -> bool:
    """Check if application lock is currently held.

    Returns:
        True if lock is held by this process, False otherwise

    """
    return _lock_acquired
