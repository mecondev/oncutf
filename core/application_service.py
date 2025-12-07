"""Application Service Layer with unified interface to all operations.

This module provides a unified interface to all application operations,
reducing the need for delegate methods in MainWindow and creating better
separation of concerns.

Author: Michael Economou
Date: 2025-06-15
"""

import os

from core.pyqt_imports import QModelIndex, Qt
from models.file_item import FileItem
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class ApplicationService:
    """
    Application Service Layer that provides unified access to all application operations.

    This service acts as a facade for all managers and reduces the coupling between
    MainWindow and individual managers. It groups related operations logically.
    """

    def __init__(self, main_window):
        """Initialize with reference to main window and its managers."""
        self.main_window = main_window
        self._initialized = False

    def initialize(self):
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
            "preview_manager",
            "shortcut_manager",
            "drag_cleanup_manager",
            "splitter_manager",
        ]

        missing_managers = []
        for manager in required_managers:
            if not hasattr(self.main_window, manager):
                missing_managers.append(manager)

        if missing_managers:
            logger.warning(f"[ApplicationService] Missing managers: {missing_managers}")
            return

        self._initialized = True
        logger.info("[ApplicationService] Initialized successfully")

    # =====================================
    # File Operations
    # =====================================

    def load_files_from_folder(self, folder_path: str, force: bool = False):  # noqa: ARG002
        """Load files from folder via FileLoadManager."""
        # Use the remembered recursive state for consistent behavior
        recursive = getattr(self.main_window, "current_folder_is_recursive", False)
        logger.info(
            f"[ApplicationService] load_files_from_folder: {folder_path} (recursive={recursive}, remembered from previous load)"
        )
        self.main_window.file_load_manager.load_folder(
            folder_path, merge_mode=False, recursive=recursive
        )

    def load_files_from_paths(self, file_paths: list[str], *, clear: bool = True) -> None:
        """Load files from paths via FileLoadManager."""
        self.main_window.file_load_manager.load_files_from_paths(file_paths, clear=clear)

    def load_files_from_dropped_items(
        self, paths: list[str], modifiers: Qt.KeyboardModifiers = Qt.NoModifier
    ) -> None:
        """Load files from dropped items via FileLoadManager."""
        self.main_window.file_load_manager.load_files_from_dropped_items(paths, modifiers)

    def prepare_folder_load(self, folder_path: str, *, clear: bool = True) -> list[str]:
        """Prepare folder load via FileLoadManager."""
        return self.main_window.file_load_manager.prepare_folder_load(folder_path, clear=clear)

    def load_single_item_from_drop(
        self, path: str, modifiers: Qt.KeyboardModifiers = Qt.NoModifier
    ) -> None:
        """Load single item from drop via FileLoadManager."""
        self.main_window.file_load_manager.load_single_item_from_drop(path, modifiers)

    def handle_folder_drop(self, folder_path: str, merge_mode: bool, recursive: bool) -> None:
        """Handle folder drop via FileLoadManager."""
        self.main_window.file_load_manager._handle_folder_drop(folder_path, merge_mode, recursive)

    def handle_file_drop(self, file_path: str, merge_mode: bool) -> None:
        """Handle file drop via FileLoadManager."""
        self.main_window.file_load_manager._handle_file_drop(file_path, merge_mode)

    def load_metadata_for_items(
        self, items: list[FileItem], use_extended: bool = False, source: str = "unknown"
    ) -> None:
        """Load metadata for items via UnifiedMetadataManager with proper cache checking."""
        if not items:
            return

        logger.info(f"[{source}] Loading metadata for {len(items)} items")

        # Delegate directly to UnifiedMetadataManager which has the cache checking logic
        manager = self.main_window.metadata_manager
        manager.load_metadata_for_items(items, use_extended=use_extended, source=source)

    # =====================================
    # Selection Operations
    # =====================================

    def select_all_rows(self):
        """Select all rows in the file table."""
        return self.main_window.selection_manager.select_all_rows()

    def clear_all_selection(self):
        """Clear all selection in the file table."""
        return self.main_window.selection_manager.clear_all_selection()

    def invert_selection(self):
        """Invert current selection."""
        return self.main_window.selection_manager.invert_selection()

    def get_selected_files(self) -> list[FileItem]:
        """Get selected files via TableManager."""
        return self.main_window.table_manager.get_selected_files()

    def get_selected_files_ordered(self):
        """Get selected files in table display order."""
        return self.main_window.get_selected_files_ordered()

    def update_preview_from_selection(self, selected_rows: list[int]) -> None:
        """Update preview from selection via SelectionManager."""
        self.main_window.selection_manager.update_preview_from_selection(selected_rows)

    # =====================================
    # Metadata Operations
    # =====================================

    def load_metadata_fast(self):
        """Load fast metadata for selected files."""
        return self.main_window.metadata_manager.shortcut_load_metadata()

    def load_metadata_extended(self):
        """Load extended metadata for selected files."""
        return self.main_window.metadata_manager.shortcut_load_extended_metadata()

    def load_metadata_all_fast(self):
        """Load basic metadata for all files."""
        return self.main_window.metadata_manager.shortcut_load_metadata_all()

    def load_metadata_all_extended(self):
        """Load extended metadata for all files."""
        return self.main_window.metadata_manager.shortcut_load_extended_metadata_all()

    def calculate_hash_selected(self):
        """Calculate hash for selected files that don't already have hashes."""
        selected_files = self.main_window.get_selected_files_ordered()
        if not selected_files:
            logger.info("[ApplicationService] No files selected for hash calculation")
            return

        # Check which files need hash calculation
        hash_analysis = self.main_window.event_handler_manager._analyze_hash_state(selected_files)

        if not hash_analysis["enable_selected"]:
            # All files already have hashes
            from utils.dialog_utils import show_info_message

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
            return

        return self.main_window.event_handler_manager.hash_ops.handle_calculate_hashes(selected_files)

    def calculate_hash_all(self):
        """Calculate hash for all files that don't already have hashes."""
        all_files = (
            self.main_window.file_model.files if hasattr(self.main_window, "file_model") else []
        )
        if not all_files:
            logger.info("[ApplicationService] No files available for hash calculation")
            return

        # Check which files need hash calculation
        hash_analysis = self.main_window.event_handler_manager._analyze_hash_state(all_files)

        if not hash_analysis["enable_selected"]:
            # All files already have hashes
            from utils.dialog_utils import show_info_message

            show_info_message(
                self.main_window,
                "Hash Calculation",
                f"All {len(all_files)} file(s) already have checksums calculated.",
                details=hash_analysis["selected_tooltip"],
            )
            return

        return self.main_window.event_handler_manager.hash_ops.handle_calculate_hashes(all_files)

    def save_selected_metadata(self):
        """Save metadata for selected files."""
        return self.main_window.metadata_manager.save_metadata_for_selected()

    def save_all_metadata(self):
        """Save all modified metadata."""
        return self.main_window.metadata_manager.save_all_modified_metadata()

    def determine_metadata_mode(self) -> tuple[bool, bool]:
        """Determine metadata mode via MetadataManager."""
        return self.main_window.metadata_manager.determine_metadata_mode(
            self.main_window.modifier_state
        )

    def should_use_extended_metadata(self) -> bool:
        """Determine if extended metadata should be used via MetadataManager."""
        return self.main_window.metadata_manager.should_use_extended_metadata(
            self.main_window.modifier_state
        )

    # =====================================
    # Table Operations
    # =====================================

    def sort_by_column(
        self, column: int, order: Qt.SortOrder = None, force_order: Qt.SortOrder = None
    ) -> None:
        """Sort by column via TableManager."""
        self.main_window.table_manager.sort_by_column(column, order, force_order)

    def prepare_file_table(self, file_items: list[FileItem]) -> None:
        """Prepare file table via TableManager."""
        self.main_window.table_manager.prepare_file_table(file_items)

    def restore_fileitem_metadata_from_cache(self) -> None:
        """Restore metadata from cache via TableManager."""
        self.main_window.table_manager.restore_fileitem_metadata_from_cache()

    def clear_file_table(self, message: str = "No folder selected") -> None:
        """Clear file table via TableManager."""
        self.main_window.table_manager.clear_file_table(message)

    def get_common_metadata_fields(self) -> list[str]:
        """Get common metadata fields via TableManager."""
        return self.main_window.table_manager.get_common_metadata_fields()

    def set_fields_from_list(self, field_names: list[str]) -> None:
        """Set fields from list via TableManager."""
        self.main_window.table_manager.set_fields_from_list(field_names)

    def after_check_change(self) -> None:
        """Handle check change via TableManager."""
        self.main_window.table_manager.after_check_change()

    # =====================================
    # Rename Operations
    # =====================================

    def rename_files(self):
        """Execute batch rename using UnifiedRenameEngine with Phase 4 optimizations."""
        try:
            # Get selected files and rename data
            selected_files = self.get_selected_files()
            rename_data = self.main_window.rename_modules_area.get_all_data()
            post_transform_data = self.main_window.final_transform_container.get_data()
            rename_data["post_transform"] = post_transform_data

            if not selected_files:
                self.main_window.status_manager.set_selection_status(
                    "No files selected for renaming",
                    selected_count=0,
                    total_count=0,
                    auto_reset=True,
                )
                return

            # Use Phase 4 batch processing for large file sets
            if len(selected_files) > 100:
                logger.info(
                    f"[ApplicationService] Using Phase 4 batch processing for {len(selected_files)} files"
                )

                # Process files in batches using Phase 4 batch processor
                def process_batch(batch_files):
                    return self.main_window.unified_rename_engine.generate_preview(
                        files=batch_files,
                        modules_data=rename_data.get("modules", []),
                        post_transform=post_transform_data,
                        metadata_cache=self.main_window.metadata_cache,
                    )

                # Use batch processor for preview generation
                batch_results = self.main_window.unified_rename_engine.batch_process_files(
                    selected_files, process_batch
                )

                # Combine batch results
                all_name_pairs = []
                for result in batch_results:
                    if result and hasattr(result, "name_pairs"):
                        all_name_pairs.extend(result.name_pairs)

                preview_result = type(
                    "PreviewResult",
                    (),
                    {"name_pairs": all_name_pairs, "has_changes": len(all_name_pairs) > 0},
                )()
            else:
                # Use standard preview generation for smaller file sets
                preview_result = self.main_window.unified_rename_engine.generate_preview(
                    files=selected_files,
                    modules_data=rename_data.get("modules", []),
                    post_transform=post_transform_data,
                    metadata_cache=self.main_window.metadata_cache,
                )

            if not preview_result.has_changes:
                self.main_window.status_manager.set_validation_status(
                    "No changes detected", validation_type="warning", auto_reset=True
                )
                return

            # Validate preview
            name_pairs = preview_result.name_pairs
            validation_result = self.main_window.unified_rename_engine.validate_preview(name_pairs)

            if validation_result.has_errors:
                self.main_window.status_manager.set_validation_status(
                    f"Validation errors found: {validation_result.has_errors}",
                    validation_type="error",
                    auto_reset=True,
                )
                return

            # Execute rename using UnifiedRenameEngine (includes companion file handling)
            new_names = [new_name for _, new_name in name_pairs]

            # Use unified rename engine which handles companion files automatically
            execution_result = self.main_window.unified_rename_engine.execute_rename(
                files=selected_files,
                new_names=new_names,
                conflict_callback=None,  # Use default conflict handling
                validator=None,  # Already validated above
            )

            # Count successful operations (includes main files + companion files)
            successful_count = execution_result.success_count
            error_count = execution_result.error_count

            # Calculate main files vs companion files
            main_files_count = len(selected_files)
            total_successful = successful_count
            companion_files_count = total_successful - main_files_count if total_successful > main_files_count else 0

            # Handle results
            if successful_count > 0:
                # Build status message with companion info
                if companion_files_count > 0:
                    status_msg = f"Successfully renamed {main_files_count} file{'s' if main_files_count != 1 else ''} + {companion_files_count} companion file{'s' if companion_files_count != 1 else ''}"
                else:
                    status_msg = f"Successfully renamed {successful_count} file{'s' if successful_count != 1 else ''}"

                self.main_window.status_manager.set_validation_status(
                    status_msg,
                    validation_type="success",
                    auto_reset=True,
                )

                # Log Phase 4 statistics
                self._log_phase4_stats()

                # Reload folder to reflect changes
                self.reload_current_folder()
            else:
                self.main_window.status_manager.set_validation_status(
                    f"Rename failed: {error_count} errors", validation_type="error", auto_reset=True
                )

        except Exception as e:
            logger.error(f"[ApplicationService] Error in Phase 4 unified rename: {e}")
            self.main_window.status_manager.set_validation_status(
                f"Rename error: {str(e)}", validation_type="error", auto_reset=True
            )

    def _log_phase4_stats(self):
        """Log Phase 4 performance statistics."""
        try:
            engine = self.main_window.unified_rename_engine

            # Get all Phase 4 statistics
            cache_stats = engine.get_advanced_cache_stats()
            batch_stats = engine.get_batch_processor_stats()
            conflict_stats = engine.get_conflict_resolver_stats()
            perf_stats = engine.get_performance_stats()

            logger.info("[ApplicationService] Phase 4 Statistics:")
            logger.info(f"  Cache: {cache_stats['overall_hit_rate']:.1f}% hit rate")
            logger.info(f"  Batch: {batch_stats.get('items_per_second', 0):.0f} items/sec")
            logger.info(f"  Conflicts: {conflict_stats['success_rate']:.1f}% success rate")
            logger.info(f"  Performance: {perf_stats['total_operations']} operations")

        except Exception as e:
            logger.warning(f"[ApplicationService] Error logging Phase 4 stats: {e}")

    def update_module_dividers(self):
        """Update module dividers."""
        return self.main_window.rename_manager.update_module_dividers()

    # =====================================
    # Preview Operations
    # =====================================

    def generate_preview_names(self):
        """Generate preview names."""
        return self.main_window.utility_manager.generate_preview_names()

    def request_preview_update(self):
        """Request preview update."""
        return self.main_window.utility_manager.request_preview_update()

    def get_identity_name_pairs(self) -> list[tuple[str, str]]:
        """Get identity name pairs via PreviewManager."""
        return self.main_window.preview_manager.get_identity_name_pairs(
            self.main_window.file_model.files
        )

    def update_preview_tables_from_pairs(self, name_pairs: list[tuple[str, str]]) -> None:
        """Update preview tables from pairs via PreviewManager."""
        self.main_window.preview_manager.update_preview_tables_from_pairs(name_pairs)

    def compute_max_filename_width(self, file_list: list[FileItem]) -> int:
        """Compute max filename width via PreviewManager."""
        return self.main_window.preview_manager.compute_max_filename_width(file_list)

    # =====================================
    # Event Handling
    # =====================================

    def handle_browse(self):
        """Handle browse action."""
        return self.main_window.event_handler_manager.handle_browse()

    def handle_folder_import(self):
        """Handle folder import."""
        return self.main_window.event_handler_manager.handle_folder_import()

    def handle_table_context_menu(self, position) -> None:
        """Handle table context menu via EventHandlerManager."""
        self.main_window.event_handler_manager.handle_table_context_menu(position)

    def handle_file_double_click(
        self, index: QModelIndex, modifiers: Qt.KeyboardModifiers = Qt.NoModifier
    ) -> None:
        """Handle file double click via EventHandlerManager."""
        self.main_window.event_handler_manager.handle_file_double_click(index, modifiers)

    def handle_header_toggle(self, _) -> None:
        """Handle header toggle via EventHandlerManager."""
        self.main_window.event_handler_manager.handle_header_toggle(_)

    def on_table_row_clicked(self, index: QModelIndex) -> None:
        """Handle table row click via EventHandlerManager."""
        self.main_window.event_handler_manager.on_table_row_clicked(index)

    # =====================================
    # Drag & Drop Operations
    # =====================================

    def force_drag_cleanup(self):
        """Force drag cleanup."""
        return self.main_window.drag_cleanup_manager.force_drag_cleanup()

    def cleanup_widget_drag_states(self):
        """Cleanup widget drag states."""
        return self.main_window.drag_cleanup_manager._cleanup_widget_drag_states()

    def emergency_drag_cleanup(self):
        """Emergency drag cleanup."""
        return self.main_window.drag_cleanup_manager.emergency_drag_cleanup()

    # =====================================
    # UI Operations
    # =====================================

    def center_window(self):
        """Center the window."""
        return self.main_window.utility_manager.center_window()

    def force_reload(self):
        """Force reload."""
        return self.main_window.utility_manager.force_reload()

    def update_files_label(self) -> None:
        """Update files label via UtilityManager."""
        self.main_window.utility_manager.update_files_label()

    def get_modifier_flags(self) -> tuple[bool, bool]:
        """Get modifier flags via UtilityManager."""
        return self.main_window.utility_manager.get_modifier_flags()

    def get_selected_rows_files(self) -> list:
        """Get selected rows as files via UtilityManager."""
        return self.main_window.utility_manager.get_selected_rows_files()

    # =====================================
    # Splitter Operations
    # =====================================

    def on_horizontal_splitter_moved(self, pos: int, index: int) -> None:
        """Handle horizontal splitter movement via SplitterManager."""
        self.main_window.splitter_manager.on_horizontal_splitter_moved(pos, index)

    def on_vertical_splitter_moved(self, pos: int, index: int) -> None:
        """Handle vertical splitter movement via SplitterManager."""
        self.main_window.splitter_manager.on_vertical_splitter_moved(pos, index)

    # =====================================
    # Shortcuts
    # =====================================

    def clear_file_table_shortcut(self):
        """Clear file table via shortcut."""
        return self.main_window.shortcut_manager.clear_file_table_shortcut()

    # =====================================
    # Validation & Dialog Operations
    # =====================================

    def confirm_large_folder(self, file_list: list[str], folder_path: str) -> bool:
        """Confirm large folder via FileValidationManager and DialogManager."""
        from core.file_validation_manager import OperationType

        # Use FileValidationManager for smart validation
        validation_result = self.main_window.file_validation_manager.validate_operation_batch(
            file_list, OperationType.FILE_LOADING
        )

        if validation_result["should_warn"]:
            # Show warning with smart information
            return self.main_window.dialog_manager.confirm_large_folder(
                folder_path, validation_result["file_count"]
            )

        return True  # No warning needed

    def check_large_files(self, files: list[FileItem]) -> list[FileItem]:
        """Check large files via FileValidationManager and DialogManager."""
        from core.file_validation_manager import OperationType

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

    def confirm_large_files(self, files: list[FileItem]) -> bool:
        """Confirm large files via FileValidationManager and DialogManager."""
        from core.file_validation_manager import OperationType

        if not files:
            return True

        # Get validation summary from FileValidationManager
        file_paths = [f.full_path for f in files if hasattr(f, "full_path")]
        validation_result = self.main_window.file_validation_manager.validate_operation_batch(
            file_paths, OperationType.METADATA_EXTENDED
        )

        if validation_result["should_warn"]:
            # Show detailed confirmation dialog
            return self.main_window.dialog_manager.confirm_large_files(files)

        return True  # No confirmation needed

    def prompt_file_conflict(self, target_path: str) -> str:
        """Prompt file conflict via DialogManager."""

        old_name = os.path.basename(target_path)
        new_name = os.path.basename(target_path)
        result = self.main_window.dialog_manager.prompt_file_conflict(old_name, new_name)
        return "overwrite" if result else "cancel"

    def validate_operation_for_user(self, files: list[str], operation_type: str) -> dict:
        """Validate operation for user via FileValidationManager."""
        from core.file_validation_manager import OperationType

        # Map string operation types to enum
        operation_map = {
            "metadata_fast": OperationType.METADATA_FAST,
            "metadata_extended": OperationType.METADATA_EXTENDED,
            "hash_calculation": OperationType.HASH_CALCULATION,
            "rename": OperationType.RENAME_OPERATION,
            "file_loading": OperationType.FILE_LOADING,
        }

        operation = operation_map.get(operation_type, OperationType.FILE_LOADING)
        return self.main_window.file_validation_manager.validate_operation_batch(files, operation)

    def identify_moved_files(self, file_paths: list[str]) -> dict:
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
                    f"[ApplicationService] Identified moved file: {file_path} (was: {file_record.get('file_path')})"
                )

        return moved_files

    # =====================================
    # Utility Operations
    # =====================================

    def find_consecutive_ranges(self, indices: list[int]):
        """Find consecutive ranges."""
        return self.main_window.utility_manager.find_consecutive_ranges(indices)

    def find_fileitem_by_path(self, path: str) -> FileItem | None:
        """Find FileItem by path via FileOperationsManager."""
        return self.main_window.file_operations_manager.find_fileitem_by_path(
            self.main_window.file_model.files, path
        )

    def should_skip_folder_reload(self, folder_path: str, force: bool = False) -> bool:
        """Check if folder reload should be skipped."""
        return self.main_window.file_operations_manager.should_skip_folder_reload(
            folder_path, self.main_window.current_folder_path, force
        )

    def has_deep_content(self, folder_path: str) -> bool:
        """Check if folder has deep content."""
        return self.main_window.file_load_manager._has_deep_content(folder_path)

    def get_file_items_from_folder(self, folder_path: str):
        """Get file items from folder."""
        return self.main_window.file_load_manager.get_file_items_from_folder(folder_path)

    # =====================================
    # Status & Initialization
    # =====================================

    def update_status_from_preview(self, status_html: str):
        """Update status from preview."""
        return self.main_window.initialization_manager.update_status_from_preview(status_html)

    def show_metadata_status(self):
        """Show metadata status."""
        return self.main_window.initialization_manager.show_metadata_status()

    def is_initialized(self) -> bool:
        """Check if service is initialized."""
        return self._initialized

    def set_status(
        self, text: str, color: str = "", auto_reset: bool = False, reset_delay: int = 3000
    ) -> None:
        """Set status text and color via StatusManager."""
        self.main_window.status_manager.set_status(text, color, auto_reset, reset_delay)

    def reload_current_folder(self) -> None:
        """Reload current folder via FileLoadManager."""
        self.main_window.file_load_manager.reload_current_folder()


# =====================================
# Global Instance Management
# =====================================

_application_service_instance: ApplicationService | None = None


def get_application_service(main_window=None) -> ApplicationService | None:
    """
    Get the global application service instance.

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


def initialize_application_service(main_window) -> ApplicationService:
    """
    Initialize the global application service.

    Args:
        main_window: MainWindow instance

    Returns:
        Initialized ApplicationService instance
    """
    service = get_application_service(main_window)
    if service:
        service.initialize()
    return service


def cleanup_application_service():
    """Cleanup the global application service."""
    global _application_service_instance
    if _application_service_instance:
        logger.info("[ApplicationService] Cleaned up global instance")
        _application_service_instance = None
