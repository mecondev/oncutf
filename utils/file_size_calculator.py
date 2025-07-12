"""
Module: file_size_calculator.py

Author: Michael Economou
Date: 2025-06-10

file_size_calculator.py
Utility functions for calculating file and folder sizes for progress tracking.
Used by progress dialogs to show size information during operations.
"""

import os
from pathlib import Path
from typing import List, Union

from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


def calculate_files_total_size(file_items: List) -> int:
    """
    Calculate total size of a list of file items with optimized caching.

    Args:
        file_items: List of FileItem objects or file paths

    Returns:
        Total size in bytes
    """
    total_size = 0
    files_checked = 0
    files_cached = 0

    for item in file_items:
        try:
            # Handle FileItem objects with cached size first (fastest path)
            if hasattr(item, 'file_size') and item.file_size is not None:
                total_size += item.file_size
                files_cached += 1
                continue

            # Handle full_path attribute
            if hasattr(item, 'full_path'):
                file_path = item.full_path
            else:
                file_path = str(item)

            # Get file size from filesystem (slower path)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                size = os.path.getsize(file_path)
                total_size += size
                files_checked += 1

                # Cache size in FileItem if available and attribute exists
                if hasattr(item, 'file_size'):
                    item.file_size = size

        except (OSError, AttributeError) as e:
            logger.debug(f"[FileSizeCalculator] Error getting size for {item}: {e}")
            continue

    logger.debug(f"[FileSizeCalculator] Total size: {total_size} bytes for {len(file_items)} files "
                f"({files_cached} cached, {files_checked} checked)")
    return total_size


def calculate_processed_size(file_items: List, current_index: int) -> int:
    """
    Calculate size of files processed so far.

    Args:
        file_items: List of FileItem objects or file paths
        current_index: Current processing index (0-based)

    Returns:
        Processed size in bytes
    """
    if current_index <= 0:
        return 0

    processed_size = 0

    for i in range(min(current_index, len(file_items))):
        item = file_items[i]
        try:
            # Handle both FileItem objects and path strings
            if hasattr(item, 'full_path'):
                file_path = item.full_path
            elif hasattr(item, 'file_size') and item.file_size is not None:
                # FileItem already has cached size
                processed_size += item.file_size
                continue
            else:
                file_path = str(item)

            # Get file size
            if os.path.exists(file_path) and os.path.isfile(file_path):
                size = os.path.getsize(file_path)
                processed_size += size

        except (OSError, AttributeError) as e:
            logger.debug(f"[FileSizeCalculator] Error getting size for {item}: {e}")
            continue

    return processed_size


def calculate_folder_size(folder_path: Union[str, Path], recursive: bool = True) -> int:
    """
    Calculate total size of a folder.

    Args:
        folder_path: Path to folder
        recursive: Whether to include subfolders

    Returns:
        Total size in bytes
    """
    total_size = 0
    folder_path = Path(folder_path)

    try:
        if recursive:
            # Recursive calculation
            for item in folder_path.rglob('*'):
                if item.is_file():
                    try:
                        total_size += item.stat().st_size
                    except (OSError, PermissionError):
                        continue
        else:
            # Only direct files
            for item in folder_path.iterdir():
                if item.is_file():
                    try:
                        total_size += item.stat().st_size
                    except (OSError, PermissionError):
                        continue

    except (OSError, PermissionError) as e:
        logger.debug(f"[FileSizeCalculator] Error calculating folder size for {folder_path}: {e}")

    logger.debug(f"[FileSizeCalculator] Folder size calculated: {total_size} bytes for {folder_path}")
    return total_size


def estimate_operation_time(file_count: int, total_size: int, operation_type: str = "metadata") -> float:
    """
    Estimate operation time based on file count and size.

    Args:
        file_count: Number of files
        total_size: Total size in bytes
        operation_type: Type of operation ("metadata", "hash", "rename", etc.)

    Returns:
        Estimated time in seconds
    """
    # Basic estimation rates (files per second and bytes per second)
    rates = {
        "metadata": {"files_per_sec": 10, "bytes_per_sec": 50 * 1024 * 1024},  # 50MB/s
        "metadata_extended": {"files_per_sec": 3, "bytes_per_sec": 20 * 1024 * 1024},  # 20MB/s
        "hash": {"files_per_sec": 5, "bytes_per_sec": 100 * 1024 * 1024},  # 100MB/s
        "rename": {"files_per_sec": 50, "bytes_per_sec": 500 * 1024 * 1024},  # 500MB/s
        "file_loading": {"files_per_sec": 100, "bytes_per_sec": 1000 * 1024 * 1024},  # 1GB/s
    }

    rate = rates.get(operation_type, rates["metadata"])

    # Estimate based on both file count and size
    time_by_files = file_count / rate["files_per_sec"]
    time_by_size = total_size / rate["bytes_per_sec"]

    # Use the larger estimate (bottleneck)
    estimated_time = max(time_by_files, time_by_size)

    # Add minimum time for UI updates
    estimated_time = max(estimated_time, 1.0)

    logger.debug(f"[FileSizeCalculator] Estimated {operation_type} time: {estimated_time:.1f}s for {file_count} files ({total_size} bytes)")
    return estimated_time
