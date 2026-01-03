"""Module: base_worker.py

Author: Michael Economou
Date: 2026-01-03

Base worker protocol and mixin for Qt background workers.

This module provides:
- WorkerProtocol: Type-safe protocol for worker implementations
- CancellableMixin: Reusable cancellation logic for QThread/QObject workers

Usage:
    from oncutf.core.base_worker import CancellableMixin, WorkerProtocol

    class MyWorker(QThread, CancellableMixin):
        progress = pyqtSignal(int, str)
        finished_work = pyqtSignal(object)
        error = pyqtSignal(str)

        def __init__(self):
            QThread.__init__(self)
            CancellableMixin.__init__(self)

        def run(self):
            for i, item in enumerate(items):
                if self.is_cancelled:
                    return
                # process item...
                self.progress.emit(i, f"Processing {item}")
"""

from typing import Any, Protocol, runtime_checkable

from oncutf.core.pyqt_imports import QMutex, QMutexLocker


@runtime_checkable
class WorkerProtocol(Protocol):
    """Protocol defining the interface for background workers.

    Workers should emit these signals:
    - progress: Reports work progress (varies by implementation)
    - finished/finished_work: Reports completion with results
    - error: Reports errors that occurred during work

    Workers should support cancellation via:
    - request_cancel(): Request graceful cancellation
    - is_cancelled: Property to check cancellation status
    """

    def request_cancel(self) -> None:
        """Request graceful cancellation of the worker."""
        ...

    @property
    def is_cancelled(self) -> bool:
        """Check if cancellation has been requested."""
        ...


class CancellableMixin:
    """Mixin providing thread-safe cancellation support for workers.

    Provides:
    - Thread-safe cancellation flag with QMutex protection
    - request_cancel() method for external cancellation requests
    - is_cancelled property for checking status in work loops
    - reset_cancellation() for worker reuse

    Usage:
        class MyWorker(QThread, CancellableMixin):
            def __init__(self):
                QThread.__init__(self)
                CancellableMixin.__init__(self)

            def run(self):
                while not self.is_cancelled:
                    # do work...
                    pass

        # To cancel:
        worker.request_cancel()
    """

    def __init__(self) -> None:
        """Initialize cancellation state with mutex protection."""
        self._cancel_mutex = QMutex()
        self._cancelled = False

    def request_cancel(self) -> None:
        """Request graceful cancellation of the worker.

        Thread-safe method that sets the cancellation flag.
        The worker should check is_cancelled periodically and exit gracefully.
        """
        with QMutexLocker(self._cancel_mutex):
            self._cancelled = True

    @property
    def is_cancelled(self) -> bool:
        """Check if cancellation has been requested.

        Thread-safe property that reads the cancellation flag.

        Returns:
            True if cancellation was requested, False otherwise.

        """
        with QMutexLocker(self._cancel_mutex):
            return self._cancelled

    def reset_cancellation(self) -> None:
        """Reset cancellation state for worker reuse.

        Call this before restarting a worker that was previously cancelled.
        """
        with QMutexLocker(self._cancel_mutex):
            self._cancelled = False


class WorkerResult:
    """Container for worker execution results.

    Provides a structured way to return results from workers,
    including success status, data, and error information.
    """

    def __init__(
        self,
        success: bool = True,
        data: Any = None,
        error_message: str | None = None,
    ) -> None:
        """Initialize worker result.

        Args:
            success: Whether the work completed successfully.
            data: Result data (type varies by worker).
            error_message: Error message if success is False.

        """
        self.success = success
        self.data = data
        self.error_message = error_message

    def __bool__(self) -> bool:
        """Allow using result in boolean context."""
        return self.success

    def __repr__(self) -> str:
        """String representation for debugging."""
        if self.success:
            return f"WorkerResult(success=True, data={type(self.data).__name__})"
        return f"WorkerResult(success=False, error={self.error_message!r})"
