"""
Module: direct_metadata_loader.py

Author: Michael Economou
Date: 2025-07-06

Direct metadata loader for on-demand metadata/hash loading.
Provides simple, fast metadata loading without automatic background processing.

Features:
- No automatic loading on folder open
- On-demand loading only when requested by user
- Immediate cache checking for instant icon display
- Thread-based loading for UI responsiveness
- Simple, clean architecture
"""

from PyQt5.QtCore import QObject, QThread, pyqtSignal

from models.file_item import FileItem
from utils.file_status_helpers import (
    get_hash_for_file,
    get_metadata_for_file,
    has_hash,
    has_metadata,
)
from utils.logger_factory import get_cached_logger
from utils.metadata_cache_helper import MetadataCacheHelper

logger = get_cached_logger(__name__)


class DirectMetadataLoader(QObject):
    """
    Simple, direct metadata loader for on-demand loading.

    Only loads metadata/hash when explicitly requested by user.
    Checks cache first for instant display, loads missing data in background.
    """

    # Signals
    metadata_loaded = pyqtSignal(str, dict)  # file_path, metadata
    loading_started = pyqtSignal(str)  # file_path
    loading_finished = pyqtSignal()

    def __init__(self, parent_window=None):
        super().__init__(parent_window)
        self.parent_window = parent_window
        self._cache_helper: MetadataCacheHelper | None = None
        self._currently_loading: set[str] = set()

        logger.info("[DirectMetadataLoader] Initialized - no automatic loading")

    def initialize_cache_helper(self) -> None:
        """Initialize the cache helper if parent window is available."""
        if self.parent_window and hasattr(self.parent_window, "metadata_cache"):
            self._cache_helper = MetadataCacheHelper(self.parent_window.metadata_cache)
            logger.debug("[DirectMetadataLoader] Cache helper initialized")

    def check_cached_metadata(self, file_item: FileItem) -> dict | None:
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
                f"[DirectMetadataLoader] Error checking cache for {file_item.filename}: {e}"
            )
            return None

    def check_cached_hash(self, file_item: FileItem) -> str | None:
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
                f"[DirectMetadataLoader] Error checking hash cache for {file_item.filename}: {e}"
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
                f"[DirectMetadataLoader] Error checking metadata existence for {file_item.filename}: {e}"
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
                f"[DirectMetadataLoader] Error checking hash existence for {file_item.filename}: {e}"
            )
            return False

    def load_metadata_for_files(
        self, files: list[FileItem], use_extended: bool = False, source: str = "user_request"
    ) -> None:
        """
        Load metadata for files that don't have it cached.

        Args:
            files: List of files to load metadata for
            use_extended: Whether to use extended metadata
            source: Source of request for logging
        """
        if not files:
            return

        # Filter files that need loading
        files_to_load = []
        for file_item in files:
            if file_item.full_path not in self._currently_loading:
                cached = self.check_cached_metadata(file_item)
                if not cached:
                    files_to_load.append(file_item)
                    self._currently_loading.add(file_item.full_path)

        if not files_to_load:
            logger.info(
                f"[DirectMetadataLoader] All {len(files)} files already have cached metadata"
            )
            return

        logger.info(
            f"[DirectMetadataLoader] Loading metadata for {len(files_to_load)} files ({source})"
        )

        # Show progress dialog for multiple files
        if len(files_to_load) > 1:
            self._show_metadata_progress_dialog(files_to_load, use_extended, source)
        else:
            # Single file - no progress dialog needed
            self._start_metadata_loading(files_to_load, use_extended, source)

    def _show_metadata_progress_dialog(
        self, files: list[FileItem], use_extended: bool, source: str
    ) -> None:
        """Show progress dialog for metadata loading."""
        try:
            from utils.progress_dialog import ProgressDialog

            # Create cancel callback
            def cancel_metadata_loading():
                logger.info("[DirectMetadataLoader] Metadata loading cancelled by user")
                self._cancel_current_loading()

            # Create progress dialog
            self._progress_dialog = ProgressDialog.create_metadata_dialog(
                parent=self.parent_window,
                is_extended=use_extended,
                cancel_callback=cancel_metadata_loading,
                show_enhanced_info=True,
            )

            # Set initial status
            operation_name = "Extended Metadata" if use_extended else "Metadata"
            self._progress_dialog.set_status(f"Loading {operation_name}...")
            self._progress_dialog.set_count(0, len(files))

            # Calculate total size for progress tracking
            total_size = sum(getattr(f, "size", 0) for f in files)
            self._progress_dialog.start_progress_tracking(total_size)

            # Show dialog
            from utils.dialog_utils import show_dialog_smooth

            show_dialog_smooth(self._progress_dialog)

            # Start loading with progress tracking
            self._start_metadata_loading_with_progress(files, use_extended, source)

        except Exception as e:
            logger.error(f"[DirectMetadataLoader] Error showing progress dialog: {e}")
            # Fallback to loading without progress dialog
            self._start_metadata_loading(files, use_extended, source)

    def _start_metadata_loading_with_progress(
        self, files: list[FileItem], use_extended: bool, source: str
    ) -> None:
        """Start metadata loading with progress tracking."""
        from utils.metadata_loader import MetadataLoader
        from widgets.metadata_worker import MetadataWorker

        # Create worker and thread
        self._metadata_thread = QThread()
        self._metadata_worker = MetadataWorker(
            reader=MetadataLoader(),
            metadata_cache=self.parent_window.metadata_cache,
            parent=None,  # No parent to avoid moveToThread issues
        )

        # Set up worker
        self._metadata_worker.file_path = [f.full_path for f in files]
        self._metadata_worker.use_extended = use_extended
        self._metadata_worker.main_window = self.parent_window

        # Connect progress signals
        if hasattr(self, "_progress_dialog") and self._progress_dialog:
            self._metadata_worker.progress.connect(
                lambda current, total: self._on_metadata_progress(current, total)
            )
            self._metadata_worker.size_progress.connect(
                lambda processed, total: self._on_metadata_size_progress(processed, total)
            )

        # Connect completion signals
        self._metadata_worker.file_metadata_loaded.connect(self._on_file_metadata_loaded)
        self._metadata_worker.finished.connect(self._on_metadata_finished)

        # Move worker to thread and start
        self._metadata_worker.moveToThread(self._metadata_thread)
        self._metadata_thread.started.connect(self._metadata_worker.run_batch)
        self._metadata_worker.finished.connect(self._metadata_thread.quit)
        self._metadata_worker.finished.connect(self._metadata_worker.deleteLater)
        self._metadata_thread.finished.connect(self._metadata_thread.deleteLater)

        # Start the thread
        self._metadata_thread.start()

    def _on_metadata_progress(self, current: int, total: int) -> None:
        """Handle metadata loading progress updates."""
        if hasattr(self, "_progress_dialog") and self._progress_dialog:
            self._progress_dialog.set_count(current, total)
            self._progress_dialog.set_progress(current, total)

    def _on_metadata_size_progress(self, processed: int, total: int) -> None:
        """Handle metadata loading size progress updates."""
        if hasattr(self, "_progress_dialog") and self._progress_dialog:
            self._progress_dialog.set_size_info(processed, total)

    def _cancel_current_loading(self) -> None:
        """Cancel current loading operation."""
        if hasattr(self, "_metadata_worker") and self._metadata_worker:
            self._metadata_worker.cancel()
        if hasattr(self, "_hash_worker") and self._hash_worker:
            self._hash_worker.cancel()

        # Clear loading flags
        self._currently_loading.clear()

    def load_hashes_for_files(self, files: list[FileItem], source: str = "user_request") -> None:
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
            hash_key = f"hash_{file_item.full_path}"
            if hash_key not in self._currently_loading:
                cached = self.check_cached_hash(file_item)
                if not cached:
                    files_to_load.append(file_item)
                    self._currently_loading.add(hash_key)

        if not files_to_load:
            logger.info(f"[DirectMetadataLoader] All {len(files)} files already have cached hashes")
            return

        logger.info(
            f"[DirectMetadataLoader] Loading hashes for {len(files_to_load)} files ({source})"
        )

        # Show progress dialog for multiple files
        if len(files_to_load) > 1:
            self._show_hash_progress_dialog(files_to_load, source)
        else:
            # Single file - no progress dialog needed
            self._start_hash_loading(files_to_load, source)

    def _show_hash_progress_dialog(self, files: list[FileItem], source: str) -> None:
        """Show progress dialog for hash loading."""
        try:
            from utils.progress_dialog import ProgressDialog

            # Create cancel callback
            def cancel_hash_loading():
                logger.info("[DirectMetadataLoader] Hash loading cancelled by user")
                self._cancel_current_loading()

            # Create progress dialog
            self._progress_dialog = ProgressDialog.create_hash_dialog(
                parent=self.parent_window,
                cancel_callback=cancel_hash_loading,
                show_enhanced_info=True,
            )

            # Set initial status
            self._progress_dialog.set_status("Calculating Hashes...")
            self._progress_dialog.set_count(0, len(files))

            # Calculate total size for progress tracking
            total_size = sum(getattr(f, "size", 0) for f in files)
            self._progress_dialog.start_progress_tracking(total_size)

            # Show dialog
            from utils.dialog_utils import show_dialog_smooth

            show_dialog_smooth(self._progress_dialog)

            # Start loading with progress tracking
            self._start_hash_loading_with_progress(files, source)

        except Exception as e:
            logger.error(f"[DirectMetadataLoader] Error showing hash progress dialog: {e}")
            # Fallback to loading without progress dialog
            self._start_hash_loading(files, source)

    def _start_hash_loading_with_progress(self, files: list[FileItem], source: str) -> None:
        """Start hash loading with progress tracking."""
        from core.hash_worker import HashWorker

        # Create worker and thread
        self._hash_thread = QThread()
        self._hash_worker = HashWorker(parent=None)  # No parent to avoid moveToThread issues

        # Set up worker
        file_paths = [f.full_path for f in files]
        self._hash_worker.set_files(file_paths)
        self._hash_worker.main_window = self.parent_window

        # Connect progress signals
        if hasattr(self, "_progress_dialog") and self._progress_dialog:
            self._hash_worker.progress.connect(
                lambda current, total: self._on_hash_progress(current, total)
            )
            self._hash_worker.size_progress.connect(
                lambda processed, total: self._on_hash_size_progress(processed, total)
            )

        # Connect completion signals
        self._hash_worker.file_hash_calculated.connect(self._on_file_hash_calculated)
        self._hash_worker.finished.connect(self._on_hash_finished)

        # Move worker to thread and start
        self._hash_worker.moveToThread(self._hash_thread)
        self._hash_thread.started.connect(self._hash_worker.run_batch)
        self._hash_worker.finished.connect(self._hash_thread.quit)
        self._hash_worker.finished.connect(self._hash_worker.deleteLater)
        self._hash_thread.finished.connect(self._hash_thread.deleteLater)

        # Start the thread
        self._hash_thread.start()

    def _on_hash_progress(self, current: int, total: int) -> None:
        """Handle hash loading progress updates."""
        if hasattr(self, "_progress_dialog") and self._progress_dialog:
            self._progress_dialog.set_count(current, total)
            self._progress_dialog.set_progress(current, total)

    def _on_hash_size_progress(self, processed: int, total: int) -> None:
        """Handle hash loading size progress updates."""
        if hasattr(self, "_progress_dialog") and self._progress_dialog:
            self._progress_dialog.set_size_info(processed, total)

    def _start_metadata_loading(
        self, files: list[FileItem], use_extended: bool, source: str
    ) -> None:
        """Start metadata loading in background thread."""
        from utils.metadata_loader import MetadataLoader
        from widgets.metadata_worker import MetadataWorker

        # Create worker and thread
        self._metadata_thread = QThread()
        self._metadata_worker = MetadataWorker(
            reader=MetadataLoader(),
            metadata_cache=self.parent_window.metadata_cache,
            parent=self.parent_window,
        )

        # Set up worker
        self._metadata_worker.file_path = [f.full_path for f in files]
        self._metadata_worker.use_extended = use_extended

        # Move worker to thread
        self._metadata_worker.moveToThread(self._metadata_thread)

        # Connect signals
        self._metadata_thread.started.connect(self._metadata_worker.run_batch)
        self._metadata_worker.finished.connect(self._metadata_thread.quit)
        self._metadata_worker.finished.connect(self._on_metadata_finished)
        self._metadata_worker.file_metadata_loaded.connect(self._on_file_metadata_loaded)

        # Start thread
        self._metadata_thread.start()

        logger.debug(
            f"[DirectMetadataLoader] Started metadata loading thread for {len(files)} files"
        )

    def _start_hash_loading(self, files: list[FileItem], source: str) -> None:
        """Start hash loading in background thread."""
        from core.hash_worker import HashWorker

        # Create worker and thread
        self._hash_thread = QThread()
        self._hash_worker = HashWorker(
            file_paths=[f.full_path for f in files],
            hash_cache=self.parent_window.hash_cache,
            parent=self.parent_window,
        )

        # Move worker to thread
        self._hash_worker.moveToThread(self._hash_thread)

        # Connect signals
        self._hash_thread.started.connect(self._hash_worker.run)
        self._hash_worker.finished.connect(self._hash_thread.quit)
        self._hash_worker.finished.connect(self._on_hash_finished)
        self._hash_worker.file_hash_calculated.connect(self._on_file_hash_calculated)

        # Start thread
        self._hash_thread.start()

        logger.debug(f"[DirectMetadataLoader] Started hash loading thread for {len(files)} files")

    def _on_file_metadata_loaded(self, file_path: str) -> None:
        """Handle individual file metadata loaded."""
        # Remove from loading set
        self._currently_loading.discard(file_path)

        # Emit signal for UI update
        self.metadata_loaded.emit(file_path, {})

        # Update file table icons
        if self.parent_window and hasattr(self.parent_window, "file_model"):
            self.parent_window.file_model.refresh_icons()

        logger.debug(f"[DirectMetadataLoader] Metadata loaded for {file_path}")

    def _on_file_hash_calculated(self, file_path: str) -> None:
        """Handle individual file hash calculated."""
        # Remove from loading set
        hash_key = f"hash_{file_path}"
        self._currently_loading.discard(hash_key)

        # Update file table icons
        if self.parent_window and hasattr(self.parent_window, "file_model"):
            self.parent_window.file_model.refresh_icons()

        logger.debug(f"[DirectMetadataLoader] Hash calculated for {file_path}")

    def _on_metadata_finished(self) -> None:
        """Handle metadata loading completion."""
        try:
            # Close progress dialog if it exists
            if hasattr(self, "_progress_dialog") and self._progress_dialog:
                self._progress_dialog.close()
                self._progress_dialog = None

            # Clear loading flags
            self._currently_loading.clear()

            # Update file icons
            if self.parent_window and hasattr(self.parent_window, "file_model"):
                self.parent_window.file_model.refresh_icons()

            logger.debug("[DirectMetadataLoader] Metadata loading finished")

        except Exception as e:
            logger.error(f"[DirectMetadataLoader] Error in metadata finished handler: {e}")
        finally:
            # Emit completion signal
            self.loading_finished.emit()

    def _on_hash_finished(self) -> None:
        """Handle hash loading completion."""
        try:
            # Close progress dialog if it exists
            if hasattr(self, "_progress_dialog") and self._progress_dialog:
                self._progress_dialog.close()
                self._progress_dialog = None

            # Clear loading flags
            self._currently_loading.clear()

            # Update file icons
            if self.parent_window and hasattr(self.parent_window, "file_model"):
                self.parent_window.file_model.refresh_icons()

            # Notify preview manager about hash calculation completion
            if (
                self.parent_window
                and hasattr(self.parent_window, "preview_manager")
                and self.parent_window.preview_manager
            ):
                self.parent_window.preview_manager.on_hash_calculation_completed()

            logger.debug("[DirectMetadataLoader] Hash loading finished")

        except Exception as e:
            logger.error(f"[DirectMetadataLoader] Error in hash finished handler: {e}")
        finally:
            # Emit completion signal
            self.loading_finished.emit()

    def is_loading(self) -> bool:
        """Check if any loading is in progress."""
        return len(self._currently_loading) > 0

    def cleanup(self) -> None:
        """Clean up resources and stop any ongoing operations."""
        try:
            # Cancel any ongoing operations
            self._cancel_current_loading()

            # Close progress dialog if open
            if hasattr(self, "_progress_dialog") and self._progress_dialog:
                self._progress_dialog.close()
                self._progress_dialog = None

            # Clean up threads
            if hasattr(self, "_metadata_thread") and self._metadata_thread:
                if self._metadata_thread.isRunning():
                    self._metadata_thread.quit()
                    self._metadata_thread.wait(3000)  # Wait max 3 seconds
                self._metadata_thread = None
                self._metadata_worker = None

            if hasattr(self, "_hash_thread") and self._hash_thread:
                if self._hash_thread.isRunning():
                    self._hash_thread.quit()
                    self._hash_thread.wait(3000)  # Wait max 3 seconds
                self._hash_thread = None
                self._hash_worker = None

            # Clear loading flags
            self._currently_loading.clear()

            logger.info("[DirectMetadataLoader] Cleanup completed")

        except Exception as e:
            logger.error(f"[DirectMetadataLoader] Error during cleanup: {e}")


# Global instance
_direct_metadata_loader = None


def get_direct_metadata_loader(parent_window=None) -> DirectMetadataLoader:
    """Get the global DirectMetadataLoader instance."""
    global _direct_metadata_loader
    if _direct_metadata_loader is None:
        _direct_metadata_loader = DirectMetadataLoader(parent_window)
    return _direct_metadata_loader


def cleanup_direct_metadata_loader() -> None:
    """Clean up the global DirectMetadataLoader instance."""
    global _direct_metadata_loader
    if _direct_metadata_loader:
        _direct_metadata_loader.cleanup()
        _direct_metadata_loader = None
