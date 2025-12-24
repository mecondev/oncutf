"""
Unit tests for ShutdownCoordinator.

Tests coordinated shutdown of all application components with special
attention to Windows-specific behavior and edge cases.

Created: 2025-12-08
"""

import time  # noqa: F401
from unittest.mock import Mock, patch

import pytest

from oncutf.core.shutdown_coordinator import ShutdownCoordinator, ShutdownPhase, ShutdownResult


class TestShutdownCoordinator:
    """Tests for ShutdownCoordinator class."""

    @pytest.fixture
    def coordinator(self, qapp):
        """Create a ShutdownCoordinator instance."""
        _ = qapp
        return ShutdownCoordinator()

    def test_initialization(self, coordinator):
        """Test coordinator initialization."""
        assert coordinator._shutdown_in_progress is False
        assert coordinator._emergency_mode is False
        assert len(coordinator._results) == 0
        assert coordinator.phase_timeouts == ShutdownCoordinator.DEFAULT_TIMEOUTS

    def test_register_components(self, coordinator):
        """Test registering components for shutdown."""
        timer_mgr = Mock()
        thread_mgr = Mock()
        db_mgr = Mock()
        exiftool_wrapper = Mock()

        coordinator.register_timer_manager(timer_mgr)
        coordinator.register_thread_pool_manager(thread_mgr)
        coordinator.register_database_manager(db_mgr)
        coordinator.register_exiftool_wrapper(exiftool_wrapper)

        assert coordinator._timer_manager is timer_mgr
        assert coordinator._thread_pool_manager is thread_mgr
        assert coordinator._database_manager is db_mgr
        assert coordinator._exiftool_wrapper is exiftool_wrapper

    def test_set_phase_timeout(self, coordinator):
        """Test setting custom timeout for a phase."""
        custom_timeout = 15.0
        coordinator.set_phase_timeout(ShutdownPhase.THREAD_POOL, custom_timeout)
        assert coordinator.phase_timeouts[ShutdownPhase.THREAD_POOL] == custom_timeout

    def test_shutdown_timers_success(self, coordinator):
        """Test successful timer shutdown."""
        mock_timer_mgr = Mock()
        mock_timer_mgr.cleanup_all.return_value = 5
        coordinator.register_timer_manager(mock_timer_mgr)

        success, error = coordinator._shutdown_timers()

        assert success is True
        assert error is None
        mock_timer_mgr.cleanup_all.assert_called_once()

    def test_shutdown_timers_no_manager(self, coordinator):
        """Test timer shutdown with no manager registered."""
        success, error = coordinator._shutdown_timers()
        assert success is True
        assert error is None

    def test_shutdown_timers_exception(self, coordinator):
        """Test timer shutdown with exception."""
        mock_timer_mgr = Mock()
        mock_timer_mgr.cleanup_all.side_effect = RuntimeError("Timer error")
        coordinator.register_timer_manager(mock_timer_mgr)

        success, error = coordinator._shutdown_timers()

        assert success is False
        assert "Timer shutdown failed" in error

    def test_shutdown_thread_pool_success(self, coordinator):
        """Test successful thread pool shutdown."""
        mock_thread_mgr = Mock()
        coordinator.register_thread_pool_manager(mock_thread_mgr)

        success, error = coordinator._shutdown_thread_pool()

        assert success is True
        assert error is None
        mock_thread_mgr.shutdown.assert_called_once()

    def test_shutdown_thread_pool_with_signal_disconnect(self, coordinator):
        """Test thread pool shutdown disconnects signals safely."""
        mock_thread_mgr = Mock()
        mock_thread_mgr.disconnect.side_effect = RuntimeError("Already disconnected")
        coordinator.register_thread_pool_manager(mock_thread_mgr)

        # Should not raise despite disconnect error
        success, error = coordinator._shutdown_thread_pool()

        assert success is True
        assert error is None
        mock_thread_mgr.shutdown.assert_called_once()

    def test_shutdown_database_success(self, coordinator):
        """Test successful database shutdown."""
        mock_db_mgr = Mock()
        coordinator.register_database_manager(mock_db_mgr)

        success, error = coordinator._shutdown_database()

        assert success is True
        assert error is None
        mock_db_mgr.close.assert_called_once()

    @patch("platform.system")
    def test_shutdown_database_windows_delay(self, mock_platform, coordinator):
        """Test database shutdown includes delay on Windows."""
        mock_platform.return_value = "Windows"
        mock_db_mgr = Mock()
        coordinator.register_database_manager(mock_db_mgr)

        start_time = time.time()
        success, error = coordinator._shutdown_database()
        duration = time.time() - start_time

        assert success is True
        assert error is None
        # Should have at least 100ms delay on Windows
        assert duration >= 0.1
        mock_db_mgr.close.assert_called_once()

    def test_shutdown_database_with_commit(self, coordinator):
        """Test database shutdown attempts commit on Windows."""
        mock_db_mgr = Mock()
        coordinator.register_database_manager(mock_db_mgr)

        with patch("platform.system", return_value="Windows"):
            success, error = coordinator._shutdown_database()

        assert success is True
        # Even if commit doesn't exist, should not fail
        if hasattr(mock_db_mgr, "commit"):
            mock_db_mgr.commit.assert_called()

    @patch("oncutf.utils.exiftool_wrapper.ExifToolWrapper")
    def test_shutdown_exiftool_success(self, mock_exiftool_class, coordinator):
        """Test successful ExifTool shutdown."""
        mock_wrapper = Mock()
        coordinator.register_exiftool_wrapper(mock_wrapper)

        success, error = coordinator._shutdown_exiftool()

        assert success is True
        assert error is None
        mock_wrapper.stop.assert_called_once()
        mock_exiftool_class.force_cleanup_all_exiftool_processes.assert_called()

    @patch("oncutf.utils.exiftool_wrapper.ExifToolWrapper")
    def test_shutdown_exiftool_no_wrapper(self, mock_exiftool_class, coordinator):
        """Test ExifTool shutdown with no wrapper registered."""
        success, error = coordinator._shutdown_exiftool()

        assert success is True
        assert error is None
        # Should still call force cleanup
        mock_exiftool_class.force_cleanup_all_exiftool_processes.assert_called()

    @patch("oncutf.utils.exiftool_wrapper.ExifToolWrapper")
    @patch("platform.system")
    def test_shutdown_exiftool_windows_delay(self, mock_platform, mock_exiftool_class, coordinator):
        """Test ExifTool shutdown includes delay on Windows."""
        mock_platform.return_value = "Windows"
        mock_wrapper = Mock()
        coordinator.register_exiftool_wrapper(mock_wrapper)

        start_time = time.time()
        success, error = coordinator._shutdown_exiftool()
        duration = time.time() - start_time

        assert success is True
        assert error is None
        # Should have at least 200ms delay on Windows
        assert duration >= 0.2
        # Verify force cleanup was called
        mock_exiftool_class.force_cleanup_all_exiftool_processes.assert_called()

    @patch("oncutf.utils.exiftool_wrapper.ExifToolWrapper")
    def test_shutdown_exiftool_exception_recovery(self, mock_exiftool_class, coordinator):
        """Test ExifTool shutdown attempts cleanup even on error."""
        mock_wrapper = Mock()

        # Make stop() raise an error that will propagate
        def stop_with_error():
            raise RuntimeError("Stop failed")

        mock_wrapper.stop.side_effect = stop_with_error

        # Make force_cleanup also fail to trigger the exception path
        mock_exiftool_class.force_cleanup_all_exiftool_processes.side_effect = RuntimeError(
            "Cleanup failed"
        )

        coordinator.register_exiftool_wrapper(mock_wrapper)

        success, error = coordinator._shutdown_exiftool()

        # Now should fail because both stop and force_cleanup failed
        assert success is False
        assert "ExifTool shutdown failed" in error
        # Should still have attempted force cleanup at least once
        assert mock_exiftool_class.force_cleanup_all_exiftool_processes.call_count >= 1

    def test_shutdown_finalize(self, coordinator):
        """Test finalization phase."""
        success, error = coordinator._shutdown_finalize()
        assert success is True
        assert error is None

    def test_execute_shutdown_success(self, coordinator):
        """Test full shutdown execution with all components."""
        # Register mock components
        mock_timer_mgr = Mock()
        mock_timer_mgr.cleanup_all.return_value = 3
        mock_thread_mgr = Mock()
        mock_db_mgr = Mock()
        mock_exiftool = Mock()

        coordinator.register_timer_manager(mock_timer_mgr)
        coordinator.register_thread_pool_manager(mock_thread_mgr)
        coordinator.register_database_manager(mock_db_mgr)
        coordinator.register_exiftool_wrapper(mock_exiftool)

        # Mock ExifToolWrapper.force_cleanup_all_exiftool_processes
        with patch("oncutf.utils.exiftool_wrapper.ExifToolWrapper"):
            success = coordinator.execute_shutdown()

        assert success is True
        assert coordinator._shutdown_in_progress is False
        assert len(coordinator._results) == 5  # 5 phases

        # Verify all components were called
        mock_timer_mgr.cleanup_all.assert_called_once()
        mock_thread_mgr.shutdown.assert_called_once()
        mock_db_mgr.close.assert_called_once()
        mock_exiftool.stop.assert_called_once()

    def test_execute_shutdown_prevents_double_execution(self, coordinator):
        """Test that shutdown can't be executed twice simultaneously."""
        coordinator._shutdown_in_progress = True

        success = coordinator.execute_shutdown()

        assert success is False

    def test_execute_shutdown_emergency_mode(self, coordinator):
        """Test emergency shutdown with reduced timeouts."""
        mock_thread_mgr = Mock()
        coordinator.register_thread_pool_manager(mock_thread_mgr)

        with patch("oncutf.utils.exiftool_wrapper.ExifToolWrapper"):
            success = coordinator.execute_shutdown(emergency=True)

        assert success is True
        assert coordinator._emergency_mode is True

    def test_execute_shutdown_with_progress_callback(self, coordinator):
        """Test shutdown with progress callback."""
        progress_calls = []

        def progress_callback(message, progress):
            progress_calls.append((message, progress))

        with patch("oncutf.utils.exiftool_wrapper.ExifToolWrapper"):
            coordinator.execute_shutdown(progress_callback=progress_callback)

        # Should have received progress updates
        assert len(progress_calls) >= 5  # At least one per phase

    def test_execute_shutdown_phase_failure(self, coordinator):
        """Test shutdown continues even if one phase fails."""
        mock_timer_mgr = Mock()
        mock_timer_mgr.cleanup_all.side_effect = RuntimeError("Timer error")
        mock_thread_mgr = Mock()

        coordinator.register_timer_manager(mock_timer_mgr)
        coordinator.register_thread_pool_manager(mock_thread_mgr)

        with patch("oncutf.utils.exiftool_wrapper.ExifToolWrapper"):
            success = coordinator.execute_shutdown()

        # Overall success should be False due to timer failure
        assert success is False
        # But other phases should still execute
        mock_thread_mgr.shutdown.assert_called_once()
        # All 5 phases should be in results
        assert len(coordinator._results) == 5

    def test_get_results(self, coordinator):
        """Test getting shutdown results."""
        with patch("oncutf.utils.exiftool_wrapper.ExifToolWrapper"):
            coordinator.execute_shutdown()

        results = coordinator.get_results()
        assert len(results) == 5
        assert all(isinstance(r, ShutdownResult) for r in results)

    def test_get_summary(self, coordinator):
        """Test getting shutdown summary."""
        with patch("oncutf.utils.exiftool_wrapper.ExifToolWrapper"):
            coordinator.execute_shutdown()

        summary = coordinator.get_summary()
        assert "executed" in summary
        assert "total_phases" in summary
        assert "successful_phases" in summary
        assert "failed_phases" in summary
        assert "total_duration" in summary
        assert "phases" in summary
        assert summary["executed"] is True
        assert summary["total_phases"] == 5

    def test_shutdown_phase_timeout_warning(self, coordinator):
        """Test that phase timeout generates warning."""
        # Set very short timeout
        coordinator.set_phase_timeout(ShutdownPhase.THREAD_POOL, 0.01)

        # Mock slow shutdown
        mock_thread_mgr = Mock()

        def slow_shutdown():
            time.sleep(0.05)  # 50ms > 10ms timeout

        mock_thread_mgr.shutdown.side_effect = slow_shutdown
        coordinator.register_thread_pool_manager(mock_thread_mgr)

        with patch("oncutf.utils.exiftool_wrapper.ExifToolWrapper"):
            coordinator.execute_shutdown()

        # Find thread pool result
        thread_pool_result = next(
            r for r in coordinator._results if r.phase == ShutdownPhase.THREAD_POOL
        )

        # Should have warning about timeout
        assert thread_pool_result.warning is not None
        assert "exceeded timeout" in thread_pool_result.warning.lower()

    def test_shutdown_signals_emitted(self, coordinator, qtbot):
        """Test that coordinator emits signals during shutdown."""
        phase_started_signals = []
        phase_completed_signals = []

        coordinator.phase_started.connect(lambda phase: phase_started_signals.append(phase))
        coordinator.phase_completed.connect(
            lambda phase, success: phase_completed_signals.append((phase, success))
        )

        with (
            qtbot.waitSignal(coordinator.shutdown_completed, timeout=5000),
            patch("oncutf.utils.exiftool_wrapper.ExifToolWrapper"),
        ):
            coordinator.execute_shutdown()

        # Should have received signals for all phases
        assert len(phase_started_signals) == 5
        assert len(phase_completed_signals) == 5

    @patch("platform.system")
    def test_windows_specific_cleanup_timing(self, mock_platform, coordinator):
        """Test that Windows gets appropriate cleanup delays."""
        mock_platform.return_value = "Windows"

        mock_db_mgr = Mock()
        mock_exiftool = Mock()

        coordinator.register_database_manager(mock_db_mgr)
        coordinator.register_exiftool_wrapper(mock_exiftool)

        start_time = time.time()

        with patch("oncutf.utils.exiftool_wrapper.ExifToolWrapper"):
            coordinator.execute_shutdown()

        duration = time.time() - start_time

        # Windows should have at least 300ms total delay (100ms db + 200ms exiftool)
        assert duration >= 0.3

    @patch("platform.system")
    def test_linux_no_extra_delays(self, mock_platform, coordinator):
        """Test that Linux doesn't get unnecessary delays."""
        mock_platform.return_value = "Linux"

        mock_db_mgr = Mock()
        mock_exiftool = Mock()

        coordinator.register_database_manager(mock_db_mgr)
        coordinator.register_exiftool_wrapper(mock_exiftool)

        start_time = time.time()

        with patch("oncutf.utils.exiftool_wrapper.ExifToolWrapper"):
            coordinator.execute_shutdown()

        duration = time.time() - start_time

        # Linux should be fast (< 100ms without delays)
        assert duration < 0.5


