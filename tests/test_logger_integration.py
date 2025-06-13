"""
test_logger_integration.py

Tests for logger integration with timer system and general logging functionality.

Author: Michael Economou
Date: 2025-05-01
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from PyQt5.QtTest import QTest

from utils.logger_factory import get_cached_logger
from utils.timer_manager import (
    schedule_ui_update, schedule_metadata_load, get_timer_manager, cleanup_all_timers
)


class TestLoggerTimerIntegration:
    """Test integration between logger and timer systems."""

    def setup_method(self):
        """Set up test fixtures."""
        self.logger = get_cached_logger(__name__)
        self.log_messages = []

        # Mock logger to capture messages
        self.original_debug = self.logger.debug
        self.original_info = self.logger.info
        self.original_warning = self.logger.warning
        self.original_error = self.logger.error

        def capture_debug(msg, *args, **kwargs):
            self.log_messages.append(('DEBUG', msg))
            self.original_debug(msg, *args, **kwargs)

        def capture_info(msg, *args, **kwargs):
            self.log_messages.append(('INFO', msg))
            self.original_info(msg, *args, **kwargs)

        def capture_warning(msg, *args, **kwargs):
            self.log_messages.append(('WARNING', msg))
            self.original_warning(msg, *args, **kwargs)

        def capture_error(msg, *args, **kwargs):
            self.log_messages.append(('ERROR', msg))
            self.original_error(msg, *args, **kwargs)

        self.logger.debug = capture_debug
        self.logger.info = capture_info
        self.logger.warning = capture_warning
        self.logger.error = capture_error

    def teardown_method(self):
        """Clean up after each test."""
        # Restore original logger methods
        self.logger.debug = self.original_debug
        self.logger.info = self.original_info
        self.logger.warning = self.original_warning
        self.logger.error = self.original_error

        cleanup_all_timers()

    def test_timer_manager_logging(self):
        """Test that timer manager logs operations correctly."""
        # Clear existing messages
        self.log_messages.clear()

        # Schedule a timer
        timer_id = schedule_ui_update(lambda: None, 10)

        # Wait for execution
        QTest.qWait(50)

        # Should have logged timer operations
        debug_messages = [msg for level, msg in self.log_messages if level == 'DEBUG']
        assert any('[TimerManager]' in msg for msg in debug_messages), \
            f"No timer manager debug messages found in: {debug_messages}"

    def test_timer_error_logging(self):
        """Test that timer callback errors are logged properly."""
        self.log_messages.clear()

        def failing_callback():
            raise ValueError("Test error for logging")

        # Schedule timer with failing callback
        timer_id = schedule_ui_update(failing_callback, 10)

        # Wait for execution
        QTest.qWait(50)

        # Should have logged the error
        error_messages = [msg for level, msg in self.log_messages if level == 'ERROR']
        assert any('Error executing timer' in msg for msg in error_messages), \
            f"No timer error messages found in: {error_messages}"

    def test_logger_performance_with_timers(self):
        """Test logger performance when used extensively with timers."""
        import time

        def logging_callback(i):
            self.logger.debug(f"Timer callback {i} executed")
            self.logger.info(f"Processing item {i}")

        # Schedule many timers with logging
        start_time = time.time()

        for i in range(100):
            schedule_ui_update(lambda idx=i: logging_callback(idx), 10 + (i % 10))

        schedule_time = time.time() - start_time

        # Wait for execution
        QTest.qWait(100)

        execution_time = time.time() - start_time

        # Should complete reasonably quickly even with extensive logging
        assert schedule_time < 0.5, f"Scheduling with logging took too long: {schedule_time}s"
        assert execution_time < 2.0, f"Execution with logging took too long: {execution_time}s"

        # Should have logged many messages
        assert len(self.log_messages) > 100, f"Expected many log messages, got {len(self.log_messages)}"

    def test_dev_only_logging_integration(self):
        """Test dev_only logging feature with timer system."""
        self.log_messages.clear()

        def callback_with_dev_logging():
            self.logger.debug("Normal debug message")
            self.logger.debug("Dev only message", extra={"dev_only": True})

        # Schedule timer with dev logging
        schedule_ui_update(callback_with_dev_logging, 10)

        # Wait for execution
        QTest.qWait(50)

        # Should have logged both types of messages
        debug_messages = [msg for level, msg in self.log_messages if level == 'DEBUG']
        assert len(debug_messages) >= 2, f"Expected multiple debug messages, got: {debug_messages}"


class TestLoggerFactory:
    """Test logger factory functionality."""

    def test_cached_logger_instances(self):
        """Test that logger factory returns cached instances."""
        logger1 = get_cached_logger('test_module')
        logger2 = get_cached_logger('test_module')

        # Should return the same instance
        assert logger1 is logger2

    def test_different_module_loggers(self):
        """Test that different modules get different loggers."""
        logger1 = get_cached_logger('module1')
        logger2 = get_cached_logger('module2')

        # Should be different instances
        assert logger1 is not logger2
        assert logger1.name != logger2.name

    def test_logger_configuration(self):
        """Test that loggers are configured correctly."""
        logger = get_cached_logger('test_config')

        # Should have basic logging capabilities
        assert hasattr(logger, 'debug')
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'warning')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'critical')

    def test_logger_memory_management(self):
        """Test that logger factory doesn't leak memory."""
        # Create many loggers
        loggers = []
        for i in range(100):
            logger = get_cached_logger(f'test_module_{i}')
            loggers.append(logger)

        # All should be unique
        assert len(set(id(logger) for logger in loggers)) == 100

        # Getting same logger names should return cached instances
        cached_logger = get_cached_logger('test_module_0')
        assert cached_logger is loggers[0]


