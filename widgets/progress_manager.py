"""
Module: progress_manager.py

Author: Michael Economou
Date: 2025-06-25

Unified Progress Manager for all file operations.

This module provides a centralized, consistent API for progress tracking across
all file operations (hashing, metadata, copy operations, etc.).

Key Features:
- Unified API for all progress operations
- Automatic mode selection based on operation type
- Built-in support for size-based and count-based progress
- Consistent throttling and performance optimization
- Ready for future operations (copy, move, etc.)

Usage Examples:

1. Hash operations:
    manager = ProgressManager("hash", parent)
    manager.start_tracking(total_size=1000000000)
    manager.update_progress(processed_bytes=500000000)

2. Metadata operations:
    manager = ProgressManager("metadata", parent)
    manager.start_tracking(total_files=100)
    manager.update_progress(file_count=50)

3. Copy operations (future):
    manager = ProgressManager("copy", parent)
    manager.start_tracking(total_size=500000000)
    manager.update_progress(processed_bytes=250000000)
"""

from core.pyqt_imports import QWidget
from utils.logger_factory import get_cached_logger
from widgets.progress_widget import ProgressWidget, create_size_based_progress_widget

logger = get_cached_logger(__name__)


class ProgressManager:
    """
    Unified progress manager for all file operations.

    Provides a consistent API for progress tracking across different operation types:
    - hash: Size-based progress with real-time tracking
    - metadata: Count-based progress with optional size tracking
    - copy: Size-based progress for file operations (future)
    """

    SUPPORTED_OPERATIONS = ["hash", "metadata", "copy"]

    def __init__(self, operation_type: str, parent: QWidget | None = None):
        """
        Initialize ProgressManager for specific operation type.

        Args:
            operation_type: Type of operation ("hash", "metadata", "copy")
            parent: Parent widget for the progress widget
        """
        if operation_type not in self.SUPPORTED_OPERATIONS:
            raise ValueError(
                f"Unsupported operation type: {operation_type}. "
                f"Supported: {self.SUPPORTED_OPERATIONS}"
            )

        self.operation_type = operation_type
        self.parent = parent
        self.progress_widget: ProgressWidget  # Type annotation to fix linter errors
        self._is_tracking = False

        # Create appropriate progress widget based on operation type
        self._create_progress_widget()

        logger.debug(f"[ProgressManager] Initialized for {operation_type} operations")

    def _create_progress_widget(self):
        """Create the appropriate progress widget based on operation type."""
        if self.operation_type == "hash":
            # Hash operations: size-based progress with full tracking
            self.progress_widget = create_size_based_progress_widget(parent=self.parent)
        elif self.operation_type == "metadata":
            # Metadata operations: count-based with optional size tracking
            self.progress_widget = ProgressWidget(
                parent=self.parent, progress_mode="count", show_size_info=True, show_time_info=True
            )
        elif self.operation_type == "copy":
            # Copy operations: size-based progress (future)
            self.progress_widget = create_size_based_progress_widget(parent=self.parent)

    def start_tracking(self, total_size: int = 0, total_files: int = 0):
        """
        Start progress tracking with appropriate parameters.

        Args:
            total_size: Total bytes to process (for size-based operations)
            total_files: Total files to process (for count-based operations)
        """
        if self._is_tracking:
            logger.warning("[ProgressManager] Already tracking progress, resetting...")
            self.reset()

        self._is_tracking = True

        if self.operation_type in ["hash", "copy"]:
            # Size-based operations
            if total_size <= 0:
                logger.warning(
                    f"[ProgressManager] {self.operation_type} operation requires total_size > 0"
                )
                return
            self.progress_widget.start_progress_tracking(total_size)
            logger.debug(
                f"[ProgressManager] Started {self.operation_type} tracking: {total_size:,} bytes"
            )

        elif self.operation_type == "metadata":
            # Count-based operations with optional size tracking
            if total_files > 0:
                self.progress_widget.set_count(0, total_files)
            if total_size > 0:
                self.progress_widget.start_progress_tracking(total_size)
            logger.debug(
                f"[ProgressManager] Started metadata tracking: {total_files} files, {total_size:,} bytes"
            )

    def update_progress(
        self,
        file_count: int = 0,
        total_files: int = 0,
        processed_bytes: int = 0,
        total_bytes: int = 0,
        filename: str = "",
        status: str = "",
    ):
        """
        Update progress with unified API.

        This method automatically selects the appropriate progress calculation
        based on the operation type and provided parameters.

        Args:
            file_count: Current number of files processed
            total_files: Total number of files to process
            processed_bytes: Current bytes processed (cumulative)
            total_bytes: Total bytes to process (optional, uses stored value if 0)
            filename: Current filename being processed
            status: Status message to display
        """
        if not self._is_tracking:
            logger.warning("[ProgressManager] Not tracking progress, call start_tracking() first")
            return

        # Update status if provided
        if status:
            self.progress_widget.set_status(status)

        # Update filename if provided
        if filename:
            self.progress_widget.set_filename(filename)

        # Update progress based on operation type
        if self.operation_type in ["hash", "copy"]:
            # Size-based operations
            if processed_bytes > 0:
                self.progress_widget.update_progress(
                    processed_bytes=processed_bytes, total_bytes=total_bytes
                )
            elif file_count > 0 and total_files > 0:
                # Fallback to count-based if no size data
                self.progress_widget.update_progress(file_count=file_count, total_files=total_files)

        elif self.operation_type == "metadata":
            # Count-based operations with optional size tracking
            self.progress_widget.update_progress(
                file_count=file_count,
                total_files=total_files,
                processed_bytes=processed_bytes,
                total_bytes=total_bytes,
            )

    def set_indeterminate_mode(self):
        """Set progress to indeterminate/animated mode."""
        self.progress_widget.set_indeterminate_mode()

    def set_determinate_mode(self):
        """Set progress back to determinate mode."""
        self.progress_widget.set_determinate_mode()

    def reset(self):
        """Reset progress tracking."""
        if self.progress_widget:
            self.progress_widget.reset()
        self._is_tracking = False
        logger.debug(f"[ProgressManager] Reset {self.operation_type} progress tracking")

    def get_widget(self) -> ProgressWidget:
        """Get the underlying progress widget."""
        return self.progress_widget

    def is_tracking(self) -> bool:
        """Check if progress tracking is active."""
        return self._is_tracking


# Factory functions for backward compatibility and convenience
def create_hash_progress_manager(parent: QWidget | None = None) -> ProgressManager:
    """Create a progress manager for hash operations."""
    return ProgressManager("hash", parent)


def create_metadata_progress_manager(parent: QWidget | None = None) -> ProgressManager:
    """Create a progress manager for metadata operations."""
    return ProgressManager("metadata", parent)


def create_copy_progress_manager(parent: QWidget | None = None) -> ProgressManager:
    """Create a progress manager for copy operations (future)."""
    return ProgressManager("copy", parent)