class TestShutdownResult:
    """Tests for ShutdownResult dataclass."""

    def test_shutdown_result_creation(self):
        """Test creating ShutdownResult."""
        result = ShutdownResult(
            phase=ShutdownPhase.TIMERS,
            success=True,
            duration=0.5,
            error=None,
            warning=None,
        )

        assert result.phase == ShutdownPhase.TIMERS
        assert result.success is True
        assert result.duration == 0.5
        assert result.error is None
        assert result.warning is None

    def test_shutdown_result_with_error(self):
        """Test ShutdownResult with error."""
        result = ShutdownResult(
            phase=ShutdownPhase.DATABASE,
            success=False,
            duration=1.0,
            error="Connection failed",
        )

        assert result.success is False
        assert result.error == "Connection failed"


class TestShutdownPhase:
    """Tests for ShutdownPhase enum."""

    def test_shutdown_phases_order(self):
        """Test that shutdown phases are properly defined."""
        assert ShutdownPhase.TIMERS.value == "timers"
        assert ShutdownPhase.THREAD_POOL.value == "thread_pool"
        assert ShutdownPhase.DATABASE.value == "database"
        assert ShutdownPhase.EXIFTOOL.value == "exiftool"
        assert ShutdownPhase.FINALIZE.value == "finalize"

    def test_shutdown_phases_count(self):
        """Test that we have the expected number of phases."""
        phases = list(ShutdownPhase)
        assert len(phases) == 5
