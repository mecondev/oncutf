"""
path_utils.py

Author: Michael Economou
Date: 2025-06-20

Utility functions for robust path operations across different operating systems.
Handles path normalization to resolve issues with mixed path separators (especially on Windows).
"""

import os
from typing import Optional


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
    return os.path.normpath(path)


def paths_equal(path1: str, path2: str) -> bool:
    """
    Compare two file paths for equality after normalizing both.

    This ensures that paths with different separator styles are compared correctly.
    For example, on Windows: "C:/folder\\file.txt" == "C:\\folder/file.txt"

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

    return normalize_path(path1) == normalize_path(path2)


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

    normalized_target = normalize_path(target_path)

    for file_obj in files:
        if hasattr(file_obj, path_attr):
            file_path = getattr(file_obj, path_attr)
            if paths_equal(file_path, target_path):
                return file_obj

    return None
