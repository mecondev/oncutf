#!/usr/bin/env python3
"""Module: test_human_readable.py

Author: Michael Economou
Date: 2025-05-31

test_human_readable.py
Test script to compare human-readable file size formatting
between our application and system commands like ls -lh.
Note: Linux-specific tests are skipped on Windows.
"""

import platform
import subprocess
import sys
from pathlib import Path

import pytest

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from oncutf.models.file_item import FileItem  # noqa: E402

# Check if we're on Windows
IS_WINDOWS = platform.system() == "Windows"


def get_system_human_sizes(filepath):
    """Get human-readable file sizes using system commands (Linux only)."""
    results = {}

    try:
        # Using ls -lh (human readable)
        ls_output = subprocess.check_output(["ls", "-lh", filepath], text=True)
        ls_size = ls_output.split()[4]
        results["ls_h"] = ls_size
    except (subprocess.CalledProcessError, IndexError, FileNotFoundError):
        results["ls_h"] = "Error"

    try:
        # Using du -h (human readable disk usage)
        du_output = subprocess.check_output(["du", "-h", filepath], text=True)
        du_size = du_output.split()[0]
        results["du_h"] = du_size
    except (subprocess.CalledProcessError, IndexError, FileNotFoundError):
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


@pytest.mark.skipif(IS_WINDOWS, reason="Linux-specific test using ls/du commands")
def test_actual_files():
    """Test with actual files comparing our format vs system (Linux only)."""
    # Test with some larger files if available
    test_paths = [
        "oncutf/config.py",
        "main.py",
        "oncutf/ui/main_window.py",
        "requirements.txt",
    ]

    for filepath in test_paths:
        full_path = project_root / filepath
        if full_path.exists():
            # Our application's method
            file_item = FileItem.from_path(str(full_path))
            file_item.get_human_readable_size()

            # System formats
            get_system_human_sizes(str(full_path))


def test_actual_files_cross_platform():
    """Test with actual files using cross-platform methods."""
    # Test with some files
    test_paths = ["oncutf/config.py", "main.py", "requirements.txt"]

    for filepath in test_paths:
        full_path = project_root / filepath
        if full_path.exists():
            # Our application's method
            file_item = FileItem.from_path(str(full_path))
            our_size = file_item.get_human_readable_size()

            # Verify it returns a valid string
            assert our_size is not None
            assert isinstance(our_size, str)
            # Should contain a unit
            assert any(unit in our_size for unit in ["B", "KB", "MB", "GB", "TB"])


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
