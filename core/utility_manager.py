"""
UtilityManager - Handles utility functions and miscellaneous operations

Author: Michael Economou
Date: 2025-05-01

This manager centralizes utility functions including:
- Event filtering and modifier handling
- Window management operations
- Preview generation and updates
- Status and UI updates
- Application lifecycle management
"""

from typing import TYPE_CHECKING

from core.qt_imports import QEvent, Qt, QApplication

from config import STATUS_COLORS
from utils.logger_factory import get_cached_logger
from utils.tooltip_helper import setup_tooltip, TooltipType

if TYPE_CHECKING:
    from main_window import MainWindow

logger = get_cached_logger(__name__)


class UtilityManager:
    """
    Manages utility functions and miscellaneous operations for the main window.

    This manager handles:
    - Event filtering and keyboard modifier tracking
    - Window positioning and lifecycle management
    - Preview generation and update scheduling
    - UI state updates and animations
    - File selection utilities
    """

    def __init__(self, main_window: 'MainWindow'):
        """
        Initialize the UtilityManager.

        Args:
            main_window: Reference to the main window instance
        """
        self.main_window = main_window
        logger.debug("[UtilityManager] Initialized", extra={"dev_only": True})

    def event_filter(self, obj, event):
        """
        Captures global keyboard modifier state (Ctrl, Shift).
        """
        if event.type() in (QEvent.KeyPress, QEvent.KeyRelease):
            self.main_window.modifier_state = QApplication.keyboardModifiers()
            logger.debug(f"[Modifiers] eventFilter saw: {event.type()} with modifiers={int(event.modifiers())}", extra={"dev_only": True})

        return super(type(self.main_window), self.main_window).eventFilter(obj, event)

    def request_preview_update(self) -> None:
        """
        Schedules a delayed update of the name previews.
        Instead of calling generate_preview_names directly every time something changes,
        the timer is restarted so that the actual update occurs only when
        changes stop for the specified duration (250ms).
        """
        if self.main_window.preview_update_timer.isActive():
            self.main_window.preview_update_timer.stop()
        self.main_window.preview_update_timer.start()

    def force_reload(self) -> None:
        """
        Triggered by Ctrl+R.
        If Ctrl is held, metadata scan is skipped (like Select/Browse).
        Otherwise, full reload with scan.
        """
        # Update current state of modifier keys
        self.main_window.modifier_state = QApplication.keyboardModifiers()

        if not self.main_window.current_folder_path:
            self.main_window.set_status("No folder loaded.", color=STATUS_COLORS["no_action"], auto_reset=True)
            return

        from widgets.custom_msgdialog import CustomMessageDialog
        if not CustomMessageDialog.question(self.main_window, "Reload Folder", "Reload current folder?", yes_text="Reload", no_text="Cancel"):
            return

        # Use determine_metadata_mode method instead of deprecated resolve_skip_metadata
        skip_metadata, use_extended = self.main_window.determine_metadata_mode()
        self.main_window.force_extended_metadata = use_extended
        self.main_window.skip_metadata_mode = skip_metadata

        logger.info(
            f"[ForceReload] Reloading {self.main_window.current_folder_path}, skip_metadata={skip_metadata} "
            f"(use_extended={use_extended})"
        )

        self.main_window.load_files_from_folder(self.main_window.current_folder_path, skip_metadata=skip_metadata, force=True)

    def find_consecutive_ranges(self, indices: list[int]) -> list[tuple[int, int]]:
        """
        Given a sorted list of indices, returns a list of (start, end) tuples for consecutive ranges.
        Example: [1,2,3,7,8,10] -> [(1,3), (7,8), (10,10)]
        """
        if not indices:
            return []
        ranges = []
        start = prev = indices[0]
        for idx in indices[1:]:
            if idx == prev + 1:
                prev = idx
            else:
                ranges.append((start, prev))
                start = prev = idx
        ranges.append((start, prev))
        return ranges

    def center_window(self) -> None:
        """
        Centers the application window on the user's screen.

        It calculates the screen's center point and moves the window
        so its center aligns with that. This improves the initial UX
        by avoiding awkward off-center placement.

        Returns:
            None
        """
        try:
            # Use modern QScreen API instead of deprecated QDesktopWidget
            app = QApplication.instance()
            if not app or not hasattr(app, 'screens'):
                logger.warning("No QApplication instance found for centering window")
                return

            # Get current geometry of the window
            window_geometry = self.main_window.frameGeometry()

            # Try to find the screen that contains the window center
            window_center = window_geometry.center()
            target_screen = None

            for screen in app.screens():
                if screen.geometry().contains(window_center):
                    target_screen = screen
                    break

            # If window is not on any screen, use primary screen
            if not target_screen:
                target_screen = app.primaryScreen()
                if not target_screen:
                    logger.warning("No primary screen found for centering window")
                    return

            # Get the center point of the available screen area
            screen_center = target_screen.availableGeometry().center()

            # Move the window geometry so that its center aligns with screen center
            window_geometry.moveCenter(screen_center)

            # Reposition the window's top-left corner to match the new centered geometry
            self.main_window.move(window_geometry.topLeft())

            logger.debug(f"Main window centered on screen {target_screen.name()}", extra={"dev_only": True})

        except Exception as e:
            logger.error(f"Failed to center window: {e}")
            # Fallback to simple positioning
            self.main_window.move(100, 100)

    def update_files_label(self) -> None:
        """
        Updates the UI label that displays the count of selected files.

        If no files are loaded, the label shows a default "Files".
        Otherwise, it shows how many files are currently selected
        out of the total number loaded.
        """
        total = len(self.main_window.file_model.files)
        selected = len(self.main_window.get_selected_files()) if total else 0

        self.main_window.status_manager.update_files_label(self.main_window.files_label, total, selected)

    def get_selected_rows_files(self) -> list:
        """
        Returns a list of FileItem objects currently selected (blue-highlighted) in the table view.
        """
        selected_indexes = self.main_window.file_table_view.selectionModel().selectedRows()
        return [self.main_window.file_model.files[i.row()] for i in selected_indexes if 0 <= i.row() < len(self.main_window.file_model.files)]

    def get_modifier_flags(self) -> tuple[bool, bool]:
        """
        Checks which keyboard modifiers are currently held down.

        Returns:
            tuple: (skip_metadata: bool, use_extended: bool)
                - skip_metadata: True if NO modifiers are pressed (default) or if Ctrl is NOT pressed
                - use_extended: True if Ctrl+Shift is pressed
        """
        modifiers = self.main_window.modifier_state
        ctrl = bool(modifiers & Qt.ControlModifier)
        shift = bool(modifiers & Qt.ShiftModifier)

        skip_metadata = not ctrl
        use_extended = ctrl and shift

        # [DEBUG] Modifiers: Ctrl=%s, Shift=%s", skip_metadata, use_extended
        return skip_metadata, use_extended

    def close_event(self, event) -> None:
        """
        Called when the main window is about to close.

        Ensures any background metadata threads are cleaned up
        properly before the application exits.
        """
        logger.info("Main window closing. Cleaning up metadata worker.")
        self.main_window.cleanup_metadata_worker()

        if hasattr(self.main_window.metadata_loader, "close"):
            self.main_window.metadata_loader.close()

        # Clean up application context
        if hasattr(self.main_window, 'context'):
            self.main_window.context.cleanup()

        # Call the original closeEvent
        super(type(self.main_window), self.main_window).closeEvent(event)

    def generate_preview_names(self) -> None:
        """
        Generate new preview names for all selected files using current rename modules.
        Updates the preview map and UI elements accordingly.
        """
        selected_files = self.main_window.get_selected_files()
        logger.debug("[Preview] Triggered! Selected rows: %s", [f.filename for f in selected_files], extra={"dev_only": True})

        if not selected_files:
            logger.debug("[Preview] No selected files — skipping preview generation.", extra={"dev_only": True})
            self.main_window.update_preview_tables_from_pairs([])
            self.main_window.rename_button.setEnabled(False)
            return

        # Get rename data and modules
        rename_data = self.main_window.rename_modules_area.get_all_data()

        # Add post_transform data from final transform container
        post_transform_data = self.main_window.final_transform_container.get_data()
        rename_data["post_transform"] = post_transform_data

        all_modules = self.main_window.rename_modules_area.get_all_module_instances()

        # Use PreviewManager to generate previews
        name_pairs, has_changes = self.main_window.preview_manager.generate_preview_names(
            selected_files, rename_data, self.main_window.metadata_cache, all_modules
        )

        # Update preview map from manager
        self.main_window.preview_map = self.main_window.preview_manager.get_preview_map()

        # Handle UI updates based on results
        if not name_pairs:
            # No modules at all → clear preview completely
            self.main_window.update_preview_tables_from_pairs([])
            self.main_window.rename_button.setEnabled(False)
            self.main_window.set_status("No rename modules defined.", color=STATUS_COLORS["loading"], auto_reset=True)
            return

        if not has_changes:
            # Modules exist but inactive → show identity mapping
            self.main_window.rename_button.setEnabled(False)
            setup_tooltip(self.main_window.rename_button, "No changes to apply", TooltipType.WARNING)
            self.main_window.update_preview_tables_from_pairs(name_pairs)
            self.main_window.set_status("Rename modules present but inactive.", color=STATUS_COLORS["loading"], auto_reset=True)
            return

        # Update preview tables with changes
        self.main_window.update_preview_tables_from_pairs(name_pairs)

        # Enable rename button and set tooltip
        valid_pairs = [p for p in name_pairs if p[0] != p[1]]

        # Check for validation errors in new names
        from utils.filename_validator import is_validation_error_marker
        has_validation_errors = any(is_validation_error_marker(new_name) for _, new_name in name_pairs)

        # Rename button should be enabled only if we have changes AND no validation errors
        can_rename = bool(valid_pairs) and not has_validation_errors
        self.main_window.rename_button.setEnabled(can_rename)

        # Set appropriate tooltip message
        if has_validation_errors:
            error_count = sum(1 for _, new_name in name_pairs if is_validation_error_marker(new_name))
            tooltip_msg = f"Cannot rename: {error_count} validation error(s) found"
            tooltip_type = TooltipType.ERROR
        elif valid_pairs:
            tooltip_msg = f"{len(valid_pairs)} files will be renamed."
            tooltip_type = TooltipType.SUCCESS
        else:
            tooltip_msg = "No changes to apply"
            tooltip_type = TooltipType.WARNING

        setup_tooltip(self.main_window.rename_button, tooltip_msg, tooltip_type)


