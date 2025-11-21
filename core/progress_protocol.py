"""
Module: progress_protocol.py

Author: Michael Economou
Date: 2025-11-21

Standard Progress Reporting Protocol
Defines consistent interfaces for progress reporting across all concurrent operations.

This module provides:
- ProgressCallback Protocol for type-safe callbacks
- ProgressSignals mixin for Qt workers
- Standard progress data classes
- Helper functions for progress calculation

Benefits:
- Consistent progress reporting patterns
- Type-safe callback interfaces
- Easy testing with mock callbacks
- Clear documentation of progress contract
"""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from core.pyqt_imports import QObject, pyqtSignal


@dataclass
class ProgressInfo:
    """
    Standard progress information structure.

    Attributes:
        current: Current item/bytes processed
        total: Total items/bytes to process
        message: Optional status message
        percent: Progress percentage (0-100)
    """

    current: int
    total: int
    message: str = ""

    @property
    def percent(self) -> float:
        """Calculate progress percentage."""
        if self.total == 0:
            return 0.0
        return (self.current / self.total) * 100.0

    @property
    def is_complete(self) -> bool:
        """Check if progress is complete."""
        return self.current >= self.total and self.total > 0


@dataclass
class SizeProgress:
    """
    Size-based progress information (for file operations).

    Attributes:
        processed_bytes: Bytes processed so far
        total_bytes: Total bytes to process
        current_file: Name of current file being processed
    """

    processed_bytes: int
    total_bytes: int
    current_file: str = ""

    @property
    def percent(self) -> float:
        """Calculate progress percentage."""
        if self.total_bytes == 0:
            return 0.0
        return (self.processed_bytes / self.total_bytes) * 100.0

    @property
    def is_complete(self) -> bool:
        """Check if progress is complete."""
        return self.processed_bytes >= self.total_bytes and self.total_bytes > 0


@runtime_checkable
class ProgressCallback(Protocol):
    """
    Protocol for progress callback functions.

    Any callable matching this signature can be used as a progress callback.

    Example:
        def my_progress_callback(current: int, total: int, message: str = "") -> None:
            print(f"Progress: {current}/{total} - {message}")

        # Type checker will accept this as ProgressCallback
        callback: ProgressCallback = my_progress_callback
    """

    def __call__(self, current: int, total: int, message: str = "") -> None:
        """
        Report progress.

        Args:
            current: Current item number (1-based)
            total: Total number of items
            message: Optional status message
        """
        ...


@runtime_checkable
class SizeProgressCallback(Protocol):
    """
    Protocol for size-based progress callback functions.

    Used for file operations where byte-level progress is important.

    Example:
        def my_size_callback(processed: int, total: int, filename: str = "") -> None:
            mb_done = processed / (1024 * 1024)
            mb_total = total / (1024 * 1024)
            print(f"{filename}: {mb_done:.2f}/{mb_total:.2f} MB")

        callback: SizeProgressCallback = my_size_callback
    """

    def __call__(self, processed_bytes: int, total_bytes: int, current_file: str = "") -> None:
        """
        Report size-based progress.

        Args:
            processed_bytes: Bytes processed so far
            total_bytes: Total bytes to process
            current_file: Name of file currently being processed
        """
        ...


class ProgressSignals(QObject):
    """
    Standard progress signals mixin for Qt workers.

    Workers should inherit from both QObject and this mixin (or just include these signals).

    Usage:
        class MyWorker(QObject):
            # Include standard progress signals
            progress = pyqtSignal(int, int, str)  # current, total, message
            size_progress = pyqtSignal(int, int, str)  # processed_bytes, total_bytes, filename
            status_message = pyqtSignal(str)  # status updates

            def run(self):
                for i, item in enumerate(items):
                    # Report progress
                    self.progress.emit(i + 1, len(items), f"Processing {item}")
                    # ... do work ...

    Signal Specifications:
        progress: Standard item-based progress
            - Arg 1 (int): Current item number (1-based)
            - Arg 2 (int): Total items
            - Arg 3 (str): Optional status message

        size_progress: Byte-level progress for file operations
            - Arg 1 (int): Processed bytes
            - Arg 2 (int): Total bytes
            - Arg 3 (str): Current filename

        status_message: General status updates
            - Arg 1 (str): Status message
    """

    # Standard item-based progress (current, total, message)
    progress = pyqtSignal(int, int, str)

    # Size-based progress for file operations (processed_bytes, total_bytes, filename)
    size_progress = pyqtSignal(int, int, str)

    # General status updates
    status_message = pyqtSignal(str)


def create_progress_callback(
    progress_signal=None, size_signal=None
) -> tuple[ProgressCallback | None, SizeProgressCallback | None]:
    """
    Create callback functions from Qt signals.

    Helper function to bridge Qt signals to callback functions.

    Args:
        progress_signal: PyQt signal for item progress
        size_signal: PyQt signal for size progress
        status_signal: PyQt signal for status updates

    Returns:
        Tuple of (progress_callback, size_callback)

    Example:
        worker = MyWorker()
        progress_cb, size_cb = create_progress_callback(
            progress_signal=worker.progress,
            size_signal=worker.size_progress
        )

        # Now use callbacks in non-Qt code
        for i, item in enumerate(items):
            if progress_cb:
                progress_cb(i + 1, len(items), f"Processing {item}")
    """
    progress_callback = None
    size_callback = None

    if progress_signal:

        def _progress_cb(current: int, total: int, message: str = "") -> None:
            progress_signal.emit(current, total, message)

        progress_callback = _progress_cb

    if size_signal:

        def _size_cb(processed_bytes: int, total_bytes: int, current_file: str = "") -> None:
            size_signal.emit(processed_bytes, total_bytes, current_file)

        size_callback = _size_cb

    return progress_callback, size_callback


def format_progress_message(
    current: int, total: int, operation: str = "Processing", item_name: str = ""
) -> str:
    """
    Format a standard progress message.

    Args:
        current: Current item number
        total: Total items
        operation: Operation description (e.g., "Loading", "Processing")
        item_name: Optional name of current item

    Returns:
        Formatted progress string

    Example:
        >>> format_progress_message(5, 10, "Loading", "image.jpg")
        'Loading 5/10: image.jpg'
        >>> format_progress_message(7, 20, "Processing")
        'Processing 7/20'
    """
    if item_name:
        return f"{operation} {current}/{total}: {item_name}"
    return f"{operation} {current}/{total}"


def format_size_progress(processed_bytes: int, total_bytes: int, include_percent: bool = True) -> str:
    """
    Format size-based progress as human-readable string.

    Args:
        processed_bytes: Bytes processed
        total_bytes: Total bytes
        include_percent: Include percentage in output

    Returns:
        Formatted size progress string

    Example:
        >>> format_size_progress(5242880, 10485760)
        '5.00 MB / 10.00 MB (50.0%)'
        >>> format_size_progress(1024, 2048, include_percent=False)
        '1.00 KB / 2.00 KB'
    """
    def format_bytes(size: int) -> str:
        """Format bytes as human-readable."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"

    processed_str = format_bytes(processed_bytes)
    total_str = format_bytes(total_bytes)

    if include_percent and total_bytes > 0:
        percent = (processed_bytes / total_bytes) * 100.0
        return f"{processed_str} / {total_str} ({percent:.1f}%)"

    return f"{processed_str} / {total_str}"


# Type aliases for convenience
ProgressCallbackType = ProgressCallback
SizeProgressCallbackType = SizeProgressCallback

