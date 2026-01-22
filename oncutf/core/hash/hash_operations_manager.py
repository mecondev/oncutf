"""Hash Operations Management Service.

Author: Michael Economou
Date: 2025-06-15 (Refactored: 2026-01-15)

Orchestrates hash-related operations for file duplicate detection, comparison, and checksum calculations.

This module uses HashLoadingService for all hash operations:
- Duplicate file detection within selected or all files
- External folder comparison for finding matching/different files
- CRC32 checksum calculation with progress tracking

Refactored 2026-01-15: Migrated from HashWorkerCoordinator to unified HashLoadingService
for consistent callback architecture across all hash operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QWidget

from oncutf.config import STATUS_COLORS
from oncutf.core.hash.hash_results_presenter import HashResultsPresenter
from oncutf.models.file_item import FileItem
from oncutf.utils.filesystem.file_status_helpers import has_hash
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class HashOperationsManager:
    """Orchestrates hash-related operations using unified HashLoadingService.

    This manager uses HashLoadingService for all hash loading operations,
    providing a consistent callback architecture for duplicates, comparison,
    and checksum operations.

    Delegates to:
    - HashLoadingService: Unified hash operations with progress tracking
    - HashResultsPresenter: UI presentation and dialogs
    """

    def __init__(self, parent_window: QWidget) -> None:
        """Initialize the hash operations manager.

        Args:
            parent_window: Reference to the main window for accessing models, views, and managers

        """
        self.parent_window: Any = parent_window

        # Use unified HashLoadingService for all operations
        from oncutf.core.metadata.hash_loading_service import HashLoadingService

        self._hash_service = HashLoadingService(parent_window, cache_service=None)
        self._results_presenter = HashResultsPresenter(parent_window)

        logger.debug("HashOperationsManager initialized", extra={"dev_only": True})

    # ===== Public Interface Methods =====

    def handle_find_duplicates(self, selected_files: list[FileItem] | None) -> None:
        """Handle duplicate file detection.

        Searches for files with identical CRC32 hashes within the selected files
        or all files in the current folder.

        Args:
            selected_files: List of FileItem objects to search, or None for all files

        """
        self._handle_find_duplicates(selected_files)

    def handle_compare_external(self, selected_files: list[FileItem]) -> None:
        """Handle comparison of selected files with an external folder.

        Args:
            selected_files: List of FileItem objects to compare

        """
        self._handle_compare_external(selected_files)

    def handle_calculate_hashes(self, selected_files: list[FileItem]) -> None:
        """Handle calculating and displaying checksums for selected files.

        Args:
            selected_files: List of FileItem objects to calculate hashes for

        """
        self._handle_calculate_hashes(selected_files)

    def check_files_have_hashes(self, files: list[FileItem] | None = None) -> bool:
        """Check if specified files or all files have hash values.

        Args:
            files: List of FileItem objects to check, or None for all files

        Returns:
            bool: True if any files have hashes, False otherwise

        """
        return self._check_files_have_hashes(files)

    def get_files_without_hashes(self) -> list[FileItem]:
        """Get list of files that don't have hash values yet.

        Returns:
            list: FileItem objects without hashes

        """
        if (
            not hasattr(self.parent_window, "file_model")
            or not self.parent_window.file_model
        ):
            return []

        all_files = self.parent_window.file_model.get_all_file_items()
        return [f for f in all_files if not self._file_has_hash(f)]

    # ===== Hash Operation Workflow =====

    def _handle_find_duplicates(self, selected_files: list[FileItem] | None) -> None:
        """Handle duplicate file detection in selected or all files.

        Args:
            selected_files: List of FileItem objects to search, or None for all files

        """
        # Determine scope
        if selected_files:
            scope = "selected"
            files_to_check = selected_files
        else:
            scope = "all"
            if (
                not hasattr(self.parent_window, "file_model")
                or not self.parent_window.file_model
            ):
                logger.warning("[HashManager] No file model available")
                return
            files_to_check = self.parent_window.file_model.get_all_file_items()

        if not files_to_check:
            logger.warning("[HashManager] No files to check for duplicates (scope: %s)", scope)
            return

        logger.info(
            "[HashManager] Finding duplicates in %d files (scope: %s)",
            len(files_to_check),
            scope,
        )

        # Convert FileItem objects to file paths
        file_paths = [item.full_path for item in files_to_check]

        # Start hash operation using unified HashLoadingService
        self._hash_service.start_duplicate_scan(
            file_paths,
            scope=scope,
            on_duplicates=self._on_duplicates_found,
            on_progress=self._update_operation_progress,
            on_file_hash=self._on_file_hash_calculated,
            on_finished=self._on_hash_operation_finished,
            on_error=self._on_hash_operation_error,
        )

    def _handle_compare_external(self, selected_files: list[FileItem]) -> None:
        """Handle comparison of selected files with an external folder.

        Args:
            selected_files: List of FileItem objects to compare

        """
        if not selected_files:
            logger.warning("[HashManager] No files selected for external comparison")
            return

        try:
            # Import Qt components

            # Show folder picker dialog
            from oncutf.app.services.folder_selection import select_folder

            external_folder = select_folder(
                self.parent_window,
                "Select folder to compare with",
                "",
            )

            if not external_folder:
                logger.debug(
                    "[HashManager] User cancelled external folder selection",
                    extra={"dev_only": True},
                )
                return

            logger.info(
                "[HashManager] Comparing %d files with %s",
                len(selected_files),
                external_folder,
            )

            # Convert FileItem objects to file paths
            file_paths = [item.full_path for item in selected_files]

            # Start hash operation using unified HashLoadingService
            self._hash_service.start_external_comparison(
                file_paths,
                external_folder,
                on_comparison=self._on_comparison_result,
                on_progress=self._update_operation_progress,
                on_file_hash=self._on_file_hash_calculated,
                on_finished=self._on_hash_operation_finished,
                on_error=self._on_hash_operation_error,
            )

        except Exception as e:
            logger.error("[HashManager] Error setting up external comparison: %s", e)
            from oncutf.ui.dialogs.custom_message_dialog import CustomMessageDialog

            CustomMessageDialog.information(
                self.parent_window,
                "Error",
                f"Failed to start external comparison: {str(e)}",
            )

    def _handle_calculate_hashes(self, selected_files: list[FileItem]) -> None:
        """Handle calculating and displaying checksums for selected files.

        Args:
            selected_files: List of FileItem objects to calculate hashes for

        """
        if not selected_files:
            logger.warning("[HashManager] No files selected for checksum calculation")
            return

        logger.info("[HashManager] Calculating checksums for %d files", len(selected_files))

        # Convert FileItem objects to file paths
        file_paths = [item.full_path for item in selected_files]

        if len(file_paths) == 1:
            # Single file - use wait cursor (fast, simple)
            self._calculate_single_file_hash_fast(selected_files[0])
        else:
            # Multiple files - use HashLoadingService with progress dialog
            self._hash_service.start_checksum_calculation(
                file_paths,
                on_checksums=self._on_checksums_calculated,
                on_progress=self._update_operation_progress,
                on_file_hash=self._on_file_hash_calculated,
                on_finished=self._on_hash_operation_finished,
                on_error=self._on_hash_operation_error,
            )

    def _calculate_single_file_hash_fast(self, file_item: FileItem) -> None:
        """Calculate hash for a single small file using wait cursor (fast, no cancellation).

        Args:
            file_item: FileItem object to calculate hash for

        """
        from oncutf.app.services import wait_cursor
        from oncutf.core.hash.hash_manager import HashManager

        try:
            hash_results = {}
            with wait_cursor():
                hash_manager = HashManager()
                file_hash = hash_manager.calculate_hash(file_item.full_path)

                if file_hash:
                    hash_results[file_item.full_path] = file_hash

            # Show results after cursor is restored
            # Wrap flat dict into nested structure expected by results presenter
            wrapped_results: dict[str, dict[str, str]] = {
                path: {"hash": hash_val} for path, hash_val in hash_results.items()
            }
            self._results_presenter.show_hash_results(wrapped_results)

        except Exception as e:
            logger.error("[HashManager] Error calculating checksum: %s", e)
            from oncutf.ui.dialogs.custom_message_dialog import CustomMessageDialog

            CustomMessageDialog.information(
                self.parent_window, "Error", f"Failed to calculate checksum: {str(e)}"
            )

    # ===== Worker Callbacks =====

    def _update_operation_progress(self, current: int, total: int, message: str) -> None:
        """Update operation progress - handled by HashLoadingService.

        This callback is kept for logging purposes; actual progress updates
        are handled internally by HashLoadingService.

        Args:
            current: Current progress value
            total: Total progress value
            message: Progress message to display

        """
        logger.debug(
            "[HashManager] Progress: %d/%d - %s",
            current,
            total,
            message,
            extra={"dev_only": True},
        )

    def _on_file_hash_calculated(self, file_path: str, hash_value: str, _size: int = 0) -> None:
        """Handle individual file hash calculation completion.

        Args:
            file_path: Path to the file
            hash_value: Calculated hash value
            _size: File size (unused, for callback compatibility)

        """
        # Update file table view to show new hash
        if (
            hasattr(self.parent_window, "file_table_view")
            and self.parent_window.file_table_view
        ):
            try:
                from oncutf.core.application_context import get_app_context
                from oncutf.core.pyqt_imports import Qt

                file_store = get_app_context().file_store
                model = self.parent_window.file_table_view.model()

                if model and file_store:
                    # Find the row for this file
                    file_items = file_store.get_loaded_files()
                    for row, file_item in enumerate(file_items):
                        if file_item.full_path == file_path:
                            # Emit dataChanged for the entire row to refresh hash column
                            left_index = model.index(row, 0)
                            right_index = model.index(row, model.columnCount() - 1)
                            model.dataChanged.emit(left_index, right_index, [Qt.DisplayRole])

                            # Force immediate repaint
                            from oncutf.core.pyqt_imports import QApplication
                            app_instance = QApplication.instance()
                            if app_instance:
                                app_instance.processEvents()
                            break

            except Exception as e:
                logger.debug(
                    "[HashManager] Could not refresh file item UI: %s",
                    e,
                    extra={"dev_only": True}
                )

        logger.debug(
            "[HashManager] File hash calculated: %s -> %s",
            file_path,
            hash_value[:16] if hash_value else "Error",
            extra={"dev_only": True},
        )

    def _on_duplicates_found(
        self, duplicates: dict[str, list[FileItem]], scope: str
    ) -> None:
        """Handle duplicate detection results.

        Args:
            duplicates: Dictionary with hash as key and list of FileItem objects as value
            scope: Scope of the search ("selected" or "all")

        """
        self._results_presenter.show_duplicate_results(duplicates, scope)

    def _on_comparison_result(
        self, results: dict[str, Any], external_folder: str
    ) -> None:
        """Handle external comparison results.

        Args:
            results: Dictionary with comparison results
            external_folder: Path to the external folder

        """
        self._results_presenter.show_comparison_results(results, external_folder)

    def _on_checksums_calculated(
        self, hash_results: dict[str, dict[str, str]]
    ) -> None:
        """Handle checksum calculation results.

        Args:
            hash_results: Dictionary with file paths and hash values

        """
        # Force restore cursor before showing results dialog
        from oncutf.app.services import force_restore_cursor

        force_restore_cursor()

        # Check if operation was cancelled
        was_cancelled = self._hash_service.is_cancelled()

        self._results_presenter.show_hash_results(hash_results, was_cancelled)

        # Reset the cancellation flag
        self._hash_service.reset_cancelled()

    def _on_hash_operation_finished(self, _success: bool) -> None:
        """Handle hash operation completion.

        Args:
            _success: Whether the operation completed successfully

        """
        # Refresh file table icons to show new hash status
        if (
            hasattr(self.parent_window, "file_model")
            and self.parent_window.file_model
        ):
            if hasattr(self.parent_window.file_model, "refresh_icons"):
                self.parent_window.file_model.refresh_icons()
                logger.debug(
                    "[HashManager] Refreshed file table icons after hash operation",
                    extra={"dev_only": True},
                )

        # Notify preview manager about hash calculation completion
        if (
            hasattr(self.parent_window, "preview_manager")
            and self.parent_window.preview_manager
        ):
            self.parent_window.preview_manager.on_hash_calculation_completed()

    def _on_hash_operation_error(self, error_message: str) -> None:
        """Handle hash operation error.

        Args:
            error_message: Error message from the worker

        """
        logger.error("[HashManager] Hash operation error: %s", error_message)

        # Show error message
        from oncutf.ui.dialogs.custom_message_dialog import CustomMessageDialog

        CustomMessageDialog.information(
            self.parent_window, "Error", f"Hash operation failed: {error_message}"
        )

        # Update status
        if hasattr(self.parent_window, "set_status"):
            self.parent_window.set_status(
                "Hash operation failed",
                color=STATUS_COLORS["critical_error"],
                auto_reset=True,
            )

    # ===== Status Check Methods =====

    def _check_files_have_hashes(self, files: list[FileItem] | None = None) -> bool:
        """Check if any of the specified files have hash values.

        Args:
            files: List of FileItem objects to check, or None for all files

        Returns:
            bool: True if any files have hashes, False otherwise

        """
        if files is None:
            # Check all files
            if (
                not hasattr(self.parent_window, "file_model")
                or not self.parent_window.file_model
            ):
                return False
            files = self.parent_window.file_model.get_all_file_items()

        if not files:
            return False

        # Check if any file has a hash
        return any(self._file_has_hash(file_item) for file_item in files)

    def _file_has_hash(self, file_item: FileItem) -> bool:
        """Check if a specific file has a hash value."""
        return has_hash(file_item.full_path)
