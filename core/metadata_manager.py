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
        Determine metadata loading mode based on modifier keys.

        Returns:
            tuple: (skip_metadata, use_extended)
        """
        # Default mode
        skip_metadata = False
        use_extended = False

        # Check modifier state
        if modifier_state is not None:
            modifiers = modifier_state
        else:
            modifiers = QApplication.keyboardModifiers()

        # Check for Ctrl and Shift keys
        ctrl = bool(modifiers & Qt.ControlModifier)
        shift = bool(modifiers & Qt.ShiftModifier)

        # Determine loading mode
        if ctrl and shift:
            use_extended = True
        elif ctrl:
            skip_metadata = True

        logger.debug(
            f"[determine_metadata_mode] modifiers={int(modifiers)}, "
            f"ctrl={ctrl}, shift={shift}, skip_metadata={skip_metadata}, use_extended={use_extended}",
            extra={"dev_only": True}
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
            logger.debug("[MetadataManager] Cleaning up existing metadata worker before starting new one...", extra={"dev_only": True})
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
        """Clean up metadata worker and thread properly."""
        try:
            # Clean up worker
            if hasattr(self, 'metadata_worker') and self.metadata_worker:
                logger.debug("[MetadataManager] Cleaning up metadata worker...", extra={"dev_only": True})
                try:
                    self.metadata_worker.stop()
                    self.metadata_worker.deleteLater()
                except Exception as e:
                    logger.warning(f"[MetadataManager] Error cleaning up metadata worker: {e}")
                finally:
                    self.metadata_worker = None

            # Clean up thread
            if hasattr(self, 'metadata_thread') and self.metadata_thread:
                logger.debug("[MetadataManager] Cleaning up metadata thread...", extra={"dev_only": True})
                try:
                    self.metadata_thread.quit()

                    # Wait for thread to finish with timeout
                    if self.metadata_thread.wait(2000):  # 2 second timeout
                        logger.debug("[MetadataManager] Thread finished gracefully", extra={"dev_only": True})
                    else:
                        logger.debug("[MetadataManager] Thread cleanup taking longer than expected, allowing background termination", extra={"dev_only": True})
                        # Allow thread to finish in background

                    thread_error = None
                    logger.debug(f"[MetadataManager] Thread cleanup completed: {thread_error}", extra={"dev_only": True})

                except Exception as thread_error:
                    logger.warning(f"[MetadataManager] Error cleaning up metadata thread: {thread_error}")
                finally:
                    self.metadata_thread = None

        except Exception as e:
            logger.debug(f"[MetadataManager] Worker/thread cleanup completed: {e}", extra={"dev_only": True})

    def save_metadata_for_selected(self) -> None:
        """Save metadata modifications for currently selected files."""
        try:
            # Get metadata tree view
            metadata_tree_view = self._get_metadata_tree_view()
            if not metadata_tree_view:
                logger.warning("[MetadataManager] No metadata tree view available for saving")
                return

            # Get current selection
            selected_files = self._get_current_selection()
            if not selected_files:
                logger.info("[MetadataManager] No files selected for metadata saving")
                return

            # Get files with modifications
            files_to_save = []
            for file_item in selected_files:
                if metadata_tree_view.has_modifications_for_file(file_item.full_path):
                    files_to_save.append(file_item)
                    logger.debug(f"[MetadataManager] Selected file with modifications: {file_item.filename}", extra={"dev_only": True})

            if not files_to_save:
                logger.info("[MetadataManager] No selected files have metadata modifications to save")
                return

            # Get all modified metadata
            all_modified_metadata = metadata_tree_view.get_all_modified_metadata_for_files()

            # Save metadata for selected files
            self._save_metadata_files(files_to_save, all_modified_metadata)

        except Exception as e:
            logger.error(f"[MetadataManager] Error saving metadata for selected files: {e}")

    def save_all_modified_metadata(self) -> None:
        """Save all modified metadata for all files."""
        try:
            # Get metadata tree view
            metadata_tree_view = self._get_metadata_tree_view()
            if not metadata_tree_view:
                logger.warning("[MetadataManager] No metadata tree view available for saving")
                return

            # Save current file modifications before collecting all
            if hasattr(metadata_tree_view, '_current_file_path') and metadata_tree_view._current_file_path:
                logger.debug(f"[MetadataManager] Saving current file modifications before collecting all: {metadata_tree_view._current_file_path}", extra={"dev_only": True})
                metadata_tree_view._save_current_file_state()

            # Get all modified metadata
            all_modified_metadata = metadata_tree_view.get_all_modified_metadata_for_files()

            if not all_modified_metadata:
                logger.info("[MetadataManager] No metadata modifications to save")
                return

            # Get all files from current context
            all_files = self._get_files_from_source("all")
            if not all_files:
                logger.warning("[MetadataManager] No files available for metadata saving")
                return

            # Filter files that have modifications
            files_to_save = []

            logger.debug(f"[MetadataManager] Got modifications for {len(all_modified_metadata)} files:", extra={"dev_only": True})
            for file_path, modifications in all_modified_metadata.items():
                logger.debug(f"[MetadataManager]   - {file_path}: {list(modifications.keys())}", extra={"dev_only": True})

                # Find corresponding FileItem
                for file_item in all_files:
                    logger.debug(f"[MetadataManager] Looking for FileItem with path: {file_path}", extra={"dev_only": True})
                    if paths_equal(file_item.full_path, file_path):
                        files_to_save.append(file_item)
                        logger.debug(f"[MetadataManager] MATCH found for: {file_item.filename}", extra={"dev_only": True})
                        break

            logger.debug(f"[MetadataManager] Found {len(files_to_save)} FileItems to save", extra={"dev_only": True})

            if not files_to_save:
                logger.warning("[MetadataManager] No FileItems found for modified metadata")
                return

            # Save metadata for all modified files
            self._save_metadata_files(files_to_save, all_modified_metadata)

        except Exception as e:
            logger.error(f"[MetadataManager] Error saving all modified metadata: {e}")

    def _get_modified_metadata_for_file(self, file_path: str, all_modified_metadata: dict) -> dict:
        """Get modified metadata for a specific file."""
        try:
            # Direct lookup first
            if file_path in all_modified_metadata:
                return all_modified_metadata[file_path]

            # Fallback: try path comparison
            for stored_path, modifications in all_modified_metadata.items():
                if paths_equal(stored_path, file_path):
                    return modifications

            # Alternative: single file metadata from tree view
            metadata_tree_view = self._get_metadata_tree_view()
            if metadata_tree_view and hasattr(metadata_tree_view, '_current_file_path'):
                if paths_equal(metadata_tree_view._current_file_path, file_path):
                    current_modifications = metadata_tree_view.get_modified_metadata()
                    if current_modifications:
                        logger.debug(f"[MetadataManager] Metadata to save: {list(current_modifications.keys())}", extra={"dev_only": True})
                        logger.debug(f"[MetadataManager] Metadata values: {current_modifications}", extra={"dev_only": True})
                        return current_modifications

            return {}

        except Exception as e:
            logger.error(f"[MetadataManager] Error getting modified metadata for {file_path}: {e}")
            return {}

    def _save_metadata_files(self, files_to_save: list, all_modified_metadata: dict) -> None:
        """Save metadata for multiple files."""
        if not files_to_save:
            logger.warning("[MetadataManager] No files to save metadata for")
            return

        success_count = 0
        failed_files = []

        try:
            # Get metadata tree view for clearing modifications
            metadata_tree_view = self._get_metadata_tree_view()

            for file_item in files_to_save:
                try:
                    # Get modifications for this file
                    modified_metadata = self._get_modified_metadata_for_file(file_item.full_path, all_modified_metadata)

                    if modified_metadata:
                        logger.debug(f"[MetadataManager] Metadata to save: {list(modified_metadata.keys())}", extra={"dev_only": True})
                        logger.debug(f"[MetadataManager] Metadata values: {modified_metadata}", extra={"dev_only": True})

                        # Save metadata using UnifiedMetadataManager
                        from core.unified_metadata_manager import UnifiedMetadataManager
                        metadata_manager = UnifiedMetadataManager()

                        # Save each metadata field
                        for key_path, new_value in modified_metadata.items():
                            try:
                                metadata_manager.set_metadata_value(file_item.full_path, key_path, new_value)
                            except Exception as field_error:
                                logger.error(f"[MetadataManager] Failed to save {key_path} for {file_item.filename}: {field_error}")
                                raise field_error

                        # Update file after successful save
                        self._update_file_after_save(file_item, modified_metadata)

                        # Clear modifications for this file
                        if metadata_tree_view:
                            metadata_tree_view.clear_modifications_for_file(file_item.full_path)

                        success_count += 1
                        logger.info(f"[MetadataManager] Successfully saved metadata for: {file_item.filename}")

                    else:
                        logger.warning(f"[MetadataManager] No modifications found for: {file_item.filename}")

                except Exception as file_error:
                    logger.error(f"[MetadataManager] Failed to save metadata for {file_item.filename}: {file_error}")
                    failed_files.append((file_item.filename, str(file_error)))

        except Exception as e:
            logger.error(f"[MetadataManager] Error in metadata saving process: {e}")

        # Show results
        self._show_save_results(success_count, failed_files, files_to_save)

    def _update_file_after_save(self, file_item, saved_metadata: dict = None):
        """Update file item and UI after successful metadata save."""
        try:
            # Update cache with saved metadata
            if saved_metadata:
                logger.debug(f"[MetadataManager] Updating cache with saved metadata for: {file_item.filename}", extra={"dev_only": True})
                if hasattr(file_item, 'metadata') and file_item.metadata:
                    for key_path, new_value in saved_metadata.items():
                        logger.debug(f"[MetadataManager] Updating cache: {key_path} = {new_value}", extra={"dev_only": True})
                        # Update nested dictionary
                        self._update_nested_dict(file_item.metadata, key_path, new_value)

            # Update file icon status
            file_item.metadata_status = "valid"

            # Get file table model for updates
            from core.application_context import ApplicationContext
            app_context = ApplicationContext()
            file_table_model = app_context.get_file_table_model()

            if file_table_model:
                # Find and update the file in the model
                for row in range(file_table_model.rowCount()):
                    model_file_item = file_table_model.get_file_item(row)
                    if model_file_item and paths_equal(model_file_item.full_path, file_item.full_path):
                        # Update the model
                        file_table_model.update_file_item(row, file_item)
                        break

            # Refresh metadata view if this is the currently displayed file
            metadata_tree_view = self._get_metadata_tree_view()
            if metadata_tree_view and hasattr(metadata_tree_view, '_current_file_path'):
                if paths_equal(metadata_tree_view._current_file_path, file_item.full_path):
                    logger.debug(f"[MetadataManager] Refreshing metadata view for updated file: {file_item.filename}", extra={"dev_only": True})
                    metadata_tree_view.display_file_metadata(file_item, "after_save")

        except Exception as e:
            logger.error(f"[MetadataManager] Error updating file after save: {e}")

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
