#!/usr/bin/env python3
"""
Module: test_human_readable.py

Author: Michael Economou
Date: 2025-05-31

test_human_readable.py
Test script to compare human-readable file size formatting
between our application and system commands like ls -lh.
"""

import warnings

warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*coroutine.*never awaited")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

import os
import subprocess
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from oncutf.models.file_item import FileItem


def get_system_human_sizes(filepath):
    """Get human-readable file sizes using system commands."""
    results = {}

    try:
        # Using ls -lh (human readable)
        ls_output = subprocess.check_output(["ls", "-lh", filepath], text=True)
        ls_size = ls_output.split()[4]
        results["ls_h"] = ls_size
    except (subprocess.CalledProcessError, IndexError):
        results["ls_h"] = "Error"

    try:
        # Using du -h (human readable disk usage)
        du_output = subprocess.check_output(["du", "-h", filepath], text=True)
        du_size = du_output.split()[0]
        results["du_h"] = du_size
    except (subprocess.CalledProcessError, IndexError):
        results["du_h"] = "Error"

    return results


def test_different_size_ranges():
    """Test our size formatting with different byte ranges."""

    test_sizes = [
        512,  # 512 B
        1023,  # 1023 B
        1024,  # 1.0 KB
        1536,  # 1.5 KB
        1048576,  # 1.0 MB
        1572864,  # 1.5 MB
        1073741824,  # 1.0 GB
        1610612736,  # 1.5 GB
    ]

    for size in test_sizes:
        format_size_our_way(size)


def format_size_our_way(size):
    """Our application's size formatting logic."""
    units = ["B", "KB", "MB", "GB", "TB"]
    index = 0
    while size >= 1024 and index < len(units) - 1:
        size /= 1024.0
        index += 1
    return f"{size:.1f} {units[index]}"


def test_actual_files():
    """Test with actual files comparing our format vs system."""

    # Test with some larger files if available
    test_paths = ["config.py", "main.py", "main_window.py", "requirements.txt"]  # Larger file

    for filepath in test_paths:
        if os.path.exists(filepath):
            # Our application's method
            file_item = FileItem.from_path(filepath)
            file_item.get_human_readable_size()

            # System formats
            get_system_human_sizes(filepath)


def test_edge_cases():
    """Test edge cases that might cause discrepancies."""

    # Test 1000 vs 1024 boundaries
    sizes_1000 = [999, 1000, 1001]
    sizes_1024 = [1023, 1024, 1025]

    for size in sizes_1000 + sizes_1024:
        format_size_our_way(size)

        # Format using 1000 as base (like some systems do)
        format_size_decimal(size)


def format_size_decimal(size):
    """Size formatting using 1000 as base (decimal) instead of 1024 (binary)."""
    units = ["B", "KB", "MB", "GB", "TB"]
    index = 0
    while size >= 1000 and index < len(units) - 1:
        size /= 1000.0
        index += 1
    return f"{size:.1f} {units[index]}"


if __name__ == "__main__":
    test_different_size_ranges()
    test_actual_files()
    test_edge_cases()
