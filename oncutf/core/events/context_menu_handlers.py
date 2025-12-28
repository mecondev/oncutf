"""Module: context_menu_handlers.py

Author: Michael Economou
Date: 2025-12-20

Context menu event handlers - right-click menus, bulk rotation, metadata analysis.
Extracted from event_handler_manager.py for better separation of concerns.

This module handles the complex context menu logic which was ~400+ lines in the
original event_handler_manager.py. It includes metadata state analysis and
bulk rotation operations.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from oncutf.config import STATUS_COLORS
from oncutf.core.pyqt_imports import QAction, QMenu
from oncutf.core.theme_manager import get_theme_manager
from oncutf.utils.filesystem.file_status_helpers import has_hash, has_metadata
from oncutf.utils.filesystem.path_utils import paths_equal
from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.ui.tooltip_helper import TooltipHelper, TooltipType

if TYPE_CHECKING:
    from oncutf.models.file_item import FileItem

logger = get_cached_logger(__name__)


class ContextMenuHandlers:
    """Handles context menu events and related operations.

    Responsibilities:
    - Table context menu (right-click)
    - Bulk rotation operations
    - Metadata state analysis
    - Hash state analysis
    - File status checking utilities
    """

    def __init__(self, parent_window: Any) -> None:
        """Initialize context menu handlers with parent window reference."""
        self.parent_window = parent_window

        # Delegate hash operations to specialized manager
        from oncutf.core.hash.hash_operations_manager import HashOperationsManager

        self.hash_ops = HashOperationsManager(parent_window)

        # Delegate metadata operations to specialized manager
        from oncutf.core.metadata_operations_manager import MetadataOperationsManager

        self.metadata_ops = MetadataOperationsManager(parent_window)

        logger.debug("ContextMenuHandlers initialized", extra={"dev_only": True})

    def handle_table_context_menu(self, position: Any) -> None:
        """Handles the right-click context menu for the file table.
        Simplified for faster response - basic functionality only.
        """
        if not self.parent_window.file_model.files:
            return

        # Check if right-click was on color column - skip context menu for color column
        index = self.parent_window.file_table_view.indexAt(position)
        if index.isValid():
            # Get column key from model
            if hasattr(self.parent_window.file_model, "_column_mapping"):
                column_key = self.parent_window.file_model._column_mapping.get(index.column())
                if column_key == "color":
                    # Color column handles its own right-click menu via ColorColumnDelegate
                    logger.debug(
                        "[ContextMenu] Skipping context menu for color column",
                        extra={"dev_only": True},
                    )
                    return

        from oncutf.utils.ui.icons_loader import get_menu_icon

        # Helper function to create actions with shortcuts
        def create_action_with_shortcut(
            icon: Any, text: str, shortcut: str | None = None
        ) -> QAction:
            action = QAction(text, self.parent_window)
            action.setIcon(icon)
            if shortcut:
                # Use tab character for right alignment - Qt handles this automatically
                action.setText(f"{text}\t{shortcut}")
            return action

        # Get total files for context
        total_files = len(self.parent_window.file_model.files)

        # Use unified selection method (fast)
        selected_files = self.parent_window.get_selected_files_ordered()
        has_selection = len(selected_files) > 0

        logger.debug(
            "Context menu: %d selected files",
            len(selected_files),
            extra={"dev_only": True},
        )

        menu = QMenu(self.parent_window)

        # Get theme colors from ThemeManager
        theme = get_theme_manager()

        # Enhanced styling for better appearance and spacing
        menu.setStyleSheet(
            f"""
            QMenu {{
                background-color: {theme.get_color('menu_background')};
                color: {theme.get_color('menu_text')};
                border: none;
                border-radius: 8px;
                font-family: "Inter", "Segoe UI", Arial, sans-serif;
                font-size: 9pt;
                padding: 6px 4px;
            }}
            QMenu::item {{
                background-color: transparent;
                padding: 3px 16px 3px 8px;
                margin: 1px 2px;
                border-radius: 4px;
                min-height: 16px;
                icon-size: 16px;
            }}
            QMenu::item:selected {{
                background-color: {theme.get_color('menu_selected_bg')};
                color: {theme.get_color('menu_selected_text')};
            }}
            QMenu::item:disabled {{
                color: {theme.get_color('menu_disabled_text')};
            }}
            QMenu::icon {{
                padding-left: 6px;
                padding-right: 6px;
            }}
            QMenu::separator {{
                background-color: {theme.get_color('separator')};
                height: 1px;
                margin: 4px 8px;
            }}
        """
        )

        # Smart Metadata actions - only analyze selected files for speed
        selected_analysis = self._analyze_metadata_state(selected_files)

        # === SELECTION ACTIONS (First in menu) ===
        action_select_all = create_action_with_shortcut(
            get_menu_icon("check-square"), "Select All", "Ctrl+A"
        )
        action_invert = create_action_with_shortcut(
            get_menu_icon("refresh-cw"), "Invert Selection", "Ctrl+I"
        )
        action_deselect_all = create_action_with_shortcut(
            get_menu_icon("square"), "Deselect All", "Ctrl+Shift+A"
        )

        menu.addAction(action_select_all)
        menu.addAction(action_invert)
        menu.addAction(action_deselect_all)

        menu.addSeparator()

        # === METADATA OPERATIONS (Selection-only) ===
        action_load_fast = create_action_with_shortcut(
            get_menu_icon("file"), "Load Fast Metadata", "Ctrl+M"
        )
        action_load_extended = create_action_with_shortcut(
            get_menu_icon("file-plus"), "Load Extended Metadata", "Ctrl+Shift+M"
        )

        menu.addAction(action_load_fast)
        menu.addAction(action_load_extended)

        # Smart enable/disable logic based on analysis
        action_load_fast.setEnabled(has_selection and selected_analysis["enable_fast_selected"])
        action_load_extended.setEnabled(
            has_selection and selected_analysis["enable_extended_selected"]
        )

        # Set smart tooltips with selection context
        if has_selection:
            sel_count = len(selected_files)
            load_fast_tip = selected_analysis["fast_tooltip"]
            if sel_count < total_files:
                load_fast_tip += f" (Tip: Ctrl+A to select all {total_files} files)"
            TooltipHelper.setup_action_tooltip(
                action_load_fast, load_fast_tip, TooltipType.INFO, menu
            )

            load_ext_tip = selected_analysis["extended_tooltip"]
            if sel_count < total_files:
                load_ext_tip += f" (Tip: Ctrl+A to select all {total_files} files)"
            TooltipHelper.setup_action_tooltip(
                action_load_extended, load_ext_tip, TooltipType.INFO, menu
            )
        else:
            TooltipHelper.setup_action_tooltip(
                action_load_fast,
                "Select files first (Ctrl+A to select all)",
                TooltipType.WARNING,
                menu,
            )
            TooltipHelper.setup_action_tooltip(
                action_load_extended,
                "Select files first (Ctrl+A to select all)",
                TooltipType.WARNING,
                menu,
            )

        menu.addSeparator()

        # === OTHER ACTIONS ===
        action_reload = create_action_with_shortcut(
            get_menu_icon("refresh-cw"), "Reload Folder", "F5"
        )
        action_clear_table = create_action_with_shortcut(
            get_menu_icon("x"), "Clear File Table", "Shift+Esc"
        )

        menu.addAction(action_reload)
        menu.addAction(action_clear_table)

        menu.addSeparator()

        # === COLOR OPERATIONS ===
        action_auto_color_folders = create_action_with_shortcut(
            get_menu_icon("palette"), "Auto-Color by Folder", "Ctrl+Shift+C"
        )
        menu.addAction(action_auto_color_folders)

        # Enable only if we have 2+ folders
        from pathlib import Path

        folders = set()
        for file_item in self.parent_window.file_model.files:
            folders.add(str(Path(file_item.path).parent))

        has_multiple_folders = len(folders) >= 2
        action_auto_color_folders.setEnabled(has_multiple_folders)

        if has_multiple_folders:
            TooltipHelper.setup_action_tooltip(
                action_auto_color_folders,
                f"Assign unique colors to files grouped by folder ({len(folders)} folders)",
                TooltipType.INFO,
                menu,
            )
        else:
            TooltipHelper.setup_action_tooltip(
                action_auto_color_folders,
                "Need 2+ folders to auto-color",
                TooltipType.WARNING,
                menu,
            )

        menu.addSeparator()

        # === HASH OPERATIONS (Selection-only) ===
        action_calculate_hashes = create_action_with_shortcut(
            get_menu_icon("hash"), "Calculate Checksums", "Ctrl+H"
        )

        # Smart hash state analysis - only analyze selected files for speed
        selected_hash_analysis = self._analyze_hash_state(selected_files)

        menu.addAction(action_calculate_hashes)

        # Smart enable/disable for hash actions
        action_calculate_hashes.setEnabled(
            has_selection and selected_hash_analysis["enable_selected"]
        )

        # Set smart tooltips with selection context
        if has_selection:
            sel_count = len(selected_files)
            hash_tip = selected_hash_analysis["selected_tooltip"]
            if sel_count < total_files:
                hash_tip += f" (Tip: Ctrl+A to select all {total_files} files)"
            TooltipHelper.setup_action_tooltip(
                action_calculate_hashes, hash_tip, TooltipType.INFO, menu
            )
        else:
            TooltipHelper.setup_action_tooltip(
                action_calculate_hashes,
                "Select files first (Ctrl+A to select all)",
                TooltipType.WARNING,
                menu,
            )

        # Show results hash list action
        action_show_hash_results = create_action_with_shortcut(
            get_menu_icon("list"), "Show calculated hashes", "Ctrl+L"
        )
        menu.addAction(action_show_hash_results)

        # Enable only if there are selected files
        action_show_hash_results.setEnabled(has_selection)
        TooltipHelper.setup_action_tooltip(
            action_show_hash_results,
            (
                "Display hashes for selected files that have been calculated"
                if has_selection
                else "Select files first to show their hashes"
            ),
            TooltipType.INFO if has_selection else TooltipType.WARNING,
            menu,
        )

        # Connect show hash results action
        action_show_hash_results.triggered.connect(
            self.parent_window.shortcut_manager.show_results_hash_list
        )

        menu.addSeparator()

        # === SAVE OPERATIONS ===
        action_save_all_modified = create_action_with_shortcut(
            get_menu_icon("save"), "Save Modified Metadata", "Ctrl+S"
        )

        menu.addAction(action_save_all_modified)

        # Simple check for modifications
        has_modifications = False
        if hasattr(self.parent_window, "metadata_tree_view"):
            has_modifications = bool(self.parent_window.metadata_tree_view.modified_items)

        action_save_all_modified.setEnabled(has_modifications)

        TooltipHelper.setup_action_tooltip(
            action_save_all_modified,
            (
                "Save all modified metadata (Ctrl+S)"
                if has_modifications
                else "No modified metadata to save"
            ),
            TooltipType.INFO if has_modifications else TooltipType.WARNING,
            menu,
        )

        action_save_all_modified.triggered.connect(self.parent_window.shortcut_save_all_metadata)

        menu.addSeparator()

        # === ROTATION OPERATION (Selection-only) ===
        action_set_rotation = create_action_with_shortcut(
            get_menu_icon("rotate-ccw"), "Set Rotation to 0", None
        )
        menu.addAction(action_set_rotation)
        action_set_rotation.setEnabled(has_selection)

        if has_selection:
            sel_count = len(selected_files)
            rotation_tip = f"Reset rotation to 0 for {sel_count} selected file(s)"
            if sel_count < total_files:
                rotation_tip += f" (Tip: Ctrl+A to select all {total_files} files)"
            TooltipHelper.setup_action_tooltip(
                action_set_rotation, rotation_tip, TooltipType.INFO, menu
            )
        else:
            TooltipHelper.setup_action_tooltip(
                action_set_rotation,
                "Select files first (Ctrl+A to select all)",
                TooltipType.WARNING,
                menu,
            )

        menu.addSeparator()

        # === HASH COMPARISON ACTIONS (Selection-only + All) ===
        action_find_duplicates_sel = create_action_with_shortcut(
            get_menu_icon("copy"), "Find Duplicates in Selection", None
        )
        action_find_duplicates_all = create_action_with_shortcut(
            get_menu_icon("layers"), "Find Duplicates in All Files", None
        )
        action_compare_external = create_action_with_shortcut(
            get_menu_icon("folder"), "Compare with external folder...", None
        )

        menu.addAction(action_find_duplicates_sel)
        menu.addAction(action_find_duplicates_all)
        menu.addAction(action_compare_external)

        menu.addSeparator()

        # === UNDO/REDO/HISTORY ACTIONS (Global) ===
        action_undo = create_action_with_shortcut(get_menu_icon("rotate-ccw"), "Undo\tCtrl+Z", None)
        action_redo = create_action_with_shortcut(
            get_menu_icon("rotate-cw"), "Redo\tCtrl+Shift+Z", None
        )
        action_show_history = create_action_with_shortcut(
            get_menu_icon("list"), "Show Command History\tCtrl+Y", None
        )

        menu.addAction(action_undo)
        menu.addAction(action_redo)
        menu.addAction(action_show_history)

        # Enable/disable undo/redo based on command manager state
        try:
            from oncutf.core.metadata_command_manager import get_metadata_command_manager

            command_manager = get_metadata_command_manager()
            action_undo.setEnabled(command_manager.can_undo())
            action_redo.setEnabled(command_manager.can_redo())
        except Exception as e:
            logger.debug(
                "[FileTable] Could not check undo/redo state: %s",
                e,
                extra={"dev_only": True},
            )
            action_undo.setEnabled(False)
            action_redo.setEnabled(False)

        action_show_history.setEnabled(True)  # Always available

        menu.addSeparator()

        # === EXPORT ACTIONS (Selection-only + All) ===
        action_export_sel = create_action_with_shortcut(
            get_menu_icon("download"), "Export Metadata (Selection)", None
        )
        action_export_all = create_action_with_shortcut(
            get_menu_icon("download"), "Export Metadata (All Files)", None
        )

        menu.addAction(action_export_sel)
        menu.addAction(action_export_all)

        # Enable/disable export actions based on metadata availability
        action_export_sel.setEnabled(has_selection)
        action_export_all.setEnabled(total_files > 0)

        # Smart tooltips
        if has_selection:
            sel_count = len(selected_files)
            export_tip = f"Export metadata for {sel_count} selected file(s)"
            if sel_count < total_files:
                export_tip += f" (Tip: Ctrl+A to export all {total_files} files)"
            TooltipHelper.setup_action_tooltip(
                action_export_sel, export_tip, TooltipType.INFO, menu
            )
        else:
            TooltipHelper.setup_action_tooltip(
                action_export_sel,
                "Select files first (Ctrl+A to select all)",
                TooltipType.WARNING,
                menu,
            )

        if total_files > 0:
            TooltipHelper.setup_action_tooltip(
                action_export_all,
                f"Export metadata for all {total_files} files in folder",
                TooltipType.INFO,
                menu,
            )
        else:
            TooltipHelper.setup_action_tooltip(
                action_export_all, "No files have metadata to export", TooltipType.WARNING, menu
            )

        # Enable/disable logic for non-operation actions
        action_invert.setEnabled(total_files > 0 and has_selection)
        action_select_all.setEnabled(total_files > 0)
        action_reload.setEnabled(total_files > 0)
        action_clear_table.setEnabled(total_files > 0)

        # Hash comparison actions enable/disable logic
        action_find_duplicates_sel.setEnabled(
            len(selected_files) >= 2
        )  # Need at least 2 files to find duplicates
        action_find_duplicates_all.setEnabled(total_files >= 2)
        action_compare_external.setEnabled(has_selection)  # Need selection to compare

        # Show menu and get chosen action
        action = menu.exec_(self.parent_window.file_table_view.viewport().mapToGlobal(position))

        self.parent_window.file_table_view.context_focused_row = None

        # === Handlers ===
        if action == action_load_fast:
            self.parent_window.load_metadata_for_items(
                selected_files, use_extended=False, source="context_menu"
            )

        elif action == action_load_extended:
            self.parent_window.load_metadata_for_items(
                selected_files, use_extended=True, source="context_menu"
            )

        elif action == action_invert:
            self.parent_window.invert_selection()

        elif action == action_select_all:
            self.parent_window.select_all_rows()

        elif action == action_reload:
            self.parent_window.force_reload()

        elif action == action_clear_table:
            self.parent_window.clear_file_table_shortcut()

        elif action == action_auto_color_folders:
            self.parent_window.auto_color_by_folder()

        elif action == action_deselect_all:
            self.parent_window.clear_all_selection()

        elif action == action_save_all_modified:
            try:
                metadata_mgr = self.parent_window.context.get_manager("metadata")
                metadata_mgr.save_all_modified_metadata()
            except KeyError:
                logger.warning("[EventHandler] No metadata manager available for save all")

        elif action == action_set_rotation:
            self._handle_bulk_rotation(selected_files)

        elif action == action_find_duplicates_sel:
            self.hash_ops.handle_find_duplicates(selected_files)

        elif action == action_find_duplicates_all:
            self.hash_ops.handle_find_duplicates(None)  # None = all files

        elif action == action_compare_external:
            self.hash_ops.handle_compare_external(selected_files)

        elif action == action_calculate_hashes:
            self.hash_ops.handle_calculate_hashes(selected_files)

        elif action == action_undo:
            self.parent_window.global_undo()

        elif action == action_redo:
            self.parent_window.global_redo()

        elif action == action_show_history:
            self.parent_window.show_command_history()

        elif action == action_export_sel:
            self.metadata_ops.handle_export_metadata(selected_files, "selected")

        elif action == action_export_all:
            all_files = (
                self.parent_window.file_table_model.get_all_file_items()
                if hasattr(self.parent_window, "file_table_model")
                and self.parent_window.file_table_model
                else []
            )
            self.metadata_ops.handle_export_metadata(all_files, "all")

    # =====================================
    # Bulk Rotation Methods
    # =====================================

    def _handle_bulk_rotation(self, selected_files: list[FileItem]) -> None:
        """Handle bulk rotation setting to 0 deg for selected files.
        Analyzes metadata availability and prompts user to load if needed.

        Args:
            selected_files: List of FileItem objects to process

        """
        if not selected_files:
            logger.warning("[BulkRotation] No files selected for bulk rotation")
            return

        logger.info("[BulkRotation] Starting bulk rotation for %d files", len(selected_files))

        # Analyze which files have metadata loaded
        files_with_metadata = []
        files_without_metadata = []

        for file_item in selected_files:
            if self._has_metadata_loaded(file_item):
                files_with_metadata.append(file_item)
            else:
                files_without_metadata.append(file_item)

        logger.debug(
            "[BulkRotation] Metadata analysis: %d with metadata, %d without metadata",
            len(files_with_metadata),
            len(files_without_metadata),
            extra={"dev_only": True},
        )

        # If files without metadata exist, prompt user
        files_to_process = selected_files
        if files_without_metadata:
            choice = self._show_load_metadata_prompt(
                len(files_with_metadata), len(files_without_metadata)
            )

            if choice == "load":
                logger.info(
                    "[BulkRotation] Loading metadata for %d files",
                    len(files_without_metadata),
                )
                self.parent_window.load_metadata_for_items(
                    files_without_metadata, use_extended=False, source="rotation_prep"
                )
                files_to_process = selected_files
            elif choice == "skip":
                if not files_with_metadata:
                    logger.info("[BulkRotation] No files with metadata to process")
                    return
                files_to_process = files_with_metadata
                logger.info(
                    "[BulkRotation] Skipping %d files without metadata",
                    len(files_without_metadata),
                )
            else:  # cancel
                logger.debug("[BulkRotation] User cancelled operation", extra={"dev_only": True})
                return

        try:
            from oncutf.ui.widgets.bulk_rotation_dialog import BulkRotationDialog

            final_files = BulkRotationDialog.get_bulk_rotation_choice(
                self.parent_window, files_to_process, self.parent_window.metadata_cache
            )

            if not final_files:
                logger.debug(
                    "[BulkRotation] User cancelled bulk rotation or no files selected",
                    extra={"dev_only": True},
                )
                return

            logger.info("[BulkRotation] Processing %d files", len(final_files))
            self._apply_bulk_rotation(final_files)

        except ImportError as e:
            logger.error("[BulkRotation] Failed to import BulkRotationDialog: %s", e)
            from oncutf.utils.ui.dialog_utils import show_error_message

            show_error_message(
                self.parent_window,
                "Error",
                "Bulk rotation dialog is not available. Please check the installation.",
            )
        except Exception as e:
            logger.exception("[BulkRotation] Unexpected error: %s", e)
            from oncutf.utils.ui.dialog_utils import show_error_message

            show_error_message(
                self.parent_window,
                "Error",
                f"An error occurred during bulk rotation: {str(e)}",
            )

    def _has_metadata_loaded(self, file_item: FileItem) -> bool:
        """Check if a file has metadata loaded in cache."""
        if not self.parent_window or not hasattr(self.parent_window, "metadata_cache"):
            return False

        metadata_entry = self.parent_window.metadata_cache.get_entry(file_item.full_path)
        if metadata_entry and hasattr(metadata_entry, "data") and metadata_entry.data:
            return True

        return hasattr(file_item, "metadata") and bool(file_item.metadata)

    def _show_load_metadata_prompt(
        self, with_metadata_count: int, without_metadata_count: int
    ) -> str:
        """Show prompt asking user whether to load metadata for files that don't have it.

        Returns:
            'load': Load metadata and continue
            'skip': Skip files without metadata
            'cancel': Cancel operation

        """
        from oncutf.ui.widgets.custom_message_dialog import CustomMessageDialog

        message_parts = []
        if with_metadata_count > 0:
            message_parts.append(
                f"{with_metadata_count} file(s) have metadata and can be processed"
            )

        message_parts.append(f"{without_metadata_count} file(s) don't have metadata loaded yet")
        message_parts.append("\nLoad metadata for these files first?")
        message_parts.append("(This ensures rotation changes can be saved properly)")

        message = "\n".join(message_parts)

        buttons = ["Load & Continue", "Skip", "Cancel"]
        dlg = CustomMessageDialog("Load Metadata First?", message, buttons, self.parent_window)

        if self.parent_window:
            from oncutf.utils.ui.multiscreen_helper import ensure_dialog_on_parent_screen

            ensure_dialog_on_parent_screen(dlg, self.parent_window)

        dlg.exec_()

        button_map: dict[str, str] = {
            "Load & Continue": "load",
            "Skip": "skip",
            "Cancel": "cancel",
        }

        selected: str = dlg.selected if dlg.selected else "cancel"
        return button_map.get(selected, "cancel")

    def _apply_bulk_rotation(self, files_to_process: list[FileItem]) -> None:
        """Apply 0 deg rotation to the specified files, but only to files that actually need the change.

        Args:
            files_to_process: List of FileItem objects to set rotation to 0 deg

        """
        if not files_to_process:
            return

        logger.info("[BulkRotation] Checking rotation for %d files", len(files_to_process))

        try:
            try:
                staging_manager = self.parent_window.context.get_manager("metadata_staging")
            except KeyError:
                logger.error("[BulkRotation] MetadataStagingManager not found")
                return

            modified_count = 0
            skipped_count = 0

            for file_item in files_to_process:
                current_rotation = self._get_current_rotation_for_file(file_item)

                if current_rotation == "0":
                    logger.debug(
                        "[BulkRotation] Skipping %s - already has 0 deg rotation",
                        file_item.filename,
                        extra={"dev_only": True},
                    )
                    skipped_count += 1
                    continue

                staging_manager.stage_change(file_item.full_path, "Rotation", "0")

                cache_entry = self.parent_window.metadata_cache.get_entry(file_item.full_path)
                if not cache_entry:
                    metadata_dict = getattr(file_item, "metadata", {}) or {}
                    self.parent_window.metadata_cache.set(file_item.full_path, metadata_dict)
                    cache_entry = self.parent_window.metadata_cache.get_entry(file_item.full_path)

                if cache_entry and hasattr(cache_entry, "data"):
                    cache_entry.data["Rotation"] = "0"
                    cache_entry.modified = True

                    if not hasattr(file_item, "metadata") or file_item.metadata is None:
                        file_item.metadata = {}
                    file_item.metadata["Rotation"] = "0"

                    file_item.metadata_status = "modified"
                    modified_count += 1

                    logger.debug(
                        "[BulkRotation] Set rotation=0 for %s (was: %s)",
                        file_item.filename,
                        current_rotation,
                        extra={"dev_only": True},
                    )

            # Update UI to reflect changes
            if modified_count > 0:
                if hasattr(self.parent_window, "file_model"):
                    for file_item in files_to_process:
                        if file_item.metadata_status == "modified":
                            try:
                                for row, model_file in enumerate(
                                    self.parent_window.file_model.files
                                ):
                                    if paths_equal(model_file.full_path, file_item.full_path):
                                        idx = self.parent_window.file_model.index(row, 0)
                                        self.parent_window.file_model.dataChanged.emit(idx, idx)
                                        break
                            except Exception as e:
                                logger.warning(
                                    "[BulkRotation] Error updating icon for %s: %s",
                                    file_item.filename,
                                    e,
                                )

                    self.parent_window.file_model.layoutChanged.emit()

                # Update metadata tree view to mark items as modified
                if hasattr(self.parent_window, "metadata_tree_view"):
                    for file_item in files_to_process:
                        if file_item.metadata_status == "modified":
                            if not self.parent_window.metadata_tree_view._path_in_dict(
                                file_item.full_path,
                                self.parent_window.metadata_tree_view.modified_items_per_file,
                            ):
                                self.parent_window.metadata_tree_view._set_in_path_dict(
                                    file_item.full_path,
                                    set(),
                                    self.parent_window.metadata_tree_view.modified_items_per_file,
                                )

                            existing_modifications = (
                                self.parent_window.metadata_tree_view._get_from_path_dict(
                                    file_item.full_path,
                                    self.parent_window.metadata_tree_view.modified_items_per_file,
                                )
                            )
                            if existing_modifications is None:
                                existing_modifications = set()
                            existing_modifications.add("Rotation")
                            self.parent_window.metadata_tree_view._set_in_path_dict(
                                file_item.full_path,
                                existing_modifications,
                                self.parent_window.metadata_tree_view.modified_items_per_file,
                            )

                            if hasattr(
                                self.parent_window.metadata_tree_view, "_current_file_path"
                            ) and paths_equal(
                                self.parent_window.metadata_tree_view._current_file_path,
                                file_item.full_path,
                            ):
                                self.parent_window.metadata_tree_view.modified_items.add("Rotation")

                    self.parent_window.metadata_tree_view.update_from_parent_selection()

                if hasattr(self.parent_window, "request_preview_update"):
                    self.parent_window.request_preview_update()

                if hasattr(self.parent_window, "set_status"):
                    if skipped_count > 0:
                        status_msg = (
                            f"Set rotation to 0 deg for {modified_count} file(s), "
                            f"{skipped_count} already had 0 deg rotation"
                        )
                    else:
                        status_msg = f"Set rotation to 0 deg for {modified_count} file(s)"

                    self.parent_window.set_status(
                        status_msg, color=STATUS_COLORS["operation_success"], auto_reset=True
                    )

                logger.info(
                    "[BulkRotation] Successfully applied rotation to %d files, skipped %d files",
                    modified_count,
                    skipped_count,
                )
            else:
                logger.info("[BulkRotation] No files needed rotation changes")
                if hasattr(self.parent_window, "set_status"):
                    self.parent_window.set_status(
                        "All selected files already have 0 deg rotation",
                        color=STATUS_COLORS["neutral_info"],
                        auto_reset=True,
                    )

        except Exception as e:
            logger.exception("[BulkRotation] Error applying rotation: %s", e)
            from oncutf.utils.ui.dialog_utils import show_error_message

            show_error_message(
                self.parent_window, "Error", f"Failed to apply rotation changes: {str(e)}"
            )

    def _get_current_rotation_for_file(self, file_item: FileItem) -> str:
        """Get the current rotation value for a file, checking cache first then file metadata.

        Returns:
            str: Current rotation value ("0", "90", "180", "270") or "0" if not found

        """
        if hasattr(self.parent_window, "metadata_cache"):
            cache_entry = self.parent_window.metadata_cache.get_entry(file_item.full_path)
            if cache_entry and hasattr(cache_entry, "data"):
                rotation = cache_entry.data.get("Rotation")
                if rotation is not None:
                    return str(rotation)

        if hasattr(file_item, "metadata") and file_item.metadata:
            rotation = file_item.metadata.get("Rotation")
            if rotation is not None:
                return str(rotation)

        return "0"

    # =====================================
    # Metadata and Hash Analysis Methods
    # =====================================

    def _analyze_metadata_state(self, files: list[FileItem]) -> dict[str, Any]:
        """Analyze the metadata state of files to determine smart metadata menu options.

        Args:
            files: List of FileItem objects to analyze

        Returns:
            dict: Analysis results with enable/disable logic for metadata menu items

        """
        if not files:
            return {
                "enable_fast_selected": False,
                "enable_extended_selected": False,
                "fast_tooltip": "No files selected",
                "extended_tooltip": "No files selected",
            }

        start_time = time.time()

        files_no_metadata: list[FileItem] = []
        files_fast_metadata: list[FileItem] = []
        files_extended_metadata: list[FileItem] = []

        try:
            metadata_cache = getattr(self.parent_window, "metadata_cache", None)

            if metadata_cache and hasattr(metadata_cache, "get_entries_batch"):
                file_paths = [file_item.full_path for file_item in files]
                batch_entries = metadata_cache.get_entries_batch(file_paths)

                for file_item in files:
                    cache_entry = batch_entries.get(file_item.full_path)

                    if cache_entry and hasattr(cache_entry, "data") and cache_entry.data:
                        if hasattr(cache_entry, "is_extended") and cache_entry.is_extended:
                            files_extended_metadata.append(file_item)
                        else:
                            files_fast_metadata.append(file_item)
                    else:
                        files_no_metadata.append(file_item)
            elif metadata_cache:
                for file_item in files:
                    cache_entry = metadata_cache.get_entry(file_item.full_path)

                    if cache_entry and hasattr(cache_entry, "data") and cache_entry.data:
                        if hasattr(cache_entry, "is_extended") and cache_entry.is_extended:
                            files_extended_metadata.append(file_item)
                        else:
                            files_fast_metadata.append(file_item)
                    else:
                        files_no_metadata.append(file_item)
            else:
                files_no_metadata.extend(files)

            elapsed_time = time.time() - start_time
            logger.debug(
                "[EventHandler] Batch metadata check completed in %.3fs: "
                "%d no metadata, %d fast, %d extended",
                elapsed_time,
                len(files_no_metadata),
                len(files_fast_metadata),
                len(files_extended_metadata),
            )

        except Exception as e:
            logger.warning("[EventHandler] Metadata state analysis failed: %s", e)
            files_no_metadata = list(files)
            files_fast_metadata = []
            files_extended_metadata = []

        total = len(files)
        no_metadata_count = len(files_no_metadata)
        fast_metadata_count = len(files_fast_metadata)
        extended_metadata_count = len(files_extended_metadata)

        enable_fast_selected = (
            no_metadata_count > 0 or fast_metadata_count > 0
        ) and extended_metadata_count == 0

        enable_extended_selected = (
            no_metadata_count > 0 or fast_metadata_count > 0 or extended_metadata_count > 0
        )

        # Fast metadata tooltip
        if extended_metadata_count > 0:
            fast_tooltip = (
                f"Cannot load fast metadata: {extended_metadata_count} file(s) "
                "already have extended metadata"
            )
            enable_fast_selected = False
        elif no_metadata_count == total:
            fast_tooltip = f"Load fast metadata for {total} file(s)"
        elif no_metadata_count == 0 and fast_metadata_count == total:
            fast_tooltip = f"All {total} file(s) already have fast metadata"
            enable_fast_selected = False
        else:
            need_fast = no_metadata_count
            fast_tooltip = f"Load fast metadata for {need_fast} of {total} file(s) that need it"

        # Extended metadata tooltip
        if extended_metadata_count == total:
            extended_tooltip = f"All {total} file(s) already have extended metadata"
            enable_extended_selected = False
        elif extended_metadata_count == 0:
            if fast_metadata_count > 0:
                extended_tooltip = (
                    f"Upgrade {fast_metadata_count} file(s) to extended metadata "
                    f"and load for {no_metadata_count} file(s)"
                )
            else:
                extended_tooltip = f"Load extended metadata for {total} file(s)"
        else:
            need_extended = total - extended_metadata_count
            extended_tooltip = (
                f"Load/upgrade extended metadata for {need_extended} of {total} file(s)"
            )

        return {
            "enable_fast_selected": enable_fast_selected,
            "enable_extended_selected": enable_extended_selected,
            "fast_label": "Load Fast Metadata",
            "extended_label": "Load Extended Metadata",
            "fast_tooltip": fast_tooltip,
            "extended_tooltip": extended_tooltip,
            "stats": {
                "total": total,
                "no_metadata": no_metadata_count,
                "fast_metadata": fast_metadata_count,
                "extended_metadata": extended_metadata_count,
            },
        }

    def _analyze_hash_state(self, files: list[FileItem]) -> dict[str, Any]:
        """Analyze the hash state of files to determine smart hash menu options.

        Args:
            files: List of FileItem objects to analyze

        Returns:
            dict: Analysis results with enable/disable logic for hash menu items

        """
        if not files:
            return {
                "enable_selected": False,
                "enable_all": False,
                "selected_label": "Calculate checksums for selection",
                "all_label": "Calculate checksums for all files",
                "selected_tooltip": "No files selected",
                "all_tooltip": "No files available",
            }

        start_time = time.time()

        files_with_hash: list[FileItem] = []
        files_without_hash: list[FileItem] = []

        try:
            file_paths = [file_item.full_path for file_item in files]

            if hasattr(self.parent_window, "hash_cache") and hasattr(
                self.parent_window.hash_cache, "get_files_with_hash_batch"
            ):
                files_with_hash_paths = self.parent_window.hash_cache.get_files_with_hash_batch(
                    file_paths, "CRC32"
                )
                files_with_hash_set = set(files_with_hash_paths)

                for file_item in files:
                    if file_item.full_path in files_with_hash_set:
                        files_with_hash.append(file_item)
                    else:
                        files_without_hash.append(file_item)

                elapsed_time = time.time() - start_time
                logger.debug(
                    "[EventHandler] Batch hash check completed in %.3fs: %d/%d files have hashes",
                    elapsed_time,
                    len(files_with_hash),
                    len(files),
                )
            else:
                for file_item in files:
                    if self._file_has_hash(file_item):
                        files_with_hash.append(file_item)
                    else:
                        files_without_hash.append(file_item)

                elapsed_time = time.time() - start_time
                logger.debug(
                    "[EventHandler] Individual hash check completed in %.3fs: "
                    "%d/%d files have hashes",
                    elapsed_time,
                    len(files_with_hash),
                    len(files),
                )

        except Exception as e:
            logger.warning(
                "[EventHandler] Batch hash check failed, falling back to individual checks: %s",
                e,
            )
            for file_item in files:
                if self._file_has_hash(file_item):
                    files_with_hash.append(file_item)
                else:
                    files_without_hash.append(file_item)

        total = len(files)
        with_hash_count = len(files_with_hash)
        without_hash_count = len(files_without_hash)

        enable_selected = without_hash_count > 0
        selected_label = "Calculate checksums for selection"

        if without_hash_count == 0:
            selected_tooltip = f"All {total} file(s) already have checksums calculated"
        elif without_hash_count == total:
            selected_tooltip = f"Calculate checksums for {total} file(s)"
        else:
            selected_tooltip = (
                f"Calculate checksums for {without_hash_count} of {total} file(s) that need them"
            )

        return {
            "enable_selected": enable_selected,
            "selected_label": selected_label,
            "selected_tooltip": selected_tooltip,
            "stats": {
                "total": total,
                "with_hash": with_hash_count,
                "without_hash": without_hash_count,
            },
        }

    # =====================================
    # File Status Checking Utilities
    # =====================================

    def _file_has_metadata(self, file_item: FileItem) -> bool:
        """Check if a file has metadata in cache."""
        return has_metadata(file_item.full_path)

    def _file_has_hash(self, file_item: FileItem) -> bool:
        """Check if a file has hash in cache."""
        return has_hash(file_item.full_path)

    def _file_has_metadata_type(self, file_item: FileItem, extended: bool) -> bool:
        """Check if a file has the specified type of metadata (basic or extended)."""
        from oncutf.utils.metadata.cache_helper import get_metadata_cache_helper

        cache_helper = get_metadata_cache_helper(parent_window=self.parent_window)
        return cache_helper.has_metadata(file_item, extended=extended)

    def check_files_status(
        self,
        files: list[FileItem] | None = None,
        check_type: str = "metadata",
        extended: bool = False,
        scope: str = "selected",
    ) -> dict[str, Any]:
        """Unified file status checking for metadata and hash operations.

        Args:
            files: List of files to check (None for all files)
            check_type: 'metadata' or 'hash'
            extended: For metadata checks, whether to check for extended metadata
            scope: 'selected' or 'all' (used when files is None)

        Returns:
            dict with status information

        """
        if files is None:
            if scope == "all" and hasattr(self.parent_window, "file_model"):
                files = self.parent_window.file_model.files or []
            else:
                files = []

        if not files:
            return {
                "has_status": False,
                "count": 0,
                "total": 0,
                "files_with_status": [],
                "files_without_status": [],
            }

        files_with_status: list[FileItem] = []
        files_without_status: list[FileItem] = []

        for file_item in files:
            if check_type == "metadata":
                if extended:
                    has_status = self._file_has_metadata_type(file_item, extended=True)
                else:
                    has_status = self._file_has_metadata_type(
                        file_item, extended=False
                    ) or self._file_has_metadata_type(file_item, extended=True)
            elif check_type == "hash":
                has_status = self._file_has_hash(file_item)
            else:
                has_status = False

            if has_status:
                files_with_status.append(file_item)
            else:
                files_without_status.append(file_item)

        return {
            "has_status": len(files_with_status) == len(files),
            "count": len(files_with_status),
            "total": len(files),
            "files_with_status": files_with_status,
            "files_without_status": files_without_status,
        }

    def get_files_without_metadata(
        self,
        files: list[FileItem] | None = None,
        extended: bool = False,
        scope: str = "selected",
    ) -> list[FileItem]:
        """Get list of files that don't have metadata."""
        status = self.check_files_status(
            files=files, check_type="metadata", extended=extended, scope=scope
        )
        result: list[FileItem] = status["files_without_status"]
        return result

    def get_files_without_hashes(
        self, files: list[FileItem] | None = None, scope: str = "selected"
    ) -> list[FileItem]:
        """Get list of files that don't have hash values."""
        status = self.check_files_status(files=files, check_type="hash", scope=scope)
        result: list[FileItem] = status["files_without_status"]
        return result

    def _get_simple_metadata_analysis(self) -> dict[str, Any]:
        """Get simple metadata analysis for all files without detailed scanning."""
        return {
            "enable_fast_selected": True,
            "enable_extended_selected": True,
            "fast_label": "Load Fast Metadata",
            "extended_label": "Load Extended Metadata",
            "fast_tooltip": "Load fast metadata for all files",
            "extended_tooltip": "Load extended metadata for all files",
        }

    def _get_simple_hash_analysis(self) -> dict[str, Any]:
        """Get simple hash analysis for all files without detailed scanning."""
        return {
            "enable_selected": True,
            "selected_label": "Calculate checksums for all files",
            "selected_tooltip": "Calculate checksums for all files",
        }
