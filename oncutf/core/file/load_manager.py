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
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from oncutf.app.services.file_load import update_file_load_ui
from oncutf.config import (
    ALLOWED_EXTENSIONS,
    COMPANION_FILES_ENABLED,
    SHOW_COMPANION_FILES_IN_TABLE,
)
from oncutf.domain.keyboard import KeyboardModifier
from oncutf.models.file_item import FileItem
from oncutf.utils.filesystem.companion_files_helper import CompanionFilesHelper
from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.app.ports.drag_state import DragStatePort

logger = get_cached_logger(__name__)


class FileLoadManager:
    """Unified file loading manager with fully optimized policy:
    - All operations: wait_cursor only (fast, synchronous like external drops)
    - Same behavior for drag, import, and external operations
    - No complex progress dialogs, just simple and fast loading.
    """

    def __init__(
        self, parent_window: Any = None, drag_state: "DragStatePort | None" = None
    ) -> None:
        """Initialize FileLoadManager with parent window reference.

        Args:
            parent_window: Reference to main window
            drag_state: Port for drag state management (injected)

        """
        self.parent_window = parent_window
        self._drag_state = drag_state
        self.allowed_extensions = set(ALLOWED_EXTENSIONS)
        # Flag to prevent metadata tree refresh conflicts during metadata operations
        self._metadata_operation_in_progress = False
        # When True, FS-monitor triggered refresh is suppressed (dirty files visible)
        self._has_dirty_renamed_files: bool = False
        logger.debug(
            "[FileLoadManager] Initialized with unified loading policy",
            extra={"dev_only": True},
        )

    @property
    def drag_state(self) -> "DragStatePort":
        """Lazy-load drag state adapter from QtAppContext."""
        if self._drag_state is None:
            from oncutf.app.state.context import get_app_context

            context = get_app_context()
            self._drag_state = context.get_manager("drag_state")
            if self._drag_state is None:
                raise RuntimeError("DragStatePort not registered in QtAppContext")
        return self._drag_state

    """Unified file loading manager with fully optimized policy:
    - All operations: wait_cursor only (fast, synchronous like external drops)
    - Same behavior for drag, import, and external operations
    - No complex progress dialogs, just simple and fast loading.
    """

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

        if not Path(folder_path).is_dir():
            logger.error("Path is not a directory: %s", folder_path)
            return

        # Clear rename-dirty suppression on full folder loads so that the FS
        # monitor can operate normally and fresh FileItem objects are shown.
        if not merge_mode:
            self.clear_rename_dirty_state()

        # Store the recursive state for future reloads (if not merging)
        # Use QtAppContext for centralized state management
        if not merge_mode:
            self.parent_window.context.set_recursive_mode(recursive)
            logger.info(
                "[FileLoadManager] Stored recursive state: %s",
                recursive,
                extra={"dev_only": True},
            )

        # CRITICAL: Force cleanup any active drag state immediately
        if self.drag_state.is_dragging():
            logger.debug(
                "[FileLoadManager] Active drag detected, forcing cleanup before loading",
                extra={"dev_only": True},
            )
            self.drag_state.force_cleanup_drag()

        # Clear any existing cursors immediately and stop all drag visuals
        from oncutf.app.services import force_restore_cursor

        force_restore_cursor()

        # Force stop any drag visual feedback
        self.drag_state.end_drag_visual()

        # Clear drag zone validator for all possible sources
        self.drag_state.clear_drag_state("file_tree")
        self.drag_state.clear_drag_state("file_table")

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
        if self.drag_state.is_dragging():
            logger.debug(
                "[FileLoadManager] Active drag detected during import, forcing cleanup",
                extra={"dev_only": True},
            )
            self.drag_state.force_cleanup_drag()

        # Process all paths with fast wait cursor approach (same as drag operations)
        all_file_paths = []

        from oncutf.app.services import wait_cursor

        with wait_cursor():
            for path in paths:
                if Path(path).is_file():
                    if self._is_allowed_extension(path):
                        all_file_paths.append(path)
                elif Path(path).is_dir():
                    # Always recursive for import button (user selected folders deliberately)
                    folder_files = self._get_files_from_folder(path, recursive=True)
                    all_file_paths.extend(folder_files)

        # Update UI with all collected files
        if all_file_paths:
            self._update_ui_with_files(all_file_paths, clear=clear)

    def load_single_item_from_drop(
        self,
        path: str,
        modifiers: KeyboardModifier | None = None,
    ) -> None:
        """Handle single item drop with modifier support.
        Uses unified load_folder method for consistent behavior.
        """
        if modifiers is None:
            modifiers = KeyboardModifier.NONE

        logger.info(
            "[FileLoadManager] load_single_item_from_drop: %s",
            path,
            extra={"dev_only": True},
        )

        # Parse modifiers
        ctrl = bool(modifiers & KeyboardModifier.CTRL)
        shift = bool(modifiers & KeyboardModifier.SHIFT)
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
        if self.drag_state.is_dragging():
            logger.debug(
                "[FileLoadManager] Active drag detected during single file drop, forcing cleanup",
                extra={"dev_only": True},
            )
            self.drag_state.force_cleanup_drag()

        if Path(path).is_dir():
            # Use unified folder loading (will handle drag cleanup internally)
            self.load_folder(path, merge_mode=merge_mode, recursive=recursive)
        else:
            # Handle single file - cleanup drag state first
            if self.drag_state.is_dragging():
                logger.debug(
                    "[FileLoadManager] Active drag detected during single file drop, forcing cleanup"
                )
                self.drag_state.force_cleanup_drag()

            if self._is_allowed_extension(path):
                self._update_ui_with_files([path], clear=not merge_mode)

    def load_files_from_dropped_items(
        self,
        paths: list[str],
        modifiers: KeyboardModifier | None = None,
    ) -> None:
        """Handle multiple dropped items (table drop).
        Uses unified loading for consistent behavior.
        """
        if modifiers is None:
            modifiers = KeyboardModifier.NONE

        if not paths:
            logger.info("[Drop] No files dropped in table.")
            return

        logger.info("[Drop] %d file(s)/folder(s) dropped in table view", len(paths))

        # Parse modifiers
        ctrl = bool(modifiers & KeyboardModifier.CTRL)
        shift = bool(modifiers & KeyboardModifier.SHIFT)
        recursive = ctrl
        merge_mode = shift

        # Process all items with unified logic
        all_file_paths = []

        for path in paths:
            if Path(path).is_file():
                if self._is_allowed_extension(path):
                    all_file_paths.append(path)
            elif Path(path).is_dir():
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
                                # Use Path for cross-platform compatibility
                                full_path = str((Path(root) / filename).resolve())
                                file_paths.append(full_path)
                            except Exception as e:
                                logger.warning(
                                    "[FileLoadManager] Error processing file %s: %s",
                                    filename,
                                    e,
                                )
            except Exception:
                logger.exception("[FileLoadManager] Error walking directory %s", folder_path)
        else:
            try:
                file_paths.extend(
                    str(entry)
                    for entry in Path(folder_path).iterdir()
                    if self._is_allowed_extension(entry.name) and entry.is_file()
                )
            except OSError:
                logger.exception("[FileLoadManager] Error listing directory %s", folder_path)

        if sorted_output:
            file_paths.sort()

        logger.info(
            "[FileLoadManager] Found %d files in %s (recursive=%s)",
            len(file_paths),
            folder_path,
            recursive,
        )
        return file_paths

    def _is_allowed_extension(self, path: str) -> bool:
        """Check if file has allowed extension."""
        ext = Path(path).suffix.lower()
        ext = ext.removeprefix(".")
        return ext in self.allowed_extensions

    def get_file_items_from_folder(
        self, folder_path: str, *, use_cache: bool = True, file_store: Any = None
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
                return cast("list[FileItem]", cached_files)

        # Scan folder using unified scanning method (I/O operation)
        file_paths = self._get_files_from_folder(folder_path, recursive=False, sorted_output=True)

        # Convert to FileItem objects
        file_items = []
        for file_path in file_paths:
            try:
                file_items.append(FileItem.from_path(file_path))
            except OSError as e:
                logger.warning(
                    "[FileLoadManager] Could not create FileItem for %s: %s",
                    Path(file_path).name,
                    e,
                )
                continue

        # Cache results (via FileStore)
        if use_cache and file_store:
            file_store.set_cached_files(folder_path, file_items)

        # Load color tags from database for all files
        self._load_color_tags(file_items)

        logger.info("[FileLoadManager] Scanned %s: %d files", folder_path, len(file_items))
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
                    "[FileLoadManager] Filtered out %d companion files. Showing %d main files.",
                    companion_count,
                    len(filtered_files),
                )
        except Exception as e:
            logger.warning("[FileLoadManager] Error filtering companion files: %s", e)
            return file_paths
        else:
            return filtered_files

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
            except Exception:
                logger.exception("Error creating FileItem for %s", path)

        if not file_items:
            logger.warning("[FileLoadManager] No valid FileItem objects created")
            return

        # Load color tags from database
        self._load_color_tags(file_items)

        # Delegate to port service for model + UI updates
        update_file_load_ui(file_items, clear=clear)

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

    def suppress_next_refresh(self) -> None:
        """Block the next FS-monitor refresh while renamed files are shown as dirty.

        Called right after a successful rename so that the filesystem-monitor
        triggered rescan does not replace the mutated-in-place FileItem objects
        (which still display the OLD filename in yellow) with fresh ones.
        The flag is cleared by a full folder load (F5 / force reload).
        """
        self._has_dirty_renamed_files = True
        logger.debug(
            "[FileLoadManager] FS-monitor refresh suppressed (dirty renamed files present)",
            extra={"dev_only": True},
        )

    def clear_rename_dirty_state(self) -> None:
        """Clear the rename-dirty suppression flag on a full folder load.

        Called before loading a fresh file list so that FS-monitor refreshes
        are no longer blocked and FileItem objects reflect the current disk state.
        """
        self._has_dirty_renamed_files = False
        logger.debug(
            "[FileLoadManager] Rename-dirty state cleared (full reload)",
            extra={"dev_only": True},
        )

    def set_allowed_extensions(self, extensions: set[str]) -> None:
        """Update the set of allowed file extensions."""
        self.allowed_extensions = extensions
        logger.info("[FileLoadManager] Updated allowed extensions: %s", extensions)

    def clear_metadata_operation_flag(self) -> None:
        """Clear the metadata operation flag."""
        self._metadata_operation_in_progress = False
        logger.debug(
            "[FileLoadManager] Cleared metadata operation flag",
            extra={"dev_only": True},
        )

    def refresh_loaded_folders(
        self, changed_folder: str | None = None, file_store: Any = None
    ) -> bool:
        """Refresh files from loaded folders after filesystem changes.

        I/O LAYER METHOD - Performs filesystem scanning to reload files.
        Mutates existing FileItem objects in-place so that file_model references
        remain valid.  Sets file_missing=True on items no longer found on disk,
        and appends newly appeared files to the live list.  Emits layoutChanged
        on the file_model when anything changed so the table repaints.

        Args:
            changed_folder: Specific folder that changed (optional)
            file_store: FileStore instance to update (optional, uses parent_window if available)

        Returns:
            bool: True if refresh was attempted

        """
        # Suppress FS-monitor refresh while renamed files are displayed as dirty
        # (old filenames with yellow color).  The refresh will proceed normally
        # after the user forces a full reload (F5).
        if self._has_dirty_renamed_files:
            logger.debug(
                "[FileLoadManager] Skipping FS-monitor refresh (dirty renamed files suppressed)",
                extra={"dev_only": True},
            )
            return True

        # Resolve FileStore instance
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

        # Authoritative display list: prefer file_model.files (keeps same object refs)
        file_model: Any = getattr(self.parent_window, "file_model", None)
        live_files: list[FileItem] = list(getattr(file_model, "files", None) or loaded_files)

        # Get unique folders from live display list
        loaded_folders: set[str] = set()
        for file_item in live_files:
            folder = str(Path(file_item.full_path).parent)
            loaded_folders.add(folder)

        # If a specific folder was given, check if it's relevant
        if changed_folder:
            changed_folder_norm = os.path.normpath(changed_folder)
            if changed_folder_norm not in loaded_folders:
                logger.debug(
                    "[FileLoadManager] Changed folder not in loaded files: %s",
                    changed_folder,
                )
                return False
            folders_to_refresh: set[str] = {changed_folder_norm}
        else:
            folders_to_refresh = loaded_folders

        logger.info(
            "[FileLoadManager] Refreshing %d folder(s) after filesystem change",
            len(folders_to_refresh),
        )

        # Invalidate cache for affected folders
        for folder in folders_to_refresh:
            file_store.invalidate_folder_cache(folder)

        # Scan the refreshed folders; build path -> FileItem map for each
        # Folders that no longer exist produce an empty map (all their files go missing)
        scanned_per_folder: dict[str, dict[str, FileItem]] = {}
        for folder in folders_to_refresh:
            if not Path(folder).exists():
                logger.info(
                    "[FileLoadManager] Folder no longer exists, marking its files as missing: %s",
                    folder,
                )
                scanned_per_folder[folder] = {}
                continue
            try:
                folder_files = self.get_file_items_from_folder(
                    folder, use_cache=False, file_store=file_store
                )
                scanned_per_folder[folder] = {f.full_path: f for f in folder_files}
            except Exception:
                logger.exception("[FileLoadManager] Error scanning folder %s", folder)
                scanned_per_folder[folder] = {}

        # Build flat set of paths currently on disk (for refreshed folders only)
        disk_paths: set[str] = set()
        for folder_map in scanned_per_folder.values():
            disk_paths.update(folder_map.keys())

        # --- In-place mutation of existing FileItem objects ---
        existing_paths: set[str] = {f.full_path for f in live_files}
        changed = False

        for item in live_files:
            item_folder = str(Path(item.full_path).parent)
            if item_folder not in folders_to_refresh:
                continue  # Not in a folder being refreshed; leave as-is
            was_missing = item.file_missing
            item.file_missing = item.full_path not in disk_paths
            if item.file_missing != was_missing:
                changed = True
                if item.file_missing:
                    logger.info("[FileLoadManager] File went missing: %s", item.filename)
                else:
                    logger.info("[FileLoadManager] File reappeared: %s", item.filename)

        # --- Append genuinely new files (appeared on disk, not in live list) ---
        new_items: list[FileItem] = []
        for folder_map in scanned_per_folder.values():
            for path, new_item in folder_map.items():
                if path not in existing_paths:
                    new_items.append(new_item)
                    changed = True
                    logger.info("[FileLoadManager] New file appeared: %s", new_item.filename)

        if new_items:
            live_files.extend(new_items)

        # Sync merged list back to FileStore
        file_store.set_loaded_files(live_files)

        # Load color tags for newly appeared files
        if new_items:
            self._load_color_tags(new_items)

        # Notify file_model to repaint when the display state changed.
        # refresh_loaded_folders() may be called from a background thread
        # (watchdog / threading.Timer).  layoutChanged is a Qt pyqtSignal on
        # QAbstractItemModel: emitting from a non-main thread is safe because
        # Qt automatically delivers it as a queued connection to the connected
        # views which live in the main thread.
        if changed and file_model is not None:
            layout_changed = getattr(file_model, "layoutChanged", None)
            if layout_changed is not None:
                layout_changed.emit()
                logger.debug(
                    "[FileLoadManager] layoutChanged emitted after file status update",
                    extra={"dev_only": True},
                )

        missing_count = sum(1 for f in live_files if f.file_missing)
        logger.info(
            "[FileLoadManager] Refresh complete: %d files total, %d missing",
            len(live_files),
            missing_count,
        )
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
