"""Module: test_progress_protocol.py

Tests for the standard progress reporting protocol.
"""

from PyQt5.QtCore import QObject, pyqtSignal

from oncutf.core.progress_protocol import (
    ProgressCallback,
    ProgressInfo,
    SizeProgress,
    SizeProgressCallback,
    create_progress_callback,
    format_progress_message,
    format_size_progress,
)


class TestProgressInfo:
    """Tests for ProgressInfo dataclass."""

    def test_progress_info_creation(self):
        """Test creating ProgressInfo."""
        info = ProgressInfo(current=5, total=10, message="Processing")
        assert info.current == 5
        assert info.total == 10
        assert info.message == "Processing"

    def test_progress_percent_calculation(self):
        """Test percent property."""
        info = ProgressInfo(current=5, total=10)
        assert info.percent == 50.0

        info2 = ProgressInfo(current=1, total=4)
        assert info2.percent == 25.0

    def test_progress_percent_zero_total(self):
        """Test percent calculation with zero total."""
        info = ProgressInfo(current=0, total=0)
        assert info.percent == 0.0

    def test_progress_is_complete(self):
        """Test is_complete property."""
        info = ProgressInfo(current=10, total=10)
        assert info.is_complete is True

        info2 = ProgressInfo(current=5, total=10)
        assert info2.is_complete is False

        info3 = ProgressInfo(current=11, total=10)
        assert info3.is_complete is True

    def test_progress_is_complete_zero_total(self):
        """Test is_complete with zero total."""
        info = ProgressInfo(current=0, total=0)
        assert info.is_complete is False


class TestSizeProgress:
    """Tests for SizeProgress dataclass."""

    def test_size_progress_creation(self):
        """Test creating SizeProgress."""
        progress = SizeProgress(processed_bytes=1024, total_bytes=2048, current_file="test.txt")
        assert progress.processed_bytes == 1024
        assert progress.total_bytes == 2048
        assert progress.current_file == "test.txt"

    def test_size_progress_percent(self):
        """Test percent calculation for size progress."""
        progress = SizeProgress(processed_bytes=2048, total_bytes=4096)
        assert progress.percent == 50.0

    def test_size_progress_is_complete(self):
        """Test is_complete for size progress."""
        progress = SizeProgress(processed_bytes=2048, total_bytes=2048)
        assert progress.is_complete is True

        progress2 = SizeProgress(processed_bytes=1024, total_bytes=2048)
        assert progress2.is_complete is False


class TestProgressCallback:
    """Tests for ProgressCallback protocol."""

    def test_callback_protocol_compliance(self):
        """Test that functions can match ProgressCallback protocol."""

        # Standard callback function
        def my_callback(current: int, total: int, message: str = "") -> None:
            pass

        # Should be recognized as ProgressCallback
        assert isinstance(my_callback, ProgressCallback)

    def test_callback_with_implementation(self):
        """Test callback with actual implementation."""
        calls = []

        def tracking_callback(current: int, total: int, message: str = "") -> None:
            calls.append((current, total, message))

        # Use the callback
        tracking_callback(5, 10, "Processing")
        assert len(calls) == 1
        assert calls[0] == (5, 10, "Processing")


class TestSizeProgressCallback:
    """Tests for SizeProgressCallback protocol."""

    def test_size_callback_protocol(self):
        """Test size callback protocol compliance."""

        def my_size_callback(
            processed_bytes: int, total_bytes: int, current_file: str = ""
        ) -> None:
            pass

        assert isinstance(my_size_callback, SizeProgressCallback)

    def test_size_callback_with_tracking(self):
        """Test size callback with tracking."""
        calls = []

        def tracking_callback(
            processed_bytes: int, total_bytes: int, current_file: str = ""
        ) -> None:
            calls.append((processed_bytes, total_bytes, current_file))

        tracking_callback(1024, 2048, "file.txt")
        assert len(calls) == 1
        assert calls[0] == (1024, 2048, "file.txt")


