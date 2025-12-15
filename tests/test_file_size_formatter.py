
from utils.file_size_formatter import (
    FileSizeFormatter,
    format_file_size,
    format_file_size_system_compatible,
)


def test_file_size_formatter_basic():
    f = FileSizeFormatter(use_binary=True, use_locale=False, use_legacy_labels=False)
    assert f.format_size(0) == "0 B"
    assert f.format_size(1024) in ("1 KiB", "1 KiB")


def test_file_size_formatter_decimal():
    f = FileSizeFormatter(use_binary=False, use_locale=False)
    assert f.format_size(1500).startswith("1.5 ")


def test_format_file_size_system_compatible():
    out = format_file_size_system_compatible(1024)
    # Should return a string with a unit suffix
    assert isinstance(out, str) and len(out) > 2


def test_get_decimal_separator_locale():
    # Temporarily try to set a known locale if available
    f = FileSizeFormatter(use_binary=False, use_locale=True)
    sep = f.get_decimal_separator()
    assert sep in (".", ",")


def test_format_file_size_uses_default():
    # format_file_size uses a global default formatter
    out = format_file_size(1234)
    assert isinstance(out, str)
#!/usr/bin/env python3
"""
Module: test_file_size_formatter.py

Author: Michael Economou
Date: 2025-05-31

test_file_size_formatter.py
Test cases for the FileSizeFormatter utility.
Tests cross-platform file size formatting with various units and locales.
"""

import warnings

warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*coroutine.*never awaited")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

import sys
import unittest
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))



class TestFileSizeFormatter(unittest.TestCase):
    """Test cases for FileSizeFormatter."""

    def test_binary_units_formatting(self):
        """Test binary (1024-based) units formatting."""
        formatter = FileSizeFormatter(use_binary=True, use_locale=False)

        test_cases = [
            (0, "0 B"),
            (512, "512 B"),
            (1023, "1023 B"),
            (1024, "1 KB"),  # Using legacy labels
            (1536, "1.5 KB"),
            (1048576, "1 MB"),
            (1572864, "1.5 MB"),
            (1073741824, "1 GB"),
        ]

        for size_bytes, expected in test_cases:
            with self.subTest(size=size_bytes):
                result = formatter.format_size(size_bytes)
                self.assertEqual(result, expected)

    def test_decimal_units_formatting(self):
        """Test decimal (1000-based) units formatting."""
        formatter = FileSizeFormatter(use_binary=False, use_locale=False)

        test_cases = [
            (0, "0 B"),
            (512, "512 B"),
            (999, "999 B"),
            (1000, "1 KB"),
            (1500, "1.5 KB"),
            (1000000, "1 MB"),
            (1500000, "1.5 MB"),
            (1000000000, "1 GB"),
        ]

        for size_bytes, expected in test_cases:
            with self.subTest(size=size_bytes):
                result = formatter.format_size(size_bytes)
                self.assertEqual(result, expected)

    def test_system_compatible_formatter(self):
        """Test system-compatible formatter."""
        formatter = FileSizeFormatter.get_system_compatible_formatter()

        # Test basic functionality (actual values will depend on system)
        result = formatter.format_size(1000000)  # 1MB
        self.assertIsInstance(result, str)
        # System locale may use different separators (e.g., KB or KiB)
        self.assertTrue("B" in result, f"Expected 'B' in result, got: {result}")

        # Test that it formats without errors
        test_sizes = [0, 1023, 1024, 1000000, 1048576, 1000000000]
        for size in test_sizes:
            with self.subTest(size=size):
                result = formatter.format_size(size)
                self.assertIsInstance(result, str)
                self.assertGreater(len(result), 0)

    def test_traditional_formatter(self):
        """Test traditional (binary) formatter."""
        formatter = FileSizeFormatter.get_traditional_formatter()

        # Should use 1024 base
        result = formatter.format_size(1024)
        self.assertEqual(result, "1 KB")

        result = formatter.format_size(1048576)
        self.assertEqual(result, "1 MB")

    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        formatter = FileSizeFormatter(use_binary=False, use_locale=False)

        # Negative size
        result = formatter.format_size(-100)
        self.assertEqual(result, "0 B")

        # Zero size
        result = formatter.format_size(0)
        self.assertEqual(result, "0 B")

        # Very large size
        very_large = 1024**6  # 1 EB
        result = formatter.format_size(very_large)
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_whole_number_formatting(self):
        """Test that whole numbers don't show .0 suffix."""
        formatter = FileSizeFormatter(use_binary=False, use_locale=False)

        # Exact multiples should not show decimals
        result = formatter.format_size(1000)
        self.assertEqual(result, "1 KB")  # Not "1.0 KB"

        result = formatter.format_size(2000)
        self.assertEqual(result, "2 KB")  # Not "2.0 KB"

        # Non-exact should show decimals
        result = formatter.format_size(1500)
        self.assertEqual(result, "1.5 KB")

    def test_global_functions(self):
        """Test global convenience functions."""

        # Test format_file_size
        result = format_file_size(1000)
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

        # Test format_file_size_system_compatible
        result = format_file_size_system_compatible(1000)
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_different_unit_labels(self):
        """Test different unit label formats."""

        # Binary with IEC labels (KiB, MiB)
        formatter_iec = FileSizeFormatter(use_binary=True, use_legacy_labels=False)
        result = formatter_iec.format_size(1024)
        self.assertEqual(result, "1 KiB")

        # Binary with legacy labels (KB, MB)
        formatter_legacy = FileSizeFormatter(use_binary=True, use_legacy_labels=True)
        result = formatter_legacy.format_size(1024)
        self.assertEqual(result, "1 KB")

        # Decimal always uses SI labels (KB, MB)
        formatter_decimal = FileSizeFormatter(use_binary=False)
        result = formatter_decimal.format_size(1000)
        self.assertEqual(result, "1 KB")


class TestIntegrationWithFileItem(unittest.TestCase):
    """Test integration with FileItem class."""

    def test_file_item_uses_new_formatter(self):
        """Test that FileItem uses the new formatter."""
        from oncutf.models.file_item import FileItem

        # Create a test file item
        test_file = project_root / "config.py"
        if test_file.exists():
            file_item = FileItem.from_path(str(test_file))

            # Get formatted size
            readable_size = file_item.get_human_readable_size()

            # Should be a non-empty string
            self.assertIsInstance(readable_size, str)
            self.assertGreater(len(readable_size), 0)

            # Should contain a unit
            units = ["B", "KB", "MB", "GB", "TB", "KiB", "MiB", "GiB", "TiB"]
            self.assertTrue(any(unit in readable_size for unit in units))


def run_comparison_test():
    """Run a comparison test to show the differences."""

    test_sizes = [512, 1000, 1024, 1500, 1536, 1000000, 1048576, 1000000000, 1073741824]

    for size in test_sizes:
        binary_fmt = FileSizeFormatter(use_binary=True, use_locale=False)
        decimal_fmt = FileSizeFormatter(use_binary=False, use_locale=False)
        system_fmt = FileSizeFormatter.get_system_compatible_formatter()

        binary_fmt.format_size(size)
        decimal_fmt.format_size(size)
        system_fmt.format_size(size)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--comparison":
        run_comparison_test()
    else:
        unittest.main()
