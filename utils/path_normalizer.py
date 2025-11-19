"""
path_normalizer.py

Central path normalization function for the entire application.
This module provides a single, consistent way to normalize file paths
across all operating systems and modules.
"""

import os
from pathlib import Path

from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


def normalize_path(file_path: str | Path) -> str:
    """
    Return normalized absolute path as string (cross-platform safe).

    This is the central path normalization function for the entire application.
    It resolves symlinks, relative paths, and normalizes separators for consistent
    cache keys across all operating systems.

    Args:
        file_path (str | Path): The file path to normalize

    Returns:
        str: Normalized absolute path as string

    Example:
        >>> normalize_path("C:/folder\\subfolder/file.txt")  # Windows
        "C:\\folder\\subfolder\\file.txt"
        >>> normalize_path("/home/user/folder/file.txt")     # Linux/Mac
        "/home/user/folder/file.txt"
    """
    if not file_path:
        return ""

    # Convert to Path object for cross-platform handling
    p = Path(file_path)

    # Resolve to absolute path and normalize
    try:
        normalized = str(p.resolve())
    except (OSError, RuntimeError) as e:
        # Fallback if resolve() fails
        logger.warning(f"[WARNING] Path resolve failed for '{file_path}': {e}, using fallback")
        normalized = os.path.normpath(str(file_path))

    # Ensure forward slashes for consistency in caching
    normalized = normalized.replace("\\", "/")

    return normalized
