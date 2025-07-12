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
from typing import Optional


def get_project_root() -> Path:
    """
    Get the project root directory based on the location of main.py.

    This ensures that resource paths work correctly regardless of the
    current working directory when the application is launched.

    Returns:
        Path: The project root directory as a Path object
    """
    # Get the directory where this file is located (utils/)
    current_file_dir = Path(__file__).parent
    # Go up one level to get project root
    project_root = current_file_dir.parent
    return project_root.resolve()


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
    Get the full path to a resource file based on relative path from project root.

    Args:
        relative_path: Relative path from project root (e.g., 'resources/icons/info.png')

    Returns:
        Path: The full path to the resource

    Example:
        >>> get_resource_path('resources/icons/info.png')
        Path('/full/path/to/project/resources/icons/info.png')
    """
    return get_project_root() / relative_path


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
    normalized = path.replace('\\', '/')

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
    norm1 = path1.replace('\\', '/').replace('//', '/')
    norm2 = path2.replace('\\', '/').replace('//', '/')

    # Remove trailing slashes for consistent comparison (except for root)
    if len(norm1) > 1 and norm1.endswith('/'):
        norm1 = norm1.rstrip('/')
    if len(norm2) > 1 and norm2.endswith('/'):
        norm2 = norm2.rstrip('/')

    # Case-insensitive comparison for Windows-style paths
    if ':' in norm1 or ':' in norm2:  # Likely Windows paths
        return norm1.lower() == norm2.lower()
    else:
        return norm1 == norm2


def find_file_by_path(files: list, target_path: str, path_attr: str = 'full_path') -> Optional[object]:
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

    parent = widget.parent() if hasattr(widget, 'parent') else None
    while parent:
        if hasattr(parent, attribute_name):
            return parent
        parent = parent.parent() if hasattr(parent, 'parent') else None

    return None
