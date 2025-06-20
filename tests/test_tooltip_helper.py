"""
Tests for tooltip helper system
"""

import pytest
from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QLabel

from utils.tooltip_helper import (
    CustomTooltip,
    TooltipHelper,
    TooltipType,
    show_error_tooltip,
    show_info_tooltip,
    show_success_tooltip,
    show_tooltip,
    show_warning_tooltip,
)


class TestTooltipHelper:
    """Test suite for tooltip helper system"""

    @pytest.fixture(autouse=True)
    def setup_widget(self, qtbot):
        """Setup test widget for tooltips"""
        self.test_widget = QLabel("Test Widget")
        qtbot.addWidget(self.test_widget)
        self.test_widget.show()
        yield
        # Clean up any active tooltips
        TooltipHelper.clear_all_tooltips()

    def test_tooltip_type_constants(self):
        """Test that tooltip type constants are properly defined"""
        assert TooltipType.DEFAULT == "default"
        assert TooltipType.ERROR == "error"
        assert TooltipType.WARNING == "warning"
        assert TooltipType.INFO == "info"
        assert TooltipType.SUCCESS == "success"

    def test_custom_tooltip_creation(self, qtbot):
        """Test custom tooltip widget creation"""
        tooltip = CustomTooltip(self.test_widget, "Test message", TooltipType.ERROR)

        assert tooltip.text() == "Test message"
        assert tooltip.tooltip_type == TooltipType.ERROR
        assert not tooltip.isVisible()  # Should not be visible initially

    def test_tooltip_helper_show_tooltip(self, qtbot):
        """Test TooltipHelper.show_tooltip method"""
        # Should not raise any exceptions
        TooltipHelper.show_tooltip(
            self.test_widget,
            "Test message",
            TooltipType.INFO,
            duration=100  # Short duration for testing
        )

        # Check that tooltip was tracked
        assert len(TooltipHelper._active_tooltips) > 0

    def test_tooltip_helper_convenience_methods(self, qtbot):
        """Test convenience methods for different tooltip types"""
        # Error tooltip
        TooltipHelper.show_error_tooltip(self.test_widget, "Error message", duration=100)

        # Warning tooltip
        TooltipHelper.show_warning_tooltip(self.test_widget, "Warning message", duration=100)

        # Info tooltip
        TooltipHelper.show_info_tooltip(self.test_widget, "Info message", duration=100)

        # Success tooltip
        TooltipHelper.show_success_tooltip(self.test_widget, "Success message", duration=100)

        # Should have multiple tooltips tracked (they replace each other for same widget)
        assert len(TooltipHelper._active_tooltips) >= 1

    def test_tooltip_clearing(self, qtbot):
        """Test tooltip clearing functionality"""
        # Show a tooltip
        TooltipHelper.show_tooltip(self.test_widget, "Test message", duration=100)
        assert len(TooltipHelper._active_tooltips) > 0

        # Clear tooltips for specific widget
        TooltipHelper.clear_tooltips_for_widget(self.test_widget)

        # Should have no active tooltips for this widget
        widget_tooltips = [t for w, t in TooltipHelper._active_tooltips if w == self.test_widget]
        assert len(widget_tooltips) == 0

    def test_clear_all_tooltips(self, qtbot):
        """Test clearing all active tooltips"""
        # Show multiple tooltips
        TooltipHelper.show_tooltip(self.test_widget, "Test 1", duration=100)

        # Create another widget and show tooltip
        another_widget = QLabel("Another Widget")
        qtbot.addWidget(another_widget)
        TooltipHelper.show_tooltip(another_widget, "Test 2", duration=100)

        # Clear all tooltips
        TooltipHelper.clear_all_tooltips()

        # Should have no active tooltips
        assert len(TooltipHelper._active_tooltips) == 0

    def test_global_convenience_functions(self, qtbot):
        """Test global convenience functions"""
        # Test global functions work without errors
        show_tooltip(self.test_widget, "Global test")
        show_error_tooltip(self.test_widget, "Global error")
        show_warning_tooltip(self.test_widget, "Global warning")
        show_info_tooltip(self.test_widget, "Global info")
        show_success_tooltip(self.test_widget, "Global success")

        # Should not raise exceptions
        assert True

    def test_tooltip_position_adjustment(self, qtbot):
        """Test that tooltip position is calculated correctly"""
        # This is more of a smoke test since position calculation
        # depends on screen geometry
        position = QPoint(100, 100)

        try:
            # Should not raise exceptions when adjusting position
            adjusted_pos = TooltipHelper._adjust_position_to_screen(
                position,
                self.test_widget.size()
            )
            assert isinstance(adjusted_pos, QPoint)
        except Exception as e:
            pytest.fail(f"Position adjustment failed: {e}")

    def test_tooltip_multiple_for_same_widget(self, qtbot):
        """Test that multiple tooltips for same widget are handled correctly"""
        # Show first tooltip
        TooltipHelper.show_tooltip(self.test_widget, "First message", duration=100)

        # Show second tooltip for same widget
        TooltipHelper.show_tooltip(self.test_widget, "Second message", duration=100)

        # Should only have one tooltip for the widget (second replaces first)
        widget_tooltips = [t for w, t in TooltipHelper._active_tooltips if w == self.test_widget]
        assert len(widget_tooltips) <= 1

    def test_tooltip_with_invalid_duration(self, qtbot):
        """Test tooltip behavior with edge case durations"""
        # None duration should use config default
        TooltipHelper.show_tooltip(self.test_widget, "Default duration")

        # Zero duration
        TooltipHelper.show_tooltip(self.test_widget, "Zero duration", duration=0)

        # Negative duration
        TooltipHelper.show_tooltip(self.test_widget, "Negative duration", duration=-100)

        # Should not raise exceptions
        assert True
