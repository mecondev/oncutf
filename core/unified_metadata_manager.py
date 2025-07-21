"""
Module: unified_metadata_manager.py

Author: Michael Economou
Date: 2025-07-06

Unified metadata management system combining MetadataManager and DirectMetadataLoader.
Provides centralized metadata operations with on-demand loading capabilities.

Features:
- Centralized metadata management operations
- On-demand metadata/hash loading
- Thread-based loading with progress tracking
- Immediate cache checking for instant icon display
- Simple, clean architecture
- Unified API for all metadata operations
"""

import os
from datetime import datetime
from typing import List, Optional, Set

from PyQt5.QtCore import QObject, pyqtSignal

from core.pyqt_imports import QApplication, Qt
from models.file_item import FileItem
from utils.logger_factory import get_cached_logger
from utils.metadata_cache_helper import MetadataCacheHelper
from utils.path_utils import paths_equal
from utils.file_status_helpers import get_metadata_for_file, get_hash_for_file, has_metadata, has_hash

logger = get_cached_logger(__name__)


class UnifiedMetadataManager(QObject):
    """
    Unified metadata management system.

    Combines the functionality of MetadataManager and DirectMetadataLoader
    to provide a single, coherent interface for all metadata operations.

    Features:
    - On-demand metadata/hash loading
    - Thread-based loading with progress tracking
    - Immediate cache checking for instant display
    - Centralized metadata management operations
    - Modifier-based metadata mode decisions
    - Dialog management for progress indication
    - Error handling and cleanup
    """

    # Signals
    metadata_loaded = pyqtSignal(str, dict)  # file_path, metadata
    loading_started = pyqtSignal(str)  # file_path
    loading_finished = pyqtSignal()

    def __init__(self, parent_window=None):
        """Initialize UnifiedMetadataManager with parent window reference."""
        super().__init__(parent_window)
        self.parent_window = parent_window
        self._cache_helper: Optional[MetadataCacheHelper] = None
        self._currently_loading: Set[str] = set()

        # State tracking
        self.force_extended_metadata = False
        self._metadata_cancelled = False  # Cancellation flag for metadata loading

        # Initialize metadata cache and exiftool wrapper
        self._metadata_cache = {}  # Cache for metadata results

        # Initialize ExifTool wrapper for single file operations
        from utils.exiftool_wrapper import ExifToolWrapper

        self._exiftool_wrapper = ExifToolWrapper()

        logger.info("[UnifiedMetadataManager] Initialized - unified metadata management")

    def initialize_cache_helper(self) -> None:
        """Initialize the cache helper if parent window is available."""
        if self.parent_window and hasattr(self.parent_window, "metadata_cache"):
            self._cache_helper = MetadataCacheHelper(self.parent_window.metadata_cache)
            logger.debug(
                "[UnifiedMetadataManager] Cache helper initialized", extra={"dev_only": True}
            )

    # =====================================
    # Cache Checking Methods
    # =====================================

    def check_cached_metadata(self, file_item: FileItem) -> Optional[dict]:
        """
        Check if metadata exists in cache without loading.

        Args:
            file_item: The file to check

        Returns:
            Metadata dict if cached, None if not available
        """
        try:
            return get_metadata_for_file(file_item.full_path)

        except Exception as e:
            logger.warning(
                f"[UnifiedMetadataManager] Error checking cache for {file_item.filename}: {e}"
            )
            return None

    def check_cached_hash(self, file_item: FileItem) -> Optional[str]:
        """
        Check if hash exists in cache without loading.

        Args:
            file_item: The file to check

        Returns:
            Hash string if cached, None if not available
        """
        try:
            return get_hash_for_file(file_item.full_path)

        except Exception as e:
            logger.warning(
                f"[UnifiedMetadataManager] Error checking hash cache for {file_item.filename}: {e}"
            )
            return None

    def has_cached_metadata(self, file_item: FileItem) -> bool:
        """
        Check if metadata exists in cache (fast check).

        Args:
            file_item: The file to check

        Returns:
            True if metadata exists in cache, False otherwise
        """
        try:
            return has_metadata(file_item.full_path)

        except Exception as e:
            logger.warning(
                f"[UnifiedMetadataManager] Error checking metadata existence for {file_item.filename}: {e}"
            )
            return False

    def has_cached_hash(self, file_item: FileItem) -> bool:
        """
        Check if hash exists in cache (fast check).

        Args:
            file_item: The file to check

        Returns:
            True if hash exists in cache, False otherwise
        """
        try:
            return has_hash(file_item.full_path)

        except Exception as e:
            logger.warning(
                f"[UnifiedMetadataManager] Error checking hash existence for {file_item.filename}: {e}"
            )
            return False

    # =====================================
    # Loading State Management
    # =====================================

    def is_running_metadata_task(self) -> bool:
        """
        Check if there's currently a metadata task running.

        Returns:
            bool: True if a metadata task is running, False otherwise
        """
        return len(self._currently_loading) > 0

    def is_loading(self) -> bool:
        """Check if any files are currently being loaded."""
        return len(self._currently_loading) > 0

    def reset_cancellation_flag(self) -> None:
        """Reset the metadata cancellation flag."""
        self._metadata_cancelled = False

    # =====================================
    # Mode Determination Methods
    # =====================================

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
            if self.parent_window and hasattr(self.parent_window, "modifier_state"):
                modifiers = self.parent_window.modifier_state
            else:
                modifiers = QApplication.keyboardModifiers()

        if modifiers == Qt.NoModifier:  # type: ignore
            modifiers = QApplication.keyboardModifiers()  # fallback to current

        ctrl = bool(modifiers & Qt.ControlModifier)  # type: ignore
        shift = bool(modifiers & Qt.ShiftModifier)  # type: ignore

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
            if self.parent_window and hasattr(self.parent_window, "modifier_state"):
                modifiers = self.parent_window.modifier_state
            else:
                modifiers = QApplication.keyboardModifiers()

        ctrl = bool(modifiers & Qt.ControlModifier)  # type: ignore
        shift = bool(modifiers & Qt.ShiftModifier)  # type: ignore
        return ctrl and shift

    # =====================================
    # Shortcut Methods
    # =====================================

    def shortcut_load_metadata(self) -> None:
        """
        Loads standard (non-extended) metadata for currently selected files.
        """
        if not self.parent_window:
            return

        # Use unified selection method
        selected_files = (
            self.parent_window.get_selected_files_ordered() if self.parent_window else []
        )

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
        selected_files = (
            self.parent_window.get_selected_files_ordered() if self.parent_window else []
        )

        if not selected_files:
            logger.info("[Shortcut] No files selected for extended metadata loading")
            return

        logger.info(f"[Shortcut] Loading extended metadata for {len(selected_files)} files")
        # Use intelligent loading with cache checking and smart UX
        self.load_metadata_for_items(selected_files, use_extended=True, source="shortcut")

    # =====================================
    # Main Loading Methods
    # =====================================

    def load_metadata_for_items(
        self, items: List[FileItem], use_extended: bool = False, source: str = "unknown"
    ) -> None:
        """
        Load metadata for the given FileItem objects using simple and fast approach.

        - Single file: Immediate loading with wait_cursor (fast and responsive)
        - Multiple files: Background worker with progress dialog

        Args:
            items: List of FileItem objects to load metadata for
            use_extended: Whether to use extended metadata loading
            source: Source of the request (for logging)
        """
        if not items:
            logger.warning("[UnifiedMetadataManager] No items provided for metadata loading")
            return

        # Reset cancellation flag for new metadata loading operation
        self.reset_cancellation_flag()

        # Check what items need loading vs what's already cached
        needs_loading = []

        for item in items:
            # Check cache for existing metadata
            cache_entry = (
                self.parent_window.metadata_cache.get_entry(item.full_path)
                if self.parent_window
                else None
            )

            if cache_entry and hasattr(cache_entry, "is_extended"):
                # If we have cache and it matches the requested type, skip loading
                if cache_entry.is_extended == use_extended:
                    continue

            needs_loading.append(item)

        # Get metadata tree view reference
        metadata_tree_view = (
            self.parent_window.metadata_tree_view
            if self.parent_window and hasattr(self.parent_window, "metadata_tree_view")
            else None
        )

        # If nothing needs loading, just handle display logic
        if not needs_loading:
            logger.info(f"[{source}] All {len(items)} files already cached")

            # Ενημέρωση εικονιδίων file table για να εμφανιστούν τα metadata icons
            if self.parent_window and hasattr(self.parent_window, "file_model"):
                self.parent_window.file_model.refresh_icons()

            # Always display metadata for cached items too
            if metadata_tree_view and items:
                # Always display metadata - same logic as loaded items
                display_file = items[0] if len(items) == 1 else items[-1]
                metadata_tree_view.display_file_metadata(display_file)

            return

        # Determine loading mode based on file count
        loading_mode = self.determine_loading_mode(len(needs_loading), use_extended)

        # Handle different loading modes using old system's simple approach
        if loading_mode == "single_file_wait_cursor":
            logger.info(
                f"[{source}] Loading metadata for single file with wait_cursor (extended={use_extended})"
            )

            from utils.cursor_helper import wait_cursor

            with wait_cursor():
                # Load metadata for the single file using ExifTool wrapper directly
                file_item = needs_loading[0]
                metadata = self._exiftool_wrapper.get_metadata(
                    file_item.full_path, use_extended=use_extended
                )

                if metadata:
                    # Mark metadata with loading mode for UI indicators
                    if use_extended and "__extended__" not in metadata:
                        metadata["__extended__"] = True
                    elif not use_extended and "__extended__" in metadata:
                        del metadata["__extended__"]

                    # Cache the result in both local and parent window caches
                    cache_key = (file_item.full_path, use_extended)
                    self._metadata_cache[cache_key] = metadata

                    # Also save to parent window's metadata_cache for UI display
                    if self.parent_window and hasattr(self.parent_window, "metadata_cache"):
                        self.parent_window.metadata_cache.set(
                            file_item.full_path, metadata, is_extended=use_extended
                        )

                    # Update the file item
                    logger.debug(f"[DEBUG] (before) file_item.metadata for {file_item.filename} (id={id(file_item)}): {getattr(file_item, 'metadata', None)}")
                    file_item.metadata = metadata
                    logger.debug(f"[DEBUG] (after) file_item.metadata for {file_item.filename} (id={id(file_item)}): {file_item.metadata}")

                    # Emit dataChanged signal to update UI icons immediately
                    if self.parent_window and hasattr(self.parent_window, "file_model"):
                        try:
                            # Find the row index and emit dataChanged for the entire row
                            for i, file in enumerate(self.parent_window.file_model.files):
                                if paths_equal(file.full_path, file_item.full_path):
                                    top_left = self.parent_window.file_model.index(i, 0)
                                    bottom_right = self.parent_window.file_model.index(
                                        i, self.parent_window.file_model.columnCount() - 1
                                    )
                                    self.parent_window.file_model.dataChanged.emit(
                                        top_left, bottom_right, [Qt.DecorationRole, Qt.ToolTipRole]
                                    )
                                    break
                        except Exception as e:
                            logger.warning(
                                f"[UnifiedMetadataManager] Failed to emit dataChanged for {file_item.filename}: {e}"
                            )

                    # Display metadata in tree view if available
                    if metadata_tree_view:
                        metadata_tree_view.display_file_metadata(file_item)

                    logger.info(f"[{source}] Successfully loaded metadata for {file_item.filename}")

        elif loading_mode == "multiple_files_dialog":
            logger.info(
                f"[{source}] Loading metadata for {len(needs_loading)} files with dialog (extended={use_extended})"
            )

            # Calculate total size for enhanced progress tracking
            from utils.file_size_calculator import calculate_files_total_size

            total_size = calculate_files_total_size(needs_loading)

            # Use progress dialog for large batches
            from utils.progress_dialog import ProgressDialog

            # Cancellation support
            self._metadata_cancelled = False

            def cancel_metadata_loading():
                self._metadata_cancelled = True
                logger.info("[UnifiedMetadataManager] Metadata loading cancelled by user")

            # Create progress dialog
            _loading_dialog = ProgressDialog.create_metadata_dialog(
                self.parent_window,
                is_extended=use_extended,
                cancel_callback=cancel_metadata_loading,
            )
            _loading_dialog.set_status(
                "Loading metadata..." if not use_extended else "Loading extended metadata..."
            )

            # Start enhanced tracking with total size
            _loading_dialog.start_progress_tracking(total_size)
            _loading_dialog.show()

            # Initialize incremental size tracking for better performance
            processed_size = 0

            # Process each file
            for i, file_item in enumerate(needs_loading):
                # Check for cancellation before processing each file
                if self._metadata_cancelled:
                    logger.info(
                        f"[UnifiedMetadataManager] Metadata loading cancelled at file {i+1}/{len(needs_loading)}"
                    )
                    _loading_dialog.close()
                    return

                # Add current file size to processed total
                try:
                    if hasattr(file_item, "file_size") and file_item.file_size is not None:
                        current_file_size = file_item.file_size
                    elif hasattr(file_item, "full_path") and os.path.exists(file_item.full_path):
                        current_file_size = os.path.getsize(file_item.full_path)
                        # Cache it for future use
                        if hasattr(file_item, "file_size"):
                            file_item.file_size = current_file_size
                    else:
                        current_file_size = 0

                    processed_size += current_file_size
                except (OSError, AttributeError):
                    current_file_size = 0

                # Update progress using unified method
                _loading_dialog.update_progress(
                    file_count=i + 1,
                    total_files=len(needs_loading),
                    processed_bytes=processed_size,
                    total_bytes=total_size,
                )
                _loading_dialog.set_filename(file_item.filename)
                _loading_dialog.set_count(i + 1, len(needs_loading))

                # Process events to update the dialog and handle cancellation
                if (i + 1) % 10 == 0 or current_file_size > 10 * 1024 * 1024:
                    from PyQt5.QtWidgets import QApplication

                    QApplication.processEvents()

                # Check again after processing events
                if self._metadata_cancelled:
                    logger.info(
                        f"[UnifiedMetadataManager] Metadata loading cancelled at file {i+1}/{len(needs_loading)}"
                    )
                    _loading_dialog.close()
                    return

                # Load metadata using ExifTool wrapper directly
                metadata = self._exiftool_wrapper.get_metadata(
                    file_item.full_path, use_extended=use_extended
                )

                if metadata:
                    # Mark metadata with loading mode for UI indicators
                    if use_extended and "__extended__" not in metadata:
                        metadata["__extended__"] = True
                    elif not use_extended and "__extended__" in metadata:
                        del metadata["__extended__"]

                    # Cache the result in both local and parent window caches
                    cache_key = (file_item.full_path, use_extended)
                    self._metadata_cache[cache_key] = metadata

                    # Also save to parent window's metadata_cache for UI display
                    if self.parent_window and hasattr(self.parent_window, "metadata_cache"):
                        self.parent_window.metadata_cache.set(
                            file_item.full_path, metadata, is_extended=use_extended
                        )

                    # Update the file item
                    logger.debug(f"[DEBUG] (before) file_item.metadata for {file_item.filename} (id={id(file_item)}): {getattr(file_item, 'metadata', None)}")
                    file_item.metadata = metadata
                    logger.debug(f"[DEBUG] (after) file_item.metadata for {file_item.filename} (id={id(file_item)}): {file_item.metadata}")

                    # Emit dataChanged signal to update UI icons
                    if self.parent_window and hasattr(self.parent_window, "file_model"):
                        try:
                            # Find the row index and emit dataChanged for the entire row
                            for j, file in enumerate(self.parent_window.file_model.files):
                                if paths_equal(file.full_path, file_item.full_path):
                                    top_left = self.parent_window.file_model.index(j, 0)
                                    bottom_right = self.parent_window.file_model.index(
                                        j, self.parent_window.file_model.columnCount() - 1
                                    )
                                    self.parent_window.file_model.dataChanged.emit(
                                        top_left, bottom_right, [Qt.DecorationRole, Qt.ToolTipRole]
                                    )
                                    break
                        except Exception as e:
                            logger.warning(
                                f"[UnifiedMetadataManager] Failed to emit dataChanged for {file_item.filename}: {e}"
                            )

            # Close the progress dialog
            _loading_dialog.close()

            # Display metadata for the last processed file if available
            if metadata_tree_view and needs_loading:
                display_file = needs_loading[-1]
                metadata_tree_view.display_file_metadata(display_file)

            logger.info(f"[{source}] Successfully loaded metadata for {len(needs_loading)} files")

        # Always emit signal to indicate loading is finished
        self.loading_finished.emit()

    def load_hashes_for_files(self, files: List[FileItem], source: str = "user_request") -> None:
        """
        Load hashes for files that don't have them cached.

        Args:
            files: List of files to load hashes for
            source: Source of request for logging
        """
        if not files:
            return

        # Filter files that need loading
        files_to_load = []
        for file_item in files:
            if file_item.full_path not in self._currently_loading:
                cached = self.check_cached_hash(file_item)
                if not cached:
                    files_to_load.append(file_item)
                    self._currently_loading.add(file_item.full_path)

        if not files_to_load:
            logger.info(
                f"[UnifiedMetadataManager] All {len(files)} files already have cached hashes"
            )
            return

        logger.info(
            f"[UnifiedMetadataManager] Loading hashes for {len(files_to_load)} files ({source})"
        )

        # Show progress dialog for multiple files
        if len(files_to_load) > 1:
            self._show_hash_progress_dialog(files_to_load, source)
        else:
            # Single file - load directly
            self._start_hash_loading(files_to_load, source)

    # =====================================
    # Progress Dialog Methods
    # =====================================

    def _show_metadata_progress_dialog(
        self, files: List[FileItem], use_extended: bool, source: str
    ) -> None:
        """Show progress dialog for metadata loading."""
        try:

            def cancel_metadata_loading():
                self._cancel_current_loading()

            # Create progress dialog
            from utils.progress_dialog import ProgressDialog

            _loading_dialog = ProgressDialog.create_metadata_dialog(
                self.parent_window,
                is_extended=use_extended,
                cancel_callback=cancel_metadata_loading,
            )

            # Start loading with progress tracking
            self._start_metadata_loading_with_progress(files, use_extended, source)

        except Exception as e:
            logger.error(f"[UnifiedMetadataManager] Error showing metadata progress dialog: {e}")
            # Fallback to direct loading
            self._start_metadata_loading(files, use_extended, source)

    def _show_hash_progress_dialog(self, files: List[FileItem], source: str) -> None:
        """Show progress dialog for hash loading."""
        try:

            def cancel_hash_loading():
                self._cancel_current_loading()

            # Create progress dialog
            from utils.progress_dialog import ProgressDialog

            _loading_dialog = ProgressDialog.create_hash_dialog(
                self.parent_window, cancel_callback=cancel_hash_loading
            )

            # Start loading with progress tracking
            self._start_hash_loading_with_progress(files, source)

        except Exception as e:
            logger.error(f"[UnifiedMetadataManager] Error showing hash progress dialog: {e}")
            # Fallback to direct loading
            self._start_hash_loading(files, source)

    # =====================================
    # Worker Loading Methods
    # =====================================

    def _start_metadata_loading_with_progress(
        self, files: List[FileItem], use_extended: bool, source: str
    ) -> None:
        """Start metadata loading with progress tracking."""
        # This will be implemented to use the existing metadata worker
        # For now, fallback to direct loading
        self._start_metadata_loading(files, use_extended, source)

    def _start_hash_loading_with_progress(self, files: List[FileItem], source: str) -> None:
        """Start hash loading with progress tracking."""
        # This will be implemented to use the existing hash worker
        # For now, fallback to direct loading
        self._start_hash_loading(files, source)

    def _start_metadata_loading(
        self, files: List[FileItem], use_extended: bool, source: str
    ) -> None:
        """Start metadata loading using existing metadata worker."""
        if not files:
            return

        try:
            # Use existing metadata worker
            from core.pyqt_imports import QThread
            from utils.metadata_loader import MetadataLoader
            from widgets.metadata_worker import MetadataWorker

            # Create metadata loader
            metadata_loader = MetadataLoader()

            # Create worker with named arguments as expected by constructor
            self._metadata_worker = MetadataWorker(
                reader=metadata_loader,
                metadata_cache=self.parent_window.metadata_cache if self.parent_window else None,
                parent=None,  # No parent to avoid moveToThread issues
            )

            # Set additional properties after creation
            self._metadata_worker.file_path = [item.full_path for item in files]
            self._metadata_worker.use_extended = use_extended
            self._metadata_worker.main_window = self.parent_window

            # Create thread
            self._metadata_thread = QThread()

            # Move worker to thread
            self._metadata_worker.moveToThread(self._metadata_thread)

            # Connect signals
            self._metadata_thread.started.connect(self._metadata_worker.run_batch)
            self._metadata_worker.finished.connect(self._on_metadata_finished)
            self._metadata_worker.file_metadata_loaded.connect(self._on_file_metadata_loaded)

            # Start thread
            self._metadata_thread.start()

            logger.info(f"[UnifiedMetadataManager] Started metadata loading for {len(files)} files")

        except Exception as e:
            logger.error(f"[UnifiedMetadataManager] Error starting metadata loading: {e}")
            # Clean up loading state
            for file_item in files:
                self._currently_loading.discard(file_item.full_path)

    def _start_hash_loading(self, files: List[FileItem], source: str) -> None:
        """Start hash loading using existing hash worker."""
        if not files:
            return

        try:
            # Use existing hash worker
            from core.hash_worker import HashWorker
            from core.pyqt_imports import QThread

            # Create worker and thread
            self._hash_worker = HashWorker(files)
            self._hash_thread = QThread()

            # Move worker to thread
            self._hash_worker.moveToThread(self._hash_thread)

            # Connect signals
            self._hash_thread.started.connect(self._hash_worker.run)
            self._hash_worker.finished.connect(self._on_hash_finished)
            self._hash_worker.file_processed.connect(self._on_file_hash_calculated)

            # Start thread
            self._hash_thread.start()

            logger.info(f"[UnifiedMetadataManager] Started hash loading for {len(files)} files")

        except Exception as e:
            logger.error(f"[UnifiedMetadataManager] Error starting hash loading: {e}")
            # Clean up loading state
            for file_item in files:
                self._currently_loading.discard(file_item.full_path)

    # =====================================
    # Progress Tracking Methods
    # =====================================

    def _on_metadata_progress(self, current: int, total: int) -> None:
        """Handle metadata loading progress updates."""
        # This will be connected to progress dialog updates

    def _on_metadata_size_progress(self, processed: int, total: int) -> None:
        """Handle metadata size progress updates."""
        # This will be connected to progress dialog updates

    def _on_hash_progress(self, current: int, total: int) -> None:
        """Handle hash loading progress updates."""
        # This will be connected to progress dialog updates

    def _on_hash_size_progress(self, processed: int, total: int) -> None:
        """Handle hash size progress updates."""
        # This will be connected to progress dialog updates

    def _cancel_current_loading(self) -> None:
        """Cancel current loading operation."""
        self._metadata_cancelled = True

        # Cancel metadata worker if running
        if hasattr(self, "_metadata_worker") and self._metadata_worker:
            self._metadata_worker.cancel()

        # Cancel hash worker if running
        if hasattr(self, "_hash_worker") and self._hash_worker:
            self._hash_worker.cancel()

        logger.info("[UnifiedMetadataManager] Loading operation cancelled")

    # =====================================
    # Completion Handlers
    # =====================================

    def _on_file_metadata_loaded(self, file_path: str) -> None:
        """Handle individual file metadata loaded."""
        # Remove from loading set
        self._currently_loading.discard(file_path)

        # Emit signal
        self.loading_started.emit(file_path)

        # Update UI if needed - use efficient single file icon refresh
        if self.parent_window:
            # Update file table model icons for this specific file
            if hasattr(self.parent_window, "file_model"):
                if hasattr(self.parent_window.file_model, "refresh_icon_for_file"):
                    self.parent_window.file_model.refresh_icon_for_file(file_path)
                else:
                    # Fallback to full refresh if method not available
                    self.parent_window.file_model.refresh_icons()

        logger.debug(
            f"[UnifiedMetadataManager] Metadata loaded for {file_path}", extra={"dev_only": True}
        )

    def _on_file_hash_calculated(self, file_path: str) -> None:
        """Handle individual file hash calculated."""
        # Remove from loading set
        self._currently_loading.discard(file_path)

        # Update UI if needed - use efficient single file icon refresh
        if self.parent_window:
            # Update file table model icons for this specific file
            if hasattr(self.parent_window, "file_model"):
                if hasattr(self.parent_window.file_model, "refresh_icon_for_file"):
                    self.parent_window.file_model.refresh_icon_for_file(file_path)
                else:
                    # Fallback to full refresh if method not available
                    self.parent_window.file_model.refresh_icons()

        logger.debug(
            f"[UnifiedMetadataManager] Hash calculated for {file_path}", extra={"dev_only": True}
        )

    def _on_metadata_finished(self) -> None:
        """Handle metadata loading completion."""
        # Clean up worker and thread
        self._cleanup_metadata_worker_and_thread()

        # Emit finished signal
        self.loading_finished.emit()

        # Update UI
        if self.parent_window:
            # Update file table model
            if hasattr(self.parent_window, "file_model"):
                self.parent_window.file_model.refresh_icons()

            # Update metadata tree view
            if hasattr(self.parent_window, "metadata_tree_view"):
                self.parent_window.metadata_tree_view.handle_metadata_load_completion(
                    None, "metadata_loading"
                )

        logger.info("[UnifiedMetadataManager] Metadata loading completed")

    def _on_hash_finished(self) -> None:
        """Handle hash loading completion."""
        # Clean up worker and thread
        self._cleanup_hash_worker_and_thread()

        # Emit finished signal
        self.loading_finished.emit()

        # Update UI
        if self.parent_window:
            # Update file table model
            if hasattr(self.parent_window, "file_model"):
                self.parent_window.file_model.refresh_icons()

            # Notify preview manager about hash calculation completion
            if (
                hasattr(self.parent_window, "preview_manager")
                and self.parent_window.preview_manager
            ):
                self.parent_window.preview_manager.on_hash_calculation_completed()

        logger.info("[UnifiedMetadataManager] Hash loading completed")

    def _cleanup_metadata_worker_and_thread(self) -> None:
        """Clean up metadata worker and thread."""
        if hasattr(self, "_metadata_worker") and self._metadata_worker:
            self._metadata_worker.deleteLater()
            self._metadata_worker = None

        if hasattr(self, "_metadata_thread") and self._metadata_thread:
            self._metadata_thread.quit()
            self._metadata_thread.wait()
            self._metadata_thread.deleteLater()
            self._metadata_thread = None

    def _cleanup_hash_worker_and_thread(self) -> None:
        """Clean up hash worker and thread."""
        if hasattr(self, "_hash_worker") and self._hash_worker:
            self._hash_worker.deleteLater()
            self._hash_worker = None

        if hasattr(self, "_hash_thread") and self._hash_thread:
            self._hash_thread.quit()
            self._hash_thread.wait()
            self._hash_thread.deleteLater()
            self._hash_thread = None

    # =====================================
    # Metadata Saving Methods
    # =====================================

    def save_metadata_for_selected(self) -> None:
        """Save metadata for selected files."""
        if not self.parent_window:
            return

        # Get selected files
        selected_files = (
            self.parent_window.get_selected_files_ordered() if self.parent_window else []
        )

        if not selected_files:
            logger.info("[UnifiedMetadataManager] No files selected for metadata saving")
            return

        # Get metadata tree view
        metadata_tree_view = getattr(self.parent_window, "metadata_tree_view", None)
        if not metadata_tree_view:
            logger.warning("[UnifiedMetadataManager] No metadata tree view available")
            return

        # Get modified metadata
        all_modified_metadata = metadata_tree_view.get_all_modified_metadata_for_files()

        if not all_modified_metadata:
            logger.info("[UnifiedMetadataManager] No modified metadata to save")
            return

        # Filter files that have modifications
        files_to_save = []
        for file_item in selected_files:
            if file_item.full_path in all_modified_metadata:
                files_to_save.append(file_item)

        if not files_to_save:
            logger.info("[UnifiedMetadataManager] No selected files have modified metadata")
            return

        logger.info(
            f"[UnifiedMetadataManager] Saving metadata for {len(files_to_save)} selected files"
        )
        self._save_metadata_files(files_to_save, all_modified_metadata)

    def save_all_modified_metadata(self) -> None:
        """Save all modified metadata across all files."""
        if not self.parent_window:
            return

        # Get metadata tree view
        metadata_tree_view = getattr(self.parent_window, "metadata_tree_view", None)
        if not metadata_tree_view:
            logger.warning("[UnifiedMetadataManager] No metadata tree view available")
            return

        # Get all modified metadata
        all_modified_metadata = metadata_tree_view.get_all_modified_metadata_for_files()

        if not all_modified_metadata:
            logger.info("[UnifiedMetadataManager] No modified metadata to save")
            return

        # Get all files that have modifications
        files_to_save = []
        file_model = getattr(self.parent_window, "file_model", None)
        if file_model and hasattr(file_model, "files"):
            for file_item in file_model.files:
                if file_item.full_path in all_modified_metadata:
                    files_to_save.append(file_item)

        if not files_to_save:
            logger.info("[UnifiedMetadataManager] No files with modified metadata found")
            return

        logger.info(
            f"[UnifiedMetadataManager] Saving metadata for {len(files_to_save)} files with modifications"
        )
        self._save_metadata_files(files_to_save, all_modified_metadata)

    def _save_metadata_files(self, files_to_save: list, all_modified_metadata: dict) -> None:
        """Save metadata files using ExifTool."""
        if not files_to_save:
            return

        success_count = 0
        failed_files = []

        try:
            # Process each file
            for file_item in files_to_save:
                file_path = file_item.full_path

                # Get modifications for this file
                modifications = self._get_modified_metadata_for_file(
                    file_path, all_modified_metadata
                )

                if not modifications:
                    continue

                try:
                    # Save using ExifTool
                    success = self._exiftool_wrapper.write_metadata(file_path, modifications)

                    if success:
                        success_count += 1
                        self._update_file_after_save(file_item, modifications)
                        logger.debug(
                            f"[UnifiedMetadataManager] Successfully saved metadata for {file_item.filename}",
                            extra={"dev_only": True},
                        )
                    else:
                        failed_files.append(file_item.filename)
                        logger.warning(
                            f"[UnifiedMetadataManager] Failed to save metadata for {file_item.filename}"
                        )

                except Exception as e:
                    failed_files.append(file_item.filename)
                    logger.error(
                        f"[UnifiedMetadataManager] Error saving metadata for {file_item.filename}: {e}"
                    )

        except Exception as e:
            logger.error(f"[UnifiedMetadataManager] Error in metadata saving process: {e}")

        # Show results
        self._show_save_results(success_count, failed_files, files_to_save)

        # Record save operation in command system for undo/redo
        if success_count > 0:
            try:
                from core.metadata_command_manager import get_metadata_command_manager
                from core.metadata_commands import SaveMetadataCommand

                command_manager = get_metadata_command_manager()
                if command_manager and SaveMetadataCommand:
                    # Create save command with successful saves
                    successful_files = []
                    successful_metadata = {}

                    for file_item in files_to_save:
                        if file_item.filename not in failed_files:
                            successful_files.append(file_item.full_path)
                            modifications = self._get_modified_metadata_for_file(
                                file_item.full_path, all_modified_metadata
                            )
                            if modifications:
                                successful_metadata[file_item.full_path] = modifications

                    if successful_files:
                        save_command = SaveMetadataCommand(
                            file_paths=successful_files, saved_metadata=successful_metadata
                        )

                        # Execute command (this just records the save operation)
                        command_manager.execute_command(save_command)
                        logger.debug(
                            f"[UnifiedMetadataManager] Recorded save command for {len(successful_files)} files",
                            extra={"dev_only": True},
                        )

            except Exception as e:
                logger.warning(f"[UnifiedMetadataManager] Error recording save command: {e}")

    def _get_modified_metadata_for_file(self, file_path: str, all_modified_metadata: dict) -> dict:
        """Get modified metadata for a specific file."""
        return all_modified_metadata.get(file_path, {})

    def _update_file_after_save(self, file_item, saved_metadata: dict = None):
        """
        Update file item after successful metadata save.

        Args:
            file_item: The FileItem that was saved
            saved_metadata: The metadata that was actually saved to the file
        """
        # CRITICAL: Update both UI cache and persistent cache with saved values
        if saved_metadata:
            # Step 1: Update UI cache (metadata_cache)
            if hasattr(self.parent_window, "metadata_cache"):
                cache = self.parent_window.metadata_cache
                metadata_entry = cache.get_entry(file_item.full_path)

                if metadata_entry and hasattr(metadata_entry, "data"):
                    logger.debug(
                        f"[UnifiedMetadataManager] Updating UI cache with saved metadata for: {file_item.filename}",
                        extra={"dev_only": True},
                    )

                    # Update the cache data with the values that were actually saved
                    for key_path, new_value in saved_metadata.items():
                        logger.debug(
                            f"[UnifiedMetadataManager] Updating UI cache: {key_path} = {new_value}",
                            extra={"dev_only": True},
                        )

                        # Handle nested keys (e.g., "EXIF:Rotation")
                        if "/" in key_path or ":" in key_path:
                            # Split by either / or : to handle both formats
                            if "/" in key_path:
                                parts = key_path.split("/", 1)
                            else:
                                parts = key_path.split(":", 1)

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

            # Step 2: Update persistent cache (CRITICAL for cross-session persistence)
            try:
                from core.persistent_metadata_cache import get_persistent_metadata_cache

                persistent_cache = get_persistent_metadata_cache()

                if persistent_cache:
                    # Get current cached metadata
                    current_metadata = persistent_cache.get(file_item.full_path)

                    if current_metadata:
                        # Update the current metadata with saved values
                        updated_metadata = dict(current_metadata)

                        for key_path, new_value in saved_metadata.items():
                            logger.debug(
                                f"[UnifiedMetadataManager] Updating persistent cache: {key_path} = {new_value}",
                                extra={"dev_only": True},
                            )

                            # Handle nested keys (e.g., "EXIF:Rotation")
                            if "/" in key_path or ":" in key_path:
                                # For persistent cache, convert colon-separated keys to forward slash
                                key_path_normalized = key_path.replace(":", "/")

                                if "/" in key_path_normalized:
                                    parts = key_path_normalized.split("/", 1)
                                    if len(parts) == 2:
                                        group, key = parts
                                        if group not in updated_metadata:
                                            updated_metadata[group] = {}
                                        if isinstance(updated_metadata[group], dict):
                                            updated_metadata[group][key] = new_value
                                        else:
                                            # If group is not a dict, make it one
                                            updated_metadata[group] = {key: new_value}
                                    else:
                                        # Fallback: treat as top-level key
                                        updated_metadata[key_path] = new_value
                                else:
                                    # Top-level key
                                    updated_metadata[key_path] = new_value
                            else:
                                # Top-level key (e.g., "Rotation")
                                updated_metadata[key_path] = new_value

                        # Save updated metadata back to persistent cache
                        persistent_cache.set(
                            file_item.full_path, updated_metadata, is_extended=False
                        )
                        logger.debug(
                            f"[UnifiedMetadataManager] Updated persistent cache for: {file_item.filename}",
                            extra={"dev_only": True},
                        )
                    else:
                        logger.warning(
                            f"[UnifiedMetadataManager] No existing metadata in persistent cache for: {file_item.filename}"
                        )

            except Exception as e:
                logger.warning(f"[UnifiedMetadataManager] Failed to update persistent cache: {e}")

        # Clear modifications in tree view
        if hasattr(self.parent_window, "metadata_tree_view"):
            self.parent_window.metadata_tree_view.clear_modifications_for_file(file_item.full_path)

        # Update file modification time
        try:
            file_item.date_modified = datetime.fromtimestamp(os.path.getmtime(file_item.full_path))
        except Exception as e:
            logger.warning(
                f"[UnifiedMetadataManager] Could not update modification time for {file_item.filename}: {e}"
            )

        # Force refresh metadata view if this file is currently displayed
        if (
            hasattr(self.parent_window, "metadata_tree_view")
            and hasattr(self.parent_window.metadata_tree_view, "_current_file_path")
            and self.parent_window.metadata_tree_view._current_file_path == file_item.full_path
        ):

            logger.debug(
                f"[UnifiedMetadataManager] Refreshing metadata view for updated file: {file_item.filename}",
                extra={"dev_only": True},
            )

            # Get updated cache data to refresh the display
            if hasattr(self.parent_window, "metadata_cache"):
                metadata_entry = self.parent_window.metadata_cache.get_entry(file_item.full_path)
                if metadata_entry and hasattr(metadata_entry, "data"):
                    display_data = dict(metadata_entry.data)
                    display_data["FileName"] = file_item.filename
                    self.parent_window.metadata_tree_view.display_metadata(
                        display_data, context="after_save"
                    )

    def _show_save_results(self, success_count, failed_files, files_to_save):
        """Show results of metadata save operation."""
        if success_count > 0:
            logger.info(
                f"[UnifiedMetadataManager] Successfully saved metadata for {success_count} files"
            )

            # Update status bar
            if self.parent_window and hasattr(self.parent_window, "status_bar"):
                self.parent_window.status_bar.showMessage(
                    f"Metadata saved for {success_count} files", 3000
                )

        if failed_files:
            logger.warning(
                f"[UnifiedMetadataManager] Failed to save metadata for {len(failed_files)} files: {failed_files}"
            )

            # Show error message
            if self.parent_window:
                from widgets.custom_message_dialog import CustomMsgDialog

                CustomMsgDialog.show_error(
                    self.parent_window,
                    "Metadata Save Error",
                    f"Failed to save metadata for {len(failed_files)} files.\n\n"
                    f"Files: {', '.join(failed_files[:5])}"
                    f"{'...' if len(failed_files) > 5 else ''}",
                )

    # =====================================
    # Cleanup Methods
    # =====================================

    def cleanup(self) -> None:
        """Clean up resources."""
        # Cancel any running operations
        self._cancel_current_loading()

        # Clean up workers
        self._cleanup_metadata_worker_and_thread()
        self._cleanup_hash_worker_and_thread()

        # Clean up ExifTool wrapper
        if hasattr(self, "_exiftool_wrapper") and self._exiftool_wrapper:
            self._exiftool_wrapper.close()

        # Clear loading state
        self._currently_loading.clear()

        logger.info("[UnifiedMetadataManager] Cleanup completed")


# =====================================
# Factory Functions
# =====================================

_unified_metadata_manager = None


def get_unified_metadata_manager(parent_window=None) -> UnifiedMetadataManager:
    """Get or create the unified metadata manager instance."""
    global _unified_metadata_manager
    if _unified_metadata_manager is None:
        _unified_metadata_manager = UnifiedMetadataManager(parent_window)
    return _unified_metadata_manager


def cleanup_unified_metadata_manager() -> None:
    """Clean up the unified metadata manager instance."""
    global _unified_metadata_manager
    if _unified_metadata_manager:
        _unified_metadata_manager.cleanup()
        _unified_metadata_manager = None