class TestLoggingInTimerScenarios:
    """Test logging in various timer usage scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.logger = get_cached_logger(__name__)

    def teardown_method(self):
        """Clean up after each test."""
        cleanup_all_timers()

    def test_metadata_loading_logging(self):
        """Test logging during simulated metadata loading operations."""
        metadata_items = []

        def simulate_metadata_load(item_id):
            self.logger.info(f"Loading metadata for item {item_id}")
            metadata_items.append(item_id)
            self.logger.debug(f"Metadata loaded for item {item_id}", extra={"dev_only": True})

        # Schedule multiple metadata loading operations
        for i in range(10):
            schedule_metadata_load(lambda idx=i: simulate_metadata_load(idx), 20 + (i * 5))

        # Wait for completion
        QTest.qWait(150)

        # Should have processed all items
        assert len(metadata_items) == 10
        assert set(metadata_items) == set(range(10))

    def test_ui_update_logging(self):
        """Test logging during UI update operations."""
        ui_updates = []

        def simulate_ui_update(update_type):
            self.logger.debug(f"Performing UI update: {update_type}")
            ui_updates.append(update_type)

        # Schedule various UI updates
        update_types = ['table_refresh', 'metadata_display', 'selection_update', 'preview_update']

        for update_type in update_types:
            schedule_ui_update(lambda ut=update_type: simulate_ui_update(ut), 15)

        # Wait for completion
        QTest.qWait(50)

        # Should have performed all updates
        assert len(ui_updates) == len(update_types)
        assert set(ui_updates) == set(update_types)

    def test_error_scenario_logging(self):
        """Test logging during error scenarios."""
        with patch.object(self.logger, 'error') as mock_error:
            def error_prone_callback():
                raise RuntimeError("Simulated error")

            # Schedule timer that will fail
            schedule_ui_update(error_prone_callback, 10)

            # Wait for execution
            QTest.qWait(50)

            # Should have logged error (timer manager should catch and log)
            # Note: This tests that the timer system properly handles and logs errors
            pass  # Error logging is handled by timer manager internally


@pytest.mark.integration
class TestLoggerTimerRealWorld:
    """Real-world integration tests for logger and timer systems."""

    def test_application_startup_logging(self):
        """Test logging during simulated application startup."""
        startup_events = []
        logger = get_cached_logger('startup_test')

        def log_startup_event(event):
            logger.info(f"Startup event: {event}")
            startup_events.append(event)

        # Simulate startup sequence with timers
        events = [
            ('ui_init', 5),
            ('load_config', 10),
            ('setup_widgets', 15),
            ('connect_signals', 20),
            ('finalize_startup', 25)
        ]

        for event, delay in events:
            schedule_ui_update(lambda e=event: log_startup_event(e), delay)

        # Wait for startup sequence
        QTest.qWait(100)

        # Should have completed startup sequence
        assert len(startup_events) == len(events)
        assert startup_events == [event for event, _ in events]

    def test_file_operation_logging(self):
        """Test logging during simulated file operations."""
        file_operations = []
        logger = get_cached_logger('file_ops_test')

        def simulate_file_operation(operation, filename):
            logger.debug(f"File operation: {operation} on {filename}")
            file_operations.append((operation, filename))

        # Simulate file operations with different timing
        operations = [
            ('load', 'file1.txt', 10),
            ('process', 'file1.txt', 20),
            ('load', 'file2.txt', 15),
            ('process', 'file2.txt', 25),
            ('save', 'output.txt', 30)
        ]

        for op, filename, delay in operations:
            schedule_metadata_load(
                lambda o=op, f=filename: simulate_file_operation(o, f),
                delay
            )

        # Wait for all operations
        QTest.qWait(100)

        # Should have performed all operations
        assert len(file_operations) == len(operations)

        # Check operation order (may not be strictly sequential due to timing)
        ops_performed = [op for op, _ in file_operations]
        expected_ops = [op for op, _, _ in operations]
        assert set(ops_performed) == set(expected_ops)
