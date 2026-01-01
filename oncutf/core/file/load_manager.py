"""Module: file_load_manager.py

Author: Michael Economou
Date: 2025-06-13

file_load_manager.py
Unified file loading manager with fully optimized policy:
- All operations: wait_cursor only (fast, synchronous)
- Consistent behavior between drag, import, and external operations
- No progress dialogs, just fast os.walk() for everything
"""

import os

from oncutf.config import (
    ALLOWED_EXTENSIONS,
    COMPANION_FILES_ENABLED,
    SHOW_COMPANION_FILES_IN_TABLE,
)
from oncutf.core.drag.drag_manager import force_cleanup_drag, is_dragging
from oncutf.core.pyqt_imports import Qt
from oncutf.models.file_item import FileItem
from oncutf.utils.filesystem.companion_files_helper import CompanionFilesHelper
from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.shared.timer_manager import get_timer_manager
from oncutf.utils.ui.cursor_helper import force_restore_cursor, wait_cursor

logger = get_cached_logger(__name__)


class FileLoadManager:
    """Unified file loading manager with fully optimized policy:
    - All operations: wait_cursor only (fast, synchronous like external drops)
    - Same behavior for drag, import, and external operations
    - No complex progress dialogs, just simple and fast loading
    """

    def __init__(self, parent_window=None):
        """Initialize FileLoadManager with parent window reference."""
        self.parent_window = parent_window
        self.allowed_extensions = set(ALLOWED_EXTENSIONS)
        self.timer_manager = get_timer_manager()
        # Flag to prevent metadata tree refresh conflicts during metadata operations
        self._metadata_operation_in_progress = False
        # Streaming file loading support
        self._pending_files = []
        self._loading_in_progress = False
        self._batch_size = 100  # Files to add per UI update cycle
        logger.debug(
            "[FileLoadManager] Initialized with unified loading policy + streaming support",
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
        force_restore_cursor()

        # Force stop any drag visual feedback
        from oncutf.core.drag.drag_visual_manager import end_drag_visual

        end_drag_visual()

        # Clear drag zone validator for all possible sources
        from oncutf.utils.ui.drag_zone_validator import DragZoneValidator

        DragZoneValidator.clear_initial_drag_widget("file_tree")
        DragZoneValidator.clear_initial_drag_widget("file_table")

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

        with wait_cursor():
            file_paths = self._get_files_from_folder(folder_path, recursive)
            self._update_ui_with_files(file_paths, clear=not merge_mode)

    def _get_files_from_folder(self, folder_path: str, recursive: bool = False) -> list[str]:
        """Get all valid files from folder.
        Returns list of file paths.
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
                logger.error(
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

        # Scan folder (I/O operation)
        file_paths = []
        try:
            for filename in sorted(os.listdir(folder_path)):
                if self._is_allowed_extension(filename):
                    full_path = os.path.join(folder_path, filename)
                    if os.path.isfile(full_path):
                        file_paths.append(full_path)
        except OSError as e:
            logger.error(
                "[FileLoadManager] Error scanning directory %s: %s",
                folder_path,
                e
            )
            return []

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
        Converts file paths to FileItem objects and updates the model.
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

        # Convert file paths to FileItem objects
        file_items = []
        for path in filtered_paths:
            try:
                file_item = FileItem.from_path(path)
                file_items.append(file_item)
            except Exception as e:
                logger.error("Error creating FileItem for %s: %s", path, e)

        if not file_items:
            logger.warning("[FileLoadManager] No valid FileItem objects created")
            return

        # Update the model
        self._update_ui_after_load(file_items, clear=clear)

    def _update_ui_after_load(self, items: list[FileItem], clear: bool = True) -> None:
        """Update UI after loading files.
        Uses streaming approach for large file sets to keep UI responsive.
        """
        if not hasattr(self.parent_window, "file_model"):
            logger.error("[FileLoadManager] Parent window has no file_model attribute")
            return

        try:
            # Set current folder path from first file's directory
            if items and clear:
                first_file_path = items[0].full_path
                if first_file_path:
                    folder_path = os.path.dirname(first_file_path)

                    # Check if this was a recursive load by looking for files in subdirectories
                    has_subdirectory_files = any(
                        os.path.dirname(item.full_path) != folder_path for item in items
                    )

                    # Set folder path and recursive mode in ApplicationContext (centralized state)
                    self.parent_window.context.set_current_folder(
                        folder_path, has_subdirectory_files
                    )
                    logger.info(
                        "[FileLoadManager] Set current_folder_path to: %s",
                        folder_path,
                        extra={"dev_only": True},
                    )
                    logger.info(
                        "[FileLoadManager] Recursive mode: %s",
                        has_subdirectory_files,
                        extra={"dev_only": True},
                    )

            # Use streaming loading for large file sets (> 200 files)
            if len(items) > 200:
                self._load_files_streaming(items, clear=clear)
            else:
                # Small file sets: load immediately (legacy behavior)
                self._load_files_immediate(items, clear=clear)

        except Exception as e:
            logger.error("[FileLoadManager] Error updating UI: %s", e)

    def _load_files_immediate(self, items: list[FileItem], clear: bool = True) -> None:
        """Load files immediately (legacy behavior for small file sets).
        Used for < 200 files where UI blocking is negligible.
        """
        if clear:
            # Replace existing files
            self.parent_window.file_model.set_files(items)
            # Also update FileStore (centralized state)
            self.parent_window.context.file_store.set_loaded_files(items)
            logger.info(
                "[FileLoadManager] Replaced files with %d new items",
                len(items),
                extra={"dev_only": True},
            )
            # Refresh UI to ensure placeholders, header and labels are updated
            try:
                self._refresh_ui_after_file_load()
            except Exception:
                logger.debug(
                    "[FileLoadManager] _refresh_ui_after_file_load failed", extra={"dev_only": True}
                )
        else:
            # Add to existing files with duplicate detection
            existing_files = self.parent_window.file_model.files

            # Create a set of existing file paths for fast lookup
            existing_paths = {file_item.full_path for file_item in existing_files}

            # Filter out duplicates from new items
            new_items = []
            duplicate_count = 0

            for item in items:
                if item.full_path not in existing_paths:
                    new_items.append(item)
                    existing_paths.add(
                        item.full_path
                    )  # Add to set to avoid duplicates within the new items too
                else:
                    duplicate_count += 1

            # Combine existing files with new non-duplicate items
            combined_files = existing_files + new_items
            self.parent_window.file_model.set_files(combined_files)
            # Also update FileStore (centralized state)
            self.parent_window.context.file_store.set_loaded_files(combined_files)

            # Log the results
            if duplicate_count > 0:
                logger.info(
                    "[FileLoadManager] Added %d new items, " "skipped %d duplicates",
                    len(new_items),
                    duplicate_count,
                )

    def _load_files_streaming(self, items: list[FileItem], clear: bool = True) -> None:
        """Load files in batches to keep UI responsive.
        Used for large file sets (> 200 files) to prevent UI freeze.
        """
        logger.info(
            "[FileLoadManager] Starting streaming load for %d files " "(batch_size=%d)",
            len(items),
            self._batch_size,
        )

        # Clear existing files if requested
        if clear:
            self.parent_window.file_model.set_files([])
            self.parent_window.context.file_store.set_loaded_files([])
            self._pending_files = items.copy()
        else:
            # Merge mode: filter duplicates first
            existing_files = self.parent_window.file_model.files
            existing_paths = {f.full_path for f in existing_files}
            self._pending_files = [item for item in items if item.full_path not in existing_paths]

        self._loading_in_progress = True
        self._process_next_batch()

    def _process_next_batch(self) -> None:
        """Process next batch of files in streaming loading.
        Called recursively via QTimer to keep UI responsive.
        """
        if not self._loading_in_progress or not self._pending_files:
            # Streaming complete
            self._loading_in_progress = False
            self._pending_files = []
            logger.info("[FileLoadManager] Streaming load complete")
            # Final UI refresh after streaming completes
            try:
                self._refresh_ui_after_file_load()
            except Exception:
                logger.debug(
                    "[FileLoadManager] _refresh_ui_after_file_load (stream end) failed",
                    extra={"dev_only": True},
                )
            return

        # Take next batch
        batch = self._pending_files[: self._batch_size]
        self._pending_files = self._pending_files[self._batch_size :]

        # Add batch to model
        existing_files = self.parent_window.file_model.files
        combined_files = existing_files + batch
        self.parent_window.file_model.set_files(combined_files)
        self.parent_window.context.file_store.set_loaded_files(combined_files)

        # Update status
        loaded_count = len(combined_files)
        total_count = loaded_count + len(self._pending_files)
        logger.debug(
            "[FileLoadManager] Streaming progress: %d/%d files",
            loaded_count,
            total_count,
            extra={"dev_only": True},
        )

        # Update files label to show progress
        if hasattr(self.parent_window, "update_files_label"):
            self.parent_window.update_files_label()

        # Schedule next batch (5ms delay to allow UI updates)
        from oncutf.utils.shared.timer_manager import TimerType, get_timer_manager

        get_timer_manager().schedule(
            self._process_next_batch,
            delay=5,
            timer_type=TimerType.UI_UPDATE,
            timer_id="file_load_next_batch",
            consolidate=False,  # Each batch must execute independently
        )

    def _refresh_ui_after_file_load(self) -> None:
        """Refresh all UI elements after files are loaded.
        This ensures placeholders are hidden, labels are updated, and selection works.
        """
        try:
            # Update files label (shows count)
            if hasattr(self.parent_window, "update_files_label"):
                self.parent_window.update_files_label()
                logger.debug("[FileLoadManager] Updated files label", extra={"dev_only": True})

            total_files = len(self.parent_window.file_model.files)

            # Hide file table placeholder when files are loaded
            if hasattr(self.parent_window, "file_table_view"):
                if total_files > 0:
                    # Hide file table placeholder when files are loaded
                    self.parent_window.file_table_view.set_placeholder_visible(False)
                    logger.debug(
                        "[FileLoadManager] Hidden file table placeholder", extra={"dev_only": True}
                    )
                else:
                    # Show file table placeholder when no files
                    self.parent_window.file_table_view.set_placeholder_visible(True)
                    logger.debug(
                        "[FileLoadManager] Shown file table placeholder", extra={"dev_only": True}
                    )

            # Ensure the header is enabled when there are files and disabled when empty
            if hasattr(self.parent_window, "header") and self.parent_window.header is not None:
                try:
                    if total_files > 0:
                        self.parent_window.header.setEnabled(True)
                    else:
                        self.parent_window.header.setEnabled(False)
                    logger.debug(
                        "[FileLoadManager] Header enabled state set to %s",
                        total_files > 0,
                        extra={"dev_only": True},
                    )
                except Exception:
                    logger.debug(
                        "[FileLoadManager] Failed to set header enabled state",
                        extra={"dev_only": True},
                    )

            # Hide placeholders in preview tables (if files are loaded)
            if hasattr(self.parent_window, "preview_tables_view"):
                if total_files > 0:
                    # Hide placeholders when files are loaded
                    self.parent_window.preview_tables_view._set_placeholders_visible(False)
                    logger.debug(
                        "[FileLoadManager] Hidden preview table placeholders",
                        extra={"dev_only": True},
                    )
                else:
                    # Show placeholders when no files
                    self.parent_window.preview_tables_view._set_placeholders_visible(True)
                    logger.debug(
                        "[FileLoadManager] Shown preview table placeholders",
                        extra={"dev_only": True},
                    )

            # Update preview tables
            if hasattr(self.parent_window, "request_preview_update"):
                self.parent_window.request_preview_update()
                logger.debug("[FileLoadManager] Requested preview update", extra={"dev_only": True})

            # Ensure file table selection works properly
            if hasattr(self.parent_window, "file_table_view"):
                # Restore previous sorting state for consistency
                if hasattr(self.parent_window, "current_sort_column") and hasattr(
                    self.parent_window, "current_sort_order"
                ):
                    sort_column = self.parent_window.current_sort_column
                    sort_order = self.parent_window.current_sort_order
                    logger.debug(
                        "[FileLoadManager] Restoring sort state: column=%s, order=%s",
                        sort_column,
                        sort_order,
                        extra={"dev_only": True},
                    )

                    # Apply sorting through the model and header
                    self.parent_window.file_model.sort(sort_column, sort_order)
                    header = self.parent_window.file_table_view.horizontalHeader()
                    header.setSortIndicator(sort_column, sort_order)

                # Force refresh of the table view
                self.parent_window.file_table_view.viewport().update()

                # Refresh icons to show any cached metadata/hash status
                if hasattr(self.parent_window.file_model, "refresh_icons"):
                    self.parent_window.file_model.refresh_icons()
                    logger.debug(
                        "[FileLoadManager] Refreshed file table icons", extra={"dev_only": True}
                    )

                # Reset selection state to ensure clicks work
                if hasattr(self.parent_window.file_table_view, "_sync_selection_safely"):
                    self.parent_window.file_table_view._sync_selection_safely()
                    logger.debug(
                        "[FileLoadManager] Refreshed file table view", extra={"dev_only": True}
                    )

            # Update metadata tree (clear it for new files)
            if hasattr(self.parent_window, "metadata_tree_view"):
                # Only refresh metadata tree if we're not in the middle of a metadata operation
                # This prevents conflicts with metadata loading operations (drag & drop, context menu, etc.)
                if not self._metadata_operation_in_progress:
                    if hasattr(
                        self.parent_window.metadata_tree_view, "refresh_metadata_from_selection"
                    ):
                        self.parent_window.metadata_tree_view.refresh_metadata_from_selection()
                        logger.debug(
                            "[FileLoadManager] Refreshed metadata tree", extra={"dev_only": True}
                        )
                else:
                    logger.debug(
                        "[FileLoadManager] Skipped metadata tree refresh (metadata operation in progress)",
                        extra={"dev_only": True},
                    )

            # Let metadata tree view handle search field state based on metadata availability
            # Don't directly enable/disable here - the metadata tree view will manage this
            # when metadata is loaded or cleared
            if total_files == 0 and hasattr(self.parent_window, "metadata_tree_view"):
                # Only force disable when no files at all
                if hasattr(self.parent_window.metadata_tree_view, "_update_search_field_state"):
                    self.parent_window.metadata_tree_view._update_search_field_state(False)
                    logger.debug(
                        "[FileLoadManager] Disabled metadata search field (no files)",
                        extra={"dev_only": True},
                    )

            logger.info(
                "[FileLoadManager] UI refresh completed successfully", extra={"dev_only": True}
            )

        except Exception as e:
            logger.error("[FileLoadManager] Error refreshing UI: %s", e)

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
            if hasattr(self.parent_window, "file_store"):
                file_store = self.parent_window.file_store
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
                logger.error("[FileLoadManager] Error refreshing folder %s: %s", folder, e)

        # Update FileStore state
        file_store.set_loaded_files(refreshed_files)

        logger.info("[FileLoadManager] Refreshed %d files", len(refreshed_files))
        return True
