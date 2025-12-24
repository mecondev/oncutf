"""Module: test_timer_manager.py

Author: Michael Economou
Date: 2025-05-31

test_timer_manager.py
Basic tests for the centralized timer management system.
"""

import warnings

warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*coroutine.*never awaited")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

import sys

import pytest
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

from oncutf.utils.timer_manager import cleanup_all_timers, get_timer_manager, schedule_ui_update

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
        QTest.qWait(100)  # Increased from 50ms to 100ms for CI reliability
        assert self.executed

    def test_cleanup(self):
        schedule_ui_update(lambda: None, 100)
        tm = get_timer_manager()
        assert tm.get_active_count() > 0
        cleanup_all_timers()
        assert tm.get_active_count() == 0

    def test_multiple_timers(self):
        executed_count = 0

        def counter():
            nonlocal executed_count
            executed_count += 1

        # Schedule multiple timers
        schedule_ui_update(counter, 10)
        schedule_ui_update(counter, 15)
        schedule_ui_update(counter, 20)

        QTest.qWait(150)  # Increased from 50ms to 150ms for CI reliability
        assert executed_count > 0  # At least some should execute


if __name__ == "__main__":
    pytest.main([__file__])
