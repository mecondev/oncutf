"""
test_progress_widget_formatting.py

Tests for ProgressWidget stable formatting improvements.
Ensures that size display is stable (no constant decimal flickering)
and time is displayed in HH:MM:SS format.
"""

import pytest
from widgets.progress_widget import ProgressWidget


class TestProgressWidgetFormatting:
    """Test ProgressWidget formatting improvements for better UX."""

    def setup_method(self):
        """Set up test fixtures."""
        self.widget = ProgressWidget(show_size_info=True, show_time_info=True)

    def test_stable_size_formatting_bytes(self):
        """Test stable size formatting for byte values."""
        # Bytes should show exact values
        assert self.widget._format_size_stable(0) == "0 B"
        assert self.widget._format_size_stable(512) == "512 B"
        assert self.widget._format_size_stable(1023) == "1023 B"

    def test_stable_size_formatting_small_values(self):
        """Test stable size formatting for small values (< 10 units)."""
        # Small values should show one decimal if significant
        assert self.widget._format_size_stable(1536) == "1.5 KB"  # 1.5 KB
        assert self.widget._format_size_stable(2048) == "2 KB"    # Exact 2 KB
        assert self.widget._format_size_stable(9830) == "9.6 KB"  # 9.6 KB

    def test_stable_size_formatting_medium_values(self):
        """Test stable size formatting for medium values (10-99 units)."""
        # Medium values should show decimal only if significant
        assert self.widget._format_size_stable(15360) == "15 KB"     # Exact 15 KB
        assert self.widget._format_size_stable(15872) == "15.5 KB"   # 15.5 KB
        assert self.widget._format_size_stable(99328) == "97 KB"     # ~97 KB (rounded)

    def test_stable_size_formatting_large_values(self):
        """Test stable size formatting for large values (>= 100 units)."""
        # Large values should never show decimals for stability
        assert self.widget._format_size_stable(157286400) == "150 MB"   # ~150 MB
        assert self.widget._format_size_stable(1610612736) == "2 GB"    # ~1.5 GB -> rounded to 2 GB
        assert self.widget._format_size_stable(1073741824) == "1 GB"    # Exact 1 GB

    def test_stable_size_formatting_prevents_flickering(self):
        """Test that stable formatting prevents decimal flickering."""
        # Values that are close should format similarly to prevent flickering
        size1 = 157286400  # ~150 MB
        size2 = 157286500  # ~150 MB + 100 bytes

        format1 = self.widget._format_size_stable(size1)
        format2 = self.widget._format_size_stable(size2)

        # Both should format the same way (no decimal flickering)
        assert format1 == format2 == "150 MB"

    def test_hms_time_formatting_seconds(self):
        """Test HH:MM:SS formatting for seconds."""
        assert self.widget._format_time_hms(0) == "00:00:00"
        assert self.widget._format_time_hms(30) == "00:00:30"
        assert self.widget._format_time_hms(59) == "00:00:59"

    def test_hms_time_formatting_minutes(self):
        """Test HH:MM:SS formatting for minutes."""
        assert self.widget._format_time_hms(60) == "00:01:00"
        assert self.widget._format_time_hms(90) == "00:01:30"
        assert self.widget._format_time_hms(3599) == "00:59:59"

    def test_hms_time_formatting_hours(self):
        """Test HH:MM:SS formatting for hours."""
        assert self.widget._format_time_hms(3600) == "01:00:00"
        assert self.widget._format_time_hms(3661) == "01:01:01"
        assert self.widget._format_time_hms(7323) == "02:02:03"
        assert self.widget._format_time_hms(36000) == "10:00:00"

    def test_hms_time_formatting_edge_cases(self):
        """Test HH:MM:SS formatting edge cases."""
        assert self.widget._format_time_hms(-5) == "00:00:00"  # Negative
        assert self.widget._format_time_hms(0.5) == "00:00:00"  # Fractional
        assert self.widget._format_time_hms(86400) == "24:00:00"  # 24 hours

    def test_legacy_time_formatting_compatibility(self):
        """Test that legacy time formatting still works."""
        # The old _format_time method should still work for compatibility
        assert self.widget._format_time(30) == "30s"
        assert self.widget._format_time(90) == "1m 30s"
        assert self.widget._format_time(3661) == "1h 1m"

    def test_set_time_info_uses_hms_format(self):
        """Test that set_time_info uses the new HH:MM:SS format."""
        # This method should now use HH:MM:SS format
        self.widget.set_time_info(3661)  # 1 hour, 1 minute, 1 second

        if hasattr(self.widget, 'time_label'):
            expected = "01:01:01"
            actual = self.widget.time_label.text()
            assert actual == expected

    def test_size_units_consistency(self):
        """Test that size units are consistent across different ranges."""
        # Test that we use binary units (1024) consistently
        assert self.widget._format_size_stable(1024) == "1 KB"
        assert self.widget._format_size_stable(1048576) == "1 MB"
        assert self.widget._format_size_stable(1073741824) == "1 GB"
        assert self.widget._format_size_stable(1099511627776) == "1 TB"

    def test_size_formatting_stability_range(self):
        """Test size formatting stability across a range of similar values."""
        # Test a range of values that should format consistently
        base_size = 150 * 1024 * 1024  # 150 MB

        formats = []
        for i in range(10):
            size = base_size + (i * 1000)  # Add small increments
            formats.append(self.widget._format_size_stable(size))

        # All should format the same way for stability
        unique_formats = set(formats)
        assert len(unique_formats) == 1  # Should all be the same
        assert list(unique_formats)[0] == "150 MB"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
