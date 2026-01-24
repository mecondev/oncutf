"""Module: base.py.

Author: Michael Economou
Date: 2026-01-01

Context menu base handler - orchestrates menu building and delegates to specialized handlers.
Main entry point for context menu operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from oncutf.core.pyqt_imports import QAction, QMenu
from oncutf.core.theme_manager import get_theme_manager
from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.ui.stylesheet_utils import inject_font_family
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
        from oncutf.core.metadata import MetadataOperationsManager

        self.metadata_ops = MetadataOperationsManager(parent_window)

        # Composition pattern - create handler instances
        from oncutf.ui.events.context_menu.file_status import FileStatusHelpers
        from oncutf.ui.events.context_menu.hash_handlers import HashHandlers
        from oncutf.ui.events.context_menu.metadata_handlers import MetadataHandlers
        from oncutf.ui.events.context_menu.rotation_handlers import RotationHandlers

        self.file_status = FileStatusHelpers(parent_window)
        self.hash_handlers = HashHandlers(parent_window)
        self.metadata_handlers = MetadataHandlers(parent_window)
        self.rotation_handlers = RotationHandlers(parent_window)

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

        from oncutf.app.services.icons import get_menu_icon

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
        menu_qss = f"""
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
        menu.setStyleSheet(inject_font_family(menu_qss))

        # Smart Metadata actions - only analyze selected files for speed
        selected_analysis = self.metadata_handlers._analyze_metadata_state(selected_files)

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
            # Normalize path to use forward slashes consistently (cross-platform)
            folder_path = str(Path(file_item.path).parent).replace("\\", "/")
            folders.add(folder_path)

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
        selected_hash_analysis = self.hash_handlers._analyze_hash_state(selected_files)

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

        # Check if ANY selected file has rotation != 0
        has_rotation_to_reset = False
        if has_selection and hasattr(self.parent_window, "metadata_cache"):
            for file_item in selected_files:
                metadata_entry = self.parent_window.metadata_cache.get_entry(file_item.full_path)
                if metadata_entry and hasattr(metadata_entry, "data"):
                    rotation = metadata_entry.data.get("rotation", "0")
                    # Enable if rotation exists and is not "0" or 0
                    if rotation and str(rotation) != "0":
                        has_rotation_to_reset = True
                        break

        action_set_rotation.setEnabled(has_selection and has_rotation_to_reset)

        if has_selection:
            sel_count = len(selected_files)
            if has_rotation_to_reset:
                rotation_tip = f"Reset rotation to 0 for {sel_count} selected file(s)"
                if sel_count < total_files:
                    rotation_tip += f" (Tip: Ctrl+A to select all {total_files} files)"
                TooltipHelper.setup_action_tooltip(
                    action_set_rotation, rotation_tip, TooltipType.INFO, menu
                )
            else:
                TooltipHelper.setup_action_tooltip(
                    action_set_rotation,
                    "All selected files already have rotation = 0",
                    TooltipType.INFO,
                    menu,
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
            from oncutf.app.services import get_metadata_command_manager

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
            self.rotation_handlers._handle_bulk_rotation(selected_files)

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
                self.parent_window.file_model.get_all_file_items()
                if hasattr(self.parent_window, "file_model")
                and self.parent_window.file_model
                else []
            )
            self.metadata_ops.handle_export_metadata(all_files, "all")

    # =====================================
    # Backward Compatibility Delegation
    # =====================================

    def _analyze_metadata_state(self, files: list[FileItem]) -> dict[str, Any]:
        """Delegate to metadata handlers."""
        return self.metadata_handlers._analyze_metadata_state(files)

    def _analyze_hash_state(self, files: list[FileItem]) -> dict[str, Any]:
        """Delegate to hash handlers."""
        return self.hash_handlers._analyze_hash_state(files)

    def _handle_bulk_rotation(self, selected_files: list[FileItem]) -> None:
        """Delegate to rotation handlers."""
        return self.rotation_handlers._handle_bulk_rotation(selected_files)

    def _file_has_metadata(self, file_item: FileItem) -> bool:
        """Delegate to file status helpers."""
        return self.file_status._file_has_metadata(file_item)

    def _file_has_hash(self, file_item: FileItem) -> bool:
        """Delegate to file status helpers."""
        return self.file_status._file_has_hash(file_item)

    def _file_has_metadata_type(self, file_item: FileItem, extended: bool) -> bool:
        """Delegate to file status helpers."""
        return self.file_status._file_has_metadata_type(file_item, extended)

    def check_files_status(
        self,
        files: list[FileItem] | None = None,
        check_type: str = "metadata",
        extended: bool = False,
        scope: str = "selected",
    ) -> dict[str, Any]:
        """Delegate to file status helpers."""
        return self.file_status.check_files_status(files, check_type, extended, scope)

    def get_files_without_metadata(
        self,
        files: list[FileItem] | None = None,
        extended: bool = False,
        scope: str = "selected",
    ) -> list[FileItem]:
        """Delegate to file status helpers."""
        return self.file_status.get_files_without_metadata(files, extended, scope)

    def get_files_without_hashes(
        self, files: list[FileItem] | None = None, scope: str = "selected"
    ) -> list[FileItem]:
        """Delegate to file status helpers."""
        return self.file_status.get_files_without_hashes(files, scope)
