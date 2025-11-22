"""
Module: hash_operations_manager.py

Author: Michael Economou
Date: 2025-06-15

Manages hash-related operations for file duplicate detection, comparison, and checksum calculations.
Extracted from EventHandlerManager as part of Phase 3 refactoring.

Features:
- Duplicate file detection within selected or all files
- External folder comparison for finding matching/different files
- CRC32 checksum calculation with progress tracking
- Hash worker management with cancellation support
- Progress dialog coordination for long-running operations
"""

from config import STATUS_COLORS
from utils.file_status_helpers import has_hash
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class HashOperationsManager:
    """
    Manages all hash-related operations (duplicates, comparison, checksums).

    This manager handles:
    - Finding duplicate files based on CRC32 hashes
    - Comparing files with external folders
    - Calculating and displaying checksums
    - Managing hash worker threads and progress dialogs
    - Coordinating cancellation of long-running operations
    """

    def __init__(self, parent_window):
        """
        Initialize the hash operations manager.

        Args:
            parent_window: Reference to the main window for accessing models, views, and managers
        """
        self.parent_window = parent_window
        self.hash_worker = None
        self.hash_dialog = None
        self._operation_cancelled = False  # Track if operation was cancelled
        logger.debug("HashOperationsManager initialized", extra={"dev_only": True})

    # ===== Public Interface Methods =====

    def handle_find_duplicates(self, selected_files: list | None) -> None:
        """
        Handle duplicate file detection.

        Searches for files with identical CRC32 hashes within the selected files
        or all files in the current folder.

        Args:
            selected_files: List of FileItem objects to search, or None for all files
        """
        self._handle_find_duplicates(selected_files)

    def handle_compare_external(self, selected_files: list) -> None:
        """
        Handle comparison of selected files with an external folder.

        Args:
            selected_files: List of FileItem objects to compare
        """
        self._handle_compare_external(selected_files)

    def handle_calculate_hashes(self, selected_files: list) -> None:
        """
        Handle calculating and displaying checksums for selected files.

        Args:
            selected_files: List of FileItem objects to calculate hashes for
        """
        self._handle_calculate_hashes(selected_files)

    def check_files_have_hashes(self, files: list | None = None) -> bool:
        """
        Check if specified files or all files have hash values.

        Args:
            files: List of FileItem objects to check, or None for all files

        Returns:
            bool: True if any files have hashes, False otherwise
        """
        return self._check_files_have_hashes(files)

    def get_files_without_hashes(self) -> list:
        """
        Get list of files that don't have hash values yet.

        Returns:
            list: FileItem objects without hashes
        """
        if (
            not hasattr(self.parent_window, "file_table_model")
            or not self.parent_window.file_table_model
        ):
            return []

        all_files = self.parent_window.file_table_model.get_all_file_items()
        return [f for f in all_files if not self._file_has_hash(f)]

    # ===== Hash Operation Workflow =====

    def _handle_find_duplicates(self, selected_files: list | None) -> None:
        """
        Handle duplicate file detection in selected or all files.

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
                not hasattr(self.parent_window, "file_table_model")
                or not self.parent_window.file_table_model
            ):
                logger.warning("[HashManager] No file model available")
                return
            files_to_check = self.parent_window.file_table_model.get_all_file_items()

        if not files_to_check:
            logger.warning(f"[HashManager] No files to check for duplicates (scope: {scope})")
            return

        logger.info(
            f"[HashManager] Finding duplicates in {len(files_to_check)} files (scope: {scope})"
        )

        # Convert FileItem objects to file paths
        file_paths = [item.full_path for item in files_to_check]

        # Start hash operation using worker thread
        self._start_hash_operation("duplicates", file_paths)

    def _start_hash_operation(
        self,
        operation: str,
        file_paths: list,
        external_folder: str | None = None,
    ) -> None:
        """
        Start a hash operation using a worker thread with progress dialog.

        Args:
            operation: Type of operation ("duplicates", "compare", "checksums")
            file_paths: List of file paths to process
            external_folder: Folder path for comparison operation
        """
        from core.hash_worker import HashWorker
        from core.pyqt_imports import QMessageBox

        # Check if an operation is already running
        if self.hash_worker and self.hash_worker.isRunning():
            logger.warning("[HashManager] Hash operation already in progress")
            QMessageBox.information(
                self.parent_window,
                "Operation In Progress",
                "A hash operation is already running. Please wait for it to complete.",
            )
            return

        # Reset cancellation flag
        self._operation_cancelled = False

        # Create and configure worker
        self.hash_worker = HashWorker(parent=self.parent_window)

        # Configure based on operation type
        if operation == "duplicates":
            self.hash_worker.setup_duplicate_scan(file_paths)
        elif operation == "compare":
            self.hash_worker.setup_external_comparison(file_paths, external_folder)
        elif operation == "checksums":
            self.hash_worker.setup_checksum_calculation(file_paths)

        # Connect signals for progress updates
        self.hash_worker.progress_updated.connect(self._on_hash_progress_updated)
        self.hash_worker.size_progress.connect(self._on_size_progress_updated)
        self.hash_worker.file_hash_calculated.connect(self._on_file_hash_calculated)

        # Connect signals for results
        self.hash_worker.duplicates_found.connect(self._on_duplicates_found)
        self.hash_worker.comparison_result.connect(self._on_comparison_result)
        self.hash_worker.checksums_calculated.connect(self._on_checksums_calculated)

        # Connect signals for completion/error
        # Use the worker's `finished_processing` (bool) signal so the handler
        # receives the success flag. Do not connect QThread.finished here
        # because it emits no arguments and would cause a TypeError.
        if hasattr(self.hash_worker, "finished_processing"):
            self.hash_worker.finished_processing.connect(self._on_hash_operation_finished)
        else:
            # Fallback: connect QThread.finished with a wrapper that passes True
            self.hash_worker.finished.connect(lambda: self._on_hash_operation_finished(True))

        self.hash_worker.error_occurred.connect(self._on_hash_operation_error)

        # Create progress dialog
        self._create_hash_progress_dialog(operation, len(file_paths))

        # Start worker
        self.hash_worker.start()

        logger.info(
            f"[HashManager] Started hash operation: {operation} for {len(file_paths)} files"
        )

    def _create_hash_progress_dialog(self, _operation: str, file_count: int) -> None:
        """
        Create and show a progress dialog for hash operations.

        Args:
            operation: Type of operation for dialog title
            file_count: Number of files being processed
        """
        from utils.progress_dialog import ProgressDialog

        # Create dialog using the unified ProgressDialog for hash operations
        self.hash_dialog = ProgressDialog.create_hash_dialog(
            self.parent_window, cancel_callback=self._cancel_hash_operation, use_size_based_progress=True
        )
        # Initialize count and show
        self.hash_dialog.set_count(0, file_count)
        self.hash_dialog.show()

    def _cancel_hash_operation(self) -> None:
        """Cancel the current hash operation."""
        logger.info("[HashManager] User cancelled hash operation")

        # Set cancellation flag
        self._operation_cancelled = True

        # Tell worker to stop
        if self.hash_worker:
            self.hash_worker.cancel()

        # Update status
        if hasattr(self.parent_window, "set_status"):
            self.parent_window.set_status(
                "Hash operation cancelled", color=STATUS_COLORS["no_action"], auto_reset=True
            )

    def _on_hash_progress_updated(self, current: int, total: int, message: str) -> None:
        """
        Handle hash calculation progress updates.

        Args:
            current: Current file number
            total: Total number of files
            message: Status message
        """
        if hasattr(self, "hash_dialog") and self.hash_dialog:
            self.hash_dialog.set_count(current, total)
            self.hash_dialog.set_status(message)
    def _on_size_progress_updated(self, current_bytes: int, total_bytes: int) -> None:
        """
        Handle file size progress updates (for large files).

        Args:
            current_bytes: Bytes processed so far
            total_bytes: Total file size
        """
        if hasattr(self, "hash_dialog") and self.hash_dialog:
            # Ensure the dialog is configured for size-based tracking and
            # start progress tracking when we learn the total size.
            try:
                # If the dialog hasn't started progress tracking yet, start it
                if hasattr(self.hash_dialog, "start_progress_tracking"):
                    # Check if widget start_time is unset (not started)
                    wt = getattr(self.hash_dialog, "waiting_widget", None)
                    started = False
                    if wt is not None:
                        started = getattr(wt, "start_time", None) is not None

                    if total_bytes > 0 and not started:
                        # Initialize size-based tracking
                        self.hash_dialog.start_progress_tracking(total_bytes)
                        # Ensure progress widget is in size mode
                        if hasattr(wt, "set_progress_mode"):
                            wt.set_progress_mode("size")

                # Update unified progress dialog with cumulative sizes
                self.hash_dialog.update_progress(processed_bytes=current_bytes, total_bytes=total_bytes)
            except Exception as e:
                # Fallback to previous behavior on any error
                logger.debug(f"[HashManager] Error updating size progress: {e}")
                try:
                    self.hash_dialog.update_progress(current_bytes, total_bytes)
                except Exception:
                    pass

    def _on_file_hash_calculated(self, file_path: str) -> None:
        """
        Handle notification that a file's hash was calculated.
        Updates the file table icon in real-time.

        Args:
            file_path: Path to the file
            # Note: hash_value is not passed via signal; fetch from cache if needed
        """
        try:
            # Find FileItem in model
            if (
                not hasattr(self.parent_window, "file_table_model")
                or not self.parent_window.file_table_model
            ):
                return

            file_item = self.parent_window.file_table_model.find_file_by_path(file_path)
            if file_item:
                # Update hash icon immediately
                self.parent_window.file_table_model.update_file_hash_icon(file_item)

                # Try to obtain cached hash for logging
                try:
                    from core.hash_manager import HashManager

                    hm = HashManager()
                    cached = hm.get_cached_hash(file_path)
                    if cached:
                        logger.debug(
                            f"[HashWorker] Updated hash icon for {file_path}: {cached[:16]}...",
                            extra={"dev_only": True},
                        )
                    else:
                        logger.debug(
                            f"[HashWorker] Updated hash icon for {file_path}",
                            extra={"dev_only": True},
                        )
                except Exception:
                    logger.debug(
                        f"[HashWorker] Updated hash icon for {file_path}", extra={"dev_only": True}
                    )
        except Exception as e:
            logger.warning(f"[HashWorker] Error updating icon for {file_path}: {e}")

    # ===== Result Handlers =====

    def _on_duplicates_found(self, duplicates: dict, scope: str) -> None:
        """Handle duplicates found result."""
        self._show_duplicates_results(duplicates, scope)

    def _on_comparison_result(self, results: dict, external_folder: str) -> None:
        """Handle comparison result."""
        self._show_comparison_results(results, external_folder)

    def _on_checksums_calculated(self, hash_results: dict) -> None:
        """Handle checksums calculated result."""
        # Force restore cursor before showing results dialog
        from utils.cursor_helper import force_restore_cursor

        force_restore_cursor()

        # Check if this was a cancelled operation
        was_cancelled = self._operation_cancelled

        self._show_hash_results(hash_results, was_cancelled)

        # Reset the flag after showing results
        self._operation_cancelled = False

    def _on_hash_operation_finished(self, _success: bool) -> None:
        """Handle hash operation completion."""
        if hasattr(self, "hash_dialog") and self.hash_dialog:
            # Keep dialog visible for a moment to show completion
            from utils.timer_manager import schedule_dialog_close

            schedule_dialog_close(self.hash_dialog.close, 500)

        # Refresh file table icons to show new hash status
        if hasattr(self.parent_window, "file_table_model") and self.parent_window.file_table_model:
            if hasattr(self.parent_window.file_table_model, "refresh_icons"):
                self.parent_window.file_table_model.refresh_icons()
                logger.debug(
                    "[EventHandler] Refreshed file table icons after hash operation",
                    extra={"dev_only": True},
                )

        # Notify preview manager about hash calculation completion
        if hasattr(self.parent_window, "preview_manager") and self.parent_window.preview_manager:
            self.parent_window.preview_manager.on_hash_calculation_completed()

        # Clean up worker
        if hasattr(self, "hash_worker") and self.hash_worker:
            self.hash_worker.quit()
            self.hash_worker.wait()
            self.hash_worker = None

        # Reset operation cancelled flag
        self._operation_cancelled = False

    def _on_hash_operation_error(self, error_message: str) -> None:
        """Handle hash operation error."""
        logger.error(f"[HashManager] Hash operation error: {error_message}")

        # Close dialog
        if hasattr(self, "hash_dialog") and self.hash_dialog:
            self.hash_dialog.close()

        # Show error message
        from widgets.custom_message_dialog import CustomMessageDialog

        CustomMessageDialog.information(
            self.parent_window, "Error", f"Hash operation failed: {error_message}"
        )

        # Update status
        if hasattr(self.parent_window, "set_status"):
            self.parent_window.set_status(
                "Hash operation failed", color=STATUS_COLORS["critical_error"], auto_reset=True
            )

        # Clean up worker
        if hasattr(self, "hash_worker") and self.hash_worker:
            self.hash_worker.quit()
            self.hash_worker.wait()
            self.hash_worker = None

    # ===== UI Display Methods =====

    def _show_duplicates_results(self, duplicates: dict, scope: str) -> None:
        """
        Show duplicate detection results to the user.

        Args:
            duplicates: Dictionary with hash as key and list of duplicate FileItem objects as value
            scope: Either "selected" or "all" for display purposes
        """
        if not duplicates:
            from widgets.custom_message_dialog import CustomMessageDialog

            CustomMessageDialog.information(
                self.parent_window,
                "Duplicate Detection Results",
                f"No duplicates found in {scope} files.",
            )
            if hasattr(self.parent_window, "set_status"):
                self.parent_window.set_status(
                    f"No duplicates found in {scope} files",
                    color=STATUS_COLORS["operation_success"],
                    auto_reset=True,
                )
            return

        # Build results message
        duplicate_count = sum(len(files) for files in duplicates.values())
        duplicate_groups = len(duplicates)

        message_lines = [f"Found {duplicate_count} duplicate files in {duplicate_groups} groups:\n"]

        for i, (hash_val, files) in enumerate(duplicates.items(), 1):
            message_lines.append(f"Group {i} ({len(files)} files):")
            for file_item in files:
                message_lines.append(f"  • {file_item.filename}")
            message_lines.append(f"  Hash: {hash_val[:16]}...")
            message_lines.append("")

        # Show results dialog
        from widgets.custom_message_dialog import CustomMessageDialog

        CustomMessageDialog.information(
            self.parent_window, "Duplicate Detection Results", "\n".join(message_lines)
        )

        # Update status
        if hasattr(self.parent_window, "set_status"):
            self.parent_window.set_status(
                f"Found {duplicate_count} duplicates in {duplicate_groups} groups",
                color=STATUS_COLORS["duplicate_found"],
                auto_reset=True,
            )

        logger.info(
            f"[HashManager] Showed duplicate results: {duplicate_count} files in {duplicate_groups} groups"
        )

    def _show_comparison_results(self, results: dict, external_folder: str) -> None:
        """
        Show external folder comparison results to the user.

        Args:
            results: Dictionary with comparison results
            external_folder: Path to the external folder that was compared
        """
        if not results:
            from widgets.custom_message_dialog import CustomMessageDialog

            CustomMessageDialog.information(
                self.parent_window,
                "External Comparison Results",
                f"No matching files found in:\n{external_folder}",
            )
            if hasattr(self.parent_window, "set_status"):
                self.parent_window.set_status(
                    "No matching files found", color=STATUS_COLORS["no_action"], auto_reset=True
                )
            return

        # Count matches and differences
        matches = sum(1 for r in results.values() if r["is_same"])
        differences = len(results) - matches

        # Build results message
        message_lines = [
            f"Comparison with: {external_folder}\n",
            f"Files compared: {len(results)}",
            f"Identical: {matches}",
            f"Different: {differences}\n",
        ]

        if differences > 0:
            message_lines.append("Different files:")
            for filename, data in results.items():
                if not data["is_same"]:
                    message_lines.append(f"  • {filename}")

        if matches > 0:
            message_lines.append("\nIdentical files:")
            for filename, data in results.items():
                if data["is_same"]:
                    message_lines.append(f"  • {filename}")

        # Show results dialog
        from widgets.custom_message_dialog import CustomMessageDialog

        CustomMessageDialog.information(
            self.parent_window, "External Comparison Results", "\n".join(message_lines)
        )

        # Update status
        if hasattr(self.parent_window, "set_status"):
            if differences > 0:
                self.parent_window.set_status(
                    f"Found {differences} different files, {matches} identical",
                    color=STATUS_COLORS["alert_notice"],
                    auto_reset=True,
                )
            else:
                self.parent_window.set_status(
                    f"All {matches} files are identical",
                    color=STATUS_COLORS["operation_success"],
                    auto_reset=True,
                )

        logger.info(
            f"[HashManager] Showed comparison results: {matches} identical, {differences} different"
        )

    def _show_hash_results(self, hash_results: dict, was_cancelled: bool = False) -> None:
        """
        Show checksum calculation results to the user.

        Args:
            hash_results: Dictionary with filename as key and hash data as value
            was_cancelled: Whether the operation was cancelled (for partial results)
        """
        if not hash_results:
            from widgets.custom_message_dialog import CustomMessageDialog

            if was_cancelled:
                CustomMessageDialog.information(
                    self.parent_window,
                    "Checksum Results",
                    "Operation was cancelled before any checksums could be calculated.",
                )
            else:
                CustomMessageDialog.information(
                    self.parent_window, "Checksum Results", "No checksums could be calculated."
                )
            if hasattr(self.parent_window, "set_status"):
                status_msg = "Operation cancelled" if was_cancelled else "No checksums calculated"
                self.parent_window.set_status(
                    status_msg, color=STATUS_COLORS["no_action"], auto_reset=True
                )
            return

        # Show results in the new table dialog
        from widgets.results_table_dialog import ResultsTableDialog

        ResultsTableDialog.show_hash_results(
            parent=self.parent_window,
            hash_results=hash_results,
            was_cancelled=was_cancelled
        )

        # Update status
        if hasattr(self.parent_window, "set_status"):
            if was_cancelled:
                self.parent_window.set_status(
                    f"Calculated checksums for {len(hash_results)} files (cancelled)",
                    color=STATUS_COLORS["hash_success"],
                    auto_reset=True,
                )
            else:
                self.parent_window.set_status(
                    f"Calculated checksums for {len(hash_results)} files",
                    color=STATUS_COLORS["hash_success"],
                    auto_reset=True,
                )

        logger.info(
            f"[HashManager] Showed checksum results for {len(hash_results)} files"
            + (" (cancelled)" if was_cancelled else "")
        )

    # ===== Entry Point Handlers =====

    def _handle_compare_external(self, selected_files: list) -> None:
        """
        Handle comparison of selected files with an external folder.

        Args:
            selected_files: List of FileItem objects to compare
        """
        if not selected_files:
            logger.warning("[HashManager] No files selected for external comparison")
            return

        try:
            # Import Qt components
            from core.pyqt_imports import QFileDialog

            # Show folder picker dialog
            from utils.multiscreen_helper import get_existing_directory_on_parent_screen

            external_folder = get_existing_directory_on_parent_screen(
                self.parent_window,
                "Select folder to compare with",
                "",
                QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks,
            )

            if not external_folder:
                logger.debug(
                    "[HashManager] User cancelled external folder selection",
                    extra={"dev_only": True},
                )
                return

            logger.info(
                f"[HashManager] Comparing {len(selected_files)} files with {external_folder}"
            )

            # Convert FileItem objects to file paths
            file_paths = [item.full_path for item in selected_files]

            # Always use worker thread with progress dialog for cancellation support
            # This is especially important for large files (videos) that may take time
            self._start_hash_operation("compare", file_paths, external_folder=external_folder)

        except Exception as e:
            logger.error(f"[HashManager] Error setting up external comparison: {e}")
            from widgets.custom_message_dialog import CustomMessageDialog

            CustomMessageDialog.information(
                self.parent_window, "Error", f"Failed to start external comparison: {str(e)}"
            )

    def _handle_calculate_hashes(self, selected_files: list) -> None:
        """
        Handle calculating and displaying checksums for selected files.

        Args:
            selected_files: List of FileItem objects to calculate hashes for
        """
        if not selected_files:
            logger.warning("[HashManager] No files selected for checksum calculation")
            return

        logger.info(f"[HashManager] Calculating checksums for {len(selected_files)} files")

        # Convert FileItem objects to file paths
        file_paths = [item.full_path for item in selected_files]

        if len(file_paths) == 1:
            # Single file - use wait cursor (fast, simple)
            self._calculate_single_file_hash_fast(selected_files[0])
        else:
            # Multiple files - use worker thread with progress dialog
            self._start_hash_operation("checksums", file_paths)

    def _calculate_single_file_hash_fast(self, file_item) -> None:
        """
        Calculate hash for a single small file using wait cursor (fast, no cancellation).

        Args:
            file_item: FileItem object to calculate hash for
        """
        from core.hash_manager import HashManager
        from utils.cursor_helper import wait_cursor

        try:
            hash_results = {}
            with wait_cursor():
                hash_manager = HashManager()
                file_hash = hash_manager.calculate_hash(file_item.full_path)

                if file_hash:
                    hash_results[file_item.full_path] = file_hash

            # Show results after cursor is restored
            self._show_hash_results(hash_results)

        except Exception as e:
            logger.error(f"[HashManager] Error calculating checksum: {e}")
            from widgets.custom_message_dialog import CustomMessageDialog

            CustomMessageDialog.information(
                self.parent_window, "Error", f"Failed to calculate checksum: {str(e)}"
            )

    # ===== Status Check Methods =====

    def _check_files_have_hashes(self, files: list | None = None) -> bool:
        """
        Check if any of the specified files have hash values.

        Args:
            files: List of FileItem objects to check, or None for all files

        Returns:
            bool: True if any files have hashes, False otherwise
        """
        if files is None:
            # Check all files
            if (
                not hasattr(self.parent_window, "file_table_model")
                or not self.parent_window.file_table_model
            ):
                return False
            files = self.parent_window.file_table_model.get_all_file_items()

        if not files:
            return False

        # Check if any file has a hash
        return any(self._file_has_hash(file_item) for file_item in files)

    def _file_has_hash(self, file_item) -> bool:
        """Check if a specific file has a hash value."""
        return has_hash(file_item.full_path)
