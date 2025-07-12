"""
Module: metadata_manager.py

Author: Michael Economou
Date: 2025-05-31

metadata_manager.py
Centralized metadata management operations extracted from MainWindow.
Handles metadata loading, progress tracking, thread management, and UI coordination.
"""

import os
from typing import List, Optional

from config import STATUS_COLORS
from core.pyqt_imports import QApplication, Qt
from models.file_item import FileItem
from utils.logger_factory import get_cached_logger
from utils.path_utils import find_file_by_path, paths_equal

logger = get_cached_logger(__name__)


class MetadataManager:
    """
    Centralized metadata management operations.

    Handles:
    - Thread-based metadata scanning with progress tracking
    - Modifier-based metadata mode decisions
    - Dialog management for progress indication
    - Error handling and cleanup
    - Integration with existing metadata cache and loader
    """

    def __init__(self, parent_window=None):
        """Initialize MetadataManager with parent window reference."""
        self.parent_window = parent_window

        # State tracking
        self.force_extended_metadata = False
        self._metadata_cancelled = False  # Cancellation flag for metadata loading

        # Initialize metadata cache and exiftool wrapper
        self._metadata_cache = {}  # Cache for metadata results

        # Initialize ExifTool wrapper for single file operations
        from utils.exiftool_wrapper import ExifToolWrapper
        self._exiftool_wrapper = ExifToolWrapper()

    def is_running_metadata_task(self) -> bool:
        """
        Check if there's currently a metadata task running.

        Returns:
            bool: True if a metadata task is running, False otherwise
        """
        # For now, return False as we don't have complex async metadata loading
        # This method can be enhanced later if we add async metadata workers
        return False

    def reset_cancellation_flag(self) -> None:
        """Reset the metadata cancellation flag."""
        self._metadata_cancelled = False

    def determine_loading_mode(self, file_count: int, use_extended: bool = False) -> str:
        """
        Determine the appropriate loading mode based on file count.

        Args:
            file_count: Number of files to load metadata for
            use_extended: Whether extended metadata is requested

        Returns:
            str: Loading mode ("single_file_wait_cursor", "multiple_files_dialog", etc.)
        """
        if file_count == 1:
            return "single_file_wait_cursor"
        else:
            # For any multiple files, use dialog
            return "multiple_files_dialog"

    def determine_metadata_mode(self, modifier_state=None) -> tuple[bool, bool]:
        """
        Determines whether to use extended mode based on modifier keys.

        Args:
            modifier_state: Qt.KeyboardModifiers to use, or None for current state

        Returns:
            tuple: (skip_metadata, use_extended)

            - skip_metadata = True ➜ No metadata scan (no modifiers)
            - skip_metadata = False & use_extended = False ➜ Fast scan (Ctrl)
            - skip_metadata = False & use_extended = True ➜ Extended scan (Ctrl+Shift)
        """
        modifiers = modifier_state
        if modifiers is None:
            if self.parent_window and hasattr(self.parent_window, 'modifier_state'):
                modifiers = self.parent_window.modifier_state
            else:
                modifiers = QApplication.keyboardModifiers()

        if modifiers == Qt.NoModifier: # type: ignore
            modifiers = QApplication.keyboardModifiers()  # fallback to current

        ctrl = bool(modifiers & Qt.ControlModifier) # type: ignore
        shift = bool(modifiers & Qt.ShiftModifier) # type: ignore

        # - No modifiers: skip metadata
        # - With Ctrl: load basic metadata
        # - With Ctrl+Shift: load extended metadata
        skip_metadata = not ctrl
        use_extended = ctrl and shift

        logger.debug(
            f"[determine_metadata_mode] modifiers={int(modifiers)}, "
            f"ctrl={ctrl}, shift={shift}, skip_metadata={skip_metadata}, use_extended={use_extended}"
        )

        return skip_metadata, use_extended

    def should_use_extended_metadata(self, modifier_state=None) -> bool:
        """
        Returns True if Ctrl+Shift are both held,
        used in cases where metadata is always loaded (double click, drag & drop).

        This assumes that metadata will be loaded — we only decide if it's fast or extended.

        Args:
            modifier_state: Qt.KeyboardModifiers to use, or None for current state
        """
        modifiers = modifier_state
        if modifiers is None:
            if self.parent_window and hasattr(self.parent_window, 'modifier_state'):
                modifiers = self.parent_window.modifier_state
            else:
                modifiers = QApplication.keyboardModifiers()

        ctrl = bool(modifiers & Qt.ControlModifier) # type: ignore
        shift = bool(modifiers & Qt.ShiftModifier) # type: ignore
        return ctrl and shift

    def shortcut_load_metadata(self) -> None:
        """
        Loads standard (non-extended) metadata for currently selected files.
        """
        if not self.parent_window:
            return

        # Use unified selection method
        selected_files = self.parent_window.get_selected_files_ordered() if self.parent_window else []

        if not selected_files:
            logger.info("[Shortcut] No files selected for metadata loading")
            return

        logger.info(f"[Shortcut] Loading basic metadata for {len(selected_files)} files")
        # Use intelligent loading with cache checking and smart UX
        self.load_metadata_for_items(selected_files, use_extended=False, source="shortcut")

    def shortcut_load_extended_metadata(self) -> None:
        """
        Loads extended metadata for selected files via custom selection system.
        """
        if not self.parent_window:
            return

        if self.is_running_metadata_task():
            logger.warning("[Shortcut] Metadata scan already running — shortcut ignored.")
            return

        # Use unified selection method
        selected_files = self.parent_window.get_selected_files_ordered() if self.parent_window else []

        if not selected_files:
            logger.info("[Shortcut] No files selected for extended metadata loading")
            return

        logger.info(f"[Shortcut] Loading extended metadata for {len(selected_files)} files")
        # Use intelligent loading with cache checking and smart UX
        self.load_metadata_for_items(selected_files, use_extended=True, source="shortcut")

    def shortcut_load_metadata_all(self) -> None:
        """
        Load basic metadata for all files using keyboard shortcut.
        """
        if not self.parent_window:
            return

        if self.is_running_metadata_task():
            logger.warning("[Shortcut] Metadata scan already running — shortcut ignored.")
            return

        if not self.parent_window.file_model.files:
            logger.info("[Shortcut] No files available for metadata loading")
            return

        all_files = self.parent_window.file_model.files
        logger.info(f"[Shortcut] Loading basic metadata for all {len(all_files)} files")

        self.load_metadata_for_items(all_files, use_extended=False, source="shortcut_all")

    def shortcut_load_extended_metadata_all(self) -> None:
        """
        Load extended metadata for all files using keyboard shortcut.
        """
        if not self.parent_window:
            return

        if self.is_running_metadata_task():
            logger.warning("[Shortcut] Metadata scan already running — shortcut ignored.")
            return

        if not self.parent_window.file_model.files:
            logger.info("[Shortcut] No files available for extended metadata loading")
            return

        all_files = self.parent_window.file_model.files
        logger.info(f"[Shortcut] Loading extended metadata for all {len(all_files)} files")

        self.load_metadata_for_items(all_files, use_extended=True, source="shortcut_all")

    def load_metadata_for_items(self, items: List[FileItem], use_extended: bool = False, source: str = "unknown") -> None:
        """
        Load metadata for the given FileItem objects.
        This method is deprecated - use UnifiedMetadataManager instead.

        Args:
            items: List of FileItem objects to load metadata for
            use_extended: Whether to use extended metadata loading
            source: Source of the request (for logging)
        """
        logger.warning("[MetadataManager] This method is deprecated - use UnifiedMetadataManager instead")

        if not items:
            logger.warning("[MetadataManager] No items provided for metadata loading")
            return

        # For backward compatibility, delegate to UnifiedMetadataManager
        from core.unified_metadata_manager import get_unified_metadata_manager
        unified_manager = get_unified_metadata_manager(self.parent_window)
        unified_manager.load_metadata_for_items(items, use_extended, source)

        logger.info(f"[MetadataManager] Delegated metadata loading for {len(items)} files to UnifiedMetadataManager")

    def _load_single_file_with_wait_cursor(self, file_item: FileItem, metadata_tree_view) -> None:
        """Load metadata for a single file using wait cursor (fast metadata only)."""
        from utils.cursor_helper import wait_cursor

        with wait_cursor():
            # Load metadata for the single file
            metadata = self._exiftool_wrapper.get_metadata(file_item.full_path, use_extended=False)

            if metadata:
                # Cache the result in both local and parent window caches
                cache_key = (file_item.full_path, False)
                self._metadata_cache[cache_key] = metadata

                # Also save to parent window's metadata_cache for UI display
                if self.parent_window and hasattr(self.parent_window, 'metadata_cache'):
                    self.parent_window.metadata_cache.set(file_item.full_path, metadata, is_extended=False)

                # Update the file item
                file_item.metadata = metadata

                # Emit dataChanged signal to update UI
                if self.parent_window and hasattr(self.parent_window, 'file_model'):
                    try:
                        # Find the row index and emit dataChanged for the entire row
                        for i, file in enumerate(self.parent_window.file_model.files):
                            if paths_equal(file.full_path, file_item.full_path):
                                top_left = self.parent_window.file_model.index(i, 0)
                                bottom_right = self.parent_window.file_model.index(i, self.parent_window.file_model.columnCount() - 1)
                                self.parent_window.file_model.dataChanged.emit(top_left, bottom_right, [Qt.DecorationRole, Qt.ToolTipRole]) # type: ignore
                                break
                    except Exception as e:
                        logger.warning(f"[Loader] Failed to emit dataChanged for {file_item.filename}: {e}")

        # Display metadata after cursor is restored
        if metadata_tree_view:
            metadata_tree_view.display_file_metadata(file_item)

    def _load_files_with_worker(self, files_to_load: List[FileItem], use_extended: bool, metadata_tree_view) -> None:
        """Load metadata for multiple files or extended metadata using MetadataWorker."""

        # First, clean up any existing metadata worker/thread to prevent conflicts
        if hasattr(self, 'metadata_worker') and self.metadata_worker:
            logger.debug("[MetadataManager] Cleaning up existing metadata worker before starting new one...")
            self._cleanup_metadata_worker_and_thread()

        # Calculate total size for enhanced progress tracking
        from utils.file_size_calculator import calculate_files_total_size
        total_size = calculate_files_total_size(files_to_load)

        # Use progress dialog for multiple files or extended metadata
        from utils.progress_dialog import ProgressDialog

        # Cancellation support
        self._metadata_cancelled = False

        def cancel_metadata_loading():
            self._metadata_cancelled = True
            logger.info("[MetadataManager] Metadata loading cancelled by user")
            if hasattr(self, 'metadata_worker') and self.metadata_worker:
                self.metadata_worker.cancel()

        # Create loading dialog
        loading_dialog = ProgressDialog.create_metadata_dialog(
            parent=self.parent_window,
            is_extended=use_extended,
            cancel_callback=cancel_metadata_loading
        )
        loading_dialog.set_status("Preparing metadata loading..." if not use_extended else "Preparing extended metadata loading...")

        # Start progress tracking with total size for time estimation
        loading_dialog.start_progress_tracking(total_size)

        # Show dialog with smooth appearance
        from utils.dialog_utils import show_dialog_smooth
        show_dialog_smooth(loading_dialog)

        # Create and configure metadata worker
        from utils.metadata_loader import MetadataLoader
        from widgets.metadata_worker import MetadataWorker

        # Create metadata loader
        metadata_loader = MetadataLoader()
        metadata_loader.model = self.parent_window.file_model if self.parent_window else None

        # Create worker WITHOUT parent (to avoid moveToThread issues)
        self.metadata_worker = MetadataWorker(
            reader=metadata_loader,
            metadata_cache=self.parent_window.metadata_cache if self.parent_window else None,
            parent=None  # No parent to avoid moveToThread issues
        )

        # Set parent window reference manually (after creation)
        self.metadata_worker.main_window = self.parent_window

        # Configure worker
        self.metadata_worker.file_path = [item.full_path for item in files_to_load]
        self.metadata_worker.use_extended = use_extended
        self.metadata_worker.set_total_size(total_size)

        # Connect worker signals
        self.metadata_worker.progress.connect(
            lambda current, total: self._on_metadata_progress(loading_dialog, current, total)
        )

        self.metadata_worker.size_progress.connect(
            lambda processed, total: self._on_metadata_size_progress(loading_dialog, processed, total)
        )

        # Connect real-time update signal for immediate UI refresh (same as HashWorker)
        self.metadata_worker.file_metadata_loaded.connect(self._on_file_metadata_loaded)

        self.metadata_worker.finished.connect(
            lambda: self._on_metadata_finished(loading_dialog, files_to_load, metadata_tree_view)
        )

        # Create and start thread
        from PyQt5.QtCore import QThread
        self.metadata_thread = QThread()
        self.metadata_worker.moveToThread(self.metadata_thread)

        # Connect thread signals
        self.metadata_thread.started.connect(self.metadata_worker.run_batch)
        self.metadata_worker.finished.connect(self.metadata_thread.quit)
        self.metadata_worker.finished.connect(self.metadata_worker.deleteLater)
        self.metadata_thread.finished.connect(self.metadata_thread.deleteLater)

        # Start the thread
        self.metadata_thread.start()

    def _on_metadata_progress(self, loading_dialog, current: int, total: int) -> None:
        """Handle metadata worker progress updates."""
        if loading_dialog:
            loading_dialog.update_progress(
                file_count=current,
                total_files=total,
                processed_bytes=0,  # Size will be updated by size_progress signal
                total_bytes=0
            )
            loading_dialog.set_count(current, total)

    def _on_metadata_size_progress(self, loading_dialog, processed: int, total: int) -> None:
        """Handle metadata worker size progress updates."""
        if loading_dialog:
            # Use the unified progress update method with size data
            loading_dialog.update_progress(
                file_count=0,  # Will be updated by file progress
                total_files=0,
                processed_bytes=processed,
                total_bytes=total
            )

    def _on_file_metadata_loaded(self, file_path: str) -> None:
        """Handle real-time metadata loading completion for individual files (same as HashWorker)."""
        try:
            # Update file icon status immediately (same logic as _on_file_hash_calculated)
            if self.parent_window and hasattr(self.parent_window, 'file_model'):
                for i, file_item in enumerate(self.parent_window.file_model.files):
                    if paths_equal(file_item.full_path, file_path):
                        # Update file icon to show metadata status
                        index = self.parent_window.file_model.index(i, 0)
                        self.parent_window.file_model.dataChanged.emit(index, index, [Qt.DecorationRole, Qt.ToolTipRole]) # type: ignore
                        logger.debug(f"[MetadataManager] Updated icon for: {os.path.basename(file_path)}", extra={"dev_only": True})
                        break

        except Exception as e:
            logger.warning(f"[MetadataManager] Error updating icon for {file_path}: {e}")

    def _on_metadata_finished(self, loading_dialog, files_to_load: List[FileItem], metadata_tree_view) -> None:
        """Handle metadata worker completion."""
        # Close dialog
        if loading_dialog:
            loading_dialog.close()

        # Update file model to show new metadata status
        if self.parent_window and hasattr(self.parent_window, 'file_model'):
            try:
                # Emit dataChanged for all loaded files
                for file_item in files_to_load:
                    for i, file in enumerate(self.parent_window.file_model.files):
                        if paths_equal(file.full_path, file_item.full_path):
                            top_left = self.parent_window.file_model.index(i, 0)
                            bottom_right = self.parent_window.file_model.index(i, self.parent_window.file_model.columnCount() - 1)
                            self.parent_window.file_model.dataChanged.emit(top_left, bottom_right, [Qt.DecorationRole, Qt.ToolTipRole]) # type: ignore
                            break
            except Exception as e:
                logger.warning(f"[Loader] Failed to emit dataChanged after worker completion: {e}")

        # Display metadata for the appropriate file
        if metadata_tree_view and files_to_load:
            display_file = files_to_load[0] if len(files_to_load) == 1 else files_to_load[-1]
            metadata_tree_view.display_file_metadata(display_file)

        # Clean up thread and worker properly
        self._cleanup_metadata_worker_and_thread()

    def _cleanup_metadata_worker_and_thread(self) -> None:
        """
        Properly clean up the metadata worker and thread.
        This ensures the thread is stopped before clearing references.
        """
        try:
            # Clean up the worker first to signal it to stop
            if hasattr(self, 'metadata_worker') and self.metadata_worker:
                logger.debug("[MetadataManager] Cleaning up metadata worker...")

                # Cancel the worker to signal it to stop gracefully
                try:
                    self.metadata_worker.cancel()
                except (AttributeError, RuntimeError):
                    pass

                # The worker should be deleted by deleteLater(), but clear our reference
                self.metadata_worker = None

            # Clean up the thread
            if hasattr(self, 'metadata_thread') and self.metadata_thread:
                logger.debug("[MetadataManager] Cleaning up metadata thread...")

                # Wait for thread to finish naturally (it should quit after finished signal)
                if self.metadata_thread.isRunning():
                    try:
                        # First try to quit gracefully
                        self.metadata_thread.quit()

                        # Give more time for graceful shutdown (5 seconds)
                        if self.metadata_thread.wait(5000):  # Wait max 5 seconds
                            logger.debug("[MetadataManager] Thread finished gracefully")
                        else:
                            # Only log as debug, not info - this is normal during shutdown
                            logger.debug("[MetadataManager] Thread cleanup taking longer than expected, allowing background termination")
                            # Don't force terminate - let it finish in background
                            # The thread will clean up itself when the worker finishes
                    except Exception as thread_error:
                        logger.debug(f"[MetadataManager] Thread cleanup completed: {thread_error}")

                # Clear reference regardless
                self.metadata_thread = None

        except Exception as e:
            logger.debug(f"[MetadataManager] Worker/thread cleanup completed: {e}")

    def save_metadata_for_selected(self) -> None:
        """
        Save modified metadata for the currently selected file(s) only.
        """
        if not hasattr(self.parent_window, 'metadata_tree_view'):
            logger.warning("[MetadataManager] No metadata tree view available")
            return

        # Get all modified metadata for all files
        all_modified_metadata = self.parent_window.metadata_tree_view.get_all_modified_metadata_for_files()

        if not all_modified_metadata:
            logger.info("[MetadataManager] No metadata modifications to save")
            return

        # Get selected files for filtering
        selected_files = []
        if hasattr(self.parent_window, 'file_table_view'):
            selected_rows = self.parent_window.file_table_view._get_current_selection()
            if selected_rows and hasattr(self.parent_window, 'file_model'):
                # Sort rows to maintain file table display order
                selected_rows_sorted = sorted(selected_rows)
                for row in selected_rows_sorted:
                    if 0 <= row < len(self.parent_window.file_model.files):
                        selected_files.append(self.parent_window.file_model.files[row])

        if not selected_files:
            logger.warning("[MetadataManager] No files selected for metadata save")
            return

        # Find files that have modifications AND are selected using path-aware comparison
        files_to_save = []
        for file_path, modified_metadata in all_modified_metadata.items():
            if modified_metadata:  # Only files with actual modifications
                # Use path-aware lookup to find corresponding FileItem
                file_item = find_file_by_path(selected_files, file_path, 'full_path')
                if file_item:
                    files_to_save.append(file_item)
                    logger.debug(f"[MetadataManager] Selected file with modifications: {file_item.filename}", extra={"dev_only": True})

        if not files_to_save:
            logger.info("[MetadataManager] No selected files have metadata modifications")
            return

        logger.info(f"[MetadataManager] Saving metadata for {len(files_to_save)} selected file(s)")
        self._save_metadata_files(files_to_save, all_modified_metadata)

    def save_all_modified_metadata(self) -> None:
        """
        Save modified metadata for ALL files that have modifications, regardless of selection.
        """
        if not hasattr(self.parent_window, 'metadata_tree_view'):
            logger.warning("[MetadataManager] No metadata tree view available")
            return

        # CRITICAL: Ensure current file's modifications are saved to per-file storage BEFORE getting all modifications
        tree_view = self.parent_window.metadata_tree_view
        if tree_view._current_file_path and tree_view.modified_items:
            logger.debug(f"[MetadataManager] Saving current file modifications before collecting all: {tree_view._current_file_path}", extra={"dev_only": True})
            tree_view._set_in_path_dict(tree_view._current_file_path, tree_view.modified_items.copy(), tree_view.modified_items_per_file)

        # Get all modified metadata for all files
        all_modified_metadata = tree_view.get_all_modified_metadata_for_files()

        if not all_modified_metadata:
            logger.info("[MetadataManager] No metadata modifications to save")
            return

        # Get all files from file model to find corresponding FileItems
        all_files = []
        if hasattr(self.parent_window, 'file_model') and self.parent_window.file_model.files:
            all_files = self.parent_window.file_model.files

        if not all_files:
            logger.warning("[MetadataManager] No files available in file model")
            return

        # DEBUG: Log what we got from MetadataTree
        logger.debug(f"[MetadataManager] Got modifications for {len(all_modified_metadata)} files:", extra={"dev_only": True})
        for file_path, modifications in all_modified_metadata.items():
            logger.debug(f"[MetadataManager]   - {file_path}: {list(modifications.keys())}", extra={"dev_only": True})

        # Find FileItems for all files that have modifications using path-aware comparison
        files_to_save = []
        for file_path, modified_metadata in all_modified_metadata.items():
            if modified_metadata:  # Only files with actual modifications
                logger.debug(f"[MetadataManager] Looking for FileItem with path: {file_path}", extra={"dev_only": True})

                # Use path-aware lookup to find corresponding FileItem
                file_item = find_file_by_path(all_files, file_path, 'full_path')
                if file_item:
                    files_to_save.append(file_item)
                    logger.debug(f"[MetadataManager] MATCH found for: {file_item.filename}", extra={"dev_only": True})
                else:
                    logger.warning(f"[MetadataManager] NO MATCH found for path: {file_path}")

        logger.debug(f"[MetadataManager] Found {len(files_to_save)} FileItems to save", extra={"dev_only": True})

        if not files_to_save:
            logger.info("[MetadataManager] No files with metadata modifications found")
            return

        logger.info(f"[MetadataManager] Saving metadata for ALL {len(files_to_save)} modified file(s)")
        self._save_metadata_files(files_to_save, all_modified_metadata)

    def _get_modified_metadata_for_file(self, file_path: str, all_modified_metadata: dict) -> dict:
        """
        Get modified metadata for a file using path-aware lookup.

        Args:
            file_path: Path of the file to get metadata for
            all_modified_metadata: Dictionary with all modified metadata

        Returns:
            dict: Modified metadata for the file, or empty dict if not found
        """
        # First try direct lookup (fastest)
        if file_path in all_modified_metadata:
            return all_modified_metadata[file_path]

        # If not found, try normalized path comparison
        for stored_path, metadata in all_modified_metadata.items():
            if paths_equal(file_path, stored_path):
                return metadata

        return {}

    def _save_metadata_files(self, files_to_save: list, all_modified_metadata: dict) -> None:
        """
        Common method to save metadata for a list of files.

        Args:
            files_to_save: List of FileItem objects to save
            all_modified_metadata: Dictionary of all modified metadata
        """
        # Create ExifToolWrapper instance
        from utils.exiftool_wrapper import ExifToolWrapper
        exiftool = ExifToolWrapper()

        success_count = 0
        failed_files = []

        try:
            if len(files_to_save) == 1:
                # Single file: Use wait cursor
                from utils.cursor_helper import wait_cursor
                with wait_cursor():
                    file_item = files_to_save[0]
                    modified_metadata = self._get_modified_metadata_for_file(file_item.full_path, all_modified_metadata)

                    if modified_metadata:
                        logger.info(f"[MetadataManager] Saving metadata for: {file_item.filename}")
                        logger.debug(f"[MetadataManager] Metadata to save: {list(modified_metadata.keys())}", extra={"dev_only": True})
                        logger.debug(f"[MetadataManager] Metadata values: {modified_metadata}", extra={"dev_only": True})
                        success = exiftool.write_metadata(file_item.full_path, modified_metadata)

                        if success:
                            logger.info(f"[MetadataManager] Successfully saved metadata to: {file_item.filename}")
                            success_count += 1
                            self._update_file_after_save(file_item, modified_metadata)
                        else:
                            logger.error(f"[MetadataManager] Failed to save metadata to: {file_item.filename}")
                            failed_files.append(file_item.filename)
                    else:
                        logger.warning(f"[MetadataManager] No modified metadata found for: {file_item.filename}")
            else:
                # Multiple files: Use progress dialog
                # Calculate total size for enhanced progress tracking
                from utils.file_size_calculator import calculate_files_total_size
                from utils.progress_dialog import ProgressDialog
                total_size = calculate_files_total_size(files_to_save)

                # Create save dialog with size-based progress
                save_dialog = ProgressDialog.create_metadata_dialog(
                    parent=self.parent_window,
                    is_extended=False,  # Save operation, not extended metadata
                    cancel_callback=None,  # No cancellation for save operations
                    use_size_based_progress=True  # Use size-based progress for consistency
                )
                save_dialog.set_status("Saving metadata...")

                # Start enhanced tracking with total size
                save_dialog.start_progress_tracking(total_size)

                # Show dialog with smooth appearance to prevent shadow flicker
                from utils.dialog_utils import show_dialog_smooth
                show_dialog_smooth(save_dialog)

                # Initialize incremental size tracking for better performance
                processed_size = 0

                # Process each file
                for i, file_item in enumerate(files_to_save):
                    # Use cached file size if available to avoid repeated os.path.getsize() calls
                    try:
                        if hasattr(file_item, 'file_size') and file_item.file_size is not None:
                            current_file_size = file_item.file_size
                        elif hasattr(file_item, 'full_path') and os.path.exists(file_item.full_path):
                            current_file_size = os.path.getsize(file_item.full_path)
                            # Cache it for future use
                            if hasattr(file_item, 'file_size'):
                                file_item.file_size = current_file_size
                        else:
                            current_file_size = 0

                        processed_size += current_file_size
                    except (OSError, AttributeError):
                        current_file_size = 0

                    # Update progress using unified method
                    save_dialog.update_progress(
                        file_count=i + 1,
                        total_files=len(files_to_save),
                        processed_bytes=processed_size,
                        total_bytes=total_size
                    )
                    save_dialog.set_filename(file_item.filename)
                    save_dialog.set_count(i + 1, len(files_to_save))

                    # Reduced frequency of processEvents() for better performance
                    # Only process events every 5 files or for large files (>10MB)
                    if (i + 1) % 5 == 0 or current_file_size > 10 * 1024 * 1024:
                        from core.pyqt_imports import QApplication
                        QApplication.processEvents()

                    # Use path-aware lookup for modified metadata
                    modified_metadata = self._get_modified_metadata_for_file(file_item.full_path, all_modified_metadata)
                    if not modified_metadata:
                        logger.warning(f"[MetadataManager] No modified metadata found for: {file_item.filename}")
                        continue

                    logger.info(f"[MetadataManager] Saving metadata for: {file_item.filename}")
                    logger.debug(f"[MetadataManager] Metadata to save: {list(modified_metadata.keys())}", extra={"dev_only": True})
                    logger.debug(f"[MetadataManager] Metadata values: {modified_metadata}", extra={"dev_only": True})

                    # Write metadata to file
                    success = exiftool.write_metadata(file_item.full_path, modified_metadata)

                    if success:
                        logger.info(f"[MetadataManager] Successfully saved metadata to: {file_item.filename}")
                        success_count += 1
                        self._update_file_after_save(file_item, modified_metadata)
                    else:
                        logger.error(f"[MetadataManager] Failed to save metadata to: {file_item.filename}")
                        failed_files.append(file_item.filename)

                # Complete progress and close dialog
                save_dialog.set_progress(len(files_to_save), len(files_to_save))
                save_dialog.set_status("Save complete!")

                # Use timer manager instead of processEvents for UI update
                from utils.timer_manager import schedule_dialog_close, schedule_ui_update
                schedule_ui_update(lambda: None, delay=1)  # Allow UI to update

                # Keep dialog visible for a moment to show completion
                schedule_dialog_close(save_dialog.close, 500)

            # Show result message
            self._show_save_results(success_count, failed_files, files_to_save)

        finally:
            exiftool.close()

    def _update_file_after_save(self, file_item, saved_metadata: dict = None):
        """
        Update file state after successful metadata save.

        Args:
            file_item: The FileItem that was saved
            saved_metadata: The metadata that was actually saved to the file
        """
        # Clear modifications for this file in tree view
        self.parent_window.metadata_tree_view.clear_modifications_for_file(file_item.full_path)

        # CRITICAL: Update cache with the saved values to prevent stale data
        metadata_entry = self.parent_window.metadata_cache.get_entry(file_item.full_path)
        if metadata_entry and saved_metadata:
            logger.debug(f"[MetadataManager] Updating cache with saved metadata for: {file_item.filename}", extra={"dev_only": True})

            # Update the cache data with the values that were actually saved
            for key_path, new_value in saved_metadata.items():
                logger.debug(f"[MetadataManager] Updating cache: {key_path} = {new_value}", extra={"dev_only": True})

                # Handle nested keys (e.g., "EXIF:Rotation")
                if '/' in key_path or ':' in key_path:
                    # Split by either / or : to handle both formats
                    if '/' in key_path:
                        parts = key_path.split('/', 1)
                    else:
                        parts = key_path.split(':', 1)

                    if len(parts) == 2:
                        group, key = parts
                        if group not in metadata_entry.data:
                            metadata_entry.data[group] = {}
                        if isinstance(metadata_entry.data[group], dict):
                            metadata_entry.data[group][key] = new_value
                        else:
                            # If group is not a dict, make it one
                            metadata_entry.data[group] = {key: new_value}
                    else:
                        # Fallback: treat as top-level key
                        metadata_entry.data[key_path] = new_value
                else:
                    # Top-level key (e.g., "Rotation")
                    metadata_entry.data[key_path] = new_value

            # Mark cache as clean but keep the data
            metadata_entry.modified = False

            # Update file_item.metadata if it exists for consistency
            if hasattr(file_item, 'metadata') and file_item.metadata:
                for key_path, new_value in saved_metadata.items():
                    if '/' in key_path or ':' in key_path:
                        # For nested keys, update the top-level key (most common case)
                        if '/' in key_path:
                            top_level_key = key_path.split('/', 1)[1]
                        else:
                            top_level_key = key_path.split(':', 1)[1]
                        file_item.metadata[top_level_key] = new_value
                    else:
                        file_item.metadata[key_path] = new_value

        elif metadata_entry:
            # No saved_metadata provided - just mark as clean
            metadata_entry.modified = False

        # Update file icon
        file_item.metadata_status = "loaded"

        # Refresh file table to show updated icon
        if hasattr(self.parent_window, 'file_model'):
            try:
                row = self.parent_window.file_model.files.index(file_item)
                icon_index = self.parent_window.file_model.index(row, 0)
                from core.pyqt_imports import Qt
                self.parent_window.file_model.dataChanged.emit(
                    icon_index,
                    icon_index,
                    [Qt.DecorationRole] # type: ignore
                )
            except ValueError:
                pass  # File not in model

        # Force refresh metadata view if this file is currently displayed
        if (hasattr(self.parent_window, 'metadata_tree_view') and
            hasattr(self.parent_window.metadata_tree_view, '_current_file_path') and
            self.parent_window.metadata_tree_view._current_file_path == file_item.full_path):

            logger.debug(f"[MetadataManager] Refreshing metadata view for updated file: {file_item.filename}", extra={"dev_only": True})

            # Use the updated cache data to refresh the display
            if metadata_entry and hasattr(metadata_entry, 'data'):
                display_data = dict(metadata_entry.data)
                display_data["FileName"] = file_item.filename
                self.parent_window.metadata_tree_view.display_metadata(display_data, context="after_save")

    def _show_save_results(self, success_count, failed_files, files_to_save):
        """Show results status message after save operation."""
        if success_count > 0:
            if failed_files:
                # Show error dialog only for failed files
                from utils.dialog_utils import show_error_message
                message = f"Successfully saved {success_count} file(s), but failed to save:\n" + "\n".join(failed_files)
                show_error_message(self.parent_window, "Partial Save Failure", message)
            else:
                # Success - just show status message, no dialog
                if success_count == 1:
                    status_msg = f"Saved metadata changes to {files_to_save[0].filename}"
                else:
                    status_msg = f"Saved metadata changes to {success_count} files"

                if hasattr(self.parent_window, 'set_status'):
                    self.parent_window.set_status(status_msg, color=STATUS_COLORS["metadata_success"], auto_reset=True)
        elif failed_files:
            # Show error dialog only for failures
            from utils.dialog_utils import show_error_message
            show_error_message(
                self.parent_window,
                "Save Failed",
                "Failed to save metadata changes to:\n" + "\n".join(failed_files)
            )

    def _get_files_from_source(self, source: str) -> Optional[List[FileItem]]:
        """
        Get files based on source type.

        Args:
            source: Source type ("selected", "all", etc.)

        Returns:
            List of FileItem objects or None if source not recognized
        """
        if not self.parent_window:
            return None

        if source == "selected":
            # Get selected files
            if (hasattr(self.parent_window, 'file_table_view') and
                hasattr(self.parent_window, 'file_model')):
                selected_rows = self.parent_window.file_table_view._get_current_selection()
                return [self.parent_window.file_model.files[r]
                       for r in selected_rows
                       if 0 <= r < len(self.parent_window.file_model.files)]
        elif source == "all":
            # Get all files
            if hasattr(self.parent_window, 'file_model'):
                return self.parent_window.file_model.files

        return None

    def cleanup(self) -> None:
        """
        Clean up metadata manager resources.

        This method should be called when shutting down the application
        to ensure all ExifTool processes and threads are properly closed.
        """
        logger.info("[MetadataManager] Starting cleanup...")

        try:
            # 1. Cancel any running metadata operations
            self._metadata_cancelled = True

            # 2. Cancel the worker if it exists
            if hasattr(self, 'metadata_worker') and self.metadata_worker:
                logger.info("[MetadataManager] Cancelling metadata worker...")
                self.metadata_worker.cancel()

                # Close the ExifToolWrapper in the worker's MetadataLoader
                if hasattr(self.metadata_worker, 'reader') and self.metadata_worker.reader:
                    logger.info("[MetadataManager] Closing MetadataWorker ExifTool...")
                    try:
                        self.metadata_worker.reader.close()
                        logger.info("[MetadataManager] MetadataWorker ExifTool closed")
                    except Exception as e:
                        logger.warning(f"[MetadataManager] Error closing MetadataWorker ExifTool: {e}")

            # 3. Clean up metadata worker and thread properly
            self._cleanup_metadata_worker_and_thread()

            # 4. Close the main ExifTool wrapper
            if hasattr(self, '_exiftool_wrapper') and self._exiftool_wrapper:
                logger.info("[MetadataManager] Closing main ExifTool wrapper...")
                try:
                    self._exiftool_wrapper.close()
                    logger.info("[MetadataManager] Main ExifTool wrapper closed")
                except Exception as e:
                    logger.warning(f"[MetadataManager] Error closing main ExifTool wrapper: {e}")

                # Clear reference
                self._exiftool_wrapper = None

            # 5. Close metadata loader ExifTool if it exists
            if hasattr(self, 'metadata_loader') and self.metadata_loader:
                logger.info("[MetadataManager] Closing metadata loader ExifTool...")
                try:
                    self.metadata_loader.close()
                    logger.info("[MetadataManager] Metadata loader ExifTool closed")
                except Exception as e:
                    logger.warning(f"[MetadataManager] Error closing metadata loader ExifTool: {e}")

            logger.info("[MetadataManager] Cleanup completed successfully")

        except Exception as e:
            logger.error(f"[MetadataManager] Error during cleanup: {e}")

        finally:
            # Force cleanup any remaining ExifTool processes as last resort
            try:
                logger.info("[MetadataManager] Force cleaning up any remaining ExifTool processes...")
                from utils.exiftool_wrapper import ExifToolWrapper
                ExifToolWrapper.force_cleanup_all_exiftool_processes()
            except Exception as e:
                logger.warning(f"[MetadataManager] Error during force cleanup: {e}")
