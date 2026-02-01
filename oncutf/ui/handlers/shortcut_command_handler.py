"""Module: shortcut_command_handler.py.

Author: Michael Economou
Date: 2026-01-01

Handler for keyboard shortcuts and command execution in MainWindow.
Extracts shortcut-related methods to reduce main_window.py complexity.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from oncutf.ui.main_window import MainWindow

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class ShortcutCommandHandler:
    """Handles keyboard shortcuts and command execution."""

    def __init__(self, main_window: MainWindow) -> None:
        """Initialize handler with MainWindow reference.

        Args:
            main_window: Reference to the main application window.

        """
        self.main_window = main_window
        logger.debug("[ShortcutCommandHandler] Initialized")

    # -------------------------------------------------------------------------
    # Simple Shortcut Delegates (direct manager calls)
    # -------------------------------------------------------------------------

    def select_all_rows(self) -> None:
        """Select all rows via SelectionManager."""
        self.main_window.selection_manager.select_all_rows()

    def clear_all_selection(self) -> None:
        """Clear all selection via SelectionManager."""
        self.main_window.selection_manager.clear_all_selection()

    def invert_selection(self) -> None:
        """Invert selection via SelectionManager."""
        self.main_window.selection_manager.invert_selection()

    def shortcut_load_metadata(self) -> None:
        """Load fast metadata via MetadataController."""
        logger.info("[ShortcutCommandHandler] shortcut_load_metadata CALLED -> extended=False")
        self.main_window.metadata_controller.load_metadata_for_selected(extended=False)

    def shortcut_load_extended_metadata(self) -> None:
        """Load extended metadata via MetadataController."""
        logger.info(
            "[ShortcutCommandHandler] shortcut_load_extended_metadata CALLED -> extended=True"
        )
        self.main_window.metadata_controller.load_metadata_for_selected(extended=True)

    def shortcut_save_selected_metadata(self) -> None:
        """Save selected metadata via MetadataManager."""
        self.main_window.metadata_manager.save_metadata_for_selected()

    def shortcut_save_all_metadata(self) -> None:
        """Save all modified metadata via MetadataManager."""
        self.main_window.metadata_manager.save_all_modified_metadata()

    def shortcut_calculate_hash_selected(self) -> None:
        """Calculate hash for selected files via ApplicationService (has business logic)."""
        self.main_window.app_service.calculate_hash_selected()

    def rename_files(self) -> None:
        """Execute batch rename via ApplicationService (has business logic)."""
        self.main_window.app_service.rename_files()

    def clear_file_table_shortcut(self) -> None:
        """Clear file table via ShortcutManager."""
        self.main_window.shortcut_manager.clear_file_table_shortcut()

    def force_drag_cleanup(self) -> None:
        """Force drag cleanup via DragCleanupManager."""
        self.main_window.drag_cleanup_manager.force_drag_cleanup()

    # -------------------------------------------------------------------------
    # History/Undo Stubs
    # -------------------------------------------------------------------------

    def global_undo(self) -> None:
        """Global undo handler (Ctrl+Z).

        Note: Unified undo/redo system not yet implemented.
        """
        logger.info(
            "[ShortcutCommandHandler] Global Ctrl+Z pressed - Unified undo system not yet implemented"
        )

    def global_redo(self) -> None:
        """Global redo handler (Ctrl+Shift+Z).

        Note: Unified undo/redo system not yet implemented.
        """
        logger.info(
            "[ShortcutCommandHandler] Global Ctrl+Shift+Z pressed - Unified redo system not yet implemented"
        )

    def show_command_history(self) -> None:
        """Show command history dialog (Ctrl+Y).

        Currently shows MetadataHistoryDialog for metadata operations.
        """
        try:
            from oncutf.ui.dialogs.metadata_history_dialog import MetadataHistoryDialog

            dialog = MetadataHistoryDialog(self.main_window)
            dialog.exec_()
        except Exception:
            logger.exception("[ShortcutCommandHandler] Error showing command history dialog")
            logger.info(
                "[ShortcutCommandHandler] Unified command history not yet fully implemented"
            )

    # -------------------------------------------------------------------------
    # Complex Methods
    # -------------------------------------------------------------------------

    def auto_color_by_folder(self) -> None:
        """Auto-color files by their parent folder (Ctrl+Shift+C).

        Groups all files by folder and assigns unique random colors to each folder's files.
        Skips files that already have colors assigned (preserves user choices).
        Only works when 2+ folders are present.
        """
        logger.info("[ShortcutCommandHandler] AUTO_COLOR: Auto-color by folder requested")

        try:
            # Check if we have files
            if not self.main_window.file_model or not self.main_window.file_model.files:
                logger.info("[ShortcutCommandHandler] AUTO_COLOR: No files loaded")
                if hasattr(self.main_window, "status_manager"):
                    self.main_window.status_manager.set_file_operation_status(
                        "No files loaded", success=False, auto_reset=True
                    )
                return

            # Check if we have 2+ folders
            from pathlib import Path

            folders = set()
            for file_item in self.main_window.file_model.files:
                # Normalize path to use forward slashes consistently (cross-platform)
                folder_path = str(Path(file_item.path).parent).replace("\\", "/")
                folders.add(folder_path)

            if len(folders) < 2:
                logger.info(
                    "[ShortcutCommandHandler] AUTO_COLOR: Need at least 2 folders, found %d",
                    len(folders),
                )
                if hasattr(self.main_window, "status_manager"):
                    self.main_window.status_manager.set_file_operation_status(
                        f"Need 2+ folders (found {len(folders)})",
                        success=False,
                        auto_reset=True,
                    )
                return

            # Check for files with existing colors
            from oncutf.app.services import get_folder_color_service

            folder_color_service = get_folder_color_service()
            files_with_colors = folder_color_service.get_files_with_existing_colors(
                self.main_window.file_model.files, self.main_window.db_manager
            )

            # Show warning dialog if files already have colors
            if files_with_colors:
                from oncutf.ui.dialogs.custom_message_dialog import CustomMessageDialog
                from oncutf.ui.helpers.tooltip_helper import TooltipHelper, TooltipType

                total_selected = len(self.main_window.file_model.files)
                count_with_colors = len(files_with_colors)

                message = f"{count_with_colors} files already have colors out of {total_selected} selected.\n\nWhat would you like to do?"

                dialog = CustomMessageDialog(
                    parent=self.main_window,
                    title="Files Already Colored",
                    message=message,
                    buttons=["Proceed", "Skip", "Cancel"],
                )

                # Add custom tooltips to buttons using TooltipHelper
                if "Proceed" in dialog._buttons:
                    TooltipHelper._setup_persistent_tooltip(
                        dialog._buttons["Proceed"],
                        "Recolor ALL files including those with existing colors",
                        TooltipType.INFO,
                    )
                if "Skip" in dialog._buttons:
                    TooltipHelper._setup_persistent_tooltip(
                        dialog._buttons["Skip"],
                        "Color only files without existing colors",
                        TooltipType.INFO,
                    )
                if "Cancel" in dialog._buttons:
                    TooltipHelper._setup_persistent_tooltip(
                        dialog._buttons["Cancel"],
                        "Cancel the auto-color operation",
                        TooltipType.WARNING,
                    )

                dialog.exec_()

                if dialog.selected == "Cancel" or dialog.selected is None:
                    logger.info("[ShortcutCommandHandler] AUTO_COLOR: User cancelled")
                    return

                # Set skip_existing based on user choice
                skip_existing = dialog.selected == "Skip"
                logger.info(
                    "[ShortcutCommandHandler] AUTO_COLOR: User chose '%s' (skip_existing=%s)",
                    dialog.selected,
                    skip_existing,
                )

                # Recreate command with skip_existing based on user choice
                command = folder_color_service.create_auto_color_command(
                    self.main_window.file_model.files,
                    self.main_window.db_manager,
                    skip_existing=skip_existing,
                )
            else:
                # No existing colors, create command with default skip_existing=True
                command = folder_color_service.create_auto_color_command(
                    self.main_window.file_model.files, self.main_window.db_manager
                )

            # Execute command with wait cursor
            from oncutf.ui.helpers.cursor_helper import wait_cursor

            with wait_cursor():
                success = command.execute()

            if success:
                # Add to command manager for undo/redo
                from oncutf.core.metadata import get_metadata_command_manager

                cmd_manager = get_metadata_command_manager()
                cmd_manager._undo_stack.append(command)
                cmd_manager._emit_state_signals()

                # Refresh table to show colors
                self.main_window.file_model.layoutChanged.emit()

                logger.info(
                    "[ShortcutCommandHandler] AUTO_COLOR: Successfully colored %d files across %d folders",
                    len(command.new_colors),
                    len(command.folder_colors),
                )

                if hasattr(self.main_window, "status_manager"):
                    self.main_window.status_manager.set_file_operation_status(
                        f"Auto-colored {len(command.new_colors)} files from {len(folders)} folders",
                        success=True,
                        auto_reset=True,
                    )
            else:
                logger.warning("[ShortcutCommandHandler] AUTO_COLOR: Command execution failed")
                if hasattr(self.main_window, "status_manager"):
                    self.main_window.status_manager.set_file_operation_status(
                        "Auto-color failed", success=False, auto_reset=True
                    )

        except Exception:
            logger.exception("[ShortcutCommandHandler] AUTO_COLOR: Error during auto-color")
            if hasattr(self.main_window, "status_manager"):
                self.main_window.status_manager.set_file_operation_status(
                    "Auto-color error", success=False, auto_reset=True
                )
