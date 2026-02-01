"""Module: file_load_controller.py.

Author: Michael Economou
Date: 2025-12-15

FileLoadController: Handles file loading operations.

This controller orchestrates file loading workflows, coordinating between
FileLoadManager, FileStore, and related services. It handles:
- File drag & drop coordination
- Directory scanning and recursion
- Companion file grouping
- File list management and validation
- Progress tracking for long operations

The controller is UI-agnostic and focuses on business logic orchestration.
"""

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from PyQt5.QtCore import Qt

from oncutf.config import ALLOWED_EXTENSIONS

if TYPE_CHECKING:
    from oncutf.app.state.context import AppContext as ApplicationContext
    from oncutf.app.state.file_store import FileStore
    from oncutf.controllers.protocols import TableManagerProtocol
    from oncutf.core.file.load_manager import FileLoadManager

logger = logging.getLogger(__name__)


class FileLoadController:
    """Controller for file loading operations.

    Orchestrates file loading workflows by coordinating FileLoadManager,
    FileStore, and related services. Provides a clean API for UI components
    to trigger file loading without knowing implementation details.

    This controller adds orchestration logic on top of FileLoadManager:
    - Path validation and filtering
    - Error handling and result aggregation
    - Coordination between multiple services
    - State management (recursive mode, merge mode)

    Attributes:
        _file_load_manager: Manager handling low-level file operations
        _file_store: Store maintaining loaded file state
        _table_manager: Manager for table UI updates
        _context: Application context for global state
        _allowed_extensions: Set of allowed file extensions

    """

    def __init__(
        self,
        file_load_manager: Optional["FileLoadManager"] = None,
        file_store: Optional["FileStore"] = None,
        table_manager: Optional["TableManagerProtocol"] = None,
        context: Optional["ApplicationContext"] = None,
    ) -> None:
        """Initialize FileLoadController.

        Args:
            file_load_manager: Manager for file loading operations (injected)
            file_store: Store for maintaining file state (injected)
            table_manager: Manager for table UI updates (injected)
            context: Application context for global state (injected)

        """
        logger.info("[FileLoadController] Initializing controller")
        self._file_load_manager = file_load_manager
        self._file_store = file_store
        self._table_manager = table_manager
        self._context = context
        self._allowed_extensions = set(ALLOWED_EXTENSIONS)

        logger.debug(
            "[FileLoadController] Initialized with managers: "
            "file_load_manager=%s, file_store=%s, table_manager=%s, context=%s",
            file_load_manager is not None,
            file_store is not None,
            table_manager is not None,
            context is not None,
            extra={"dev_only": True},
        )

    def load_files(self, paths: list[str], clear: bool = True) -> dict[str, Any]:
        """Load files from given paths with validation and error handling.

        This method orchestrates file loading by:
        1. Validating input paths exist
        2. Filtering valid files by extension
        3. Delegating to FileLoadManager for actual loading
        4. Collecting and returning results

        Args:
            paths: List of file paths as strings
            clear: Whether to clear existing files before loading

        Returns:
            Dictionary containing:
                - success (bool): Whether operation succeeded overall
                - loaded_count (int): Number of files successfully loaded
                - errors (List[str]): Any error messages encountered
                - skipped (List[str]): Files skipped (wrong extension, etc.)

        """
        logger.info("[FileLoadController] load_files: %d paths (clear=%s)", len(paths), clear)

        if not self._file_load_manager:
            logger.error("[FileLoadController] FileLoadManager not available")
            return {
                "success": False,
                "loaded_count": 0,
                "errors": ["FileLoadManager not initialized"],
                "skipped": [],
            }

        # Validate paths exist and separate files from directories
        valid_files: list[str] = []
        errors: list[str] = []
        skipped: list[str] = []

        for path_str in paths:
            path = Path(path_str)

            # Check path exists
            if not path.exists():
                errors.append(f"Path does not exist: {path_str}")
                logger.warning("[FileLoadController] Path does not exist: %s", path_str)
                continue

            # Handle directories separately
            if path.is_dir():
                logger.debug(
                    "[FileLoadController] Directory in paths, skipping (use load_folder): %s",
                    path_str,
                    extra={"dev_only": True},
                )
                skipped.append(f"Directory (use load_folder): {path_str}")
                continue

            # Validate file extension
            if path.suffix.lower() not in self._allowed_extensions:
                logger.debug(
                    "[FileLoadController] File extension not allowed: %s",
                    path_str,
                    extra={"dev_only": True},
                )
                skipped.append(f"Extension not allowed: {path_str}")
                continue

            # Check file is readable
            if not os.access(path, os.R_OK):
                errors.append(f"File not readable: {path_str}")
                logger.warning("[FileLoadController] File not readable: %s", path_str)
                continue

            valid_files.append(path_str)

        # If no valid files, return early
        if not valid_files:
            logger.info("[FileLoadController] No valid files to load after validation")
            return {
                "success": len(errors) == 0,
                "loaded_count": 0,
                "errors": errors,
                "skipped": skipped,
            }

        # Delegate to FileLoadManager for actual loading
        try:
            logger.debug(
                "[FileLoadController] Delegating %d valid files to FileLoadManager",
                len(valid_files),
                extra={"dev_only": True},
            )
            self._file_load_manager.load_files_from_paths(valid_files, clear=clear)

            # Get loaded count from file store
            loaded_count = len(valid_files)  # Assume all loaded successfully

            logger.info("[FileLoadController] Successfully loaded %d files", loaded_count)
        except Exception as e:
            logger.exception("[FileLoadController] Error during file loading")
            errors.append(f"Loading error: {e!s}")
            return {
                "success": False,
                "loaded_count": 0,
                "errors": errors,
                "skipped": skipped,
            }
        else:
            return {
                "success": True,
                "loaded_count": loaded_count,
                "errors": errors,
                "skipped": skipped,
            }

    def load_folder(
        self, folder_path: str, merge_mode: bool = False, recursive: bool = False
    ) -> dict[str, Any]:
        """Load all files from a folder with optional recursion.

        Args:
            folder_path: Path to folder to load
            merge_mode: If True, merge with existing files; if False, clear first
            recursive: If True, scan subdirectories recursively

        Returns:
            Dictionary with success status and loaded count

        """
        logger.info(
            "[FileLoadController] load_folder: %s (merge=%s, recursive=%s)",
            folder_path,
            merge_mode,
            recursive,
        )

        if not self._file_load_manager:
            logger.error("[FileLoadController] FileLoadManager not available")
            return {
                "success": False,
                "loaded_count": 0,
                "errors": ["Manager not initialized"],
            }

        # Validate folder exists
        folder = Path(folder_path)
        if not folder.exists():
            error_msg = f"Folder does not exist: {folder_path}"
            logger.error("[FileLoadController] %s", error_msg)
            return {"success": False, "loaded_count": 0, "errors": [error_msg]}

        if not folder.is_dir():
            error_msg = f"Path is not a directory: {folder_path}"
            logger.error("[FileLoadController] %s", error_msg)
            return {"success": False, "loaded_count": 0, "errors": [error_msg]}

        # Store recursive state in context for future reloads
        if self._context and not merge_mode:
            self._context.set_recursive_mode(recursive)
            logger.debug(
                "[FileLoadController] Stored recursive state: %s",
                recursive,
                extra={"dev_only": True},
            )

        # Delegate to FileLoadManager
        try:
            self._file_load_manager.load_folder(folder_path, merge_mode, recursive)

            logger.info("[FileLoadController] Folder loaded successfully")
        except Exception as e:
            logger.exception("[FileLoadController] Error loading folder")
            return {
                "success": False,
                "loaded_count": 0,
                "errors": [str(e)],
            }
        else:
            return {
                "success": True,
                "loaded_count": -1,
                "errors": [],
            }  # Count not available yet

    def handle_drop(
        self,
        paths: list[str],
        modifiers: "Qt.KeyboardModifiers" = Qt.KeyboardModifiers(),
    ) -> dict[str, Any]:
        """Handle file/folder drop with keyboard modifiers.

        Args:
            paths: List of dropped paths (files or folders)
            modifiers: Keyboard modifiers during drop (Ctrl, Shift, etc.)

        Returns:
            Dictionary with success status

        """
        import time

        t0 = time.time()

        # Decode modifiers for readable logging
        from oncutf.core.modifier_handler import decode_modifiers_to_flags

        _, _, modifier_desc = decode_modifiers_to_flags(modifiers)
        logger.debug(
            "[DROP-CONTROLLER] handle_drop START: %d paths (modifiers=%s)",
            len(paths),
            modifier_desc,
            extra={"dev_only": True},
        )

        if not self._file_load_manager:
            logger.error("[FileLoadController] FileLoadManager not available")
            return {"success": False, "errors": ["Manager not initialized"]}

        if not paths:
            logger.warning("[FileLoadController] No paths provided for drop")
            return {"success": False, "errors": ["No paths provided"]}

        # Delegate to FileLoadManager which handles modifiers
        try:
            t1 = time.time()
            logger.debug(
                "[DROP-CONTROLLER] Calling load_files_from_dropped_items at +%.3fms",
                (t1 - t0) * 1000,
                extra={"dev_only": True},
            )

            self._file_load_manager.load_files_from_dropped_items(paths, modifiers)

            t2 = time.time()
            logger.debug(
                "[DROP-CONTROLLER] load_files_from_dropped_items returned at +%.3fms",
                (t2 - t0) * 1000,
                extra={"dev_only": True},
            )
            logger.info("[FileLoadController] Drop handled successfully")
        except Exception as e:
            logger.exception("[FileLoadController] Error handling drop")
            return {"success": False, "errors": [str(e)]}
        else:
            return {"success": True, "errors": []}
        finally:
            # Ensure wait cursor is restored
            from PyQt5.QtWidgets import QApplication

            t_restore = time.time()
            logger.debug(
                "[DROP-CONTROLLER] Restoring cursor at +%.3fms",
                (t_restore - t0) * 1000,
                extra={"dev_only": True},
            )
            QApplication.restoreOverrideCursor()
            logger.debug(
                "[DROP-CONTROLLER] Cursor restored at +%.3fms",
                (time.time() - t0) * 1000,
                extra={"dev_only": True},
            )

    def clear_files(self) -> bool:
        """Clear all loaded files.

        Returns:
            True if files were cleared successfully

        """
        logger.info("[FileLoadController] Clearing all files")

        if not self._table_manager:
            logger.error("[FileLoadController] TableManager not available")
            return False

        try:
            # Use table manager to clear the file table
            self._table_manager.clear_file_table()
            logger.info("[FileLoadController] Files cleared successfully")
        except Exception as e:
            logger.exception("[FileLoadController] Error clearing files")
            return False
        else:
            return True

    def get_loaded_file_count(self) -> int:
        """Get count of currently loaded files.

        Returns:
            Number of loaded files

        """
        if self._file_store is None:
            logger.debug(
                "[FileLoadController] FileStore not available, returning 0",
                extra={"dev_only": True},
            )
            return 0

        try:
            count = len(self._file_store.get_loaded_files())
            logger.debug(
                "[FileLoadController] Current file count: %d",
                count,
                extra={"dev_only": True},
            )
        except Exception as e:
            logger.error("[FileLoadController] Error getting file count: %s", str(e))
            return 0
        else:
            return count

    def is_recursive_mode(self) -> bool:
        """Check if recursive mode is enabled.

        Returns:
            True if recursive mode is active

        """
        if self._context is None:
            return False

        try:
            return self._context.is_recursive_mode()
        except Exception:
            return False

    def set_recursive_mode(self, recursive: bool) -> None:
        """Set recursive mode for future folder loads.

        Args:
            recursive: Whether to enable recursive scanning

        """
        logger.info("[FileLoadController] Setting recursive mode: %s", recursive)

        if self._context:
            self._context.set_recursive_mode(recursive)
        else:
            logger.warning("[FileLoadController] Cannot set recursive mode: context not available")
