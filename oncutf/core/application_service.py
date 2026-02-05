"""Application Service Layer with unified interface to all operations.

This module provides a unified interface to all application operations,
reducing the need for delegate methods in MainWindow and creating better
separation of concerns.

Author: Michael Economou
Date: 2025-06-15
"""

import os
from pathlib import Path
from typing import Any, cast

from oncutf.models.file_item import FileItem
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class ApplicationService:
    """Application Service Layer that provides unified access to all application operations.

    This service acts as a facade for all managers and reduces the coupling between
    MainWindow and individual managers. It groups related operations logically.
    """

    def __init__(self, main_window: Any) -> None:
        """Initialize with reference to main window and its managers."""
        self.main_window = main_window
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the service after all managers are ready."""
        if self._initialized:
            return

        # Verify all required managers exist
        required_managers = [
            "event_handler_manager",
            "file_load_manager",
            "table_manager",
            "metadata_manager",
            "selection_manager",
            "utility_manager",
            "rename_manager",
            "shortcut_manager",
            "drag_cleanup_manager",
            "splitter_manager",
        ]

        missing_managers = [
            manager for manager in required_managers if not hasattr(self.main_window, manager)
        ]

        if missing_managers:
            logger.warning("[ApplicationService] Missing managers: %s", missing_managers)
            return

        self._initialized = True
        logger.info("[ApplicationService] Initialized successfully")

    # =====================================
    # File Operations
    # =====================================

    def load_files_from_folder(self, folder_path: str, _force: bool = False) -> None:
        """Load files from folder via FileLoadController.

        Args:
            folder_path: Path to folder to load
            _force: Reserved for future use (currently unused)

        """
        # Use the remembered recursive state for consistent behavior
        recursive = getattr(self.main_window, "current_folder_is_recursive", False)
        logger.info(
            "[ApplicationService] load_files_from_folder: %s (recursive=%s, remembered from previous load)",
            folder_path,
            recursive,
        )
        # Use controller instead of manager (proper architecture)
        self.main_window.file_load_controller.load_folder(
            folder_path, merge_mode=False, recursive=recursive
        )

    def prepare_folder_load(self, folder_path: str, *, clear: bool = True) -> list[str]:
        """Prepare folder load via FileLoadManager."""
        return cast(
            "list[str]",
            self.main_window.file_load_manager.prepare_folder_load(folder_path, clear=clear),
        )

    def load_single_item_from_drop(
        self,
        path: str,
        modifiers: Any = None,
    ) -> None:
        """Load single item from drop via FileLoadController.

        Args:
            path: File or folder path to load
            modifiers: Keyboard modifiers (KeyboardModifier or None)

        """
        if modifiers is None:
            from oncutf.domain.keyboard import KeyboardModifier

            modifiers = KeyboardModifier.NONE

        import time

        from oncutf.utils.logging.logger_factory import get_cached_logger

        logger_local = get_cached_logger(__name__)
        t0 = time.time()
        logger_local.debug(
            "[DROP-SERVICE] load_single_item_from_drop START: %s",
            path,
            extra={"dev_only": True},
        )

        # Use controller for orchestration (proper architecture)
        # Controller handles modifiers parsing and delegates to manager
        self.main_window.file_load_controller.handle_drop([path], modifiers)
        logger_local.debug(
            "[DROP-SERVICE] Completed at +%.3fms",
            (time.time() - t0) * 1000,
            extra={"dev_only": True},
        )

    # =====================================
    # Metadata Operations (with business logic)
    # =====================================

    def calculate_hash_selected(self) -> Any:
        """Calculate hash for selected files that don't already have hashes."""
        selected_files = self.main_window.get_selected_files_ordered()
        if not selected_files:
            logger.info("[ApplicationService] No files selected for hash calculation")
            return None

        # Check which files need hash calculation
        hash_analysis = self.main_window.event_handler_manager._analyze_hash_state(selected_files)

        if not hash_analysis["enable_selected"]:
            # All files already have hashes
            from oncutf.app.services import show_info_message

            # Combine message with details
            message = (
                f"All {len(selected_files)} selected file(s) already have checksums calculated."
            )
            if hash_analysis.get("selected_tooltip"):
                message += f"\n\n{hash_analysis['selected_tooltip']}"

            show_info_message(
                self.main_window,
                "Hash Calculation",
                message,
            )
            return None

        return self.main_window.event_handler_manager.hash_ops.handle_calculate_hashes(
            selected_files
        )

    def calculate_hash_all(self) -> Any:
        """Calculate hash for all files that don't already have hashes."""
        all_files = (
            self.main_window.file_model.files if hasattr(self.main_window, "file_model") else []
        )
        if not all_files:
            logger.info("[ApplicationService] No files available for hash calculation")
            return None

        # Check which files need hash calculation
        hash_analysis = self.main_window.event_handler_manager._analyze_hash_state(all_files)

        if not hash_analysis["enable_selected"]:
            # All files already have hashes
            from oncutf.app.services import show_info_message

            show_info_message(
                self.main_window,
                "Hash Calculation",
                f"All {len(all_files)} file(s) already have checksums calculated.",
                details=hash_analysis["selected_tooltip"],
            )
            return None

        return self.main_window.event_handler_manager.hash_ops.handle_calculate_hashes(all_files)

    # =====================================
    # Rename Operations (with business logic)
    # =====================================

    def rename_files(self) -> None:
        """Execute batch rename using RenameController."""
        try:
            # Get selected files and rename data
            selected_files = self.main_window.table_manager.get_selected_files()
            rename_data = self.main_window.rename_modules_area.get_all_data()
            post_transform_data = self.main_window.final_transform_container.get_data()

            if not selected_files:
                self.main_window.status_manager.set_selection_status(
                    "No files selected for renaming",
                    selected_count=0,
                    total_count=0,
                    auto_reset=True,
                )
                return

            # Use RenameController for orchestration
            result = self.main_window.rename_controller.execute_rename(
                file_items=selected_files,
                modules_data=rename_data.get("modules", []),
                post_transform=post_transform_data,
                metadata_cache=self.main_window.metadata_cache,
                current_folder=self.main_window.context.get_current_folder(),
            )

            # Handle results
            if not result["success"]:
                # Show error message
                error_msg = result["errors"][0] if result["errors"] else "Unknown error"
                self.main_window.status_manager.set_validation_status(
                    error_msg, validation_type="error", auto_reset=True
                )
                return

            renamed_count = result["renamed_count"]
            failed_count = result["failed_count"]
            skipped_count = result["skipped_count"]

            # Build status message
            status_msg = (
                f"Successfully renamed {renamed_count} file{'s' if renamed_count != 1 else ''}"
            )
            if skipped_count > 0:
                status_msg += f" ({skipped_count} skipped)"
            if failed_count > 0:
                status_msg += f", {failed_count} failed"

            self.main_window.status_manager.set_validation_status(
                status_msg,
                validation_type="success" if failed_count == 0 else "warning",
                auto_reset=True,
            )

            # Reload folder to reflect changes
            if renamed_count > 0:
                self.main_window.file_load_manager.reload_current_folder()

        except Exception as e:
            logger.exception("[ApplicationService] Error in RenameController rename")
            self.main_window.status_manager.set_validation_status(
                f"Rename error: {e!s}", validation_type="error", auto_reset=True
            )

    def _update_file_items_after_rename(
        self, files: list[FileItem], _new_names: list[str], execution_result: Any
    ) -> None:
        """Update FileItem objects with new paths after successful rename.

        This prevents the issue where files are renamed but FileItem objects still
        reference the old paths, causing subsequent rename operations to fail.

        Args:
            files: List of FileItem objects
            _new_names: Expected new names (unused - extracted from execution_result)
            execution_result: Result from rename execution containing actual mappings

        """
        try:
            # Build a map of old_path -> new_path from successful executions
            rename_map = {}
            for item in execution_result.items:
                if item.success:
                    rename_map[item.old_path] = item.new_path

            # Update FileItem objects
            updated_count = 0
            for file_item in files:
                if file_item.full_path in rename_map:
                    new_path = rename_map[file_item.full_path]
                    new_filename = Path(new_path).name

                    logger.debug(
                        "[ApplicationService] Updating FileItem: %s -> %s",
                        file_item.filename,
                        new_filename,
                    )

                    # Update the FileItem
                    file_item.full_path = new_path
                    file_item.filename = new_filename
                    updated_count += 1

            if updated_count > 0:
                logger.info(
                    "[ApplicationService] Updated %d FileItem objects with new paths",
                    updated_count,
                )

        except Exception:
            logger.exception("[ApplicationService] Error updating FileItem objects")

    # =====================================
    # Validation & Dialog Operations (with business logic)
    # =====================================

    def confirm_large_folder(self, file_list: list[str], folder_path: str) -> bool:
        """Confirm large folder via FileValidationManager and DialogManager."""
        from oncutf.core.file import OperationType

        # Use FileValidationManager for smart validation
        validation_result = self.main_window.file_validation_manager.validate_operation_batch(
            file_list, OperationType.FILE_LOADING
        )

        if validation_result["should_warn"]:
            # Show warning with smart information
            return cast(
                "bool",
                self.main_window.dialog_manager.confirm_large_folder(
                    folder_path, validation_result["file_count"]
                ),
            )

        return True  # No warning needed

    def check_large_files(self, files: list[FileItem]) -> list[FileItem]:
        """Check large files via FileValidationManager and DialogManager."""
        from oncutf.core.file import OperationType

        # Convert FileItems to paths for validation
        file_paths = [f.full_path for f in files if hasattr(f, "full_path")]

        validation_result = self.main_window.file_validation_manager.validate_operation_batch(
            file_paths, OperationType.METADATA_EXTENDED
        )

        # Return files that exceed size thresholds
        if validation_result["should_warn"]:
            # Use DialogManager for detailed large file detection
            has_large, large_file_paths = self.main_window.dialog_manager.check_large_files(
                file_paths
            )
            if has_large:
                return [f for f in files if f.full_path in large_file_paths]

        return []

    def _check_files_have_hashes(self, files: list[FileItem] | None = None) -> bool:
        """Check if all provided files already have hashes.

        Args:
            files: A list of FileItem objects to check. If None, checks all files in the model.

        Returns:
            True if all files have hashes, False otherwise.

        """
        files_to_check = files if files is not None else self.main_window.file_model.files

        if not files_to_check:
            return True  # No files to check, so implicitly all have hashes

        from typing import cast

        for file_item in files_to_check:
            fi = cast("FileItem", file_item)
            if not fi.hash_value:
                return False
        return True

    def confirm_large_files(self, files: list[FileItem]) -> bool:
        """Confirm large files via FileValidationManager and DialogManager."""
        from oncutf.core.file import OperationType

        if not files:
            return True

        # Get validation summary from FileValidationManager
        file_paths = [f.full_path for f in files if hasattr(f, "full_path")]
        validation_result = self.main_window.file_validation_manager.validate_operation_batch(
            file_paths, OperationType.METADATA_EXTENDED
        )

        if validation_result["should_warn"]:
            # Show detailed confirmation dialog
            return cast("bool", self.main_window.dialog_manager.confirm_large_files(files))

        return True  # No confirmation needed

    def _get_file_type_field_support(
        self, file_item: FileItem, metadata: dict[str, Any]
    ) -> set[str]:
        """Determine which metadata fields are supported for a given file type.

        This method is intended to be called by the metadata manager.
        """
        return cast(
            "set[str]",
            self.main_window.metadata_manager.get_file_type_field_support(file_item, metadata),
        )

    def prompt_file_conflict(self, target_path: str) -> str:
        """Prompt file conflict via DialogManager."""
        old_name = Path(target_path).name
        new_name = Path(target_path).name
        result = self.main_window.dialog_manager.prompt_file_conflict(old_name, new_name)
        return "overwrite" if result else "cancel"

    def confirm_operation_for_user(self, files: list[str], operation_type: str) -> dict[str, Any]:
        """Validate operation for user via FileValidationManager."""
        from oncutf.core.file import OperationType

        # Map string operation types to enum
        operation_map = {
            "metadata_fast": OperationType.METADATA_FAST,
            "metadata_extended": OperationType.METADATA_EXTENDED,
            "hash_calculation": OperationType.HASH_CALCULATION,
            "rename": OperationType.RENAME_OPERATION,
            "file_loading": OperationType.FILE_LOADING,
        }

        operation = operation_map.get(operation_type, OperationType.FILE_LOADING)
        return cast(
            "dict[str, Any]",
            self.main_window.file_validation_manager.validate_operation_batch(files, operation),
        )

    def identify_moved_files(self, file_paths: list[str]) -> dict[str, Any]:
        """Identify moved files via FileValidationManager."""
        moved_files = {}

        for file_path in file_paths:
            file_record, was_moved = (
                self.main_window.file_validation_manager.identify_file_with_content_fallback(
                    file_path
                )
            )

            if was_moved and file_record:
                moved_files[file_path] = {
                    "original_path": file_record.get("file_path"),
                    "preserved_metadata": file_record.get("metadata_json") is not None,
                    "preserved_hash": file_record.get("hash_value") is not None,
                    "file_record": file_record,
                }

                # Log successful identification
                logger.info(
                    "[ApplicationService] Identified moved file: %s (was: %s)",
                    file_path,
                    file_record.get("file_path"),
                )

        return moved_files

    # =====================================
    # Status & Initialization
    # =====================================

    def is_initialized(self) -> bool:
        """Check if service is initialized."""
        return self._initialized


# =====================================
# Global Instance Management
# =====================================

_application_service_instance: ApplicationService | None = None


def get_application_service(main_window: Any = None) -> ApplicationService | None:
    """Get the global application service instance.

    Args:
        main_window: MainWindow instance (required for first call)

    Returns:
        ApplicationService instance or None if not initialized

    """
    global _application_service_instance

    if _application_service_instance is None and main_window:
        _application_service_instance = ApplicationService(main_window)
        logger.info("[ApplicationService] Created global instance")

    return _application_service_instance


def initialize_application_service(main_window: Any) -> ApplicationService | None:
    """Initialize the global application service.

    Args:
        main_window: MainWindow instance

    Returns:
        Initialized ApplicationService instance

    """
    service = get_application_service(main_window)
    if service:
        service.initialize()
    return service


def cleanup_application_service() -> None:
    """Cleanup the global application service."""
    global _application_service_instance
    if _application_service_instance:
        logger.info("[ApplicationService] Cleaned up global instance")
        _application_service_instance = None
