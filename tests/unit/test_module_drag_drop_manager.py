"""Tests for ModuleDragDropManager.

Author: Michael Economou
Date: 2025-12-27

Tests drag & drop state management independently of UI.
"""

from oncutf.controllers.module_drag_drop_manager import ModuleDragDropManager


class MockWidget:
    """Mock widget for testing."""

    def __init__(self, name: str):
        self.name = name


class TestModuleDragDropManager:
    """Test ModuleDragDropManager drag state tracking."""

    def test_initialization(self):
        """Test manager initializes with no active drag."""
        manager = ModuleDragDropManager()

        assert manager.is_dragging is False
        assert manager.dragged_widget is None

    def test_start_drag(self):
        """Test starting drag tracking."""
        manager = ModuleDragDropManager()
        widget = MockWidget("test")

        manager.start_drag(widget, (100, 100))

        assert manager.dragged_widget == widget
        assert manager.is_dragging is False  # Not dragging until threshold

    def test_update_drag_below_threshold(self):
        """Test drag update below threshold doesn't start drag."""
        manager = ModuleDragDropManager()
        widget = MockWidget("test")

        manager.start_drag(widget, (100, 100))

        # Move 2 pixels (below 5px threshold)
        drag_started = manager.update_drag((102, 100))

        assert drag_started is False
        assert manager.is_dragging is False

    def test_update_drag_above_threshold(self):
        """Test drag update above threshold starts drag."""
        manager = ModuleDragDropManager()
        widget = MockWidget("test")

        manager.start_drag(widget, (100, 100))

        # Move 10 pixels (above 5px threshold)
        drag_started = manager.update_drag((110, 100))

        assert drag_started is True
        assert manager.is_dragging is True

    def test_update_drag_diagonal(self):
        """Test drag threshold with diagonal movement."""
        manager = ModuleDragDropManager()
        widget = MockWidget("test")

        manager.start_drag(widget, (100, 100))

        # Move diagonally (3, 4) = 5 pixels exactly (threshold)
        drag_started = manager.update_drag((103, 104))

        assert drag_started is False  # Exactly at threshold, not over

        # Move slightly more
        drag_started = manager.update_drag((104, 105))
        assert drag_started is True
        assert manager.is_dragging is True

    def test_update_drag_without_start(self):
        """Test updating drag without starting first."""
        manager = ModuleDragDropManager()

        # Try to update without starting
        drag_started = manager.update_drag((100, 100))

        assert drag_started is False
        assert manager.is_dragging is False

    def test_update_drag_only_starts_once(self):
        """Test drag only starts once even with multiple updates."""
        manager = ModuleDragDropManager()
        widget = MockWidget("test")

        manager.start_drag(widget, (100, 100))

        # First update crosses threshold
        drag_started = manager.update_drag((110, 100))
        assert drag_started is True

        # Second update should not return True again
        drag_started = manager.update_drag((120, 100))
        assert drag_started is False
        assert manager.is_dragging is True  # Still dragging

    def test_end_drag(self):
        """Test ending drag operation."""
        manager = ModuleDragDropManager()
        widget = MockWidget("test")

        manager.start_drag(widget, (100, 100))
        manager.update_drag((110, 100))  # Start dragging

        returned_widget = manager.end_drag()

        assert returned_widget == widget
        assert manager.is_dragging is False
        assert manager.dragged_widget is None

    def test_end_drag_without_active_drag(self):
        """Test ending drag when no drag active."""
        manager = ModuleDragDropManager()

        returned_widget = manager.end_drag()

        assert returned_widget is None
        assert manager.is_dragging is False

    def test_cancel_drag(self):
        """Test cancelling active drag."""
        manager = ModuleDragDropManager()
        widget = MockWidget("test")

        manager.start_drag(widget, (100, 100))
        manager.update_drag((110, 100))  # Start dragging

        manager.cancel_drag()

        assert manager.is_dragging is False
        assert manager.dragged_widget is None

    def test_cancel_drag_during_tracking(self):
        """Test cancelling during tracking (before threshold)."""
        manager = ModuleDragDropManager()
        widget = MockWidget("test")

        manager.start_drag(widget, (100, 100))
        # Don't cross threshold

        manager.cancel_drag()

        assert manager.is_dragging is False
        assert manager.dragged_widget is None

    def test_multiple_drag_cycles(self):
        """Test multiple drag operations in sequence."""
        manager = ModuleDragDropManager()

        # First drag
        widget1 = MockWidget("widget1")
        manager.start_drag(widget1, (100, 100))
        manager.update_drag((110, 100))
        result1 = manager.end_drag()
        assert result1 == widget1

        # Second drag
        widget2 = MockWidget("widget2")
        manager.start_drag(widget2, (200, 200))
        manager.update_drag((210, 200))
        result2 = manager.end_drag()
        assert result2 == widget2

        # States are independent
        assert manager.is_dragging is False
        assert manager.dragged_widget is None

    def test_drag_with_negative_coordinates(self):
        """Test drag with negative coordinates."""
        manager = ModuleDragDropManager()
        widget = MockWidget("test")

        manager.start_drag(widget, (-100, -100))
        drag_started = manager.update_drag((-90, -100))

        assert drag_started is True
        assert manager.is_dragging is True

    def test_drag_threshold_calculation(self):
        """Test various threshold distances."""
        manager = ModuleDragDropManager()
        widget = MockWidget("test")

        test_cases = [
            ((100, 100), (104, 100), False),  # 4px horizontal
            ((100, 100), (100, 104), False),  # 4px vertical
            ((100, 100), (103, 103), False),  # 4.24px diagonal
            ((100, 100), (106, 100), True),  # 6px horizontal
            ((100, 100), (100, 106), True),  # 6px vertical
            ((100, 100), (104, 104), True),  # 5.66px diagonal
        ]

        for start_pos, end_pos, expected in test_cases:
            manager.cancel_drag()  # Reset
            manager.start_drag(widget, start_pos)
            result = manager.update_drag(end_pos)
            assert result == expected, f"Failed for {start_pos} -> {end_pos}"
