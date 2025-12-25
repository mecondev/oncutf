"""Module: main_window_controller.py

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
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from oncutf.controllers.file_load_controller import FileLoadController
    from oncutf.controllers.metadata_controller import MetadataController
    from oncutf.controllers.rename_controller import RenameController
    from oncutf.core.application_context import ApplicationContext

logger = logging.getLogger(__name__)


class MainWindowController:
    """High-level orchestration controller.

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
        """Initialize MainWindowController.

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
        """Orchestrate session restoration workflow.

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

        errors: list[str] = []
        result = {
            "success": False,
            "folder_restored": False,
            "folder_path": "",
            "files_loaded": 0,
            "metadata_loaded": 0,
            "sort_column": sort_column,
            "sort_order": sort_order,
            "errors": errors,
        }

        # Step 1: Validate folder
        if not last_folder:
            logger.debug(
                "[MainWindowController] No last folder to restore", extra={"dev_only": True}
            )
            result["success"] = True  # Not an error, just nothing to restore
            return result

        if not os.path.exists(last_folder):
            error_msg = f"Last folder no longer exists: {last_folder}"
            logger.warning("[MainWindowController] %s", error_msg)
            errors.append(error_msg)
            result["success"] = False
            return result

        logger.info("[MainWindowController] Restoring folder: %s", last_folder)
        result["folder_path"] = last_folder

        # Step 2: Load files via FileLoadController
        try:
            folder_path_str = str(last_folder)
            load_result = self._file_load_controller.load_folder(
                folder_path_str, merge_mode=False, recursive=recursive
            )

            if not load_result.get("success", False):
                errors.extend(load_result.get("errors", []))
                result["success"] = False
                return result

            files_loaded = load_result.get("loaded_count", 0)
            result["files_loaded"] = files_loaded
            result["folder_restored"] = True

            logger.info("[MainWindowController] Loaded %d files from folder", files_loaded)

        except Exception as e:
            error_msg = f"Error loading folder: {e}"
            logger.error("[MainWindowController] %s", error_msg)
            errors.append(error_msg)
            result["success"] = False
            return result

        # Step 3: Optionally load metadata via MetadataController
        if load_metadata and files_loaded > 0:
            try:
                logger.debug(
                    "[MainWindowController] Loading metadata for %d files",
                    files_loaded,
                    extra={"dev_only": True},
                )

                # Get loaded files from file store
                file_store = self._app_context.file_store
                loaded_files = file_store.get_loaded_files()

                if loaded_files:
                    metadata_result = self._metadata_controller.load_metadata(
                        file_items=loaded_files, use_extended=False, source="session_restore"
                    )

                    if metadata_result.get("success", False):
                        result["metadata_loaded"] = metadata_result.get("loaded_count", 0)
                        logger.info(
                            "[MainWindowController] Loaded metadata for %d files",
                            result["metadata_loaded"],
                        )
                    else:
                        # Metadata loading failure is not critical, just log it
                        logger.warning(
                            "[MainWindowController] Metadata loading failed: %s",
                            metadata_result.get("errors", []),
                        )
                        errors.extend(metadata_result.get("errors", []))

            except Exception as e:
                # Metadata loading failure is not critical
                error_msg = f"Error loading metadata: {e}"
                logger.warning("[MainWindowController] %s", error_msg)
                errors.append(error_msg)

        # Success if folder was loaded, even if metadata failed
        result["success"] = result["folder_restored"]
        logger.info(
            "[MainWindowController] Session restoration complete: %d files, %d metadata",
            result["files_loaded"],
            result["metadata_loaded"],
        )

        return result

    def coordinate_shutdown_workflow(
        self,
        main_window: Any,
        progress_callback: Any = None,
    ) -> dict[str, Any]:
        """Coordinate application shutdown workflow across all services.

        This method orchestrates the graceful shutdown of the application by:
        1. Saving configuration and window state
        2. Creating database backup
        3. Flushing pending operations
        4. Cleaning up resources (drag manager, dialogs)
        5. Coordinating with ShutdownCoordinator for final cleanup

        Note: UI-specific parts (close event handling, dialog creation, cursor changes)
        remain in MainWindow. This method handles only service orchestration.

        Args:
            main_window: Reference to MainWindow for accessing managers
            progress_callback: Optional callback for progress updates (message, 0.0-1.0)

        Returns:
            dict: {
                'success': bool,           # Overall success status
                'config_saved': bool,      # Configuration saved successfully
                'backup_created': bool,    # Database backup created
                'operations_flushed': bool, # Batch operations flushed
                'coordinator_success': bool, # ShutdownCoordinator executed
                'errors': list[str],       # Any errors encountered
                'summary': dict            # ShutdownCoordinator summary
            }

        """
        logger.info("[MainWindowController] Starting coordinated shutdown workflow")
        result: dict[str, Any] = {
            "success": False,
            "config_saved": False,
            "backup_created": False,
            "operations_flushed": False,
            "coordinator_success": False,
            "errors": [],
            "summary": {},
        }

        def update_progress(message: str, progress: float) -> None:
            """Internal progress updater."""
            if progress_callback:
                progress_callback(message, progress)

        try:
            # Step 1: Save configuration (10%)
            update_progress("Saving configuration...", 0.1)
            try:
                from oncutf.utils.json_config_manager import get_app_config_manager

                get_app_config_manager().save_immediate()
                result["config_saved"] = True
                logger.info("[Shutdown] Configuration saved")
            except Exception as e:
                error_msg = f"Failed to save configuration: {e}"
                logger.error("[Shutdown] %s", error_msg)
                result["errors"].append(error_msg)

            # Step 2: Create database backup (20%)
            update_progress("Creating database backup...", 0.2)
            if hasattr(main_window, "backup_manager") and main_window.backup_manager:
                try:
                    main_window.backup_manager.create_backup(reason="auto")
                    result["backup_created"] = True
                    logger.info("[Shutdown] Database backup created")
                except Exception as e:
                    error_msg = f"Database backup failed: {e}"
                    logger.warning("[Shutdown] %s", error_msg)
                    result["errors"].append(error_msg)

            # Step 3: Save window configuration (30%)
            update_progress("Saving window state...", 0.3)
            if hasattr(main_window, "window_config_manager") and main_window.window_config_manager:
                try:
                    main_window.window_config_manager.save_window_config()
                    logger.info("[Shutdown] Window configuration saved")
                except Exception as e:
                    error_msg = f"Failed to save window config: {e}"
                    logger.warning("[Shutdown] %s", error_msg)
                    result["errors"].append(error_msg)

            # Step 4: Flush batch operations (40%)
            update_progress("Flushing pending operations...", 0.4)
            if hasattr(main_window, "batch_manager") and main_window.batch_manager:
                try:
                    if hasattr(main_window.batch_manager, "flush_operations"):
                        main_window.batch_manager.flush_operations()
                        result["operations_flushed"] = True
                        logger.info("[Shutdown] Batch operations flushed")
                except Exception as e:
                    error_msg = f"Batch flush failed: {e}"
                    logger.warning("[Shutdown] %s", error_msg)
                    result["errors"].append(error_msg)

            # Step 5: Cleanup drag operations (50%)
            update_progress("Cleaning up drag operations...", 0.5)
            if hasattr(main_window, "drag_manager") and main_window.drag_manager:
                try:
                    main_window.drag_manager.force_cleanup()
                    logger.info("[Shutdown] Drag manager cleaned up")
                except Exception as e:
                    error_msg = f"Drag cleanup failed: {e}"
                    logger.warning("[Shutdown] %s", error_msg)
                    result["errors"].append(error_msg)

            # Step 6: Close dialogs (60%)
            update_progress("Closing dialogs...", 0.6)
            if hasattr(main_window, "dialog_manager") and main_window.dialog_manager:
                try:
                    main_window.dialog_manager.cleanup()
                    logger.info("[Shutdown] All dialogs closed")
                except Exception as e:
                    error_msg = f"Dialog cleanup failed: {e}"
                    logger.warning("[Shutdown] %s", error_msg)
                    result["errors"].append(error_msg)

            # Step 7: Coordinate final shutdown via ShutdownCoordinator (70-100%)
            update_progress("Coordinating final shutdown...", 0.7)
            if hasattr(main_window, "shutdown_coordinator") and main_window.shutdown_coordinator:
                try:

                    def coordinator_progress(msg: str, prog: float) -> None:
                        """Map coordinator progress (0-1) to our range (0.7-1.0)."""
                        scaled_progress = 0.7 + (prog * 0.3)
                        update_progress(msg, scaled_progress)

                    coordinator_success = main_window.shutdown_coordinator.execute_shutdown(
                        progress_callback=coordinator_progress, emergency=False
                    )
                    result["coordinator_success"] = coordinator_success
                    result["summary"] = main_window.shutdown_coordinator.get_summary()
                    logger.info("[Shutdown] ShutdownCoordinator executed: %s", coordinator_success)
                except Exception as e:
                    error_msg = f"ShutdownCoordinator failed: {e}"
                    logger.error("[Shutdown] %s", error_msg)
                    result["errors"].append(error_msg)

            # Determine overall success
            result["success"] = (
                result["config_saved"]
                and (result["backup_created"] or len(result["errors"]) == 0)
                and result["coordinator_success"]
            )

            update_progress("Shutdown complete", 1.0)
            logger.info(
                "[MainWindowController] Shutdown workflow completed: success=%s, errors=%d",
                result["success"],
                len(result["errors"]),
            )

        except Exception as e:
            error_msg = f"Unexpected error in shutdown workflow: {e}"
            logger.exception("[MainWindowController] %s", error_msg)
            result["errors"].append(error_msg)
            result["success"] = False

        return result
