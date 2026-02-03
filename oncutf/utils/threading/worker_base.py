"""Qt-free worker base class for background operations.

Author: Michael Economou
Date: 2026-02-03

Provides a QThread-compatible interface using standard threading.Thread.
This allows core modules to run background operations without Qt dependency.
"""

import threading
from abc import abstractmethod
from typing import Any

from oncutf.utils.events import Observable, Signal
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class WorkerBase(threading.Thread):
    """Base class for background workers.

    Provides QThread-like interface using standard threading.Thread.
    Subclasses must implement run() method.

    Signals (Observable descriptors):
    - finished_processing: Emitted when worker completes (args: success)
    - status_updated: Emitted for status messages (args: message)
    - progress_updated: Emitted for progress updates (args: current, total, info)

    Usage:
        class MyWorker(WorkerBase):
            def run(self):
                # Do background work
                self.status_updated.emit("Working...")
                self.finished_processing.emit(True)

        worker = MyWorker()
        worker.finished_processing.connect(on_finished)
        worker.start()
    """

    # Observable signals (no type parameters at runtime)
    finished_processing = Signal()
    status_updated = Signal()
    progress_updated = Signal()

    def __init__(self, parent: Any = None, daemon: bool = True) -> None:
        """Initialize worker.

        Args:
            parent: Parent object (for compatibility with QThread API, ignored)
            daemon: Whether thread should be daemon (default True)

        """
        super().__init__(daemon=daemon)
        self._parent = parent
        self._cancel_lock = threading.Lock()
        self._cancelled = False

        # Initialize Observable mixin
        Observable.__init__(self)

    def request_cancellation(self) -> None:
        """Request worker to cancel operation (thread-safe)."""
        with self._cancel_lock:
            self._cancelled = True
            logger.debug("[%s] Cancellation requested", self.__class__.__name__)

    def is_cancelled(self) -> bool:
        """Check if cancellation was requested (thread-safe).

        Returns:
            True if cancellation requested, False otherwise

        """
        with self._cancel_lock:
            return self._cancelled

    @abstractmethod
    def run(self) -> None:
        """Main worker execution method.

        Must be implemented by subclasses.
        Should periodically check is_cancelled() and exit early if True.
        """
        ...

    def isRunning(self) -> bool:
        """Check if worker thread is running (QThread compatibility).

        Returns:
            True if thread is alive, False otherwise

        """
        return self.is_alive()

    def wait(self, timeout: float | None = None) -> bool:
        """Wait for worker to finish (QThread compatibility).

        Args:
            timeout: Maximum time to wait in seconds (None = wait forever)

        Returns:
            True if thread finished, False if timeout occurred

        """
        self.join(timeout=timeout)
        return not self.is_alive()
