"""
status_manager.py

Author: Michael Economou
Date: 2025-05-01

Manages status bar updates and UI feedback.
Provides clean, immediate status updates without fade effects.
"""

from typing import Optional

from config import STATUS_COLORS
from core.qt_imports import QTimer
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class StatusManager:
    """Manages status bar updates and UI feedback."""

    def __init__(self, status_label=None) -> None:
        """Initialize StatusManager with status label reference."""
        self.status_label = status_label
        self._status_timer: Optional[QTimer] = None
        logger.debug("[StatusManager] Initialized", extra={"dev_only": True})

    def set_status(self, text: str, color: str = "", auto_reset: bool = False, reset_delay: int = 3000) -> None:
        """
        Set status label text with optional color and auto-reset.

        Args:
            text: Status text to display
            color: Optional color (CSS color string)
            auto_reset: Whether to auto-reset to "Ready" after delay
            reset_delay: Delay in milliseconds before reset
        """
        if not self.status_label:
            logger.warning("[StatusManager] No status label set")
            return

        # Set text and color
        self.status_label.setText(text)
        if color:
            self.status_label.setStyleSheet(f"color: {color};")
        else:
            self.status_label.setStyleSheet("")

        # Handle auto-reset
        if auto_reset:
            self._start_auto_reset(reset_delay)

        logger.debug(f"[StatusManager] Status set: '{text}' (color: {color}, auto_reset: {auto_reset})")

    def set_ready(self) -> None:
        """Set status to 'Ready' with default styling."""
        self.set_status("Ready", color=STATUS_COLORS["ready"], auto_reset=False)

    def set_error(self, message: str, auto_reset: bool = True) -> None:
        """Set error status with red color."""
        self.set_status(message, color=STATUS_COLORS["error"], auto_reset=auto_reset)

    def set_success(self, message: str, auto_reset: bool = True) -> None:
        """Set success status with green color."""
        self.set_status(message, color=STATUS_COLORS["success"], auto_reset=auto_reset)

    def set_warning(self, message: str, auto_reset: bool = True) -> None:
        """Set warning status with orange color."""
        self.set_status(message, color=STATUS_COLORS["warning"], auto_reset=auto_reset)

    def set_info(self, message: str, auto_reset: bool = True) -> None:
        """Set info status with blue color."""
        self.set_status(message, color=STATUS_COLORS["info"], auto_reset=auto_reset)

    def set_loading(self, message: str = "Loading...") -> None:
        """Set loading status with gray color."""
        self.set_status(message, color=STATUS_COLORS["loading"], auto_reset=False)

    def _start_auto_reset(self, delay: int) -> None:
        """Start auto-reset timer."""
        # Stop existing timer if running
        if self._status_timer:
            self._status_timer.stop()
        else:
            self._status_timer = QTimer()

        # Setup timer
        self._status_timer.setSingleShot(True)
        self._status_timer.timeout.connect(self.set_ready)
        self._status_timer.start(delay)

    def stop_auto_reset(self) -> None:
        """Stop any running auto-reset timer."""
        if self._status_timer:
            self._status_timer.stop()

    def update_files_label(self, files_label, total_files: int, selected_files: int) -> None:
        """
        Update the files count label.

        Args:
            files_label: The QLabel widget to update
            total_files: Total number of files loaded
            selected_files: Number of selected files
        """
        if not files_label:
            return

        if total_files == 0:
            files_label.setText("Files (0)")
        else:
            files_label.setText(f"Files ({total_files} loaded, {selected_files} selected)")

        logger.debug(f"[StatusManager] Files label updated: {total_files} total, {selected_files} selected")

    def clear_file_table_status(self, files_label, message: str = "No folder selected") -> None:
        """
        Update status when file table is cleared.

        Args:
            files_label: The files count label to update
            message: Status message to display
        """
        if files_label:
            files_label.setText("Files (0)")

        self.set_status(message, color=STATUS_COLORS["loading"], auto_reset=False)

    def show_metadata_status(self, num_files: int, skip_metadata_mode: bool, force_extended_metadata: bool) -> None:
        """
        Show status bar message indicating loaded files and metadata scan type.

        Args:
            num_files: Number of loaded files
            skip_metadata_mode: Whether metadata was skipped
            force_extended_metadata: Whether extended metadata was used
        """
        if skip_metadata_mode:
            status_msg = f"Loaded {num_files} files — metadata skipped"
            color = STATUS_COLORS["metadata_skipped"]
        elif force_extended_metadata:
            status_msg = f"Loaded {num_files} files — metadata (extended)"
            color = STATUS_COLORS["metadata_extended"]
        else:
            status_msg = f"Loaded {num_files} files — metadata (basic)"
            color = STATUS_COLORS["metadata_basic"]

        self.set_status(status_msg, color=color, auto_reset=True)

    def update_status_from_preview(self, status_html: str) -> None:
        """
        Update status from preview generation.

        Args:
            status_html: HTML status text from preview
        """
        if not self.status_label:
            return

        self.status_label.setText(status_html)
        logger.debug(f"[StatusManager] Status updated from preview: {status_html[:50]}...")
