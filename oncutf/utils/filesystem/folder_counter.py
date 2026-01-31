"""Folder content counter with timeout support for drag operations.

This module provides utilities to count folder contents (files/folders) with
configurable timeout and recursion depth. Used for displaying accurate drag
feedback without blocking the UI.

Author: Michael Economou
Date: 2025-12-06
"""

import os
import time
from pathlib import Path
from dataclasses import dataclass

from oncutf.config import ALLOWED_EXTENSIONS
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


@dataclass
class FolderCount:
    """Result of folder counting operation."""

    files: int = 0
    folders: int = 0
    timed_out: bool = False
    elapsed_ms: float = 0.0

    @property
    def total_items(self) -> int:
        """Total number of items (files + folders)."""
        return self.files + self.folders

    def format_display(self) -> str:
        """Format count for display in drag cursor.

        Returns:
            String like "5 items", "3 folders / 127 items", etc.

        """
        # Always show in format "X folder(s) / Y item(s)" for folders
        # For consistency and clarity
        if self.folders == 0 and self.files == 0:
            # Empty folder
            return "0 items"
        elif self.folders == 0:
            # No subfolders, only files
            return f"{self.files} {'item' if self.files == 1 else 'items'}"
        elif self.files == 0:
            # Only subfolders, no files
            return f"{self.folders} {'folder' if self.folders == 1 else 'folders'} / 0 items"
        else:
            # Both folders and files
            return f"{self.folders} {'folder' if self.folders == 1 else 'folders'} / {self.files} {'item' if self.files == 1 else 'items'}"


def count_folder_contents(
    folder_path: str,
    *,
    recursive: bool = False,
    timeout_ms: float = 100.0,
    include_hidden: bool = False,
) -> FolderCount:
    """Count contents of a folder with optional recursion and timeout.

    Args:
        folder_path: Path to folder to count
        recursive: If True, count recursively through subfolders
        timeout_ms: Maximum time to spend counting (in milliseconds)
        include_hidden: If True, include hidden files/folders

    Returns:
        FolderCount with results and timeout status

    """
    start_time = time.perf_counter()
    timeout_seconds = timeout_ms / 1000.0
    result = FolderCount()

    try:
        if not Path(folder_path).is_dir():
            return result

        if recursive:
            # Recursive scan with timeout
            result = _count_recursive(folder_path, timeout_seconds, start_time, include_hidden)
        else:
            # Shallow scan (fast, no timeout needed)
            result = _count_shallow(folder_path, include_hidden)

        elapsed = (time.perf_counter() - start_time) * 1000
        result.elapsed_ms = elapsed

        logger.debug(
            "[FolderCounter] Counted %s: %d folders, %d files (%s, %.1fms, %s)",
            folder_path,
            result.folders,
            result.files,
            "recursive" if recursive else "shallow",
            elapsed,
            "TIMEOUT" if result.timed_out else "completed",
            extra={"dev_only": True},
        )

    except PermissionError:
        logger.debug(
            "[FolderCounter] Permission denied: %s",
            folder_path,
            extra={"dev_only": True},
        )
    except Exception as e:
        logger.warning("[FolderCounter] Error counting %s: %s", folder_path, e)

    return result


def _count_shallow(folder_path: str, include_hidden: bool) -> FolderCount:
    """Count direct child folders (shallow) but ALL files recursively.

    This provides intuitive feedback: shows immediate subfolders but counts
    all files that would be loaded, regardless of depth.
    """
    result = FolderCount()

    try:
        # First pass: count direct children folders only
        for entry in os.scandir(folder_path):
            # Skip hidden files/folders if requested
            if not include_hidden and entry.name.startswith("."):
                continue

            if entry.is_dir(follow_symlinks=False):
                result.folders += 1

        # Second pass: count ALL files recursively using os.walk
        for _root, dirs, files in os.walk(folder_path, followlinks=False):
            # Filter hidden directories if needed
            if not include_hidden:
                dirs[:] = [d for d in dirs if not d.startswith(".")]

            # Count all files with allowed extensions
            for file in files:
                # Skip hidden files if requested
                if not include_hidden and file.startswith("."):
                    continue

                if _has_allowed_extension(file):
                    result.files += 1
                else:
                    # Debug: log filtered files
                    logger.debug(
                        "[FolderCounter] Skipped file (extension filter): %s",
                        file,
                        extra={"dev_only": True},
                    )

    except PermissionError:
        logger.debug(
            "[FolderCounter] Permission denied in shallow scan: %s",
            folder_path,
            extra={"dev_only": True},
        )
    except Exception as e:
        logger.warning("[FolderCounter] Error in shallow scan: %s", e)

    return result


def _count_recursive(
    folder_path: str, timeout_seconds: float, start_time: float, include_hidden: bool
) -> FolderCount:
    """Count recursively with timeout check."""
    result = FolderCount()

    try:
        for root, dirs, files in os.walk(folder_path, followlinks=False):
            # Check timeout
            elapsed = time.perf_counter() - start_time
            if elapsed > timeout_seconds:
                result.timed_out = True
                break

            # Filter hidden directories if needed
            if not include_hidden:
                dirs[:] = [d for d in dirs if not d.startswith(".")]

            # Count folders (but don't count root itself)
            if root != folder_path:
                result.folders += 1

            # Count files with allowed extensions
            for file in files:
                # Skip hidden files if requested
                if not include_hidden and file.startswith("."):
                    continue

                if _has_allowed_extension(file):
                    result.files += 1

    except PermissionError:
        pass
    except Exception as e:
        logger.debug("[FolderCounter] Error in recursive scan: %s", e, extra={"dev_only": True})

    return result


def _has_allowed_extension(filename: str) -> bool:
    """Check if filename has an allowed extension."""
    if not ALLOWED_EXTENSIONS:
        return True  # No filter, allow all

    path_obj = Path(filename.lower())
    ext = path_obj.suffix
    # Remove leading dot from extension for comparison
    if ext.startswith("."):
        ext = ext[1:]
    return ext in ALLOWED_EXTENSIONS


def is_mount_point_or_root(path: str) -> bool:
    r"""Check if path is a mount point or root drive.

    Returns True for:
    - Root directories: /, C:\\, D:\\
    - Mount points: /mnt/..., /media/..., /Volumes/...
    - Top-level Windows drives
    - Direct children of mount directories (e.g., /mnt/disk1)
    """
    path = str(Path(path).resolve())

    # Check if it's a mount point (Linux/macOS)
    if os.path.ismount(path):
        return True

    # Check for root directory
    if path in (os.path.sep, "/"):
        return True

    # Windows: Check for drive roots (C:\\, D:\\, etc.)
    import platform

    if platform.system() == "Windows":
        # Match X:\\ or X:/ pattern
        if len(path) <= 3 and path[1:3] in (":\\", ":/"):
            return True

    # Linux/macOS: Check common mount directories AND their direct children
    mount_prefixes = ("/mnt", "/media", "/Volumes")

    # Check if path itself is a mount directory
    if path in mount_prefixes:
        return True

    # Check if path is a direct child of a mount directory (e.g., /mnt/disk1)
    parent = str(Path(path).parent)
    return parent in mount_prefixes
