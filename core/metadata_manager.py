"""
metadata_manager.py

Author: Michael Economou
Date: 2025-05-01

Centralized metadata management operations extracted from MainWindow.
Handles metadata loading, progress tracking, thread management, and UI coordination.
"""

import os
from typing import List, Optional

from config import STATUS_COLORS
from core.qt_imports import QApplication, Qt
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
        Determines whether to skip metadata scan or use extended mode based on modifier keys.

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

        if (hasattr(self.parent_window, 'file_table_view') and
            hasattr(self.parent_window, 'file_model')):
            # Use the new selection system
            selected_rows = self.parent_window.file_table_view._get_current_selection()
            selected = [self.parent_window.file_model.files[r]
                       for r in selected_rows
                       if 0 <= r < len(self.parent_window.file_model.files)]

            if not selected:
                logger.info("[Shortcut] No files selected for metadata loading")
                return

            logger.info(f"[Shortcut] Loading basic metadata for {len(selected)} files")
            # Use intelligent loading with cache checking and smart UX
            self.load_metadata_for_items(selected, use_extended=False, source="shortcut")

    def shortcut_load_extended_metadata(self) -> None:
        """
        Loads extended metadata for selected files via custom selection system.
        """
        if not self.parent_window:
            return

        if self.is_running_metadata_task():
            logger.warning("[Shortcut] Metadata scan already running — shortcut ignored.")
            return

        if (hasattr(self.parent_window, 'file_table_view') and
            hasattr(self.parent_window, 'file_model')):
            # Use the new selection system
            selected_rows = self.parent_window.file_table_view._get_current_selection()
            selected = [self.parent_window.file_model.files[r]
                       for r in selected_rows
                       if 0 <= r < len(self.parent_window.file_model.files)]

            if not selected:
                logger.info("[Shortcut] No files selected for extended metadata loading")
                return

            logger.info(f"[Shortcut] Loading extended metadata for {len(selected)} files")
            # Use intelligent loading with cache checking and smart UX
            self.load_metadata_for_items(selected, use_extended=True, source="shortcut")

    def load_metadata_for_items(self, items: List[FileItem], use_extended: bool = False, source: str = "unknown") -> None:
        """
        Load metadata for the given FileItem objects.

        Args:
            items: List of FileItem objects to load metadata for
            use_extended: Whether to use extended metadata loading
            source: Source of the request (for logging)
        """
        if not items:
            logger.warning("[MetadataManager] No items provided for metadata loading")
            return

        # Reset cancellation flag for new metadata loading operation
        self.reset_cancellation_flag()

        # Check what items need loading vs what's already cached
        needs_loading = []

        for item in items:
            # Check cache for existing metadata
            cache_entry = self.parent_window.metadata_cache.get_entry(item.full_path) if self.parent_window else None

            if cache_entry and hasattr(cache_entry, 'is_extended'):
                # Smart loading logic:
                # - If we have the exact type requested, skip
                # - If we have extended and requesting basic, skip (extended includes basic)
                # - If we have basic and requesting extended, load extended
                if cache_entry.is_extended == use_extended:
                    continue
                elif cache_entry.is_extended and not use_extended:
                    # We have extended but requesting basic - extended includes basic, so skip
                    continue

            needs_loading.append(item)

        # Get metadata tree view reference
        metadata_tree_view = (self.parent_window.metadata_tree_view
                            if self.parent_window and hasattr(self.parent_window, 'metadata_tree_view')
                            else None)

        # If nothing needs loading, just handle display logic
        if not needs_loading:
            logger.info(f"[{source}] All {len(items)} files already cached")

            # Always display metadata for cached items too
            if metadata_tree_view and items:
                # Always display metadata - same logic as loaded items
                display_file = items[0] if len(items) == 1 else items[-1]
                metadata_tree_view.display_file_metadata(display_file)

            return

        # Determine loading mode based on file count and settings
        loading_mode = self.determine_loading_mode(len(needs_loading), use_extended)

        # Handle different loading modes
        if loading_mode == "single_file_wait_cursor":
            logger.info(f"[{source}] Loading metadata for single file with wait_cursor (extended={use_extended})")

            from utils.cursor_helper import wait_cursor
            with wait_cursor():
                # Load metadata for the single file
                file_item = needs_loading[0]
                metadata = self._exiftool_wrapper.get_metadata(file_item.full_path, use_extended=use_extended)

                if metadata:
                    # Mark metadata with loading mode for UI indicators
                    if use_extended and '__extended__' not in metadata:
                        metadata['__extended__'] = True
                    elif not use_extended and '__extended__' in metadata:
                        del metadata['__extended__']

                    # Cache the result in both local and parent window caches
                    cache_key = (file_item.full_path, use_extended)
                    self._metadata_cache[cache_key] = metadata

                    # Also save to parent window's metadata_cache for UI display
                    if self.parent_window and hasattr(self.parent_window, 'metadata_cache'):
                        self.parent_window.metadata_cache.set(file_item.full_path, metadata, is_extended=use_extended)

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

        elif loading_mode == "multiple_files_dialog":
            logger.info(f"[{source}] Loading metadata for {len(needs_loading)} files with dialog (extended={use_extended})")

            # Calculate total size for enhanced progress tracking
            from utils.file_size_calculator import calculate_files_total_size
            total_size = calculate_files_total_size(needs_loading)

            # Use progress dialog for large batches
            from utils.progress_dialog import ProgressDialog

            # Cancellation support
            self._metadata_cancelled = False

            def cancel_metadata_loading():
                self._metadata_cancelled = True
                logger.info("[MetadataManager] Metadata loading cancelled by user")

            # Create loading dialog
            loading_dialog = ProgressDialog.create_metadata_dialog(
                parent=self.parent_window,
                is_extended=use_extended,
                cancel_callback=cancel_metadata_loading
            )
            loading_dialog.set_status("Loading metadata..." if not use_extended else "Loading extended metadata...")

            # Show dialog with smooth appearance to prevent shadow flicker
            from utils.dialog_utils import show_dialog_smooth
            show_dialog_smooth(loading_dialog)

            # Initialize incremental size tracking for better performance
            processed_size = 0

            # Delay metadata loading start to allow dialog to fully appear
            # This prevents the shadow-only appearance issue for fast operations
            from utils.timer_manager import schedule_ui_update

            def start_metadata_loading():
                """Start the actual metadata loading after dialog is shown."""
                # Initialize incremental size tracking for better performance
                processed_size = 0

                # Process each file
                for i, file_item in enumerate(needs_loading):
                    # Check for cancellation before processing each file
                    if self._metadata_cancelled:
                        logger.info(f"[MetadataManager] Metadata loading cancelled at file {i+1}/{len(needs_loading)}")
                        loading_dialog.close()
                        return

                    # Add current file size to processed total
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
                    loading_dialog.update_progress(
                        file_count=i + 1,
                        total_files=len(needs_loading),
                        processed_bytes=processed_size,
                        total_bytes=total_size
                    )
                    loading_dialog.set_filename(file_item.filename)
                    loading_dialog.set_count(i + 1, len(needs_loading))

                    # Process events to update the dialog and handle cancellation
                    if (i + 1) % 10 == 0 or current_file_size > 10 * 1024 * 1024:
                        from PyQt5.QtWidgets import QApplication
                        QApplication.processEvents()

                    # Check again after processing events
                    if self._metadata_cancelled:
                        logger.info(f"[MetadataManager] Metadata loading cancelled at file {i+1}/{len(needs_loading)}")
                        loading_dialog.close()
                        return

                    metadata = self._exiftool_wrapper.get_metadata(file_item.full_path, use_extended=use_extended)

                    if metadata:
                        # Mark metadata with loading mode for UI indicators
                        if use_extended and '__extended__' not in metadata:
                            metadata['__extended__'] = True
                        elif not use_extended and '__extended__' in metadata:
                            del metadata['__extended__']

                        # Cache the result in both local and parent window caches
                        cache_key = (file_item.full_path, use_extended)
                        self._metadata_cache[cache_key] = metadata

                        # Also save to parent window's metadata_cache for UI display
                        if self.parent_window and hasattr(self.parent_window, 'metadata_cache'):
                            self.parent_window.metadata_cache.set(file_item.full_path, metadata, is_extended=use_extended)

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

                # Close the dialog
                loading_dialog.close()

                # Display metadata for the appropriate file
                if metadata_tree_view and needs_loading:
                    display_file = needs_loading[0] if len(needs_loading) == 1 else needs_loading[-1]
                    metadata_tree_view.display_file_metadata(display_file)

            # Schedule the metadata loading to start after dialog is fully shown
            schedule_ui_update(start_metadata_loading, delay=10)  # 10ms delay for dialog to appear

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
                for row in selected_rows:
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
                        success = exiftool.write_metadata(file_item.full_path, modified_metadata)

                        if success:
                            logger.info(f"[MetadataManager] Successfully saved metadata to: {file_item.filename}")
                            success_count += 1
                            self._update_file_after_save(file_item)
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
                        from core.qt_imports import QApplication
                        QApplication.processEvents()

                    # Use path-aware lookup for modified metadata
                    modified_metadata = self._get_modified_metadata_for_file(file_item.full_path, all_modified_metadata)
                    if not modified_metadata:
                        logger.warning(f"[MetadataManager] No modified metadata found for: {file_item.filename}")
                        continue

                    logger.info(f"[MetadataManager] Saving metadata for: {file_item.filename}")
                    logger.debug(f"[MetadataManager] Metadata to save: {list(modified_metadata.keys())}", extra={"dev_only": True})

                    # Write metadata to file
                    success = exiftool.write_metadata(file_item.full_path, modified_metadata)

                    if success:
                        logger.info(f"[MetadataManager] Successfully saved metadata to: {file_item.filename}")
                        success_count += 1
                        self._update_file_after_save(file_item)
                    else:
                        logger.error(f"[MetadataManager] Failed to save metadata to: {file_item.filename}")
                        failed_files.append(file_item.filename)

                # Complete progress and close dialog
                save_dialog.set_progress(len(files_to_save), len(files_to_save))
                save_dialog.set_status("Save complete!")

                # Use timer manager instead of processEvents for UI update
                from utils.timer_manager import schedule_ui_update, schedule_dialog_close
                schedule_ui_update(lambda: None, delay=1)  # Allow UI to update

                # Keep dialog visible for a moment to show completion
                schedule_dialog_close(save_dialog.close, 500)

            # Show result message
            self._show_save_results(success_count, failed_files, files_to_save)

        finally:
            exiftool.close()

    def _update_file_after_save(self, file_item):
        """Update file state after successful metadata save."""
        # Clear modifications for this file in tree view
        self.parent_window.metadata_tree_view.clear_modifications_for_file(file_item.full_path)

        # Clear modified flag in cache
        metadata_entry = self.parent_window.metadata_cache.get_entry(file_item.full_path)
        if metadata_entry:
            metadata_entry.modified = False

        # Update file icon
        file_item.metadata_status = "loaded"

        # Refresh file table to show updated icon
        if hasattr(self.parent_window, 'file_model'):
            try:
                row = self.parent_window.file_model.files.index(file_item)
                icon_index = self.parent_window.file_model.index(row, 0)
                from core.qt_imports import Qt
                self.parent_window.file_model.dataChanged.emit(
                    icon_index,
                    icon_index,
                    [Qt.DecorationRole] # type: ignore
                )
            except ValueError:
                pass  # File not in model

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
        Get list of files based on source identifier.

        Args:
            source: Source identifier (e.g., "selected", "all")

        Returns:
            List of FileItem objects or None
        """
        if not self.parent_window:
            return None

        if source == "selected":
            # Get selected files
            if hasattr(self.parent_window, 'file_table_view'):
                selected_rows = self.parent_window.file_table_view._get_current_selection()
                if selected_rows and hasattr(self.parent_window, 'file_model'):
                    return [self.parent_window.file_model.files[r]
                           for r in selected_rows
                           if 0 <= r < len(self.parent_window.file_model.files)]
        elif source == "all":
            # Get all files
            if hasattr(self.parent_window, 'file_model'):
                return self.parent_window.file_model.files

        return None
