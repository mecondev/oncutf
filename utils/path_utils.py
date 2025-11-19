"""
Module: path_utils.py

Author: Michael Economou
Date: 2025-06-10

path_utils.py
Utility functions for robust path operations across different operating systems.
Handles path normalization to resolve issues with mixed path separators (especially on Windows).
Also provides centralized project path management to ensure resources are loaded correctly
regardless of current working directory.
"""

import os
from pathlib import Path

from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


def get_project_root() -> Path:
    """
    Get the project root directory (where main.py is located).

    This function finds the project root regardless of current working directory
    by looking for main.py in the path hierarchy.

    Returns:
        Path: Absolute path to project root directory
    """
    # Start from the directory containing this utils module
    current_path = Path(__file__).parent.absolute()

    # Go up one level to project root (utils is inside project root)
    project_root = current_path.parent

    # Verify this is actually the project root by checking for main.py
    main_py_path = project_root / "main.py"
    if not main_py_path.exists():
        # Fallback: search up the directory tree for main.py
        search_path = current_path
        max_levels = 10  # Prevent infinite loops

        for _ in range(max_levels):
            if (search_path / "main.py").exists():
                project_root = search_path
                break
            parent = search_path.parent
            if parent == search_path:  # Reached filesystem root
                break
            search_path = parent
        else:
            # If we still haven't found main.py, use current directory as fallback
            logger.warning("Could not locate main.py, using current directory as project root")
            project_root = Path.cwd()

    logger.debug(f"Project root determined as: {project_root}", extra={"dev_only": True})
    return project_root


def get_resources_dir() -> Path:
    """
    Get the resources directory path.

    Returns:
        Path: The resources directory path
    """
    return get_project_root() / "resources"


def get_assets_dir() -> Path:
    """
    Get the assets directory path.

    Returns:
        Path: The assets directory path
    """
    return get_project_root() / "assets"


def get_style_dir() -> Path:
    """
    Get the style directory path.

    Returns:
        Path: The style directory path
    """
    return get_project_root() / "style"


def get_fonts_dir() -> Path:
    """
    Get the fonts directory path.

    Returns:
        Path: The fonts directory path (resources/fonts/inter)
    """
    return get_resources_dir() / "fonts" / "inter"


def get_icons_dir() -> Path:
    """
    Get the icons directory path.

    Returns:
        Path: The icons directory path (resources/icons)
    """
    return get_resources_dir() / "icons"


def get_images_dir() -> Path:
    """
    Get the images directory path.

    Returns:
        Path: The images directory path (resources/images)
    """
    return get_resources_dir() / "images"


def get_theme_dir(theme_name: str) -> Path:
    """
    Get the theme directory path for a specific theme.

    Args:
        theme_name: The theme name (e.g., 'dark', 'light')

    Returns:
        Path: The theme directory path (style/{theme_name}_theme)
    """
    return get_style_dir() / f"{theme_name}_theme"


def get_resource_path(relative_path: str) -> Path:
    """
    Get the absolute path to a resource file, handling both development and packaged scenarios.

    This function ensures resources are found regardless of:
    - Current working directory
    - Whether running from source or packaged executable
    - Operating system differences

    Args:
        relative_path: Path relative to project root (e.g., "resources/icons/chevron-down.svg")

    Returns:
        Path: Absolute path to the resource
    """
    # Get project root - always use the directory containing main.py
    project_root = get_project_root()

    # Convert relative path to Path object and resolve against project root
    resource_path = project_root / relative_path

    # Resolve to absolute path to handle any symlinks or relative components
    absolute_path = resource_path.resolve()

    # Log for debugging path issues
    logger.debug(
        f"Resource path resolution: '{relative_path}' -> '{absolute_path}'",
        extra={"dev_only": True},
    )

    # Check if file exists and log warning if not found
    if not absolute_path.exists():
        logger.warning(f"Resource not found: {absolute_path}")
        # Try fallback to current working directory (for backward compatibility)
        fallback_path = Path.cwd() / relative_path
        if fallback_path.exists():
            logger.debug(f"Using fallback path: {fallback_path}", extra={"dev_only": True})
            return fallback_path

    return absolute_path


