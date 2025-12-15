#!/usr/bin/env python3
"""
Module: test_filesize.py

Author: Michael Economou
Date: 2025-05-31

test_filesize.py
Test script to compare file size calculations between our application
and system commands (ls, stat, du) on Linux.
"""

import warnings

warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*coroutine.*never awaited")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

import subprocess
import sys
import unittest
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from oncutf.models.file_item import FileItem


class TestFileSizeComparison(unittest.TestCase):
    """Test file size calculations against system commands."""

    def setUp(self):
        """Set up test files."""
        self.test_files = ["oncutf.config.py", "main.py", "requirements.txt"]

    def get_system_file_sizes(self, filepath):
        """Get file sizes using various system commands."""
        results = {}

        try:
            # Using ls -l (apparent size)
            ls_output = subprocess.check_output(["ls", "-l", filepath], text=True)
            ls_size = int(ls_output.split()[4])
            results["ls"] = ls_size
        except (subprocess.CalledProcessError, ValueError, IndexError):
            results["ls"] = "Error"

        try:
            # Using stat (apparent size)
            stat_output = subprocess.check_output(["stat", "-c", "%s", filepath], text=True)
            stat_size = int(stat_output.strip())
            results["stat"] = stat_size
        except (subprocess.CalledProcessError, ValueError):
            results["stat"] = "Error"

        try:
            # Using du -b (disk usage in bytes)
            du_output = subprocess.check_output(["du", "-b", filepath], text=True)
            du_size = int(du_output.split()[0])
            results["du"] = du_size
        except (subprocess.CalledProcessError, ValueError, IndexError):
            results["du"] = "Error"

        try:
            # Using wc -c for text files (actual content size)
            wc_output = subprocess.check_output(["wc", "-c", filepath], text=True)
            wc_size = int(wc_output.split()[0])
            results["wc"] = wc_size
        except (subprocess.CalledProcessError, ValueError, IndexError):
            results["wc"] = "Error"

        return results

    def test_file_size_accuracy(self):
        """Test that our file size calculation matches system stat command."""
        for test_file in self.test_files:
            file_path = project_root / test_file
            if file_path.exists():
                with self.subTest(file=test_file):
                    # Our application's method
                    file_item = FileItem.from_path(str(file_path))
                    app_size = file_item.size

                    # System stat command (most accurate)
                    sys_sizes = self.get_system_file_sizes(str(file_path))

                    if isinstance(sys_sizes.get("stat"), int):
                        self.assertEqual(
                            app_size,
                            sys_sizes["stat"],
                            f"Size mismatch for {test_file}: app={app_size}, stat={sys_sizes['stat']}",
                        )

    def test_file_size_comparison(self):
        """Print detailed comparison for manual verification."""

        for test_file in self.test_files:
            file_path = project_root / test_file
            if file_path.exists():
                # Our application's method
                file_item = FileItem.from_path(str(file_path))
                app_size = file_item.size
                file_item.get_human_readable_size()

                # System commands
                sys_sizes = self.get_system_file_sizes(str(file_path))

                # Check for discrepancies
                if isinstance(sys_sizes.get("stat"), int) and app_size != sys_sizes["stat"]:
                    pass


def run_manual_test():
    """Run the test as a standalone script for manual verification."""

    test_files = ["oncutf.config.py", "main.py", "requirements.txt"]

    for test_file in test_files:
        file_path = project_root / test_file
        if file_path.exists():
            # Our application's method
            file_item = FileItem.from_path(str(file_path))
            app_size = file_item.size
            file_item.get_human_readable_size()

            # System commands
            tester = TestFileSizeComparison()
            sys_sizes = tester.get_system_file_sizes(str(file_path))

            # Check for discrepancies
            if isinstance(sys_sizes.get("stat"), int) and app_size != sys_sizes["stat"]:
                pass


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--manual":
        run_manual_test()
    else:
        unittest.main()
