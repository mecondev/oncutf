"""Qt signal proxy for thread-safe Observable signal forwarding.

Author: Michael Economou
Date: 2026-02-04

Provides thread-safe forwarding of Observable signals to Qt signals,
ensuring UI updates happen on the main Qt thread.
"""

from typing import Any

from PyQt5.QtCore import QObject, pyqtSignal

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class SignalProxy(QObject):
    """Proxy that forwards Observable signals to Qt signals safely.

    This allows worker threads to emit Observable signals which are
    then forwarded to Qt signals that execute callbacks on the main thread.

    Usage:
        proxy = SignalProxy()
        worker.status_updated.connect(proxy.forward_status)
        proxy.status_signal.connect(ui_callback)  # UI callback runs on main thread
    """

    # Qt signals (always execute on main thread via queued connection)
    status_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int, str)
    size_progress_signal = pyqtSignal(int, int)
    finished_signal = pyqtSignal(bool)
    error_signal = pyqtSignal(str)
    duplicates_signal = pyqtSignal(dict)
    checksums_signal = pyqtSignal(dict)
    file_hash_signal = pyqtSignal(str, str)
    comparison_signal = pyqtSignal(dict)

    def __init__(self, parent: QObject | None = None) -> None:
        """Initialize signal proxy.

        Args:
            parent: Parent QObject

        """
        super().__init__(parent)

    def forward_status(self, message: str) -> None:
        """Forward status message to Qt signal."""
        self.status_signal.emit(message)

    def forward_progress(self, current: int, total: int, info: str = "") -> None:
        """Forward progress update to Qt signal."""
        self.progress_signal.emit(current, total, info)

    def forward_size_progress(self, current_bytes: int, total_bytes: int) -> None:
        """Forward size progress to Qt signal."""
        self.size_progress_signal.emit(current_bytes, total_bytes)

    def forward_finished(self, success: bool) -> None:
        """Forward finished event to Qt signal."""
        self.finished_signal.emit(success)

    def forward_error(self, error_msg: str) -> None:
        """Forward error message to Qt signal."""
        self.error_signal.emit(error_msg)

    def forward_duplicates(self, duplicates: dict[str, list[str]]) -> None:
        """Forward duplicates result to Qt signal."""
        self.duplicates_signal.emit(duplicates)

    def forward_checksums(self, checksums: dict[str, str]) -> None:
        """Forward checksums result to Qt signal."""
        self.checksums_signal.emit(checksums)

    def forward_file_hash(self, file_path: str, hash_value: str) -> None:
        """Forward individual file hash to Qt signal."""
        self.file_hash_signal.emit(file_path, hash_value)

    def forward_comparison(self, results: dict[str, Any]) -> None:
        """Forward comparison results to Qt signal."""
        self.comparison_signal.emit(results)
