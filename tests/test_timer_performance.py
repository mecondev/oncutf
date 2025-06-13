"""
test_timer_performance.py

Performance tests for the centralized timer management system.

Author: Michael Economou
Date: 2025-05-01
"""

import pytest
import time
import threading
from PyQt5.QtTest import QTest

from utils.timer_manager import (
    TimerManager, TimerType, schedule_ui_update,
    schedule_metadata_load, cleanup_all_timers, get_timer_manager
)


class TestTimerPerformance:
    """Performance tests for timer manager."""

    def setup_method(self):
        """Set up test fixtures."""
        self.timer_manager = TimerManager()
        self.execution_count = 0

    def teardown_method(self):
        """Clean up after each test."""
        self.timer_manager.cleanup_all()
        cleanup_all_timers()

    def increment_counter(self):
        """Simple callback to increment counter."""
        self.execution_count += 1

    def test_consolidation_efficiency(self):
        """Test that timer consolidation actually reduces timer count."""
        # Schedule many similar timers that should consolidate
        timer_ids = []
        for i in range(10):
            timer_id = self.timer_manager.schedule(
                self.increment_counter,
                delay=20,  # Same delay
                timer_type=TimerType.UI_UPDATE,
                consolidate=True
            )
            timer_ids.append(timer_id)

        # Due to consolidation, should have fewer active timers than scheduled
        active_count = self.timer_manager.get_active_count()
        assert active_count < 10, f"Expected fewer than 10 timers, got {active_count}"

        # Most timer IDs should be the same (consolidated)
        unique_ids = set(timer_ids)
        assert len(unique_ids) < 10, f"Expected consolidation, got {len(unique_ids)} unique IDs"

    def test_high_frequency_scheduling(self):
        """Test performance with rapid timer scheduling."""
        start_time = time.time()

        # Schedule 1000 timers rapidly
        for i in range(1000):
            schedule_ui_update(
                lambda: None,
                delay=50 + (i % 10),  # Vary delays slightly
            )

        schedule_time = time.time() - start_time

        # Should complete scheduling quickly (< 1 second)
        assert schedule_time < 1.0, f"Scheduling took too long: {schedule_time}s"

        # Should have reasonable number of active timers (due to consolidation)
        tm = get_timer_manager()
        active_count = tm.get_active_count()
        assert active_count < 1000, f"Too many active timers: {active_count}"

    def test_timer_execution_performance(self):
        """Test that timers execute within reasonable time bounds."""
        execution_times = []

        def time_callback():
            execution_times.append(time.time())

        # Schedule timers with precise delays
        start_time = time.time()
        delays = [10, 20, 30, 40, 50]

        for delay in delays:
            schedule_ui_update(time_callback, delay)

        # Wait for all to execute
        QTest.qWait(100)

        # Check execution timing
        assert len(execution_times) == len(delays)

        for i, expected_delay in enumerate(delays):
            actual_delay = (execution_times[i] - start_time) * 1000  # Convert to ms
            # Allow 20ms tolerance for Qt event loop timing
            assert abs(actual_delay - expected_delay) < 20, \
                f"Timer {i} executed at {actual_delay}ms, expected ~{expected_delay}ms"

    def test_memory_usage_stability(self):
        """Test that memory usage doesn't grow with timer usage."""
        # Get initial stats
        tm = get_timer_manager()
        initial_stats = tm.get_stats()

        # Schedule and execute many timers
        for batch in range(10):
            for i in range(50):
                schedule_ui_update(lambda: None, 10)

            # Wait for execution
            QTest.qWait(50)

            # Force cleanup to ensure no accumulation
            tm.cleanup_all()

        # Check final stats
        final_stats = tm.get_stats()

        # Should not have accumulated active timers
        assert final_stats['active_timers'] == 0

        # Should have processed many timers
        assert final_stats['completed_timers'] > initial_stats['completed_timers']

    def test_concurrent_timer_access(self):
        """Test thread safety of timer operations (basic test)."""
        results = []

        def worker_thread(thread_id):
            """Worker function for threading test."""
            for i in range(10):
                timer_id = schedule_ui_update(
                    lambda tid=thread_id, idx=i: results.append(f"{tid}-{idx}"),
                    delay=20
                )

        # Create multiple threads scheduling timers
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker_thread, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Wait for timer execution
        QTest.qWait(100)

        # Should have executed timers from all threads
        assert len(results) > 0

        # Should have results from different threads
        thread_ids = set(result.split('-')[0] for result in results)
        assert len(thread_ids) > 1, f"Expected multiple threads, got: {thread_ids}"


