"""
test_timer_performance.py

Performance tests for the centralized timer management system.
"""

import pytest
import time
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication
import sys

from utils.timer_manager import (
    schedule_ui_update, cleanup_all_timers, get_timer_manager
)

# Ensure QApplication exists for timer tests
if not QApplication.instance():
    app = QApplication(sys.argv)


class TestTimerPerformance:
    """Performance tests for timer manager."""

    def setup_method(self):
        """Set up test fixtures."""
        self.execution_count = 0

    def teardown_method(self):
        """Clean up after each test."""
        cleanup_all_timers()

    def increment_counter(self):
        """Simple callback to increment counter."""
        self.execution_count += 1

    def test_consolidation_efficiency(self):
        """Test that timer consolidation reduces timer count."""
        tm = get_timer_manager()

        # Schedule many similar timers that should consolidate
        timer_ids = []
        for i in range(20):
            timer_id = schedule_ui_update(
                self.increment_counter,
                delay=20,  # Same delay for consolidation
            )
            timer_ids.append(timer_id)

        # Due to consolidation, should have fewer active timers
        active_count = tm.get_active_count()
        assert active_count < 20, f"Expected consolidation, got {active_count} active timers"

        # Wait for execution
        QTest.qWait(100)

        # Should execute at least some callbacks
        assert self.execution_count > 0
        print(f"📊 Consolidation: {20} scheduled → {active_count} active timers")

    def test_scheduling_performance(self):
        """Test rapid timer scheduling performance."""
        start_time = time.time()

        # Schedule many timers rapidly
        timer_count = 300
        for i in range(timer_count):
            schedule_ui_update(
                lambda: None,
                delay=50 + (i % 10),  # Vary delays slightly
            )

        schedule_time = time.time() - start_time

        # Should complete scheduling quickly
        assert schedule_time < 2.0, f"Scheduling took too long: {schedule_time:.3f}s"

        tm = get_timer_manager()
        active_count = tm.get_active_count()

        print(f"📊 Scheduled {timer_count} timers in {schedule_time:.3f}s")
        print(f"📊 Active after consolidation: {active_count}")
        consolidation_ratio = (timer_count - active_count) / timer_count * 100
        print(f"📊 Consolidation efficiency: {consolidation_ratio:.1f}%")

    def test_cleanup_performance(self):
        """Test cleanup performance with many timers."""
        tm = get_timer_manager()

        # Schedule many timers with long delays
        timer_count = 200
        for i in range(timer_count):
            schedule_ui_update(lambda: None, 1000)  # 1 second delay

        initial_active = tm.get_active_count()

        # Measure cleanup time
        start_time = time.time()
        cancelled_count = cleanup_all_timers()
        cleanup_time = time.time() - start_time

        # Should cleanup quickly
        assert cleanup_time < 1.0, f"Cleanup took too long: {cleanup_time:.3f}s"
        assert tm.get_active_count() == 0, "Timers still active after cleanup"

        print(f"📊 Cleaned up {cancelled_count} timers in {cleanup_time:.3f}s")

    def test_memory_stability(self):
        """Test that memory usage doesn't grow with repeated timer usage."""
        tm = get_timer_manager()
        initial_stats = tm.get_stats()

        # Run multiple batches of timers
        batch_count = 5
        timers_per_batch = 30

        for batch in range(batch_count):
            # Schedule batch of timers
            for i in range(timers_per_batch):
                schedule_ui_update(lambda: None, 10)

            # Wait for execution
            QTest.qWait(50)

            # Check that we don't accumulate too many timers
            current_active = tm.get_active_count()
            assert current_active <= 10, f"Too many timers remaining: {current_active}"

        # Final cleanup and stats
        cleanup_all_timers()
        final_stats = tm.get_stats()

        assert final_stats['active_timers'] == 0

        total_processed = final_stats['completed_timers'] - initial_stats['completed_timers']
        print(f"📊 Processed {total_processed} timers across {batch_count} batches")
        print(f"📊 Memory stable: {final_stats['active_timers']} active timers remaining")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
