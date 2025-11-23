import os

from utils import text_helpers


def test_elide_text_short():
    assert text_helpers.elide_text("short", 10) == "short"


def test_elide_text_exact():
    assert text_helpers.elide_text("exact", 5) == "exact"


def test_elide_text_truncate():
    assert text_helpers.elide_text("abcdefghijklmnopqrstuvwxyz", 5) == "abcd…"


def test_truncate_filename_middle_no_ext():
    name = "a" * 80
    truncated = text_helpers.truncate_filename_middle(name, max_length=20)
    assert "..." in truncated
    assert len(truncated) <= 20


def test_truncate_filename_middle_with_ext():
    filename = "very_long_filename_example_that_needs_truncation.jpg"
    out = text_helpers.truncate_filename_middle(filename, max_length=30)
    assert out.endswith(".jpg")
    assert len(out) <= 30


def test_format_file_size_stable_bytes():
    s = text_helpers.format_file_size_stable(123)
    assert s.strip().endswith("B")
    assert len(s) == 10


def test_format_file_size_stable_kb():
    s = text_helpers.format_file_size_stable(2048)
    assert s.strip().endswith("KB") or s.strip().endswith("MB")
    assert len(s) == 10
"""
Module: test_text_helpers.py

Author: Michael Economou
Date: 2025-05-31

test_text_helpers.py
Tests for text helper functions in utils/text_helpers.py
"""

import warnings

warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*coroutine.*never awaited")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

from utils.text_helpers import elide_text, format_file_size_stable, truncate_filename_middle


class TestElideText:
    """Tests for the elide_text function."""

    def test_returns_empty_when_max_len_non_positive(self):
        """Should return empty string when max_len is zero or negative."""
        assert elide_text("sample", 0) == ""
        assert elide_text("sample", -5) == ""

    def test_returns_ellipsis_when_max_len_is_one(self):
        """Should return just an ellipsis when max_len is one."""
        assert elide_text("sample", 1) == "…"

    def test_truncates_with_ellipsis_when_over_limit(self):
        """Should truncate text and append ellipsis when exceeding limit."""
        assert elide_text("example", 5) == "exam…"

    def test_no_truncation_when_within_limit(self):
        """Should return original text if it fits within max_len."""
        assert elide_text("abc", 5) == "abc"


class TestTruncateFilenameMiddle:
    """Test the truncate_filename_middle function."""

    def test_short_filename_no_truncation(self):
        """Test that short filenames are not truncated."""
        filename = "short.txt"
        result = truncate_filename_middle(filename)
        assert result == filename

    def test_long_filename_with_extension(self):
        """Test truncation of long filename with extension."""
        filename = "very_long_filename_that_needs_truncation.jpg"
        result = truncate_filename_middle(filename, max_length=30)

        # Should preserve extension and truncate in middle
        assert result.endswith(".jpg")
        assert "..." in result
        assert len(result) <= 30
        assert result != filename

    def test_long_filename_without_extension(self):
        """Test truncation of long filename without extension."""
        filename = "very_long_filename_without_extension"
        result = truncate_filename_middle(filename, max_length=25)

        # Should truncate in middle
        assert "..." in result
        assert len(result) <= 25
        assert result != filename

    def test_empty_filename(self):
        """Test empty filename."""
        result = truncate_filename_middle("")
        assert result == ""

    def test_none_filename(self):
        """Test None filename."""
        result = truncate_filename_middle(None)
        assert result == ""

    def test_long_extension(self):
        """Test filename with very long extension."""
        filename = "short.very_long_extension_that_is_too_long"
        result = truncate_filename_middle(filename, max_length=20)

        # Should still truncate even with long extension
        assert "..." in result
        assert len(result) <= 20

    def test_exact_length(self):
        """Test filename that is exactly at the limit."""
        filename = "exactly_sixty_characters_long_filename_with_extension.txt"
        result = truncate_filename_middle(filename, max_length=60)
        assert result == filename  # Should not truncate


class TestFormatFileSizeStable:
    """Test the format_file_size_stable function."""

    def test_bytes_formatting(self):
        """Test formatting of byte values."""
        # Small byte values
        assert format_file_size_stable(0) == "  0 B     "
        assert format_file_size_stable(1) == "  1 B     "
        assert format_file_size_stable(512) == "  512 B   "
        assert format_file_size_stable(1023) == "  1023 B  "

    def test_kilobytes_formatting(self):
        """Test formatting of kilobyte values."""
        # 1 KB = 1024 bytes
        assert format_file_size_stable(1024) == "    1.0 KB"
        assert format_file_size_stable(1536) == "    1.5 KB"  # 1.5 KB
        assert format_file_size_stable(102400) == "  100.0 KB"  # 100 KB

    def test_megabytes_formatting(self):
        """Test formatting of megabyte values."""
        # 1 MB = 1024 * 1024 bytes
        assert format_file_size_stable(1048576) == "    1.0 MB"  # 1 MB
        assert format_file_size_stable(1572864) == "    1.5 MB"  # 1.5 MB
        assert format_file_size_stable(104857600) == "  100.0 MB"  # 100 MB

    def test_gigabytes_formatting(self):
        """Test formatting of gigabyte values."""
        # 1 GB = 1024 MB = 1073741824 bytes
        assert format_file_size_stable(1073741824) == "    1.0 GB"
        assert format_file_size_stable(1610612736) == "    1.5 GB"
        assert format_file_size_stable(10737418240) == "   10.0 GB"

    def test_large_values_no_decimals(self):
        """Test that large values are formatted without decimals where appropriate."""
        # Large values should still show decimals for consistency
        assert format_file_size_stable(1073741824) == "    1.0 GB"  # 1 GB
        assert format_file_size_stable(104857600) == "  100.0 MB"  # 100 MB

    def test_negative_values(self):
        """Test handling of negative values."""
        assert format_file_size_stable(-1) == "     0 B  "
        assert format_file_size_stable(-1000) == "     0 B  "

    def test_fixed_width(self):
        """Test that all formatted strings have the same width."""
        test_sizes = [0, 1024, 1048576, 1073741824]  # 0 B, 1 KB, 1 MB, 1 GB
        results = [format_file_size_stable(size) for size in test_sizes]
        lengths = [len(result) for result in results]

        # All results should have exactly 10 characters
        assert all(length == 10 for length in lengths), f"Lengths: {lengths}, Results: {results}"

    def test_rounding_behavior(self):
        """Test rounding behavior for decimal values."""
        # 1.4 KB should round to 1.4
        assert format_file_size_stable(1434) == "    1.4 KB"  # 1434 bytes ≈ 1.4 KB
        # 1.6 KB should round to 1.6
        assert format_file_size_stable(1638) == "    1.6 KB"  # 1638 bytes ≈ 1.6 KB


class TestIntegration:
    """Integration tests for both functions."""

    def test_filename_and_size_together(self):
        """Test using both functions together for UI display."""
        filename = "very_long_filename_that_needs_truncation_for_display.jpg"
        size_bytes = 1048576  # 1 MB

        truncated_filename = truncate_filename_middle(filename, 40)
        formatted_size = format_file_size_stable(size_bytes)

        # Test that both functions work together
        assert truncated_filename == "very_long_filena...ation_for_display.jpg"
        assert formatted_size == "    1.0 MB"

        # Test that size formatting is stable
        assert len(formatted_size) == 10
