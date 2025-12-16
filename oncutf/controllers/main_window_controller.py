"""
Module: main_window_controller.py

Author: Michael Economou
Date: 2025-12-16

MainWindowController: High-level orchestration controller.

This controller coordinates all sub-controllers (FileLoad, Metadata, Rename)
and manages complex workflows that involve multiple domains. It handles:
- Multi-controller workflows (e.g., load files → load metadata)
- Application-level state coordination
- Complex user actions that span multiple domains
- Event propagation between controllers

The controller is UI-agnostic and focuses on orchestration logic.

Architecture:
    MainWindow (UI) → MainWindowController (orchestration)
                    ├→ FileLoadController (file operations)
                    ├→ MetadataController (metadata operations)
                    └→ RenameController (rename operations)

Each controller is UI-agnostic and testable independently.
MainWindowController coordinates complex workflows that span multiple domains.
"""

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from oncutf.controllers.file_load_controller import FileLoadController
    from oncutf.controllers.metadata_controller import MetadataController
    from oncutf.controllers.rename_controller import RenameController
    from oncutf.core.application_context import ApplicationContext

logger = logging.getLogger(__name__)


class MainWindowController:
    """
    High-level orchestration controller.

    Coordinates FileLoadController, MetadataController, and RenameController
    to handle complex workflows that span multiple domains.

    Responsibilities:
    - Orchestrate multi-step workflows
    - Coordinate between sub-controllers
    - Manage application-level state
    - Handle complex user actions

    This controller does NOT:
    - Interact directly with UI widgets
    - Contain domain-specific logic (that's in sub-controllers)
    - Duplicate logic from sub-controllers

    Attributes:
        _app_context: Application context with shared services
        _file_load_controller: Controller for file loading operations
        _metadata_controller: Controller for metadata operations
        _rename_controller: Controller for rename operations
    """

    def __init__(
        self,
        app_context: "ApplicationContext",
        file_load_controller: "FileLoadController",
        metadata_controller: "MetadataController",
        rename_controller: "RenameController",
    ) -> None:
        """
        Initialize MainWindowController.

        Args:
            app_context: Application context with shared services
            file_load_controller: Controller for file loading operations
            metadata_controller: Controller for metadata operations
            rename_controller: Controller for rename operations
        """
        self._app_context = app_context
        self._file_load_controller = file_load_controller
        self._metadata_controller = metadata_controller
        self._rename_controller = rename_controller

        logger.info("[MainWindowController] Initialized")

    def restore_last_session_workflow(
        self,
        last_folder: str | None = None,
        recursive: bool = False,
        load_metadata: bool = False,
        sort_column: int | None = None,
        sort_order: int | None = None,
    ) -> dict[str, Any]:
        """
        Orchestrate session restoration workflow.

        This workflow handles the restoration of a previous session by:
        1. Validating the last folder exists
        2. Loading files from the folder via FileLoadController
        3. Optionally loading metadata via MetadataController
        4. Returning sorting configuration for UI to apply

        Args:
            last_folder: Path to the last opened folder (if None, no restoration)
            recursive: Whether to load files recursively
            load_metadata: Whether to automatically load metadata after files
            sort_column: Column index for sorting (returned for UI to apply)
            sort_order: Sort order (0=ascending, 1=descending, returned for UI)

        Returns:
            dict: {
                'success': bool,
                'folder_restored': bool,
                'folder_path': Optional[str],
                'files_loaded': int,
                'metadata_loaded': int,
                'sort_column': Optional[int],
                'sort_order': Optional[int],
                'errors': List[str]
            }
        """
        logger.info("[MainWindowController] Starting session restoration workflow")

        errors = []
        result = {
            'success': False,
            'folder_restored': False,
            'folder_path': None,
            'files_loaded': 0,
            'metadata_loaded': 0,
            'sort_column': sort_column,
            'sort_order': sort_order,
            'errors': errors
        }

        # Step 1: Validate folder
        if not last_folder:
            logger.debug(
                "[MainWindowController] No last folder to restore",
                extra={"dev_only": True}
            )
            result['success'] = True  # Not an error, just nothing to restore
            return result

        if not os.path.exists(last_folder):
            error_msg = f"Last folder no longer exists: {last_folder}"
            logger.warning("[MainWindowController] %s", error_msg)
            errors.append(error_msg)
            result['success'] = False
            return result

        logger.info("[MainWindowController] Restoring folder: %s", last_folder)
        result['folder_path'] = last_folder

        # Step 2: Load files via FileLoadController
        try:
            folder_path = Path(last_folder)
            load_result = self._file_load_controller.load_folder(
                folder_path,
                merge=False,
                recursive=recursive
            )

            if not load_result.get('success', False):
                errors.extend(load_result.get('errors', []))
                result['success'] = False
                return result

            files_loaded = load_result.get('loaded_count', 0)
            result['files_loaded'] = files_loaded
            result['folder_restored'] = True

            logger.info(
                "[MainWindowController] Loaded %d files from folder",
                files_loaded
            )

        except Exception as e:
            error_msg = f"Error loading folder: {e}"
            logger.error("[MainWindowController] %s", error_msg)
            errors.append(error_msg)
            result['success'] = False
            return result

        # Step 3: Optionally load metadata via MetadataController
        if load_metadata and files_loaded > 0:
            try:
                logger.debug(
                    "[MainWindowController] Loading metadata for %d files",
                    files_loaded,
                    extra={"dev_only": True}
                )

                # Get loaded files from file store
                file_store = self._app_context.file_store
                loaded_files = file_store.get_loaded_files()

                if loaded_files:
                    metadata_result = self._metadata_controller.load_metadata(
                        items=loaded_files,
                        use_extended=False,
                        source="session_restore"
                    )

                    if metadata_result.get('success', False):
                        result['metadata_loaded'] = metadata_result.get('loaded_count', 0)
                        logger.info(
                            "[MainWindowController] Loaded metadata for %d files",
                            result['metadata_loaded']
                        )
                    else:
                        # Metadata loading failure is not critical, just log it
                        logger.warning(
                            "[MainWindowController] Metadata loading failed: %s",
                            metadata_result.get('errors', [])
                        )
                        errors.extend(metadata_result.get('errors', []))

            except Exception as e:
                # Metadata loading failure is not critical
                error_msg = f"Error loading metadata: {e}"
                logger.warning("[MainWindowController] %s", error_msg)
                errors.append(error_msg)

        # Success if folder was loaded, even if metadata failed
        result['success'] = result['folder_restored']
        logger.info(
            "[MainWindowController] Session restoration complete: %d files, %d metadata",
            result['files_loaded'],
            result['metadata_loaded']
        )

        return result