class TestCreateProgressCallback:
    """Tests for create_progress_callback helper."""

    def test_create_from_qt_signals(self, qtbot):
        """Test creating callbacks from Qt signals."""

        class TestWorker(QObject):
            progress = pyqtSignal(int, int, str)
            size_progress = pyqtSignal(int, int, str)

        worker = TestWorker()
        # Add worker to qtbot for proper cleanup
        qtbot.addWidget(worker) if hasattr(worker, "show") else None

        # Track signal emissions
        progress_calls = []
        size_calls = []

        worker.progress.connect(
            lambda current, total, msg: progress_calls.append((current, total, msg))
        )
        worker.size_progress.connect(lambda proc, tot, file: size_calls.append((proc, tot, file)))

        # Create callbacks
        progress_cb, size_cb = create_progress_callback(
            progress_signal=worker.progress, size_signal=worker.size_progress
        )

        # Use callbacks
        assert progress_cb is not None
        assert size_cb is not None

        progress_cb(5, 10, "Processing")
        qtbot.wait(50)  # Increased wait time for signal processing
        assert len(progress_calls) == 1
        assert progress_calls[0] == (5, 10, "Processing")

        size_cb(1024, 2048, "file.txt")
        qtbot.wait(50)  # Increased wait time for signal processing
        assert len(size_calls) == 1
        assert size_calls[0] == (1024, 2048, "file.txt")

        # Explicitly disconnect and cleanup
        worker.progress.disconnect()
        worker.size_progress.disconnect()
        worker.deleteLater()
        qtbot.wait(50)  # Wait for cleanup

    def test_create_with_none_signals(self):
        """Test create_progress_callback with None signals."""
        progress_cb, size_cb = create_progress_callback(progress_signal=None, size_signal=None)

        assert progress_cb is None
        assert size_cb is None

    def test_create_with_partial_signals(self):
        """Test create_progress_callback with only one signal."""

        class TestWorker(QObject):
            progress = pyqtSignal(int, int, str)

        worker = TestWorker()

        progress_cb, size_cb = create_progress_callback(
            progress_signal=worker.progress, size_signal=None
        )

        assert progress_cb is not None
        assert size_cb is None


class TestFormatProgressMessage:
    """Tests for format_progress_message helper."""

    def test_format_with_item_name(self):
        """Test formatting with item name."""
        msg = format_progress_message(5, 10, "Loading", "image.jpg")
        assert msg == "Loading 5/10: image.jpg"

    def test_format_without_item_name(self):
        """Test formatting without item name."""
        msg = format_progress_message(7, 20, "Processing")
        assert msg == "Processing 7/20"

    def test_format_with_empty_item_name(self):
        """Test formatting with empty item name."""
        msg = format_progress_message(3, 15, "Analyzing", "")
        assert msg == "Analyzing 3/15"


class TestFormatSizeProgress:
    """Tests for format_size_progress helper."""

    def test_format_bytes(self):
        """Test formatting bytes."""
        msg = format_size_progress(512, 1024)
        assert "512.00 B" in msg
        assert "1.00 KB" in msg
        assert "50.0%" in msg

    def test_format_kilobytes(self):
        """Test formatting kilobytes."""
        msg = format_size_progress(1024, 2048)
        assert "1.00 KB" in msg
        assert "2.00 KB" in msg
        assert "50.0%" in msg

    def test_format_megabytes(self):
        """Test formatting megabytes."""
        msg = format_size_progress(5242880, 10485760)  # 5 MB / 10 MB
        assert "5.00 MB" in msg
        assert "10.00 MB" in msg
        assert "50.0%" in msg

    def test_format_without_percent(self):
        """Test formatting without percentage."""
        msg = format_size_progress(1024, 2048, include_percent=False)
        assert "1.00 KB" in msg
        assert "2.00 KB" in msg
        assert "%" not in msg

    def test_format_zero_total(self):
        """Test formatting with zero total bytes."""
        msg = format_size_progress(0, 0)
        assert "0.00 B" in msg

    def test_format_gigabytes(self):
        """Test formatting gigabytes."""
        gb = 1024 * 1024 * 1024
        msg = format_size_progress(gb, gb * 2)
        assert "1.00 GB" in msg
        assert "2.00 GB" in msg
