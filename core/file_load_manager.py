"""
file_load_manager.py

Author: Michael Economou
Date: 2025-05-01

Unified file loading manager with simplified policy:
- Non-recursive folder loading: wait_cursor only (fast, no progress bar)
- Recursive folder loading: FileLoadingDialog with progress bar
- Consistent behavior between drag-and-drop and import button
"""

import os
from typing import List, Set, Optional
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from config import ALLOWED_EXTENSIONS
from models.file_item import FileItem
from widgets.file_loading_dialog import FileLoadingDialog
from utils.cursor_helper import wait_cursor, force_restore_cursor
from utils.timer_manager import get_timer_manager, TimerType, TimerPriority
from core.drag_manager import force_cleanup_drag, is_dragging
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)

class FileLoadManager:
    """
    Unified file loading manager with simplified policy:
    - Non-recursive: wait_cursor only (fast)
    - Recursive: progress dialog (for large operations)
    - Same behavior for drag and import
    """

    def __init__(self, parent_window=None):
        self.parent_window = parent_window
        self.allowed_extensions = set(ALLOWED_EXTENSIONS)
        self.timer_manager = get_timer_manager()
        logger.debug("[FileLoadManager] Initialized with unified loading policy")

    def load_folder(self, folder_path: str, merge_mode: bool = False, recursive: bool = False) -> None:
        """
        Unified folder loading method for both drag and import operations.

        Policy:
        - Non-recursive: wait_cursor only (fast, synchronous)
        - Recursive: FileLoadingDialog with progress bar
        """
        logger.info(f"[FileLoadManager] load_folder: {folder_path} (merge={merge_mode}, recursive={recursive})")

        if not os.path.isdir(folder_path):
            logger.error(f"Path is not a directory: {folder_path}")
            return

        # Store the recursive state for future reloads (if not merging)
        if not merge_mode and hasattr(self.parent_window, 'current_folder_is_recursive'):
            self.parent_window.current_folder_is_recursive = recursive
            logger.info(f"[FileLoadManager] Stored recursive state: {recursive}")

        # CRITICAL: Force cleanup any active drag state immediately
        # This ensures ESC key works properly in FileLoadingDialog
        if is_dragging():
            logger.debug("[FileLoadManager] Active drag detected, forcing cleanup before loading")
            force_cleanup_drag()

        # Clear any existing cursors immediately
        force_restore_cursor()

        if recursive:
            # Recursive: Use progress dialog for potentially long operations
            self._load_folder_with_progress(folder_path, merge_mode)
        else:
            # Non-recursive: Simple wait cursor for fast operations
            self._load_folder_with_wait_cursor(folder_path, merge_mode)

    # Legacy method name for compatibility
    def handle_folder_drop(self, folder_path: str, merge_mode: bool = False, recursive: bool = False) -> None:
        """Legacy method - redirects to unified load_folder."""
        self.load_folder(folder_path, merge_mode, recursive)

    def load_files_from_paths(self, paths: List[str], clear: bool = True) -> None:
        """
        Load files from multiple paths (used by import button).
        Always uses progress dialog since it can handle multiple paths.
        """
        logger.info(f"[FileLoadManager] load_files_from_paths: {len(paths)} paths")

        # Force cleanup any active drag state (import button shouldn't have drag, but safety first)
        if is_dragging():
            logger.debug("[FileLoadManager] Active drag detected during import, forcing cleanup")
            force_cleanup_drag()

        def on_files_loaded(file_paths: List[str]):
            logger.info(f"[FileLoadManager] Loaded {len(file_paths)} files from paths")
            self._update_ui_with_files(file_paths, clear=clear)

        # Always use progress dialog for multi-path operations
        dialog = FileLoadingDialog(self.parent_window, on_files_loaded)
        dialog.load_files_with_options(paths, self.allowed_extensions, recursive=True)
        dialog.exec_()

    def load_single_item_from_drop(self, path: str, modifiers: Qt.KeyboardModifiers = Qt.NoModifier) -> None:
        """
        Handle single item drop with modifier support.
        Uses unified load_folder method for consistent behavior.
        """
        logger.info(f"[FileLoadManager] load_single_item_from_drop: {path}")

        # Parse modifiers
        ctrl = bool(modifiers & Qt.ControlModifier)
        shift = bool(modifiers & Qt.ShiftModifier)
        recursive = ctrl
        merge_mode = shift

        logger.debug(f"[Drop] Modifiers: ctrl={ctrl}, shift={shift} → recursive={recursive}, merge={merge_mode}")

        if os.path.isdir(path):
            # Use unified folder loading (will handle drag cleanup internally)
            self.load_folder(path, merge_mode=merge_mode, recursive=recursive)
        else:
            # Handle single file - cleanup drag state first
            if is_dragging():
                logger.debug("[FileLoadManager] Active drag detected during single file drop, forcing cleanup")
                force_cleanup_drag()

            if self._is_allowed_extension(path):
                self._update_ui_with_files([path], clear=not merge_mode)

    def load_files_from_dropped_items(self, paths: list[str], modifiers: Qt.KeyboardModifiers = Qt.NoModifier) -> None:
        """
        Handle multiple dropped items (table drop).
        Uses unified loading for consistent behavior.
        """
        if not paths:
            logger.info("[Drop] No files dropped in table.")
            return

        logger.info(f"[Drop] {len(paths)} file(s)/folder(s) dropped in table view")

        # Parse modifiers
        ctrl = bool(modifiers & Qt.ControlModifier)
        shift = bool(modifiers & Qt.ShiftModifier)
        recursive = ctrl
        merge_mode = shift

        # Process all items with unified logic
        all_file_paths = []
        has_folders = False

        for path in paths:
            if os.path.isfile(path):
                if self._is_allowed_extension(path):
                    all_file_paths.append(path)
            elif os.path.isdir(path):
                has_folders = True
                # For table drops, collect files synchronously to avoid multiple dialogs
                folder_files = self._get_files_from_folder(path, recursive)
                all_file_paths.extend(folder_files)

        # Update UI with all collected files
        if all_file_paths:
            self._update_ui_with_files(all_file_paths, clear=not merge_mode)

    def load_metadata_from_dropped_files(self, paths: list[str], modifiers: Qt.KeyboardModifiers = Qt.NoModifier) -> None:
        """
        Handle files dropped onto metadata tree with modifier-based loading.

        Modifier behavior:
        - Shift: Fast metadata with CompactWaitingWidget
        - Ctrl+Shift: Extended metadata with CompactWaitingWidget
        - No modifiers: Use intelligent loading (wait cursor for 1 file, dialog for multiple)

        IMPORTANT: This loads metadata for ALL CURRENTLY SELECTED FILES,
        not just the dropped file(s). This ensures consistent behavior with
        context menu and shortcuts.
        """
        # Get currently selected files (the real selection we want to process)
        if not hasattr(self.parent_window, 'file_table_view'):
            logger.warning("[Drop] No file_table_view available for selection")
            return

        current_selection = self.parent_window.file_table_view._get_current_selection()
        if not current_selection:
            logger.info("[Drop] No files selected for metadata loading.")
            return

        # Convert selection to FileItem objects
        selected_files = [self.parent_window.file_model.files[r]
                         for r in current_selection
                         if 0 <= r < len(self.parent_window.file_model.files)]

        if not selected_files:
            logger.warning("[Drop] No valid selected files found for metadata loading")
            return

        # Debug logging: Compare dropped vs selected
        dropped_filenames = [os.path.basename(path) for path in paths]
        selected_filenames = [f.filename for f in selected_files]

        logger.debug(f"[Drop] Current selection: {selected_filenames}", extra={"dev_only": True})
        logger.debug(f"[Drop] Dropped files: {dropped_filenames}", extra={"dev_only": True})
        logger.debug(f"[Drop] Processing {len(selected_files)} selected files (ignoring specific dropped files)", extra={"dev_only": True})

        # Parse modifiers for metadata loading
        ctrl = bool(modifiers & Qt.ControlModifier)
        shift = bool(modifiers & Qt.ShiftModifier)

        # Determine loading mode based on modifiers
        if shift and ctrl:
            # Ctrl+Shift: Extended metadata with CompactWaitingWidget
            use_extended = True
            use_compact_widget = True
            logger.debug(f"[Modifiers] Ctrl+Shift detected → Extended metadata with CompactWaitingWidget")
        elif shift:
            # Shift only: Fast metadata with CompactWaitingWidget
            use_extended = False
            use_compact_widget = True
            logger.debug(f"[Modifiers] Shift detected → Fast metadata with CompactWaitingWidget")
        else:
            # No modifiers: Use intelligent loading (existing behavior)
            use_extended = False
            use_compact_widget = False
            logger.debug(f"[Modifiers] No modifiers → Intelligent loading")

        logger.info(f"[Drop] Loading metadata for {len(selected_files)} files (extended={use_extended}, compact={use_compact_widget})")

        # Use appropriate loading method
        if use_compact_widget:
            # Use CompactWaitingWidget for Shift/Ctrl+Shift drags
            self._load_metadata_with_compact_widget(selected_files, use_extended, source="drag_drop")
        else:
            # Use intelligent loading for normal drags (existing behavior)
            if hasattr(self.parent_window, 'load_metadata_for_items'):
                self.parent_window.load_metadata_for_items(selected_files, use_extended, source="drag_drop")
            else:
                logger.error("[Drop] No load_metadata_for_items available")

    def _load_metadata_with_compact_widget(self, selected_files: list, use_extended: bool, source: str) -> None:
        """
        Load metadata using CompactWaitingWidget for better UX on drag operations.

        Args:
            selected_files: List of FileItem objects to load metadata for
            use_extended: Whether to load extended metadata
            source: Source of the call (for logging)
        """
        if not hasattr(self.parent_window, 'metadata_manager'):
            logger.error("[Drop] No metadata_manager available")
            return

        metadata_manager = self.parent_window.metadata_manager

        if metadata_manager.is_running_metadata_task():
            logger.warning(f"[{source}] Metadata scan already running — ignoring request.")
            return

        # Get required components from parent window
        metadata_cache = getattr(self.parent_window, 'metadata_cache', None)
        metadata_loader = getattr(self.parent_window, 'metadata_loader', None)

        if not metadata_cache or not metadata_loader:
            logger.error(f"[{source}] Missing metadata_cache or metadata_loader from parent window")
            return

        # Intelligent cache checking - only load what's needed
        needs_loading = []
        for item in selected_files:
            # Get the cached entry (which includes extended status)
            entry = metadata_cache.get_entry(item.full_path)

            # Add file to loading list if:
            # 1. No cached entry exists
            # 2. Extended metadata is requested but entry is not extended
            if not entry:
                logger.debug(f"[{source}] {item.filename} needs loading (no cache entry)")
                needs_loading.append(item)
            elif use_extended and not entry.is_extended:
                logger.debug(f"[{source}] {item.filename} needs loading (extended requested but only basic loaded)")
                needs_loading.append(item)
            else:
                logger.debug(f"[{source}] {item.filename} already has {'extended' if entry.is_extended else 'basic'} metadata")

        # Always show metadata for the last file in the list
        target_file = selected_files[-1]

        # If all files already have appropriate metadata, just show it for the target file
        if not needs_loading:
            # Display the existing metadata for target file
            metadata = target_file.metadata or metadata_cache.get(target_file.full_path)
            if (self.parent_window and
                hasattr(self.parent_window, 'metadata_tree_view') and
                hasattr(self.parent_window.metadata_tree_view, 'display_metadata')):
                self.parent_window.metadata_tree_view.display_metadata(metadata, context=f"existing_{source}")
            if self.parent_window and hasattr(self.parent_window, 'set_status'):
                self.parent_window.set_status(f"Metadata already loaded for {target_file.filename}.", color="green", auto_reset=True)
            return

        # Check for large files if extended metadata was requested
        if (use_extended and self.parent_window and
            hasattr(self.parent_window, 'file_operations_manager') and
            not self.parent_window.file_operations_manager.confirm_large_files(needs_loading)):
            return

        # Set extended metadata flag (sync with parent window)
        metadata_manager.force_extended_metadata = use_extended
        if self.parent_window:
            self.parent_window.force_extended_metadata = use_extended

        # Always use CompactWaitingWidget for drag operations (better UX)
        logger.info(f"[{source}] Loading metadata for {len(needs_loading)} files with CompactWaitingWidget (extended={use_extended})")

        # Convert to file paths and use the compact metadata scan method
        file_paths = [item.full_path for item in needs_loading]

        # Force cleanup any active drag state before showing dialog
        if is_dragging():
            logger.debug(f"[{source}] Active drag detected, forcing cleanup before metadata loading")
            force_cleanup_drag()

        # Use compact metadata loading with enhanced UX
        self._start_compact_metadata_scan(file_paths, use_extended)

    def _start_compact_metadata_scan(self, file_paths: list[str], use_extended: bool) -> None:
        """
        Start metadata scan with CompactWaitingWidget for better drag & drop UX.

        Args:
            file_paths: List of file paths to scan
            use_extended: Whether to use extended metadata
        """
        if not file_paths:
            logger.warning("[CompactScan] No files to scan")
            return

        logger.info(f"[CompactScan] Starting compact metadata scan for {len(file_paths)} files (extended={use_extended})")

        # Import CompactWaitingWidget
        from widgets.compact_waiting_widget import CompactWaitingWidget
        from widgets.custom_msgdialog import CustomMessageDialog
        from PyQt5.QtWidgets import QDialog, QVBoxLayout
        from PyQt5.QtCore import Qt
        from utils.cursor_helper import wait_cursor

        # Create a simple dialog to host the CompactWaitingWidget
        dialog = QDialog(self.parent_window)
        dialog.setWindowTitle("Loading Metadata" if not use_extended else "Loading Extended Metadata")
        dialog.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint)
        dialog.setModal(True)
        dialog.setFixedSize(420, 120)  # Compact size

        # Create layout
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(10, 10, 10, 10)

        # Create CompactWaitingWidget with appropriate colors
        if use_extended:
            # Orange/amber colors for extended metadata
            compact_widget = CompactWaitingWidget(
                parent=dialog,
                bar_color="#f5a623",  # Orange for extended
                bar_bg_color="#2a2a2a"
            )
            compact_widget.set_status("Reading extended metadata...")
        else:
            # Blue colors for fast metadata
            compact_widget = CompactWaitingWidget(
                parent=dialog,
                bar_color="#007acc",  # Blue for fast
                bar_bg_color="#2a2a2a"
            )
            compact_widget.set_status("Reading metadata...")

        layout.addWidget(compact_widget)

        # Set initial progress
        compact_widget.set_progress(0, len(file_paths))
        compact_widget.set_filename("")

        # Store references for cleanup
        self._compact_dialog = dialog
        self._compact_widget = compact_widget

        # Show dialog
        dialog.show()
        QApplication.processEvents()

        # Start metadata loading in thread
        self._load_compact_metadata_in_thread(file_paths, use_extended)

    def _load_compact_metadata_in_thread(self, file_paths: list[str], use_extended: bool) -> None:
        """
        Load metadata in background thread with CompactWaitingWidget progress updates.

        Args:
            file_paths: List of file paths to scan
            use_extended: Whether to use extended metadata
        """
        if not hasattr(self.parent_window, 'metadata_manager'):
            logger.error("[CompactScan] No metadata_manager available")
            return

        metadata_manager = self.parent_window.metadata_manager

        # Get required components
        metadata_loader = getattr(self.parent_window, 'metadata_loader', None)
        metadata_cache = getattr(self.parent_window, 'metadata_cache', None)

        if not metadata_loader or not metadata_cache:
            logger.error("[CompactScan] Missing metadata_loader or metadata_cache")
            return

        from PyQt5.QtCore import QThread
        from widgets.metadata_worker import MetadataWorker

        # Create background thread
        self._compact_thread = QThread()

        # Create worker object
        self._compact_worker = MetadataWorker(
            reader=metadata_loader,
            metadata_cache=metadata_cache
        )

        # Give worker access to main window for FileItem updates
        self._compact_worker.main_window = self.parent_window

        # Set the worker's inputs
        self._compact_worker.file_path = file_paths
        self._compact_worker.use_extended = use_extended

        # Move worker to the thread context
        self._compact_worker.moveToThread(self._compact_thread)

        # Connect signals
        self._compact_thread.started.connect(self._compact_worker.run_batch)

        # Connect progress updates to CompactWaitingWidget
        self._compact_worker.progress.connect(self._on_compact_metadata_progress)

        # Connect completion
        self._compact_worker.finished.connect(self._handle_compact_metadata_finished)

        # Start thread
        self._compact_thread.start()

        logger.debug("[CompactScan] Background thread started")

    def _on_compact_metadata_progress(self, current: int, total: int) -> None:
        """
        Handle progress updates for CompactWaitingWidget.

        Args:
            current: Current file number (1-based)
            total: Total number of files
        """
        if not hasattr(self, '_compact_widget') or not self._compact_widget:
            return

        logger.debug(f"[CompactScan] Progress: {current}/{total}", extra={"dev_only": True})

        # Update progress bar and count
        self._compact_widget.set_progress(current, total)

        # Show filename of current file (current-1 because progress starts at 1)
        if hasattr(self, '_compact_worker') and self._compact_worker:
            if 0 <= current - 1 < len(self._compact_worker.file_path):
                import os
                filename = os.path.basename(self._compact_worker.file_path[current - 1])
                self._compact_widget.set_filename(filename)
            else:
                self._compact_widget.set_filename("")

        # Force UI update
        QApplication.processEvents()

    def _handle_compact_metadata_finished(self) -> None:
        """
        Handle completion of compact metadata loading.
        """
        logger.info("[CompactScan] Compact metadata loading finished")

        # Close dialog
        if hasattr(self, '_compact_dialog') and self._compact_dialog:
            self._compact_dialog.close()
            self._compact_dialog = None

        # Clean up worker and thread
        self._cleanup_compact_metadata_worker()

        # Update metadata tree view with the last selected file
        if (self.parent_window and
            hasattr(self.parent_window, 'metadata_tree_view')):
            self.parent_window.metadata_tree_view.refresh_metadata_from_selection()

        # Restore cursor
        QApplication.restoreOverrideCursor()

        logger.debug("[CompactScan] Compact metadata scan completed")

    def _cleanup_compact_metadata_worker(self) -> None:
        """
        Clean up compact metadata worker and thread.
        """
        if hasattr(self, '_compact_thread') and self._compact_thread:
            if self._compact_thread.isRunning():
                logger.debug("[CompactScan] Stopping compact thread...")
                self._compact_thread.quit()
                self._compact_thread.wait()
                logger.debug("[CompactScan] Compact thread stopped")

            self._compact_thread.deleteLater()
            self._compact_thread = None

        if hasattr(self, '_compact_worker') and self._compact_worker:
            self._compact_worker.deleteLater()
            self._compact_worker = None

        # Clean up widget reference
        if hasattr(self, '_compact_widget'):
            self._compact_widget = None

        logger.debug("[CompactScan] Compact worker cleanup completed")

    def _load_folder_with_progress(self, folder_path: str, merge_mode: bool) -> None:
        """Load folder with progress dialog (for recursive operations)."""
        logger.debug(f"[FileLoadManager] Loading folder with progress: {folder_path}")

        def on_files_loaded(file_paths: List[str]):
            logger.info(f"[FileLoadManager] Progress loading completed: {len(file_paths)} files")
            self._update_ui_with_files(file_paths, clear=not merge_mode)

        # Show progress dialog
        dialog = FileLoadingDialog(self.parent_window, on_files_loaded)
        dialog.load_files_with_options([folder_path], self.allowed_extensions, recursive=True)
        dialog.exec_()

    def _load_folder_with_wait_cursor(self, folder_path: str, merge_mode: bool) -> None:
        """Load folder with wait cursor only (for non-recursive operations)."""
        logger.debug(f"[FileLoadManager] Loading folder with wait cursor: {folder_path}")

        with wait_cursor():
            file_paths = self._get_files_from_folder(folder_path, recursive=False)
            self._update_ui_with_files(file_paths, clear=not merge_mode)

    def _count_files_in_folder(self, folder_path: str, recursive: bool = False) -> int:
        """
        Count total number of valid files in folder.
        Returns accurate count for progress bar decision.
        """
        count = 0
        if recursive:
            for root, _, filenames in os.walk(folder_path):
                count += sum(1 for f in filenames if self._is_allowed_extension(f))
        else:
            try:
                filenames = os.listdir(folder_path)
                count = sum(1 for f in filenames if self._is_allowed_extension(f))
            except OSError:
                pass
        return count

    def _get_files_from_folder(self, folder_path: str, recursive: bool = False) -> List[str]:
        """
        Get all valid files from folder.
        Returns list of file paths.
        """
        file_paths = []
        if recursive:
            for root, _, filenames in os.walk(folder_path):
                for filename in filenames:
                    if self._is_allowed_extension(filename):
                        file_paths.append(os.path.join(root, filename))
        else:
            try:
                for filename in os.listdir(folder_path):
                    if self._is_allowed_extension(filename):
                        full_path = os.path.join(folder_path, filename)
                        if os.path.isfile(full_path):
                            file_paths.append(full_path)
            except OSError:
                pass
        return file_paths

    def _is_allowed_extension(self, path: str) -> bool:
        """Check if file has allowed extension."""
        ext = os.path.splitext(path)[1].lower()
        if ext.startswith('.'):
            ext = ext[1:]
        return ext in self.allowed_extensions

    def _update_ui_with_files(self, file_paths: List[str], clear: bool = True) -> None:
        """
        Update UI with loaded files.
        Converts file paths to FileItem objects and updates the model.
        """
        if not file_paths:
            logger.info("[FileLoadManager] No files to update UI with")
            return

        logger.info(f"[FileLoadManager] Updating UI with {len(file_paths)} files (clear={clear})")

        # Convert file paths to FileItem objects
        file_items = []
        for path in file_paths:
            try:
                file_item = FileItem.from_path(path)
                file_items.append(file_item)
            except Exception as e:
                logger.error(f"Error creating FileItem for {path}: {e}")

        if not file_items:
            logger.warning("[FileLoadManager] No valid FileItem objects created")
            return

        # Update the model
        self._update_ui_after_load(file_items, clear=clear)

    def _update_ui_after_load(self, items: List[FileItem], clear: bool = True) -> None:
        """
        Update UI after loading files.
        Handles model updates and UI refresh.
        """
        if not hasattr(self.parent_window, 'file_model'):
            logger.error("[FileLoadManager] Parent window has no file_model attribute")
            return

        try:
            # Set current folder path from first file's directory
            if items and clear:
                first_file_path = items[0].full_path
                if first_file_path:
                    folder_path = os.path.dirname(first_file_path)
                    self.parent_window.current_folder_path = folder_path
                    logger.info(f"[FileLoadManager] Set current_folder_path to: {folder_path}")

                    # Check if this was a recursive load by looking for files in subdirectories
                    has_subdirectory_files = any(
                        os.path.dirname(item.full_path) != folder_path for item in items
                    )
                    self.parent_window.current_folder_is_recursive = has_subdirectory_files
                    logger.info(f"[FileLoadManager] Set recursive mode to: {has_subdirectory_files}")

            if clear:
                # Replace existing files
                self.parent_window.file_model.set_files(items)
                logger.info(f"[FileLoadManager] Replaced files with {len(items)} new items")
            else:
                # Add to existing files
                existing_files = self.parent_window.file_model.files
                combined_files = existing_files + items
                self.parent_window.file_model.set_files(combined_files)
                logger.info(f"[FileLoadManager] Added {len(items)} items to existing {len(existing_files)} files")

            # CRITICAL: Update all UI elements after file loading
            self._refresh_ui_after_file_load()

        except Exception as e:
            logger.error(f"[FileLoadManager] Error updating UI: {e}")

    def _refresh_ui_after_file_load(self) -> None:
        """
        Refresh all UI elements after files are loaded.
        This ensures placeholders are hidden, labels are updated, and selection works.
        """
        try:
            # Update files label (shows count)
            if hasattr(self.parent_window, 'update_files_label'):
                self.parent_window.update_files_label()
                logger.debug("[FileLoadManager] Updated files label")

            total_files = len(self.parent_window.file_model.files)

            # Hide file table placeholder when files are loaded
            if hasattr(self.parent_window, 'file_table_view'):
                if total_files > 0:
                    # Hide file table placeholder when files are loaded
                    self.parent_window.file_table_view.set_placeholder_visible(False)
                    logger.debug("[FileLoadManager] Hidden file table placeholder")
                else:
                    # Show file table placeholder when no files
                    self.parent_window.file_table_view.set_placeholder_visible(True)
                    logger.debug("[FileLoadManager] Shown file table placeholder")

            # Hide placeholders in preview tables (if files are loaded)
            if hasattr(self.parent_window, 'preview_tables_view'):
                if total_files > 0:
                    # Hide placeholders when files are loaded
                    self.parent_window.preview_tables_view._set_placeholders_visible(False)
                    logger.debug("[FileLoadManager] Hidden preview table placeholders")
                else:
                    # Show placeholders when no files
                    self.parent_window.preview_tables_view._set_placeholders_visible(True)
                    logger.debug("[FileLoadManager] Shown preview table placeholders")

            # Update preview tables
            if hasattr(self.parent_window, 'request_preview_update'):
                self.parent_window.request_preview_update()
                logger.debug("[FileLoadManager] Requested preview update")

            # Ensure file table selection works properly
            if hasattr(self.parent_window, 'file_table_view'):
                # Restore previous sorting state for consistency
                if (hasattr(self.parent_window, 'current_sort_column') and
                    hasattr(self.parent_window, 'current_sort_order')):
                    sort_column = self.parent_window.current_sort_column
                    sort_order = self.parent_window.current_sort_order
                    logger.debug(f"[FileLoadManager] Restoring sort state: column={sort_column}, order={sort_order}")

                    # Apply sorting through the model and header
                    self.parent_window.file_model.sort(sort_column, sort_order)
                    header = self.parent_window.file_table_view.horizontalHeader()
                    header.setSortIndicator(sort_column, sort_order)

                # Force refresh of the table view
                self.parent_window.file_table_view.viewport().update()

                # Reset selection state to ensure clicks work
                if hasattr(self.parent_window.file_table_view, '_sync_selection_safely'):
                    self.parent_window.file_table_view._sync_selection_safely()

                logger.debug("[FileLoadManager] Refreshed file table view")

            # Update metadata tree (clear it for new files)
            if hasattr(self.parent_window, 'metadata_tree_view'):
                if hasattr(self.parent_window.metadata_tree_view, 'refresh_metadata_from_selection'):
                    self.parent_window.metadata_tree_view.refresh_metadata_from_selection()
                    logger.debug("[FileLoadManager] Refreshed metadata tree")

            logger.info("[FileLoadManager] UI refresh completed successfully")

        except Exception as e:
            logger.error(f"[FileLoadManager] Error refreshing UI: {e}")

    def prepare_folder_load(self, folder_path: str, *, clear: bool = True) -> list[str]:
        """
        Prepare folder for loading by getting file list.
        Returns list of file paths without loading them into UI.
        """
        logger.info(f"[FileLoadManager] prepare_folder_load: {folder_path}")
        return self._get_files_from_folder(folder_path, recursive=False)

    def reload_current_folder(self) -> None:
        """Reload the current folder if available."""
        logger.info("[FileLoadManager] reload_current_folder called")
        # Implementation depends on how current folder is tracked

    def set_allowed_extensions(self, extensions: Set[str]) -> None:
        """Update the set of allowed file extensions."""
        self.allowed_extensions = extensions
        logger.info(f"[FileLoadManager] Updated allowed extensions: {extensions}")
