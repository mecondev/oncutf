"""Module: initialization_manager.py

Author: Michael Economou
Date: 2025-05-31

InitializationManager - Handles initialization and setup operations
This manager centralizes initialization and setup operations including:
- Metadata status display
- SelectionStore mode initialization
- Application component setup
- Status and display management
"""

from typing import TYPE_CHECKING, Any

from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.ui.main_window import MainWindow

logger = get_cached_logger(__name__)


class InitializationManager:
    """Manages initialization and setup operations for the main window.

    This manager handles:
    - Metadata status display logic
    - SelectionStore mode initialization
    - Application component setup
    - Status and display management
    """

    def __init__(self, main_window: "MainWindow"):
        """Initialize the InitializationManager.

        Args:
            main_window: Reference to the main window instance

        """
        self.main_window = main_window
        logger.debug("[InitializationManager] Initialized", extra={"dev_only": True})

    def show_metadata_status(self) -> None:
        """Shows a status bar message indicating the number of loaded files
        and the type of metadata scan performed (basic, extended).
        """
        num_files = len(self.main_window.file_model.files)
        self.main_window.status_manager.show_metadata_status(
            num_files, self.main_window.force_extended_metadata
        )

    def enable_selection_store_mode(self):
        """Enable SelectionStore mode in FileTableView once ApplicationContext is ready."""
        try:
            self.main_window.file_table_view.enable_selection_store_mode()

            # Connect SelectionStore signals to MainWindow handlers
            from oncutf.core.application_context import get_app_context

            context = get_app_context()
            if context and context.selection_store:
                # Connect selection changed signal to existing preview update
                context.selection_store.selection_changed.connect(
                    self.main_window.update_preview_from_selection
                )
                logger.debug(
                    "[MainWindow] Connected SelectionStore signals", extra={"dev_only": True}
                )
            else:
                pass

            # Connect ApplicationContext files_changed signal to update UI
            if context:
                context.files_changed.connect(self._on_files_changed)
                logger.debug(
                    "[MainWindow] Connected ApplicationContext files_changed signal",
                    extra={"dev_only": True},
                )

            logger.debug(
                "[MainWindow] Enabling SelectionStore mode in FileTableView",
                extra={"dev_only": True},
            )
        except Exception as e:
            logger.warning("[MainWindow] Failed to enable SelectionStore mode: %s", e)

    def _on_files_changed(self, files: list[str]) -> None:
        """Handle files changed from ApplicationContext.

        This is called when FileStore updates its internal state (e.g., after USB unmount).
        We update the UI here - FileStore has already been updated.
        Also clears stale selections and preview data.
        """
        from oncutf.utils.ui.cursor_helper import wait_cursor

        logger.info(
            "[MainWindow] Files changed from context - updating UI with %d files", len(files)
        )

        # Show wait cursor during UI update (runs in main thread - visible to user)
        with wait_cursor():
            # Save current selection (as file paths) before clearing
            saved_selection_paths = []
            try:
                # Get selected FileItems from model
                file_table_model = self.main_window.file_table_view.model()
                if file_table_model and hasattr(file_table_model, "file_items"):
                    from oncutf.core.application_context import get_app_context

                    context = get_app_context()
                    if context and context.selection_store:
                        selected_rows = context.selection_store.get_selected_rows()
                        for row in selected_rows:
                            if 0 <= row < len(file_table_model.file_items):
                                file_item = file_table_model.file_items[row]
                                path = file_item.full_path if hasattr(file_item, "full_path") else str(file_item)
                                saved_selection_paths.append(path)

                        logger.info(
                            "[MainWindow] Saved %d selected file paths before refresh",
                            len(saved_selection_paths),
                        )
            except Exception as e:
                logger.warning("[MainWindow] Error saving selection: %s", e)

            # 1. Clear stale selections (files may no longer exist)
            try:
                from oncutf.core.application_context import get_app_context

                context = get_app_context()
                if context and context.selection_store:
                    context.selection_store.clear_selection(emit_signal=False)
            except Exception:
                pass

            # 2. Clear preview cache and tables (stale data)
            if hasattr(self.main_window, "preview_manager") and self.main_window.preview_manager:
                self.main_window.preview_manager.clear_all_caches()
            if hasattr(self.main_window, "update_preview_tables_from_pairs"):
                self.main_window.update_preview_tables_from_pairs([])

            # 3. Apply companion file filtering (maintain state after refresh)
            from oncutf.config import COMPANION_FILES_ENABLED, SHOW_COMPANION_FILES_IN_TABLE

            filtered_files = files
            if COMPANION_FILES_ENABLED and not SHOW_COMPANION_FILES_IN_TABLE:
                try:
                    from oncutf.utils.filesystem.companion_files_helper import CompanionFilesHelper

                    file_groups = CompanionFilesHelper.group_files_with_companions(
                        [f.full_path if hasattr(f, 'full_path') else str(f) for f in files]
                    )
                    # Extract main files only
                    companion_count = 0
                    main_files = []
                    for main_file, group_info in file_groups.items():
                        # Find FileItem matching main_file
                        for f in files:
                            file_path = f.full_path if hasattr(f, 'full_path') else str(f)
                            if file_path == main_file:
                                main_files.append(f)
                                break
                        companion_count += len(group_info.get("companions", []))

                    filtered_files = main_files
                    if companion_count > 0:
                        logger.info(
                            "[MainWindow] Filtered out %d companion files after refresh. Showing %d main files.",
                            companion_count,
                            len(filtered_files),
                        )
                except Exception as e:
                    logger.warning("[MainWindow] Error filtering companion files: %s", e)

            # 4. Update table view (FileStore already updated)
            self.main_window.file_table_view.prepare_table(filtered_files)

            # 5. Restore selection for files that still exist
            if saved_selection_paths:
                from oncutf.utils.shared.timer_manager import schedule_ui_update

                def restore_selection():
                    try:
                        file_table_model = self.main_window.file_table_view.model()
                        if not file_table_model or not hasattr(file_table_model, "file_items"):
                            return

                        from oncutf.core.application_context import get_app_context

                        context = get_app_context()
                        if not context or not context.selection_store:
                            return

                        # Find row indices for saved file paths
                        rows_to_select = set()
                        for row, file_item in enumerate(file_table_model.file_items):
                            path = file_item.full_path if hasattr(file_item, "full_path") else str(file_item)
                            if path in saved_selection_paths:
                                rows_to_select.add(row)

                        if rows_to_select:
                            context.selection_store.set_selected_rows(
                                rows_to_select, emit_signal=True, force_emit=True
                            )
                            logger.info(
                                "[MainWindow] Restored %d/%d selected rows after refresh",
                                len(rows_to_select),
                                len(saved_selection_paths),
                            )
                        else:
                            logger.warning(
                                "[MainWindow] No selected files found after refresh (saved %d paths)",
                                len(saved_selection_paths),
                            )

                    except Exception as e:
                        logger.error("[MainWindow] Error restoring selection: %s", e)

                # Restore selection after table has finished updating
                schedule_ui_update(restore_selection, delay=100)

            # 6. Update placeholder visibility
            if files:
                self.main_window.file_table_view.set_placeholder_visible(False)
            else:
                self.main_window.file_table_view.set_placeholder_visible(True)

            # 7. Update UI labels
            self.main_window.update_files_label()

    def update_status_from_preview(self, status_html: str) -> None:
        """Updates status from preview widgets.
        Delegates to PreviewManager for status updates from preview.
        """
        self.main_window.preview_manager.update_status_from_preview(status_html)

    def setup_application_components(self) -> None:
        """Setup and initialize application components.
        This can be extended with other initialization logic.
        """
        logger.debug(
            "[InitializationManager] Setting up application components", extra={"dev_only": True}
        )

        # Enable SelectionStore mode
        self.enable_selection_store_mode()

        # Additional setup can be added here
        logger.debug(
            "[InitializationManager] Application components setup completed",
            extra={"dev_only": True},
        )

    def get_initialization_status(self) -> dict[str, Any]:
        """Get current initialization status.

        Returns:
            Dictionary with initialization status information

        """
        return {
            "has_files": len(self.main_window.file_model.files) > 0,
            "current_folder": self.main_window.current_folder_path,
            "force_extended_metadata": self.main_window.force_extended_metadata,
            "has_status_manager": self.main_window.status_manager is not None,
            "has_file_table_view": hasattr(self.main_window, "file_table_view"),
        }

    def validate_initialization(self) -> bool:
        """Validate that all required components are properly initialized.

        Returns:
            True if initialization is valid, False otherwise

        """
        required_components = ["status_manager", "file_model", "file_table_view", "preview_manager"]

        for component in required_components:
            if (
                not hasattr(self.main_window, component)
                or getattr(self.main_window, component) is None
            ):
                logger.warning("[InitializationManager] Missing required component: %s", component)
                return False

        logger.debug(
            "[InitializationManager] All required components are initialized",
            extra={"dev_only": True},
        )
        return True
