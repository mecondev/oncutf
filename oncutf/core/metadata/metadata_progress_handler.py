"""
Module: metadata_progress_handler.py

Author: Michael Economou
Date: 2025-12-21

Progress dialog handler for metadata and hash operations.
Extracted from unified_metadata_manager.py for better separation of concerns.

Responsibilities:
- Create and manage progress dialogs for metadata loading
- Create and manage progress dialogs for hash calculation
- Handle progress callbacks and updates
- Handle cancellation requests
"""
from __future__ import annotations

import contextlib
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from oncutf.utils.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.models.file_item import FileItem
    from oncutf.utils.progress_dialog import ProgressDialog

logger = get_cached_logger(__name__)


class MetadataProgressHandler:
    """
    Handler for progress dialogs during metadata and hash operations.

    This class encapsulates all progress-related logic that was previously
    in UnifiedMetadataManager, including:
    - Creating metadata progress dialogs
    - Creating hash progress dialogs
    - Progress callbacks
    - Cancellation handling
    """

    def __init__(self, parent_window: Any = None) -> None:
        """
        Initialize progress handler.

        Args:
            parent_window: Reference to the main application window
        """
        self._parent_window = parent_window

        # Progress dialogs (kept as instance variables to prevent garbage collection)
        self._metadata_progress_dialog: ProgressDialog | None = None
        self._hash_progress_dialog: ProgressDialog | None = None

    @property
    def parent_window(self) -> Any:
        """Get parent window."""
        return self._parent_window

    @parent_window.setter
    def parent_window(self, value: Any) -> None:
        """Set parent window."""
        self._parent_window = value

    # =========================================================================
    # Metadata Progress Dialog
    # =========================================================================

    def create_metadata_progress_dialog(
        self,
        is_extended: bool,
        cancel_callback: Callable[[], None] | None = None,
    ) -> ProgressDialog:
        """
        Create a progress dialog for metadata loading.

        Args:
            is_extended: Whether loading extended metadata
            cancel_callback: Callback to invoke when user cancels

        Returns:
            ProgressDialog instance
        """
        from oncutf.utils.progress_dialog import ProgressDialog

        self._metadata_progress_dialog = ProgressDialog.create_metadata_dialog(
            self._parent_window,
            is_extended=is_extended,
            cancel_callback=cancel_callback,
        )
        return self._metadata_progress_dialog

    def show_metadata_progress_dialog(
        self,
        files: list[FileItem],
        is_extended: bool,
        cancel_callback: Callable[[], None] | None = None,
    ) -> ProgressDialog | None:
        """
        Create and show a progress dialog for metadata loading.

        Args:
            files: List of files being processed
            is_extended: Whether loading extended metadata
            cancel_callback: Callback to invoke when user cancels

        Returns:
            ProgressDialog instance or None on error
        """
        try:
            from oncutf.core.pyqt_imports import QApplication
            from oncutf.utils.dialog_utils import show_dialog_smooth
            from oncutf.utils.file_size_calculator import calculate_files_total_size

            # Create dialog
            dialog = self.create_metadata_progress_dialog(is_extended, cancel_callback)

            # Set initial status
            status_text = "Loading extended metadata..." if is_extended else "Loading metadata..."
            dialog.set_status(status_text)

            # Show dialog smoothly
            show_dialog_smooth(dialog)
            dialog.activateWindow()
            dialog.setFocus()
            dialog.raise_()

            # Process events to ensure dialog is visible
            for _ in range(3):
                QApplication.processEvents()

            # Calculate total size for progress tracking
            total_size = calculate_files_total_size(files)
            dialog.start_progress_tracking(total_size)

            return dialog

        except Exception:
            logger.exception("[MetadataProgressHandler] Error showing metadata progress dialog")
            return None

    def close_metadata_progress_dialog(self) -> None:
        """Close the metadata progress dialog if open."""
        if self._metadata_progress_dialog:
            with contextlib.suppress(Exception):
                self._metadata_progress_dialog.close()
            self._metadata_progress_dialog = None

    # =========================================================================
    # Hash Progress Dialog
    # =========================================================================

    def create_hash_progress_dialog(
        self,
        cancel_callback: Callable[[], None] | None = None,
    ) -> ProgressDialog:
        """
        Create a progress dialog for hash calculation.

        Args:
            cancel_callback: Callback to invoke when user cancels

        Returns:
            ProgressDialog instance
        """
        from oncutf.utils.progress_dialog import ProgressDialog

        self._hash_progress_dialog = ProgressDialog.create_hash_dialog(
            self._parent_window,
            cancel_callback=cancel_callback,
        )
        return self._hash_progress_dialog

    def show_hash_progress_dialog(
        self,
        files: list[FileItem],
        cancel_callback: Callable[[], None] | None = None,
    ) -> ProgressDialog | None:
        """
        Create and show a progress dialog for hash calculation.

        Args:
            files: List of files being processed
            cancel_callback: Callback to invoke when user cancels

        Returns:
            ProgressDialog instance or None on error
        """
        try:
            from oncutf.core.pyqt_imports import QApplication
            from oncutf.utils.file_size_calculator import calculate_files_total_size

            # Create dialog
            dialog = self.create_hash_progress_dialog(cancel_callback)

            # Set initial status
            dialog.set_status("Calculating file hashes...")

            # Show dialog
            dialog.show()

            # Process events
            QApplication.processEvents()

            # Calculate total size
            total_size = calculate_files_total_size(files)
            dialog.start_progress_tracking(total_size)

            return dialog

        except Exception:
            logger.exception("[MetadataProgressHandler] Error showing hash progress dialog")
            return None

    def close_hash_progress_dialog(self) -> None:
        """Close the hash progress dialog if open."""
        if self._hash_progress_dialog:
            with contextlib.suppress(Exception):
                self._hash_progress_dialog.close()
            self._hash_progress_dialog = None

    # =========================================================================
    # Progress Callbacks
    # =========================================================================

    def update_metadata_progress(
        self,
        current: int,
        total: int,
        processed_bytes: int = 0,
        total_bytes: int = 0,
        filename: str = "",
    ) -> None:
        """
        Update metadata progress dialog.

        Args:
            current: Current file index
            total: Total file count
            processed_bytes: Bytes processed so far
            total_bytes: Total bytes to process
            filename: Current filename being processed
        """
        if not self._metadata_progress_dialog:
            return

        try:
            self._metadata_progress_dialog.update_progress(
                file_count=current,
                total_files=total,
                processed_bytes=processed_bytes,
                total_bytes=total_bytes,
            )
            if filename:
                self._metadata_progress_dialog.set_filename(filename)
            self._metadata_progress_dialog.set_count(current, total)
        except Exception:
            logger.warning(
                "[MetadataProgressHandler] Error updating metadata progress",
                exc_info=True,
            )

    def update_hash_progress(
        self,
        current: int,
        total: int,
        processed_bytes: int = 0,
        total_bytes: int = 0,
    ) -> None:
        """
        Update hash progress dialog.

        Args:
            current: Current file index
            total: Total file count
            processed_bytes: Bytes processed so far
            total_bytes: Total bytes to process
        """
        if not self._hash_progress_dialog:
            return

        try:
            self._hash_progress_dialog.update_progress(current, total)
            if processed_bytes and total_bytes:
                self._hash_progress_dialog.set_size_info(processed_bytes, total_bytes)
        except Exception:
            logger.warning(
                "[MetadataProgressHandler] Error updating hash progress",
                exc_info=True,
            )

    # =========================================================================
    # Cleanup
    # =========================================================================

    def cleanup(self) -> None:
        """Clean up all progress dialogs."""
        self.close_metadata_progress_dialog()
        self.close_hash_progress_dialog()
