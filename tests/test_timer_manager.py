"""
test_timer_manager.py

Basic tests for the centralized timer management system.

Author: Michael Economou
Date: 2025-05-01
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from PyQt5.QtCore import QTimer, QObject
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication
import sys

from utils.timer_manager import (
    TimerManager, TimerPriority, TimerType,
    get_timer_manager, schedule_ui_update, schedule_drag_cleanup,
    schedule_selection_update, schedule_metadata_load, schedule_scroll_adjust,
    schedule_resize_adjust, cancel_timer, cancel_timers_by_type, cleanup_all_timers
)

# Ensure QApplication exists for timer tests
if not QApplication.instance():
    app = QApplication(sys.argv)

class TestTimerBasics:
    def setup_method(self):
        self.executed = False

    def teardown_method(self):
        cleanup_all_timers()

    def test_callback(self):
        self.executed = True

    def test_timer_works(self):
        schedule_ui_update(self.test_callback, 10)
        QTest.qWait(50)
        assert self.executed

    def test_cleanup(self):
        schedule_ui_update(lambda: None, 100)
        tm = get_timer_manager()
        assert tm.get_active_count() > 0
        cleanup_all_timers()
        assert tm.get_active_count() == 0


class TestTimerManager:
    """Basic tests for timer manager functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.callback_executed = False
        self.execution_count = 0

    def teardown_method(self):
        """Clean up after each test."""
        cleanup_all_timers()

    def test_callback(self):
        """Simple test callback."""
        self.callback_executed = True
        self.execution_count += 1

    def test_timer_manager_creation(self):
        """Test timer manager can be created."""
        tm = TimerManager()
        assert tm.get_active_count() == 0

    def test_global_timer_manager(self):
        """Test global timer manager singleton."""
        tm1 = get_timer_manager()
        tm2 = get_timer_manager()
        assert tm1 is tm2

    def test_basic_timer_scheduling(self):
        """Test basic timer scheduling works."""
        timer_id = schedule_ui_update(self.test_callback, 10)
        assert timer_id is not None

        # Wait for execution
        QTest.qWait(50)
        assert self.callback_executed

    def test_convenience_functions(self):
        """Test convenience functions work."""
        functions = [
            schedule_ui_update,
            schedule_metadata_load,
        ]

        for func in functions:
            timer_id = func(lambda: None, 10)
            assert timer_id is not None

        # Wait for execution
        QTest.qWait(50)

    def test_timer_cleanup(self):
        """Test timer cleanup works."""
        # Schedule timer
        schedule_ui_update(lambda: None, 100)

        tm = get_timer_manager()
        assert tm.get_active_count() > 0

        # Cleanup
        cleanup_all_timers()
        assert tm.get_active_count() == 0


