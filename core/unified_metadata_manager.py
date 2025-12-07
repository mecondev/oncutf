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

import contextlib
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from PyQt5.QtCore import QObject, pyqtSignal

from config import COMPANION_FILES_ENABLED, LOAD_COMPANION_METADATA
from core.pyqt_imports import QApplication, Qt
from models.file_item import FileItem
from utils.companion_files_helper import CompanionFilesHelper
from utils.cursor_helper import wait_cursor
from utils.file_status_helpers import (
    get_hash_for_file,
    get_metadata_for_file,
    has_hash,
    has_metadata,
)
from utils.logger_factory import get_cached_logger
from utils.metadata_cache_helper import MetadataCacheHelper
from utils.path_utils import paths_equal
from utils.progress_dialog import ProgressDialog

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
        self._cache_helper: MetadataCacheHelper | None = None
        self._currently_loading: set[str] = set()

        # Progress dialogs (kept as instance variables to prevent garbage collection)
        self._metadata_progress_dialog = None
        self._hash_progress_dialog = None

        # State tracking
        self.force_extended_metadata = False
        self._metadata_cancelled = False  # Cancellation flag for metadata loading
        self._save_cancelled = False  # Cancellation flag for save operations

        # Structured metadata system (lazy-initialized)
        self._structured_manager = None

        # Initialize ExifTool wrapper for single file operations
        from utils.exiftool_wrapper import ExifToolWrapper

        self._exiftool_wrapper = ExifToolWrapper()

        # Initialize parallel metadata loader (lazy-initialized on first use)
        self._parallel_loader = None

        logger.info("[UnifiedMetadataManager] Initialized - unified metadata management")

    def initialize_cache_helper(self) -> None:
        """Initialize the cache helper if parent window is available."""
        if self.parent_window and hasattr(self.parent_window, "metadata_cache"):
            self._cache_helper = MetadataCacheHelper(self.parent_window.metadata_cache, self.parent_window)
            logger.debug(
                "[UnifiedMetadataManager] Cache helper initialized", extra={"dev_only": True}
            )

    @property
    def structured(self):
        """
        Lazy-initialized structured metadata manager.

        Returns:
            StructuredMetadataManager instance
        """
        if self._structured_manager is None:
            from core.structured_metadata_manager import StructuredMetadataManager

            self._structured_manager = StructuredMetadataManager()
            logger.debug(
                "[UnifiedMetadataManager] StructuredMetadataManager initialized",
                extra={"dev_only": True},
            )
        return self._structured_manager

    @property
    def parallel_loader(self):
        """
        Lazy-initialized parallel metadata loader.

        Returns:
            ParallelMetadataLoader instance
        """
        if self._parallel_loader is None:
            from core.parallel_metadata_loader import ParallelMetadataLoader

            self._parallel_loader = ParallelMetadataLoader()
            logger.debug(
                "[UnifiedMetadataManager] ParallelMetadataLoader initialized",
                extra={"dev_only": True},
            )
        return self._parallel_loader

    # =====================================
    # Cache Checking Methods
    # =====================================

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
                f"[UnifiedMetadataManager] Error checking cache for {file_item.filename}: {e}"
            )
            return None

    def get_enhanced_metadata(self, file_item: FileItem, folder_files: list[str] = None) -> dict | None:
        """
        Get enhanced metadata that includes companion file metadata.

        Args:
            file_item: The main file item
            folder_files: List of all files in the same folder (for companion detection)

        Returns:
            Enhanced metadata dict including companion file data, or None if not available
        """
        if not COMPANION_FILES_ENABLED or not LOAD_COMPANION_METADATA:
            return self.check_cached_metadata(file_item)

        try:
            # Get base metadata from cache
            base_metadata = self.check_cached_metadata(file_item)
            if not base_metadata:
                return None

            # If no folder files provided, get them from the file's directory
            if folder_files is None:
                folder_path = os.path.dirname(file_item.full_path)
                try:
                    folder_files = [
                        os.path.join(folder_path, f)
                        for f in os.listdir(folder_path)
                        if os.path.isfile(os.path.join(folder_path, f))
                    ]
                except OSError:
                    folder_files = []

            # Find companion files
            companions = CompanionFilesHelper.find_companion_files(file_item.full_path, folder_files)

            if not companions:
                # No companions found, return base metadata
                return base_metadata

            # Create enhanced metadata by copying base metadata
            enhanced_metadata = base_metadata.copy()

            # Add companion metadata
            companion_metadata = {}
            for companion_path in companions:
                try:
                    companion_data = CompanionFilesHelper.extract_companion_metadata(companion_path)
                    if companion_data:
                        # Prefix companion metadata to avoid conflicts
                        companion_name = os.path.basename(companion_path)
                        for key, value in companion_data.items():
                            if key != "source":  # Skip the source indicator
                                companion_key = f"Companion:{companion_name}:{key}"
                                companion_metadata[companion_key] = value

                        logger.debug(
                            f"[UnifiedMetadataManager] Added companion metadata from {companion_name} "
                            f"with {len(companion_data)} fields"
                        )
                except Exception as e:
                    logger.warning(
                        f"[UnifiedMetadataManager] Failed to extract metadata from companion {companion_path}: {e}"
                    )

            # Merge companion metadata into enhanced metadata
            if companion_metadata:
                enhanced_metadata.update(companion_metadata)
                enhanced_metadata["__companion_files__"] = companions
                logger.debug(
                    f"[UnifiedMetadataManager] Enhanced metadata for {file_item.filename} "
                    f"with {len(companion_metadata)} companion fields"
                )

            return enhanced_metadata

        except Exception as e:
            logger.warning(
                f"[UnifiedMetadataManager] Error getting enhanced metadata for {file_item.filename}: {e}"
            )
            return self.check_cached_metadata(file_item)

    def _enhance_metadata_with_companions(
        self, file_item: FileItem, base_metadata: dict, all_files: list[FileItem]
    ) -> dict:
        """
        Enhance metadata with companion file data during loading.

        Args:
            file_item: The main file being processed
            base_metadata: Base metadata from ExifTool
            all_files: All files being processed (for folder context)

        Returns:
            Enhanced metadata including companion data
        """
        if not COMPANION_FILES_ENABLED or not LOAD_COMPANION_METADATA:
            return base_metadata

        try:
            # Get folder files for companion detection
            folder_path = os.path.dirname(file_item.full_path)
            folder_files = []

            # First try to use the files being loaded (more efficient)
            if all_files:
                folder_files = [f.full_path for f in all_files if os.path.dirname(f.full_path) == folder_path]

            # If not enough context, scan the folder
            if len(folder_files) < 2:
                try:
                    folder_files = [
                        os.path.join(folder_path, f)
                        for f in os.listdir(folder_path)
                        if os.path.isfile(os.path.join(folder_path, f))
                    ]
                except OSError:
                    return base_metadata

            # Find companion files
            companions = CompanionFilesHelper.find_companion_files(file_item.full_path, folder_files)

            if not companions:
                return base_metadata

            # Create enhanced metadata
            enhanced_metadata = base_metadata.copy()
            companion_metadata = {}

            # Extract metadata from companion files
            for companion_path in companions:
                try:
                    companion_data = CompanionFilesHelper.extract_companion_metadata(companion_path)
                    if companion_data:
                        companion_name = os.path.basename(companion_path)
                        for key, value in companion_data.items():
                            if key != "source":
                                companion_key = f"Companion:{companion_name}:{key}"
                                companion_metadata[companion_key] = value

                        logger.debug(
                            f"[UnifiedMetadataManager] Enhanced {file_item.filename} with companion {companion_name}"
                        )
                except Exception as e:
                    logger.warning(
                        f"[UnifiedMetadataManager] Failed to extract companion metadata from {companion_path}: {e}"
                    )

            # Merge companion metadata
            if companion_metadata:
                enhanced_metadata.update(companion_metadata)
                enhanced_metadata["__companion_files__"] = companions
                logger.debug(
                    f"[UnifiedMetadataManager] Added {len(companion_metadata)} companion fields to {file_item.filename}"
                )

            return enhanced_metadata

        except Exception as e:
            logger.warning(
                f"[UnifiedMetadataManager] Error enhancing metadata with companions for {file_item.filename}: {e}"
            )
            return base_metadata

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

    def determine_loading_mode(self, file_count: int, _use_extended: bool = False) -> str:
        """
        Determine the appropriate loading mode based on file count.

        Args:
            file_count: Number of files to process
            _use_extended: Whether to use extended metadata (unused parameter kept for compatibility)

        Returns:
            str: Loading mode ("single_file_wait_cursor" or "multiple_files_dialog")
        """
        if file_count == 1:
            return "single_file_wait_cursor"
        else:
            # Use progress dialog for 2+ files (parallel loading with progress)
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

        # Analyze metadata state
        metadata_analysis = self.parent_window.event_handler_manager._analyze_metadata_state(
            selected_files
        )

        if not metadata_analysis["enable_fast_selected"]:
            # All files already have fast metadata or better
            from utils.dialog_utils import show_info_message

            message = (
                f"All {len(selected_files)} selected file(s) already have fast metadata or better."
            )
            if metadata_analysis.get("fast_tooltip"):
                message += f"\n\n{metadata_analysis['fast_tooltip']}"

            show_info_message(
                self.parent_window,
                "Fast Metadata Loading",
                message,
            )
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

        # Analyze metadata state
        metadata_analysis = self.parent_window.event_handler_manager._analyze_metadata_state(
            selected_files
        )

        if not metadata_analysis["enable_extended_selected"]:
            # All files already have extended metadata
            from utils.dialog_utils import show_info_message

            message = f"All {len(selected_files)} selected file(s) already have extended metadata."
            if metadata_analysis.get("extended_tooltip"):
                message += f"\n\n{metadata_analysis['extended_tooltip']}"

            show_info_message(
                self.parent_window,
                "Extended Metadata Loading",
                message,
            )
            return

        # Check if we have files with fast metadata that can be upgraded
        stats = metadata_analysis.get("stats", {})
        fast_count = stats.get("fast_metadata", 0)

        if fast_count > 0:
            from utils.dialog_utils import show_question_message

            message = f"Found {fast_count} file(s) with fast metadata.\n\nDo you want to upgrade them to extended metadata?"
            if metadata_analysis.get("extended_tooltip"):
                message += f"\n\nDetails: {metadata_analysis['extended_tooltip']}"

            result = show_question_message(
                self.parent_window,
                "Upgrade to Extended Metadata",
                message,
            )

            if not result:
                return

        logger.info(f"[Shortcut] Loading extended metadata for {len(selected_files)} files")
        # Use intelligent loading with cache checking and smart UX
        self.load_metadata_for_items(selected_files, use_extended=True, source="shortcut")

    def shortcut_load_metadata_all(self) -> None:
        """
        Load basic metadata for ALL files in current folder (keyboard shortcut).

        This loads metadata for all files regardless of selection state.
        """
        if not self.parent_window:
            return

        if self.is_running_metadata_task():
            logger.warning("[Shortcut] Metadata scan already running — shortcut ignored.")
            return

        from core.application_context import ApplicationContext

        context = ApplicationContext()
        all_files = list(context.file_store)

        if not all_files:
            logger.info("[Shortcut] No files available for metadata loading")
            if hasattr(self.parent_window, "status_manager"):
                self.parent_window.status_manager.set_selection_status(
                    "No files available", selected_count=0, total_count=0, auto_reset=True
                )
            return

        # Analyze metadata state to avoid loading if all files already have metadata
        metadata_analysis = self.parent_window.event_handler_manager._analyze_metadata_state(all_files)

        if not metadata_analysis["enable_fast_selected"]:
            # All files already have fast metadata or better
            from utils.dialog_utils import show_info_message

            message = f"All {len(all_files)} file(s) already have fast metadata or better."
            if metadata_analysis.get("fast_tooltip"):
                message += f"\n\n{metadata_analysis['fast_tooltip']}"

            show_info_message(
                self.parent_window,
                "Fast Metadata Loading",
                message,
            )
            return

        logger.info(f"[Shortcut] Loading basic metadata for all {len(all_files)} files")
        self.load_metadata_for_items(all_files, use_extended=False, source="shortcut_all")

    def shortcut_load_extended_metadata_all(self) -> None:
        """
        Load extended metadata for ALL files in current folder (keyboard shortcut).

        This loads extended metadata for all files regardless of selection state.
        """
        if not self.parent_window:
            return

        if self.is_running_metadata_task():
            logger.warning("[Shortcut] Metadata scan already running — shortcut ignored.")
            return

        from core.application_context import ApplicationContext

        context = ApplicationContext()
        all_files = list(context.file_store)

        if not all_files:
            logger.info("[Shortcut] No files available for extended metadata loading")
            if hasattr(self.parent_window, "status_manager"):
                self.parent_window.status_manager.set_selection_status(
                    "No files available", selected_count=0, total_count=0, auto_reset=True
                )
            return

        # Analyze metadata state to avoid loading if all files already have extended metadata
        metadata_analysis = self.parent_window.event_handler_manager._analyze_metadata_state(all_files)

        if not metadata_analysis["enable_extended_selected"]:
            # All files already have extended metadata
            from utils.dialog_utils import show_info_message

            message = f"All {len(all_files)} file(s) already have extended metadata."
            if metadata_analysis.get("extended_tooltip"):
                message += f"\n\n{metadata_analysis['extended_tooltip']}"

            show_info_message(
                self.parent_window,
                "Extended Metadata Loading",
                message,
            )
            return

        logger.info(f"[Shortcut] Loading extended metadata for all {len(all_files)} files")
        self.load_metadata_for_items(all_files, use_extended=True, source="shortcut_all")

    # =====================================
    # Main Loading Methods
    # =====================================

    def load_metadata_streaming(
        self, items: list[FileItem], use_extended: bool = False
    ):
        """
        Yield metadata as soon as available using parallel loading.

        Args:
            items: List of FileItem objects to load metadata for
            use_extended: Whether to use extended metadata loading

        Yields:
            Tuple[FileItem, dict]: (item, metadata)
        """
        if not items:
            return

        # Separate cached vs non-cached
        items_to_load = []

        for item in items:
            # Check cache
            cache_entry = (
                self.parent_window.metadata_cache.get_entry(item.full_path)
                if self.parent_window and hasattr(self.parent_window, "metadata_cache")
                else None
            )

            has_valid_cache = (
                cache_entry
                and hasattr(cache_entry, "is_extended")
                and hasattr(cache_entry, "data")
                and cache_entry.data
            )

            if has_valid_cache:
                if cache_entry.is_extended and not use_extended or cache_entry.is_extended == use_extended:
                    yield item, cache_entry.data
                    continue

            items_to_load.append(item)

        if not items_to_load:
            return

        # Use parallel loading for the rest
        # We use a local executor to allow yielding
        max_workers = 4  # Default safe value
        if self._parallel_loader:
            max_workers = self._parallel_loader.max_workers
        else:
            import multiprocessing

            max_workers = min(multiprocessing.cpu_count() * 2, 16)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_item = {
                executor.submit(
                    self._exiftool_wrapper.get_metadata, item.full_path, use_extended
                ): item
                for item in items_to_load
            }

            for future in as_completed(future_to_item):
                item = future_to_item[future]
                try:
                    metadata = future.result()

                    # Update cache
                    if self.parent_window and hasattr(self.parent_window, "metadata_cache"):
                        self.parent_window.metadata_cache.set(
                            item.full_path, metadata, is_extended=use_extended
                        )

                    # Update item metadata
                    item.metadata = metadata

                    yield item, metadata
                except Exception as e:
                    logger.error(f"Failed to load metadata for {item.filename}: {e}")
                    yield item, {}

    def load_metadata_for_items(
        self, items: list[FileItem], use_extended: bool = False, source: str = "unknown"
    ) -> None:
        """
        Load metadata for the given FileItem objects.

        Loading modes (determined by file count AFTER cache check):
        - Single file: Immediate loading with wait_cursor (fast and responsive)
        - Multiple files (2+): ProgressDialog with ESC cancel support

        Cache behavior:
        - Files with extended metadata are never downgraded to fast
        - Files with fast metadata can be upgraded to extended
        - Files with matching metadata type are skipped

        Args:
            items: List of FileItem objects to load metadata for
            use_extended: Whether to use extended metadata loading (Shift modifier)
            source: Source of the request (for logging)
        """
        if not items:
            logger.debug("[UnifiedMetadataManager] No items provided for metadata loading")
            return

        # Reset cancellation flag for new metadata loading operation
        self.reset_cancellation_flag()

        # ===== PHASE 1: Cache Pre-Check (fast, no UI blocking) =====
        needs_loading = []
        skipped_count = 0

        # Use batch cache retrieval for performance
        if self.parent_window and hasattr(self.parent_window, "metadata_cache"):
            paths = [item.full_path for item in items]
            cache_entries = self.parent_window.metadata_cache.get_entries_batch(paths)
        else:
            cache_entries = {}

        from utils.path_normalizer import normalize_path

        for item in items:
            norm_path = normalize_path(item.full_path)
            cache_entry = cache_entries.get(norm_path)

            # Check if we have valid metadata in cache
            has_valid_cache = (
                cache_entry
                and hasattr(cache_entry, "is_extended")
                and hasattr(cache_entry, "data")
                and cache_entry.data
            )

            if has_valid_cache:
                # Already has extended - never downgrade
                if cache_entry.is_extended and not use_extended or cache_entry.is_extended == use_extended:
                    skipped_count += 1
                    continue
                # else: Need upgrade from fast to extended - add to needs_loading

            needs_loading.append(item)

        # Get metadata tree view reference
        metadata_tree_view = (
            self.parent_window.metadata_tree_view
            if self.parent_window and hasattr(self.parent_window, "metadata_tree_view")
            else None
        )

        # ===== PHASE 2: Handle "all cached" case =====
        if not needs_loading:
            logger.info(f"[{source}] All {len(items)} files already cached (skipped {skipped_count})")

            # Update file table icons to show metadata icons
            if self.parent_window and hasattr(self.parent_window, "file_model"):
                self.parent_window.file_model.refresh_icons()

            # Display metadata for the last item (or single item)
            if metadata_tree_view and items:
                display_file = items[0] if len(items) == 1 else items[-1]
                metadata_tree_view.display_file_metadata(display_file)

            return

        # Log loading info
        mode_str = "extended" if use_extended else "fast"
        if skipped_count > 0:
            logger.info(
                f"[{source}] Loading {mode_str} metadata: {len(needs_loading)} files "
                f"(skipped {skipped_count} cached)"
            )
        else:
            logger.info(f"[{source}] Loading {mode_str} metadata for {len(needs_loading)} files")

        # ===== PHASE 3: Single file - use wait_cursor (immediate) =====
        if len(needs_loading) == 1:
            self._load_single_file_metadata(needs_loading[0], use_extended, metadata_tree_view)
            return

        # ===== PHASE 4: Multiple files - use ProgressDialog with parallel loading =====
        self._load_multiple_files_metadata(needs_loading, use_extended, metadata_tree_view, source)

    def _load_single_file_metadata(
        self, item: FileItem, use_extended: bool, metadata_tree_view
    ) -> None:
        """
        Load metadata for a single file with wait_cursor (immediate, no dialog).

        Args:
            item: The FileItem to load metadata for
            use_extended: Whether to use extended metadata
            metadata_tree_view: Reference to metadata tree view for display
        """
        from utils.cursor_helper import wait_cursor

        with wait_cursor():
            try:
                # Load metadata using ExifTool wrapper
                metadata = self._exiftool_wrapper.get_metadata(item.full_path, use_extended)

                if metadata:
                    # Mark metadata with loading mode
                    if use_extended:
                        metadata["__extended__"] = True
                    elif "__extended__" in metadata:
                        del metadata["__extended__"]

                    # Enhance with companion file data
                    enhanced_metadata = self._enhance_metadata_with_companions(
                        item, metadata, [item]
                    )

                    # Save to cache
                    if self.parent_window and hasattr(self.parent_window, "metadata_cache"):
                        self.parent_window.metadata_cache.set(
                            item.full_path, enhanced_metadata, is_extended=use_extended
                        )

                    # Update file item
                    item.metadata = enhanced_metadata

                    # Update UI
                    if self.parent_window and hasattr(self.parent_window, "file_model"):
                        self.parent_window.file_model.refresh_icons()

                    # Display in metadata tree
                    if metadata_tree_view:
                        metadata_tree_view.display_file_metadata(item)

                    logger.debug(
                        f"[UnifiedMetadataManager] Loaded {'extended' if use_extended else 'fast'} "
                        f"metadata for {item.filename}"
                    )
                else:
                    logger.warning(f"[UnifiedMetadataManager] No metadata returned for {item.filename}")

            except Exception as e:
                logger.error(f"[UnifiedMetadataManager] Failed to load metadata for {item.filename}: {e}")

        # Always emit signal
        self.loading_finished.emit()

    def _load_multiple_files_metadata(
        self, needs_loading: list[FileItem], use_extended: bool, metadata_tree_view, source: str
    ) -> None:
        """
        Load metadata for multiple files with ProgressDialog and parallel loading.

        Args:
            needs_loading: List of FileItem objects that need loading
            use_extended: Whether to use extended metadata
            metadata_tree_view: Reference to metadata tree view for display
            source: Source of the request (for logging)
        """
        # Cancellation support
        self._metadata_cancelled = False

        def cancel_metadata_loading():
            self._metadata_cancelled = True
            logger.info("[UnifiedMetadataManager] Metadata loading cancelled by user")

        # Create progress dialog
        from utils.dialog_utils import show_dialog_smooth
        from utils.file_size_calculator import calculate_files_total_size
        from utils.progress_dialog import ProgressDialog

        _loading_dialog = ProgressDialog.create_metadata_dialog(
            self.parent_window,
            is_extended=use_extended,
            cancel_callback=cancel_metadata_loading,
        )
        _loading_dialog.set_status(
            "Loading extended metadata..." if use_extended else "Loading metadata..."
        )

        # Show dialog smoothly
        show_dialog_smooth(_loading_dialog)
        _loading_dialog.activateWindow()
        _loading_dialog.setFocus()
        _loading_dialog.raise_()

        # Process events to ensure dialog is visible
        for _ in range(3):
            QApplication.processEvents()

        # Calculate total size for progress tracking
        total_size = calculate_files_total_size(needs_loading)
        _loading_dialog.start_progress_tracking(total_size)

        # Progress tracking
        processed_size = 0

        def on_progress(current: int, total: int, item: FileItem, metadata: dict):
            """Called for each completed file during parallel loading."""
            nonlocal processed_size

            # Update processed size
            try:
                if hasattr(item, "size") and item.size is not None:
                    current_file_size = item.size
                elif hasattr(item, "full_path") and os.path.exists(item.full_path):
                    current_file_size = os.path.getsize(item.full_path)
                    item.size = current_file_size
                else:
                    current_file_size = 0
                processed_size += current_file_size
            except (OSError, AttributeError):
                pass

            # Update progress dialog
            _loading_dialog.update_progress(
                file_count=current,
                total_files=total,
                processed_bytes=processed_size,
                total_bytes=total_size,
            )
            _loading_dialog.set_filename(item.filename)
            _loading_dialog.set_count(current, total)

            # Process metadata
            if metadata:
                # Mark metadata with loading mode
                if use_extended:
                    metadata["__extended__"] = True
                elif "__extended__" in metadata:
                    del metadata["__extended__"]

                # Enhance with companion data
                enhanced_metadata = self._enhance_metadata_with_companions(
                    item, metadata, needs_loading
                )

                # Save to cache
                if self.parent_window and hasattr(self.parent_window, "metadata_cache"):
                    self.parent_window.metadata_cache.set(
                        item.full_path, enhanced_metadata, is_extended=use_extended
                    )

                # Update file item
                item.metadata = enhanced_metadata

                # Emit dataChanged for progressive UI update
                if self.parent_window and hasattr(self.parent_window, "file_model"):
                    try:
                        for j, file in enumerate(self.parent_window.file_model.files):
                            if paths_equal(file.full_path, item.full_path):
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
                            f"[UnifiedMetadataManager] Failed to emit dataChanged for {item.filename}: {e}"
                        )

        def on_completion():
            """Called when parallel loading completes."""
            _loading_dialog.close()

            # Display metadata for the last loaded file
            if metadata_tree_view and needs_loading:
                display_file = needs_loading[-1]
                metadata_tree_view.display_file_metadata(display_file)

            logger.info(f"[{source}] Completed loading metadata for {len(needs_loading)} files")

        def check_cancellation():
            """Check if loading should be cancelled."""
            return self._metadata_cancelled

        # Start parallel loading
        self.parallel_loader.load_metadata_parallel(
            items=needs_loading,
            use_extended=use_extended,
            progress_callback=on_progress,
            completion_callback=on_completion,
            cancellation_check=check_cancellation
        )

        # Emit signal
        self.loading_finished.emit()

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
        self, files: list[FileItem], use_extended: bool, source: str
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

    def _show_hash_progress_dialog(self, files: list[FileItem], source: str) -> None:
        """Show progress dialog for hash loading."""
        try:

            def cancel_hash_loading():
                self._cancel_current_loading()

            # Create progress dialog
            from utils.progress_dialog import ProgressDialog

            self._hash_progress_dialog = ProgressDialog.create_hash_dialog(
                self.parent_window, cancel_callback=cancel_hash_loading
            )

            # Connect signals from hash worker to dialog
            if self._hash_worker:
                self._hash_worker.progress_updated.connect(
                    lambda current, total, _filename: self._hash_progress_dialog.update_progress(current, total)
                )
                self._hash_worker.size_progress.connect(
                    lambda processed, total: self._hash_progress_dialog.update_size_progress(processed, total)
                )

            # Show dialog
            self._hash_progress_dialog.show()

            # Start loading with progress tracking
            self._start_hash_loading_with_progress(files, source)

        except Exception as e:
            logger.error(f"[UnifiedMetadataManager] Error showing hash progress dialog: {e}")
            # Clean up dialog
            if self._hash_progress_dialog:
                self._hash_progress_dialog.close()
                self._hash_progress_dialog = None
            # Fallback to direct loading
            self._start_hash_loading(files, source)

    # =====================================
    # Worker Loading Methods
    # =====================================

    def _start_metadata_loading_with_progress(
        self, files: list[FileItem], use_extended: bool, source: str
    ) -> None:
        """Start metadata loading with progress tracking."""
        # This will be implemented to use the existing metadata worker
        # For now, fallback to direct loading
        self._start_metadata_loading(files, use_extended, source)

    def _start_hash_loading_with_progress(self, files: list[FileItem], source: str) -> None:
        """Start hash loading with progress tracking."""
        # Create worker first so we can connect signals
        self._start_hash_loading(files, source)

        # Connect dialog signals if dialog exists
        if self._hash_progress_dialog and self._hash_worker:
            self._hash_worker.progress_updated.connect(
                lambda current, total, _filename: self._hash_progress_dialog.update_progress(current, total),
                Qt.QueuedConnection
            )
            self._hash_worker.size_progress.connect(
                lambda processed, total: self._hash_progress_dialog.update_size_progress(processed, total),
                Qt.QueuedConnection
            )

    def _start_metadata_loading(
        self, files: list[FileItem], use_extended: bool, _source: str
    ) -> None:
        """Start metadata loading using existing metadata worker."""
        if not files:
            return

        # Create metadata worker
        from core.pyqt_imports import QThread
        from widgets.metadata_worker import MetadataWorker

        self._metadata_worker = MetadataWorker()
        self._metadata_thread = QThread()
        self._metadata_worker.moveToThread(self._metadata_thread)

        # Connect signals
        self._metadata_worker.metadata_loaded.connect(self._on_file_metadata_loaded)
        self._metadata_worker.finished.connect(self._on_metadata_finished)
        self._metadata_worker.progress.connect(self._on_metadata_progress)
        self._metadata_worker.size_progress.connect(self._on_metadata_size_progress)

        # Start loading
        self._metadata_thread.started.connect(
            lambda: self._metadata_worker.load_metadata_for_files(files, use_extended)
        )
        self._metadata_thread.start()

    def _start_hash_loading(self, files: list[FileItem], _source: str) -> None:
        """Start hash loading using parallel hash worker."""
        if not files:
            return

        # Create parallel hash worker (inherits QThread, no separate thread needed)
        from core.parallel_hash_worker import ParallelHashWorker

        # Extract file paths from FileItem objects
        file_paths = [f.full_path for f in files]

        # Create worker
        self._hash_worker = ParallelHashWorker(parent=self.parent_window)

        # Setup operation
        self._hash_worker.setup_checksum_calculation(file_paths)

        # Connect signals (ParallelHashWorker uses different signal names)
        # Use Qt.QueuedConnection to ensure UI updates happen in main thread
        from core.pyqt_imports import Qt
        self._hash_worker.file_hash_calculated.connect(
            self._on_file_hash_calculated, Qt.QueuedConnection
        )
        # finished_processing emits bool (success flag) but we don't use it
        self._hash_worker.finished_processing.connect(
            lambda _success: self._on_hash_finished(), Qt.QueuedConnection
        )
        # progress_updated emits (current, total, filename) but we only need (current, total)
        self._hash_worker.progress_updated.connect(
            lambda current, total, _filename: self._on_hash_progress(current, total),
            Qt.QueuedConnection
        )
        self._hash_worker.size_progress.connect(
            self._on_hash_size_progress, Qt.QueuedConnection
        )

        # Start worker thread
        self._hash_worker.start()

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

    def request_save_cancel(self) -> None:
        """Request cancellation of current save operation."""
        self._save_cancelled = True
        logger.info("[UnifiedMetadataManager] Save cancellation requested by user")

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

    def _on_file_hash_calculated(self, file_path: str, hash_value: str = "") -> None:
        """Handle individual file hash calculated with progressive UI update."""
        # Remove from loading set
        self._currently_loading.discard(file_path)

        # Store hash if provided (safe in main thread)
        if hash_value:
            try:
                from core.hash_manager import HashManager
                hm = HashManager()
                hm.store_hash(file_path, hash_value)
            except Exception as e:
                logger.warning(f"[UnifiedMetadataManager] Failed to store hash for {file_path}: {e}")

        # Progressive UI update - emit dataChanged for this specific file
        if self.parent_window and hasattr(self.parent_window, "file_model"):
            if hasattr(self.parent_window.file_model, "refresh_icon_for_file"):
                self.parent_window.file_model.refresh_icon_for_file(file_path)
            else:
                try:
                    from utils.path_utils import paths_equal

                    # Find the file in the model and emit dataChanged
                    for i, file in enumerate(self.parent_window.file_model.files):
                        if paths_equal(file.full_path, file_path):
                            top_left = self.parent_window.file_model.index(i, 0)
                            bottom_right = self.parent_window.file_model.index(
                                i, self.parent_window.file_model.columnCount() - 1
                            )
                            logger.debug(
                                f"[UnifiedMetadataManager] Emitting progressive dataChanged for hash: '{file.filename}' at row {i}",
                                extra={"dev_only": True}
                            )
                            self.parent_window.file_model.dataChanged.emit(
                                top_left, bottom_right, [Qt.DecorationRole, Qt.ToolTipRole]
                            )
                            break
                except Exception as e:
                    logger.warning(f"[UnifiedMetadataManager] Failed to emit dataChanged for hash {file_path}: {e}")

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
            if not self._metadata_thread.wait(3000):  # Wait max 3 seconds
                logger.warning("[UnifiedMetadataManager] Metadata thread did not stop, terminating...")
                self._metadata_thread.terminate()
                if not self._metadata_thread.wait(1000):  # Wait another 1 second
                    logger.error("[UnifiedMetadataManager] Metadata thread did not terminate")
            self._metadata_thread.deleteLater()
            self._metadata_thread = None

    def _cleanup_hash_worker_and_thread(self) -> None:
        """Clean up hash worker (ParallelHashWorker is a QThread itself)."""
        if hasattr(self, "_hash_worker") and self._hash_worker:
            # Wait for thread to finish (ParallelHashWorker inherits QThread)
            if self._hash_worker.isRunning():
                if not self._hash_worker.wait(3000):  # Wait max 3 seconds
                    logger.warning("[UnifiedMetadataManager] Hash worker did not stop, terminating...")
                    self._hash_worker.terminate()
                    if not self._hash_worker.wait(1000):  # Wait another 1 second
                        logger.error("[UnifiedMetadataManager] Hash worker did not terminate")

            self._hash_worker.deleteLater()
            self._hash_worker = None

    # =====================================
    # Metadata Saving Methods
    # =====================================

    def set_metadata_value(self, file_path: str, key_path: str, new_value: str) -> bool:
        """
        Set a metadata value for a file (updates cache only, doesn't write to disk).

        Args:
            file_path: Path to the file
            key_path: Metadata key path (e.g., "Rotation", "EXIF/DateTimeOriginal")
            new_value: New value to set

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Stage the change
            try:
                staging_manager = self.parent_window.context.get_manager('metadata_staging')
                staging_manager.stage_change(file_path, key_path, new_value)
            except KeyError:
                logger.warning("[UnifiedMetadataManager] MetadataStagingManager not found during set_metadata_value")

            # Update UI cache
            if hasattr(self.parent_window, "metadata_cache"):
                cache = self.parent_window.metadata_cache
                metadata_entry = cache.get_entry(file_path)

                if metadata_entry and hasattr(metadata_entry, "data"):
                    # Handle rotation as top-level key
                    if key_path.lower() == "rotation":
                        metadata_entry.data["Rotation"] = new_value
                    # Handle nested keys
                    elif "/" in key_path or ":" in key_path:
                        parts = key_path.replace(":", "/").split("/", 1)
                        if len(parts) == 2:
                            group, key = parts
                            if group not in metadata_entry.data:
                                metadata_entry.data[group] = {}
                            metadata_entry.data[group][key] = new_value
                    # Handle top-level keys
                    else:
                        metadata_entry.data[key_path] = new_value

                    metadata_entry.modified = True
                    logger.debug(
                        f"[UnifiedMetadataManager] Set {key_path}={new_value} for {os.path.basename(file_path)}"
                    )
                    return True

            return False

        except Exception as e:
            logger.error(f"[UnifiedMetadataManager] Error setting metadata value: {e}")
            return False

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
            if hasattr(self.parent_window, "status_manager"):
                self.parent_window.status_manager.set_selection_status(
                    "No files selected", selected_count=0, total_count=0, auto_reset=True
                )
            return

        # Get staging manager
        try:
            staging_manager = self.parent_window.context.get_manager('metadata_staging')
        except KeyError:
            logger.error("[UnifiedMetadataManager] MetadataStagingManager not found")
            return

        # Collect staged changes for selected files
        files_to_save = []
        all_staged_changes = {}

        for file_item in selected_files:
            if staging_manager.has_staged_changes(file_item.full_path):
                files_to_save.append(file_item)
                all_staged_changes[file_item.full_path] = staging_manager.get_staged_changes(file_item.full_path)

        if not files_to_save:
            logger.info("[UnifiedMetadataManager] No selected files have staged changes")
            if hasattr(self.parent_window, "status_manager"):
                self.parent_window.status_manager.set_file_operation_status(
                    "No changes in selected files", success=False, auto_reset=True
                )
            return

        logger.info(
            f"[UnifiedMetadataManager] Saving metadata for {len(files_to_save)} selected files"
        )
        self._save_metadata_files(files_to_save, all_staged_changes)

    def save_all_modified_metadata(self, is_exit_save: bool = False) -> None:
        """Save all modified metadata across all files.

        Args:
            is_exit_save: If True, indicates this is a save-on-exit operation.
                         ESC will be blocked to prevent incomplete saves.
        """
        if not self.parent_window:
            return

        # Get staging manager
        try:
            staging_manager = self.parent_window.context.get_manager('metadata_staging')
        except KeyError:
            logger.error("[UnifiedMetadataManager] MetadataStagingManager not found")
            return

        # Get all staged changes
        all_staged_changes = staging_manager.get_all_staged_changes()

        if not all_staged_changes:
            logger.info("[UnifiedMetadataManager] No staged metadata changes to save")
            if hasattr(self.parent_window, "status_manager"):
                self.parent_window.status_manager.set_file_operation_status(
                    "No metadata changes to save", success=False, auto_reset=True
                )
            return

        # Match staged changes to file items
        files_to_save = []
        file_model = getattr(self.parent_window, "file_model", None)

        if file_model and hasattr(file_model, "files"):
            from utils.path_normalizer import normalize_path

            # Create a map of normalized path -> file item for fast lookup
            path_map = {normalize_path(f.full_path): f for f in file_model.files}

            for staged_path in all_staged_changes:
                if staged_path in path_map:
                    files_to_save.append(path_map[staged_path])

        if not files_to_save:
            logger.info("[UnifiedMetadataManager] No files with staged metadata found in current view")
            if hasattr(self.parent_window, "status_manager"):
                self.parent_window.status_manager.set_file_operation_status(
                    "No metadata changes to save", success=False, auto_reset=True
                )
            return

        logger.info(
            f"[UnifiedMetadataManager] Saving metadata for {len(files_to_save)} files with modifications (exit_save: {is_exit_save})"
        )
        # Reset cancellation flag before starting save
        self._save_cancelled = False
        self._save_metadata_files(files_to_save, all_staged_changes, is_exit_save=is_exit_save)

    def _save_metadata_files(self, files_to_save: list, all_modifications: dict, is_exit_save: bool = False) -> None:
        """Save metadata files using ExifTool.

        Args:
            files_to_save: List of FileItem objects to save
            all_modifications: Dictionary of all staged modifications
            is_exit_save: If True, ESC will be blocked in progress dialog
        """
        if not files_to_save:
            return

        success_count = 0
        failed_files = []
        _loading_dialog = None

        # Determine save mode based on file count
        file_count = len(files_to_save)
        save_mode = "single_file_wait_cursor" if file_count == 1 else "multiple_files_dialog"

        logger.info(
            f"[UnifiedMetadataManager] Saving metadata for {file_count} file(s) using mode: {save_mode}"
        )

        try:
            # Setup progress dialog for multiple files
            if save_mode == "multiple_files_dialog":
                # Only allow cancellation for normal saves when enabled in config
                cancel_callback = self.request_save_cancel if not is_exit_save else None

                _loading_dialog = ProgressDialog(
                    parent=self.parent_window,
                    operation_type="metadata_save",
                    cancel_callback=cancel_callback,
                    show_enhanced_info=False,
                    is_exit_save=is_exit_save,  # Pass exit save flag
                )
                _loading_dialog.set_status("Saving metadata...")
                _loading_dialog.show()

                # Process events to show dialog
                QApplication.processEvents()

            # Use wait_cursor context manager for single file
            cursor_context = wait_cursor() if save_mode == "single_file_wait_cursor" else contextlib.nullcontext()

            with cursor_context:
                # Process each file
                current_file_index = 0
                for file_item in files_to_save:
                    # Check for cancellation before processing each file
                    if self._save_cancelled:
                        logger.info(
                            f"[UnifiedMetadataManager] Save operation cancelled by user after {success_count}/{file_count} files"
                        )
                        break

                    current_file_index += 1

                    # Update progress dialog if in batch mode
                    if _loading_dialog:
                        _loading_dialog.set_filename(file_item.filename)
                        _loading_dialog.set_count(current_file_index, file_count)
                        _loading_dialog.set_progress(current_file_index, file_count)
                        QApplication.processEvents()

                    file_path = file_item.full_path

                    # Get modifications for this file - use path matching with normalization
                    modifications = self._get_modified_metadata_for_file(
                        file_path, all_modifications
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
        finally:
            # Close progress dialog if it was created
            if _loading_dialog:
                _loading_dialog.close()

        # Show results
        was_cancelled = self._save_cancelled
        self._show_save_results(success_count, failed_files, files_to_save, was_cancelled)

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
                                file_item.full_path, all_modifications
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
        """Get modified metadata for a specific file with path normalization."""
        # Try direct lookup first
        if file_path in all_modified_metadata:
            return all_modified_metadata[file_path]

        # Try normalized path lookup if direct fails (critical for cross-platform)
        from utils.path_normalizer import normalize_path
        normalized = normalize_path(file_path)

        for key, value in all_modified_metadata.items():
            if normalize_path(key) == normalized:
                return value

        # Not found
        return {}

    def _update_file_after_save(self, file_item, saved_metadata: dict = None):
        """
        Update file item after successful metadata save.

        Args:
            file_item: The FileItem that was saved
            saved_metadata: The metadata that was actually saved to the file
        """
        # Clear staged changes for this file
        try:
            staging_manager = self.parent_window.context.get_manager('metadata_staging')
            staging_manager.clear_staged_changes(file_item.full_path)
        except KeyError:
            logger.warning("[UnifiedMetadataManager] MetadataStagingManager not found during cleanup")

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

    def _show_save_results(self, success_count, failed_files, files_to_save, was_cancelled=False):
        """Show results of metadata save operation.

        Args:
            success_count: Number of files successfully saved
            failed_files: List of filenames that failed to save
            files_to_save: Original list of files to save
            was_cancelled: Whether the operation was cancelled by user
        """
        total_files = len(files_to_save)

        # Handle cancellation case
        if was_cancelled:
            skipped_count = total_files - success_count - len(failed_files)

            if success_count > 0:
                message = f"Save cancelled after {success_count}/{total_files} files"
                logger.info(f"[UnifiedMetadataManager] {message}")

                if self.parent_window and hasattr(self.parent_window, "status_bar"):
                    self.parent_window.status_bar.showMessage(message, 5000)
            else:
                message = "Save operation cancelled"
                logger.info(f"[UnifiedMetadataManager] {message}")

                if self.parent_window and hasattr(self.parent_window, "status_bar"):
                    self.parent_window.status_bar.showMessage(message, 3000)

            # Show info dialog about cancellation
            if self.parent_window:
                from widgets.custom_message_dialog import CustomMessageDialog

                msg_parts = ["Save operation cancelled by user."]

                if success_count > 0:
                    msg_parts.append(f"\nSuccessfully saved: {success_count} files")

                if failed_files:
                    msg_parts.append(f"Failed: {len(failed_files)} files")

                if skipped_count > 0:
                    msg_parts.append(f"Skipped: {skipped_count} files")

                CustomMessageDialog.information(
                    self.parent_window,
                    "Save Cancelled",
                    "\n".join(msg_parts)
                )
            return

        # Normal completion (not cancelled)
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
                f"[UnifiedMetadataManager] Failed to save metadata for {len(failed_files)} files"
            )
            for file_path in failed_files:
                logger.warning(f"[UnifiedMetadataManager] Failed to save metadata for: {file_path}")

            # Show error message
            if self.parent_window:
                from core.pyqt_imports import QMessageBox

                QMessageBox.warning(
                    self.parent_window,
                    "Metadata Save Error",
                    f"Failed to save metadata for {len(failed_files)} files.\n\n"
                    f"Files: {', '.join(failed_files[:5])}"
                    f"{'...' if len(failed_files) > 5 else ''}",
                )

    # =====================================
    # Structured Metadata Integration
    # =====================================

    def get_structured_metadata(self, file_path: str) -> dict:
        """
        Get structured metadata for a file with categorization.

        Args:
            file_path: Path to the file

        Returns:
            Dictionary with categorized metadata
        """
        return self.structured.get_structured_metadata(file_path)

    def process_and_store_metadata(self, file_path: str, raw_metadata: dict) -> bool:
        """
        Process raw metadata and store it in structured format.

        Args:
            file_path: Path to the file
            raw_metadata: Raw metadata dictionary from ExifTool

        Returns:
            True if successful, False otherwise
        """
        return self.structured.process_and_store_metadata(file_path, raw_metadata)

    def get_field_value(self, file_path: str, field_key: str) -> str | None:
        """
        Get specific metadata field value.

        Args:
            file_path: Path to the file
            field_key: Metadata field key

        Returns:
            Field value or None if not found
        """
        return self.structured.get_field_value(file_path, field_key)

    def update_field_value(self, file_path: str, field_key: str, field_value: str) -> bool:
        """
        Update metadata field value.

        Args:
            file_path: Path to the file
            field_key: Metadata field key
            field_value: New field value

        Returns:
            True if successful, False otherwise
        """
        return self.structured.update_field_value(file_path, field_key, field_value)

    def add_custom_field(
        self, field_key: str, field_name: str, category: str, **kwargs
    ) -> bool:
        """
        Add custom metadata field definition.

        Args:
            field_key: Unique field key
            field_name: Human-readable field name
            category: Category name
            **kwargs: Additional field properties

        Returns:
            True if successful, False otherwise
        """
        return self.structured.add_custom_field(field_key, field_name, category, **kwargs)

    def get_available_categories(self) -> list[dict]:
        """
        Get available metadata categories.

        Returns:
            List of category dictionaries
        """
        return self.structured.get_available_categories()

    def get_available_fields(self, category: str | None = None) -> list[dict]:
        """
        Get available metadata fields, optionally filtered by category.

        Args:
            category: Optional category name to filter by

        Returns:
            List of field dictionaries
        """
        return self.structured.get_available_fields(category)

    def search_files_by_metadata(self, field_key: str, field_value: str) -> list[str]:
        """
        Search files by metadata field value.

        Args:
            field_key: Metadata field key
            field_value: Value to search for

        Returns:
            List of file paths matching the criteria
        """
        return self.structured.search_files_by_metadata(field_key, field_value)

    def refresh_structured_caches(self) -> None:
        """Refresh structured metadata caches."""
        self.structured.refresh_caches()

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

        # Clean up structured manager
        if self._structured_manager is not None:
            self._structured_manager = None

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
