"""Module: file_load_manager.py.

Author: Michael Economou
Date: 2025-06-13

File loading and I/O operations manager.

Responsibilities:
- Folder scanning (recursive and non-recursive)
- File loading with streaming support for large sets
- Drag & drop handling with modifier keys
- Filesystem refresh after external changes
- Cache coordination with FileStore
"""

import os

from oncutf.config import (
    ALLOWED_EXTENSIONS,
    COMPANION_FILES_ENABLED,
    SHOW_COMPANION_FILES_IN_TABLE,
)
from oncutf.core.drag.drag_manager import force_cleanup_drag, is_dragging
from oncutf.core.pyqt_imports import Qt
from oncutf.core.ui_managers.file_load_ui_service import FileLoadUIService
from oncutf.models.file_item import FileItem
from oncutf.utils.filesystem.companion_files_helper import CompanionFilesHelper
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class FileLoadManager:
    """Unified file loading manager with fully optimized policy:
    - All operations: wait_cursor only (fast, synchronous like external drops)
    - Same behavior for drag, import, and external operations
    - No complex progress dialogs, just simple and fast loading.
    """

    def __init__(self, parent_window=None):
        """Initialize FileLoadManager with parent window reference."""
        self.parent_window = parent_window
        self.allowed_extensions = set(ALLOWED_EXTENSIONS)
        # Flag to prevent metadata tree refresh conflicts during metadata operations
        self._metadata_operation_in_progress = False
        # UI refresh service (handles all model and UI updates)
        self._ui_service = FileLoadUIService(parent_window)
        logger.debug(
            "[FileLoadManager] Initialized with unified loading policy",
            extra={"dev_only": True},
        )

    def load_folder(
        self, folder_path: str, merge_mode: bool = False, recursive: bool = False
    ) -> None:
        """Unified folder loading method for both drag and import operations.

        New Policy:
        - All operations: wait_cursor only (fast, synchronous like external drops)
        - Consistent behavior between internal and external drag operations
        """
        logger.info(
            "[FileLoadManager] load_folder: %s (merge=%s, recursive=%s)",
            folder_path,
            merge_mode,
            recursive,
            extra={"dev_only": True},
        )

        if not os.path.isdir(folder_path):
            logger.error("Path is not a directory: %s", folder_path)
            return

        # Store the recursive state for future reloads (if not merging)
        # Use ApplicationContext for centralized state management
        if not merge_mode:
            self.parent_window.context.set_recursive_mode(recursive)
            logger.info(
                "[FileLoadManager] Stored recursive state: %s", recursive, extra={"dev_only": True}
            )

        # CRITICAL: Force cleanup any active drag state immediately
        if is_dragging():
            logger.debug(
                "[FileLoadManager] Active drag detected, forcing cleanup before loading",
                extra={"dev_only": True},
            )
            force_cleanup_drag()

        # Clear any existing cursors immediately and stop all drag visuals
        from oncutf.app.services import force_restore_cursor

        force_restore_cursor()

        # Force stop any drag visual feedback
        from oncutf.core.drag.drag_visual_manager import end_drag_visual

        end_drag_visual()

        # Clear drag zone validator for all possible sources
        from oncutf.app.services.drag_state import clear_drag_state

        clear_drag_state("file_tree")
        clear_drag_state("file_table")

        # Always use fast wait cursor approach (same as external drops)
        # This makes internal and external drag behavior consistent
        self._load_folder_with_wait_cursor(folder_path, merge_mode, recursive)

    def load_files_from_paths(self, paths: list[str], clear: bool = True) -> None:
        """Load files from multiple paths (used by import button).
        Now uses same fast approach as drag operations for consistency.
        """
        logger.info(
            "[FileLoadManager] load_files_from_paths: %d paths",
            len(paths),
            extra={"dev_only": True},
        )

        # Force cleanup any active drag state (import button shouldn't have drag, but safety first)
        if is_dragging():
            logger.debug(
                "[FileLoadManager] Active drag detected during import, forcing cleanup",
                extra={"dev_only": True},
            )
            force_cleanup_drag()

        # Process all paths with fast wait cursor approach (same as drag operations)
        all_file_paths = []

        from oncutf.app.services import wait_cursor

        with wait_cursor():
            for path in paths:
                if os.path.isfile(path):
                    if self._is_allowed_extension(path):
                        all_file_paths.append(path)
                elif os.path.isdir(path):
                    # Always recursive for import button (user selected folders deliberately)
                    folder_files = self._get_files_from_folder(path, recursive=True)
                    all_file_paths.extend(folder_files)

        # Update UI with all collected files
        if all_file_paths:
            self._update_ui_with_files(all_file_paths, clear=clear)

    def load_single_item_from_drop(
        self, path: str, modifiers: Qt.KeyboardModifiers = Qt.KeyboardModifiers(Qt.NoModifier)
    ) -> None:
        """Handle single item drop with modifier support.
        Uses unified load_folder method for consistent behavior.
        """
        logger.info(
            "[FileLoadManager] load_single_item_from_drop: %s", path, extra={"dev_only": True}
        )

        # Parse modifiers
        ctrl = bool(modifiers & Qt.ControlModifier)
        shift = bool(modifiers & Qt.ShiftModifier)
        recursive = ctrl
        merge_mode = shift

        logger.debug(
            "[Drop] Modifiers: ctrl=%s, shift=%s -> recursive=%s, merge=%s",
            ctrl,
            shift,
            recursive,
            merge_mode,
            extra={"dev_only": True},
        )

        # CRITICAL: Force cleanup any active drag state immediately
        if is_dragging():
            logger.debug(
                "[FileLoadManager] Active drag detected during single file drop, forcing cleanup",
                extra={"dev_only": True},
            )
            force_cleanup_drag()

        if os.path.isdir(path):
            # Use unified folder loading (will handle drag cleanup internally)
            self.load_folder(path, merge_mode=merge_mode, recursive=recursive)
        else:
            # Handle single file - cleanup drag state first
            if is_dragging():
                logger.debug(
                    "[FileLoadManager] Active drag detected during single file drop, forcing cleanup"
                )
                force_cleanup_drag()

            if self._is_allowed_extension(path):
                self._update_ui_with_files([path], clear=not merge_mode)

    def load_files_from_dropped_items(
        self, paths: list[str], modifiers: Qt.KeyboardModifiers = Qt.KeyboardModifiers(Qt.NoModifier)
    ) -> None:
        """Handle multiple dropped items (table drop).
        Uses unified loading for consistent behavior.
        """
        if not paths:
            logger.info("[Drop] No files dropped in table.")
            return

        logger.info("[Drop] %d file(s)/folder(s) dropped in table view", len(paths))

        # Parse modifiers
        ctrl = bool(modifiers & Qt.ControlModifier)
        shift = bool(modifiers & Qt.ShiftModifier)
        recursive = ctrl
        merge_mode = shift

        # Process all items with unified logic
        all_file_paths = []

        for path in paths:
            if os.path.isfile(path):
                if self._is_allowed_extension(path):
                    all_file_paths.append(path)
            elif os.path.isdir(path):
                # For table drops, collect files synchronously to avoid multiple dialogs
                folder_files = self._get_files_from_folder(path, recursive)
                all_file_paths.extend(folder_files)

        # Update UI with all collected files
        if all_file_paths:
            self._update_ui_with_files(all_file_paths, clear=not merge_mode)

    def _load_folder_with_wait_cursor(
        self, folder_path: str, merge_mode: bool, recursive: bool = False
    ) -> None:
        """Load folder with wait cursor only (fast approach for all operations)."""
        logger.debug(
            "[FileLoadManager] Loading folder with wait cursor: %s (recursive=%s)",
            folder_path,
            recursive,
            extra={"dev_only": True},
        )

        from oncutf.app.services import wait_cursor

        with wait_cursor():
            file_paths = self._get_files_from_folder(folder_path, recursive)
            self._update_ui_with_files(file_paths, clear=not merge_mode)

    def _get_files_from_folder(
        self, folder_path: str, recursive: bool = False, *, sorted_output: bool = False
    ) -> list[str]:
        """Get all valid files from folder (I/O operation).

        Core scanning method used by all folder loading operations.

        Args:
            folder_path: Path to folder to scan
            recursive: Whether to scan subdirectories
            sorted_output: Whether to sort results alphabetically

        Returns:
            List of file paths

        """
        file_paths = []
        if recursive:
            try:
                for root, _, filenames in os.walk(folder_path):
                    for filename in filenames:
                        if self._is_allowed_extension(filename):
                            try:
                                # Use normpath for cross-platform compatibility
                                full_path = os.path.normpath(os.path.join(root, filename))
                                file_paths.append(full_path)
                            except Exception as e:
                                logger.warning(
                                    "[FileLoadManager] Error processing file %s: %s",
                                    filename,
                                    e
                                )
            except Exception as e:
                logger.exception(
                    "[FileLoadManager] Error walking directory %s: %s",
                    folder_path,
                    e
                )
        else:
            try:
                for filename in os.listdir(folder_path):
                    if self._is_allowed_extension(filename):
                        full_path = os.path.join(folder_path, filename)
                        if os.path.isfile(full_path):
                            file_paths.append(full_path)
            except OSError as e:
                logger.error(
                    "[FileLoadManager] Error listing directory %s: %s",
                    folder_path,
                    e
                )

        if sorted_output:
            file_paths.sort()

        logger.info(
            "[FileLoadManager] Found %d files in %s (recursive=%s)",
            len(file_paths),
            folder_path,
            recursive
        )
        return file_paths

    def _is_allowed_extension(self, path: str) -> bool:
        """Check if file has allowed extension."""
        ext = os.path.splitext(path)[1].lower()
        if ext.startswith("."):
            ext = ext[1:]
        return ext in self.allowed_extensions

    def get_file_items_from_folder(
        self, folder_path: str, *, use_cache: bool = True, file_store=None
    ) -> list[FileItem]:
        """Scan folder and return FileItem objects (with caching support).

        This method performs I/O operations to scan the filesystem.
        Cache is stored in FileStore for state persistence.
        Delegates scanning to _get_files_from_folder() for consistency.

        Args:
            folder_path: Absolute path to folder to scan
            use_cache: Whether to use cached results if available
            file_store: FileStore instance (optional, uses parent_window.context if not provided)

        Returns:
            List of FileItem objects for supported files

        """
        # Get FileStore instance
        if not file_store:
            if hasattr(self.parent_window, "context"):
                file_store = self.parent_window.context.file_store
            else:
                file_store = None

        # Check cache first (via FileStore)
        if use_cache and file_store:
            cached_files = file_store.get_cached_files(folder_path)
            if cached_files is not None:
                logger.debug(
                    "[FileLoadManager] Using cached files for %s: %d items",
                    folder_path,
                    len(cached_files),
                )
                return cached_files

        # Scan folder using unified scanning method (I/O operation)
        file_paths = self._get_files_from_folder(
            folder_path, recursive=False, sorted_output=True
        )

        # Convert to FileItem objects
        file_items = []
        for file_path in file_paths:
            try:
                file_items.append(FileItem.from_path(file_path))
            except OSError as e:
                logger.warning(
                    "[FileLoadManager] Could not create FileItem for %s: %s",
                    os.path.basename(file_path),
                    e
                )
                continue

        # Cache results (via FileStore)
        if use_cache and file_store:
            file_store.set_cached_files(folder_path, file_items)

        # Load color tags from database for all files
        self._load_color_tags(file_items)

        logger.info(
            "[FileLoadManager] Scanned %s: %d files", folder_path, len(file_items)
        )
        return file_items

    def _filter_companion_files(self, file_paths: list[str]) -> list[str]:
        """Filter companion files based on configuration.

        Args:
            file_paths: List of file paths to filter

        Returns:
            Filtered list of file paths

        """
        if not COMPANION_FILES_ENABLED or SHOW_COMPANION_FILES_IN_TABLE:
            # Either companion files are disabled or we should show them
            return file_paths

        try:
            # Group files with their companions
            file_groups = CompanionFilesHelper.group_files_with_companions(file_paths)

            filtered_files = []
            companion_count = 0

            # Extract main files only (hide companion files)
            for main_file, group_info in file_groups.items():
                filtered_files.append(main_file)
                companion_count += len(group_info.get("companions", []))

            if companion_count > 0:
                logger.info(
                    "[FileLoadManager] Filtered out %d companion files. " "Showing %d main files.",
                    companion_count,
                    len(filtered_files),
                )

            return filtered_files

        except Exception as e:
            logger.warning("[FileLoadManager] Error filtering companion files: %s", e)
            return file_paths

    def _update_ui_with_files(self, file_paths: list[str], clear: bool = True) -> None:
        """Update UI with loaded files.
        Converts file paths to FileItem objects and delegates to service.
        """
        if not file_paths:
            logger.info("[FileLoadManager] No files to update UI with")
            return

        # Filter companion files if needed
        filtered_paths = self._filter_companion_files(file_paths)

        logger.info(
            "[FileLoadManager] Updating UI with %d files (clear=%s)",
            len(filtered_paths),
            clear,
            extra={"dev_only": True},
        )

        # Convert file paths to FileItem objects (I/O only)
        file_items = []
        for path in filtered_paths:
            try:
                file_item = FileItem.from_path(path)
                file_items.append(file_item)
            except Exception as e:
                logger.exception("Error creating FileItem for %s: %s", path, e)

        if not file_items:
            logger.warning("[FileLoadManager] No valid FileItem objects created")
            return

        # Load color tags from database
        self._load_color_tags(file_items)

        # Delegate to service for model + UI updates
        self._ui_service.update_model_and_ui(file_items, clear=clear)

    def prepare_folder_load(self, folder_path: str, *, _clear: bool = True) -> list[str]:
        """Prepare folder for loading by getting file list.
        Returns list of file paths without loading them into UI.
        """
        logger.info("[FileLoadManager] prepare_folder_load: %s", folder_path)
        return self._get_files_from_folder(folder_path, recursive=False)

    def reload_current_folder(self) -> None:
        """Reload the current folder if available."""
        logger.info("[FileLoadManager] reload_current_folder called")
        # Implementation depends on how current folder is tracked

    def set_allowed_extensions(self, extensions: set[str]) -> None:
        """Update the set of allowed file extensions."""
        self.allowed_extensions = extensions
        logger.info("[FileLoadManager] Updated allowed extensions: %s", extensions)

    def clear_metadata_operation_flag(self) -> None:
        """Clear the metadata operation flag."""
        self._metadata_operation_in_progress = False
        logger.debug("[FileLoadManager] Cleared metadata operation flag", extra={"dev_only": True})

    def refresh_loaded_folders(
        self, changed_folder: str | None = None, file_store=None
    ) -> bool:
        """Refresh files from loaded folders after filesystem changes.

        I/O LAYER METHOD - Performs filesystem scanning to reload files.
        Updates FileStore state with refreshed file list.

        Args:
            changed_folder: Specific folder that changed (optional)
            file_store: FileStore instance to update (optional, uses parent_window if available)

        Returns:
            bool: True if files were refreshed

        """
        # Get FileStore instance
        if not file_store:
            if hasattr(self.parent_window, "context") and hasattr(
                self.parent_window.context, "file_store"
            ):
                file_store = self.parent_window.context.file_store
            else:
                logger.warning("[FileLoadManager] No FileStore available for refresh")
                return False

        loaded_files = file_store.get_loaded_files()
        if not loaded_files:
            logger.debug("[FileLoadManager] No files loaded, skipping refresh")
            return False

        # Get unique folders from loaded files
        loaded_folders = set()
        for file_item in loaded_files:
            folder = os.path.dirname(file_item.full_path)
            loaded_folders.add(folder)

        # If specific folder given, check if it's relevant
        if changed_folder:
            changed_folder_norm = os.path.normpath(changed_folder)
            if changed_folder_norm not in loaded_folders:
                logger.debug(
                    "[FileLoadManager] Changed folder not in loaded files: %s", changed_folder
                )
                return False

            folders_to_refresh = {changed_folder_norm}
        else:
            folders_to_refresh = loaded_folders

        logger.info(
            "[FileLoadManager] Refreshing %d folder(s) after filesystem change",
            len(folders_to_refresh),
        )

        # Invalidate cache for affected folders
        for folder in folders_to_refresh:
            file_store.invalidate_folder_cache(folder)

        # Reload files from all loaded folders (I/O operation)
        refreshed_files: list[FileItem] = []
        for folder in loaded_folders:
            # Skip folders that no longer exist (e.g., unmounted USB drives)
            if not os.path.exists(folder):
                logger.info(
                    "[FileLoadManager] Folder no longer exists, removing its files: %s", folder
                )
                continue

            try:
                # Use get_file_items_from_folder for I/O (bypasses cache)
                folder_files = self.get_file_items_from_folder(
                    folder, use_cache=False, file_store=file_store
                )
                refreshed_files.extend(folder_files)
            except Exception as e:
                logger.exception("[FileLoadManager] Error refreshing folder %s: %s", folder, e)

        # Update FileStore state
        file_store.set_loaded_files(refreshed_files)

        logger.info("[FileLoadManager] Refreshed %d files", len(refreshed_files))
        return True

    def _load_color_tags(self, file_items: list[FileItem]) -> None:
        """Load color tags from database for a list of files.

        This method breaks the models→core cycle by loading colors
        after FileItem initialization using the repository pattern.

        Args:
            file_items: List of FileItems to load colors for

        """
        if not file_items:
            return

        try:
            from oncutf.infra.db import get_file_repository

            repo = get_file_repository()

            # Load colors for all files
            for item in file_items:
                try:
                    color = repo.get_color_tag(item.full_path)
                    item.color = color
                    if color != "none":
                        logger.debug(
                            "[FileLoadManager] Loaded color %s for %s",
                            color,
                            item.filename,
                            extra={"dev_only": True},
                        )
                except Exception as e:
                    logger.warning(
                        "[FileLoadManager] Could not load color for %s: %s",
                        item.filename,
                        e,
                    )
                    item.color = "none"

        except Exception as e:
            logger.warning("[FileLoadManager] Could not initialize file repository: %s", e)