class TestConvenienceFunctions:
    """Test the convenience functions for common timer operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.callback_executed = False

    def teardown_method(self):
        """Clean up after each test."""
        cleanup_all_timers()

    def test_callback(self):
        """Simple test callback."""
        self.callback_executed = True

    def test_schedule_ui_update(self):
        """Test schedule_ui_update convenience function."""
        timer_id = schedule_ui_update(self.test_callback, 10)
        assert timer_id is not None

        QTest.qWait(50)
        assert self.callback_executed

    def test_schedule_drag_cleanup(self):
        """Test schedule_drag_cleanup convenience function."""
        timer_id = schedule_drag_cleanup(self.test_callback, 10)
        assert timer_id is not None

        QTest.qWait(50)
        assert self.callback_executed

    def test_schedule_selection_update(self):
        """Test schedule_selection_update convenience function."""
        timer_id = schedule_selection_update(self.test_callback, 10)
        assert timer_id is not None

        QTest.qWait(50)
        assert self.callback_executed

    def test_schedule_metadata_load(self):
        """Test schedule_metadata_load convenience function."""
        timer_id = schedule_metadata_load(self.test_callback, 10)
        assert timer_id is not None

        QTest.qWait(50)
        assert self.callback_executed

    def test_schedule_scroll_adjust(self):
        """Test schedule_scroll_adjust convenience function."""
        timer_id = schedule_scroll_adjust(self.test_callback, 10)
        assert timer_id is not None

        QTest.qWait(50)
        assert self.callback_executed

    def test_schedule_resize_adjust(self):
        """Test schedule_resize_adjust convenience function."""
        timer_id = schedule_resize_adjust(self.test_callback, 10)
        assert timer_id is not None

        QTest.qWait(50)
        assert self.callback_executed

    def test_cancel_timer_function(self):
        """Test cancel_timer convenience function."""
        timer_id = schedule_ui_update(self.test_callback, 100)

        cancelled = cancel_timer(timer_id)
        assert cancelled is True

        QTest.qWait(150)
        assert not self.callback_executed

    def test_cancel_timers_by_type_function(self):
        """Test cancel_timers_by_type convenience function."""
        # Schedule multiple UI update timers
        schedule_ui_update(lambda: None, 100)
        schedule_ui_update(lambda: None, 100)
        schedule_metadata_load(lambda: None, 100)

        cancelled_count = cancel_timers_by_type(TimerType.UI_UPDATE)
        assert cancelled_count == 2


class TestGlobalTimerManager:
    """Test the global timer manager instance."""

    def test_singleton_behavior(self):
        """Test that get_timer_manager returns the same instance."""
        tm1 = get_timer_manager()
        tm2 = get_timer_manager()
        assert tm1 is tm2

    def test_global_cleanup(self):
        """Test global cleanup function."""
        # Schedule some timers through global instance
        schedule_ui_update(lambda: None, 100)
        schedule_metadata_load(lambda: None, 100)

        tm = get_timer_manager()
        assert tm.get_active_count() > 0

        # Global cleanup
        cleanup_all_timers()
        assert tm.get_active_count() == 0


class TestTimerMemoryManagement:
    """Test memory management and leak prevention."""

    def setup_method(self):
        """Set up test fixtures."""
        self.timer_manager = TimerManager()

    def teardown_method(self):
        """Clean up after each test."""
        self.timer_manager.cleanup_all()

    def test_callback_reference_cleanup(self):
        """Test that callback references are cleaned up properly."""
        def callback():
            pass

        # Schedule timer
        timer_id = self.timer_manager.schedule(callback, 10)

        # Timer should be active
        assert self.timer_manager.get_active_count() == 1

        # Wait for execution
        QTest.qWait(50)

        # Timer should be cleaned up
        assert self.timer_manager.get_active_count() == 0

        # Internal references should be cleaned up
        assert timer_id not in self.timer_manager._timer_callbacks
        assert timer_id not in self.timer_manager._timer_types
        assert timer_id not in self.timer_manager._active_timers

    def test_massive_timer_scheduling(self):
        """Test performance with many timers."""
        # Schedule many timers
        timer_ids = []
        for i in range(100):
            timer_id = self.timer_manager.schedule(
                lambda: None,
                delay=10 + (i % 10),  # Vary delays
                timer_type=TimerType.GENERIC
            )
            timer_ids.append(timer_id)

        # Should handle this gracefully
        assert len(timer_ids) == 100
        assert self.timer_manager.get_active_count() > 0

        # Wait for execution
        QTest.qWait(100)

        # All should be cleaned up
        assert self.timer_manager.get_active_count() == 0


class TestTimerErrorHandling:
    """Test error handling in timer operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.timer_manager = TimerManager()

    def teardown_method(self):
        """Clean up after each test."""
        self.timer_manager.cleanup_all()

    def test_callback_exception_handling(self):
        """Test that callback exceptions don't crash the timer system."""
        def failing_callback():
            raise ValueError("Test exception")

        # Schedule timer with failing callback
        timer_id = self.timer_manager.schedule(failing_callback, 10)

        # Should not crash - wait for execution
        QTest.qWait(50)

        # Timer should still be cleaned up despite exception
        assert self.timer_manager.get_active_count() == 0

    def test_cancel_nonexistent_timer(self):
        """Test cancelling a timer that doesn't exist."""
        cancelled = self.timer_manager.cancel("nonexistent_timer_id")
        assert cancelled is False

    def test_cancel_already_executed_timer(self):
        """Test cancelling a timer that has already been executed."""
        timer_id = self.timer_manager.schedule(lambda: None, 10)

        # Wait for execution
        QTest.qWait(50)

        # Try to cancel already executed timer
        cancelled = self.timer_manager.cancel(timer_id)
        assert cancelled is False


@pytest.mark.integration
class TestTimerIntegration:
    """Integration tests to ensure timer manager works with Qt event loop."""

    def test_qt_integration(self):
        """Test that timers work properly with Qt event loop."""
        execution_order = []

        def callback1():
            execution_order.append(1)

        def callback2():
            execution_order.append(2)

        def callback3():
            execution_order.append(3)

        # Schedule timers with different delays
        schedule_ui_update(callback3, 30)  # Should execute last
        schedule_ui_update(callback1, 10)  # Should execute first
        schedule_ui_update(callback2, 20)  # Should execute second

        # Wait for all to execute
        QTest.qWait(100)

        # Should execute in order of delay
        assert execution_order == [1, 2, 3]


if __name__ == '__main__':
    pytest.main([__file__])
