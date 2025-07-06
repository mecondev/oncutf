"""
Module: direct_metadata_loader.py

Author: Michael Economou
Date: 2025-07-06

Direct metadata loader for on-demand metadata/hash loading.
Replaces LazyMetadataManager with a simpler, faster approach.

Features:
- No automatic loading on folder open
- On-demand loading only when requested by user
- Immediate cache checking for instant icon display
- Thread-based loading for UI responsiveness
- Simple, clean architecture
"""
import logging
from typing import Optional, List, Dict, Set
from datetime import datetime

from PyQt5.QtCore import QObject, pyqtSignal, QThread

from models.file_item import FileItem
from utils.metadata_cache_helper import MetadataCacheHelper
from utils.logger_factory import get_cached_logger

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
        self._cache_helper: Optional[MetadataCacheHelper] = None
        self._currently_loading: Set[str] = set()

        logger.info("[DirectMetadataLoader] Initialized - no automatic loading")

    def initialize_cache_helper(self) -> None:
        """Initialize the cache helper if parent window is available."""
        if self.parent_window and hasattr(self.parent_window, 'metadata_cache'):
            self._cache_helper = MetadataCacheHelper(self.parent_window.metadata_cache)
            logger.debug("[DirectMetadataLoader] Cache helper initialized")

    def check_cached_metadata(self, file_item: FileItem) -> Optional[dict]:
        """
        Check if metadata exists in cache without loading.

        Args:
            file_item: The file to check

        Returns:
            Metadata dict if cached, None if not available
        """
        if not self._cache_helper:
            return None

        try:
            cached_metadata = self._cache_helper.get_metadata_for_file(file_item)
            if cached_metadata:
                logger.debug(f"[DirectMetadataLoader] Cache hit for {file_item.filename}")
                return cached_metadata
        except Exception as e:
            logger.warning(f"[DirectMetadataLoader] Error checking cache for {file_item.filename}: {e}")

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
            from core.persistent_hash_cache import get_persistent_hash_cache
            cache = get_persistent_hash_cache()
            hash_value = cache.get_hash(file_item.full_path)
            if hash_value:
                logger.debug(f"[DirectMetadataLoader] Hash cache hit for {file_item.filename}")
                return hash_value
        except Exception as e:
            logger.warning(f"[DirectMetadataLoader] Error checking hash cache for {file_item.filename}: {e}")

        return None

    def has_cached_metadata(self, file_item: FileItem) -> bool:
        """Check if file has cached metadata."""
        return self.check_cached_metadata(file_item) is not None

    def has_cached_hash(self, file_item: FileItem) -> bool:
        """Check if file has cached hash."""
        return self.check_cached_hash(file_item) is not None

    def load_metadata_for_files(
        self,
        files: List[FileItem],
        use_extended: bool = False,
        source: str = "user_request"
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
            logger.info(f"[DirectMetadataLoader] All {len(files)} files already have cached metadata")
            return

        logger.info(f"[DirectMetadataLoader] Loading metadata for {len(files_to_load)} files ({source})")

        # Start loading in background thread
        self._start_metadata_loading(files_to_load, use_extended, source)

    def load_hashes_for_files(
        self,
        files: List[FileItem],
        source: str = "user_request"
    ) -> None:
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

        logger.info(f"[DirectMetadataLoader] Loading hashes for {len(files_to_load)} files ({source})")

        # Start loading in background thread
        self._start_hash_loading(files_to_load, source)

    def _start_metadata_loading(
        self,
        files: List[FileItem],
        use_extended: bool,
        source: str
    ) -> None:
        """Start metadata loading in background thread."""
        from widgets.metadata_worker import MetadataWorker
        from utils.metadata_loader import MetadataLoader

        # Create worker and thread
        self._metadata_thread = QThread()
        self._metadata_worker = MetadataWorker(
            reader=MetadataLoader(),
            metadata_cache=self.parent_window.metadata_cache,
            parent=self.parent_window
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

        logger.debug(f"[DirectMetadataLoader] Started metadata loading thread for {len(files)} files")

    def _start_hash_loading(self, files: List[FileItem], source: str) -> None:
        """Start hash loading in background thread."""
        from core.hash_worker import HashWorker

        # Create worker and thread
        self._hash_thread = QThread()
        self._hash_worker = HashWorker(
            file_paths=[f.full_path for f in files],
            hash_cache=self.parent_window.hash_cache,
            parent=self.parent_window
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
        if self.parent_window and hasattr(self.parent_window, 'file_model'):
            self.parent_window.file_model.refresh_icons()

        logger.debug(f"[DirectMetadataLoader] Metadata loaded for {file_path}")

    def _on_file_hash_calculated(self, file_path: str) -> None:
        """Handle individual file hash calculated."""
        # Remove from loading set
        hash_key = f"hash_{file_path}"
        self._currently_loading.discard(hash_key)

        # Update file table icons
        if self.parent_window and hasattr(self.parent_window, 'file_model'):
            self.parent_window.file_model.refresh_icons()

        logger.debug(f"[DirectMetadataLoader] Hash calculated for {file_path}")

    def _on_metadata_finished(self) -> None:
        """Handle metadata loading finished."""
        # Clean up thread
        if hasattr(self, '_metadata_thread'):
            self._metadata_thread.quit()
            self._metadata_thread.wait()
            self._metadata_thread = None
            self._metadata_worker = None

        self.loading_finished.emit()
        logger.debug("[DirectMetadataLoader] Metadata loading finished")

    def _on_hash_finished(self) -> None:
        """Handle hash loading finished."""
        # Clean up thread
        if hasattr(self, '_hash_thread'):
            self._hash_thread.quit()
            self._hash_thread.wait()
            self._hash_thread = None
            self._hash_worker = None

        self.loading_finished.emit()
        logger.debug("[DirectMetadataLoader] Hash loading finished")

    def is_loading(self) -> bool:
        """Check if any loading is in progress."""
        return len(self._currently_loading) > 0

    def cleanup(self) -> None:
        """Clean up resources."""
        # Stop any running threads
        if hasattr(self, '_metadata_thread') and self._metadata_thread:
            self._metadata_thread.quit()
            self._metadata_thread.wait()

        if hasattr(self, '_hash_thread') and self._hash_thread:
            self._hash_thread.quit()
            self._hash_thread.wait()

        self._currently_loading.clear()
        logger.info("[DirectMetadataLoader] Cleanup completed")


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