def resource_exists(relative_path: str) -> bool:
    """
    Check if a resource file exists.

    Args:
        relative_path: Relative path from project root

    Returns:
        bool: True if the resource exists, False otherwise
    """
    return get_resource_path(relative_path).exists()


def normalize_path(path: str) -> str:
    """
    Normalize a file path to use consistent separators for the current OS.

    This resolves issues with mixed path separators (e.g., forward slashes mixed
    with backslashes on Windows) that can occur when paths come from different sources.

    Args:
        path (str): The file path to normalize

    Returns:
        str: Normalized path with consistent separators

    Example:
        >>> normalize_path("C:/folder\\subfolder/file.txt")  # Windows
        "C:\\folder\\subfolder\\file.txt"
        >>> normalize_path("/home/user\\folder/file.txt")   # Linux/Mac
        "/home/user/folder/file.txt"
    """
    if not path:
        return path

    # First normalize separators to forward slashes for cross-platform compatibility
    normalized = path.replace("\\", "/")

    # Then use os.path.normpath for final normalization
    return os.path.normpath(normalized)


def paths_equal(path1: str, path2: str) -> bool:
    """
    Compare two file paths for equality after normalizing both.

    This ensures that paths with different separator styles are compared correctly
    across different operating systems. Works correctly even when comparing Windows
    paths on Linux systems.

    Args:
        path1 (str): First path to compare
        path2 (str): Second path to compare

    Returns:
        bool: True if the normalized paths are equal, False otherwise

    Example:
        >>> paths_equal("C:/folder\\file.txt", "C:\\folder/file.txt")  # Windows
        True
        >>> paths_equal("/home/user/file.txt", "/home/user\\file.txt")  # Linux
        True
    """
    if not path1 or not path2:
        return path1 == path2

    # Normalize both paths to use forward slashes for comparison
    norm1 = path1.replace("\\", "/").replace("//", "/")
    norm2 = path2.replace("\\", "/").replace("//", "/")

    # Remove trailing slashes for consistent comparison (except for root)
    if len(norm1) > 1 and norm1.endswith("/"):
        norm1 = norm1.rstrip("/")
    if len(norm2) > 1 and norm2.endswith("/"):
        norm2 = norm2.rstrip("/")

    # Case-insensitive comparison for Windows-style paths
    if ":" in norm1 or ":" in norm2:  # Likely Windows paths
        return norm1.lower() == norm2.lower()
    else:
        return norm1 == norm2


def find_file_by_path(files: list, target_path: str, path_attr: str = "full_path") -> object | None:
    """
    Find a file object in a list by comparing paths with normalization.

    Args:
        files (list): List of file objects to search through
        target_path (str): The path to search for
        path_attr (str): The attribute name containing the path (default: 'full_path')

    Returns:
        Optional[object]: The matching file object or None if not found

    Example:
        >>> files = [FileItem(full_path="C:\\folder\\file1.txt"), ...]
        >>> find_file_by_path(files, "C:/folder\\file1.txt")
        <FileItem object>
    """
    if not files or not target_path:
        return None

    for file_obj in files:
        if hasattr(file_obj, path_attr):
            file_path = getattr(file_obj, path_attr)
            if paths_equal(file_path, target_path):
                return file_obj

    return None


def find_parent_with_attribute(widget, attribute_name: str):
    """
    Unified function to find parent widget with specific attribute.

    Args:
        widget: Starting widget
        attribute_name: Name of attribute to search for

    Returns:
        Parent widget with the attribute, or None if not found
    """
    if not widget:
        return None

    parent = widget.parent() if hasattr(widget, "parent") else None
    while parent:
        if hasattr(parent, attribute_name):
            return parent
        parent = parent.parent() if hasattr(parent, "parent") else None

    return None