class TestTimerResourceManagement:
    """Test resource management and cleanup."""

    def setup_method(self):
        """Set up test fixtures."""
        self.timer_manager = TimerManager()

    def teardown_method(self):
        """Clean up after each test."""
        self.timer_manager.cleanup_all()

    def test_qt_timer_cleanup(self):
        """Test that Qt QTimer objects are properly cleaned up."""
        # Schedule timer
        timer_id = self.timer_manager.schedule(lambda: None, 100)

        # Should have one active timer
        assert self.timer_manager.get_active_count() == 1

        # Cancel timer
        self.timer_manager.cancel(timer_id)

        # Should clean up immediately
        assert self.timer_manager.get_active_count() == 0

        # Internal storage should be clean
        assert len(self.timer_manager._active_timers) == 0
        assert len(self.timer_manager._timer_callbacks) == 0
        assert len(self.timer_manager._timer_types) == 0

    def test_callback_reference_cycles(self):
        """Test that callback references don't create memory cycles."""
        class CallbackObject:
            def __init__(self):
                self.executed = False

            def callback(self):
                self.executed = True

        # Create object and schedule timer
        obj = CallbackObject()
        timer_id = self.timer_manager.schedule(obj.callback, 10)

        # Wait for execution
        QTest.qWait(50)

        # Callback should have been executed
        assert obj.executed

        # Timer should be cleaned up
        assert self.timer_manager.get_active_count() == 0

        # No references should remain in timer manager
        assert timer_id not in self.timer_manager._timer_callbacks

    def test_large_scale_cleanup(self):
        """Test cleanup performance with many timers."""
        # Schedule many timers
        timer_count = 500
        for i in range(timer_count):
            self.timer_manager.schedule(
                lambda: None,
                delay=1000,  # Long delay so they don't execute
                timer_type=TimerType.GENERIC
            )

        # Should have all timers active
        assert self.timer_manager.get_active_count() == timer_count

        # Measure cleanup time
        start_time = time.time()
        cancelled_count = self.timer_manager.cleanup_all()
        cleanup_time = time.time() - start_time

        # Should cleanup all timers quickly
        assert cancelled_count == timer_count
        assert cleanup_time < 1.0, f"Cleanup took too long: {cleanup_time}s"
        assert self.timer_manager.get_active_count() == 0


@pytest.mark.stress
class TestTimerStress:
    """Stress tests for timer system."""

    def test_extreme_timer_load(self):
        """Test system behavior under extreme timer load."""
        tm = get_timer_manager()
        initial_count = tm.get_active_count()

        # Schedule massive number of timers
        timer_count = 2000
        for i in range(timer_count):
            schedule_ui_update(
                lambda: None,
                delay=100 + (i % 50),  # Spread delays
            )

        # System should handle this gracefully
        active_count = tm.get_active_count()
        assert active_count > 0, "No timers were scheduled"

        # Due to consolidation, should be much fewer than scheduled
        assert active_count < timer_count / 2, \
            f"Consolidation not working: {active_count} active out of {timer_count} scheduled"

        # Wait for execution
        QTest.qWait(200)

        # Should cleanup after execution
        final_count = tm.get_active_count()
        assert final_count <= initial_count, "Timers not cleaned up properly"

    def test_rapid_schedule_cancel_cycles(self):
        """Test rapid scheduling and cancellation cycles."""
        tm = get_timer_manager()

        for cycle in range(100):
            # Schedule timer
            timer_id = schedule_ui_update(lambda: None, 100)

            # Immediately cancel
            cancelled = tm.cancel(timer_id)
            assert cancelled, f"Failed to cancel timer in cycle {cycle}"

        # Should have no active timers
        assert tm.get_active_count() == 0
