"""Module: metadata_shortcut_handler.py

Author: Michael Economou
Date: 2025-12-21

Keyboard shortcut handler for metadata operations.
Extracted from unified_metadata_manager.py for better separation of concerns.

Responsibilities:
- Handle keyboard shortcuts for metadata loading (M, Ctrl+M, Shift+M, etc.)
- Determine metadata loading mode based on modifier keys
- Coordinate with metadata loader for actual loading
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.core.unified_metadata_manager import UnifiedMetadataManager
    from oncutf.models.file_item import FileItem

logger = get_cached_logger(__name__)


class MetadataShortcutHandler:
    """Handler for keyboard shortcuts that trigger metadata operations.

    This class encapsulates all shortcut-related logic that was previously
    in UnifiedMetadataManager, including:
    - Modifier key detection (Ctrl, Shift)
    - Metadata mode determination (fast vs extended)
    - Shortcut methods for loading metadata (selected, all)
    """

    def __init__(self, manager: UnifiedMetadataManager, parent_window: Any = None) -> None:
        """Initialize shortcut handler.

        Args:
            manager: Reference to the UnifiedMetadataManager for delegation
            parent_window: Reference to the main application window

        """
        self._manager = manager
        self._parent_window = parent_window

    @property
    def parent_window(self) -> Any:
        """Get parent window, preferring manager's reference."""
        return self._parent_window or (self._manager.parent_window if self._manager else None)

    # =========================================================================
    # Mode Determination Methods
    # =========================================================================

    def determine_metadata_mode(self, modifier_state: Any = None) -> tuple[bool, bool]:
        """Determines whether to use extended mode based on modifier keys.

        Args:
            modifier_state: Qt.KeyboardModifiers to use, or None for current state

        Returns:
            tuple: (skip_metadata, use_extended)

            - skip_metadata = True  -> No metadata scan (no modifiers)
            - skip_metadata = False & use_extended = False -> Fast scan (Ctrl)
            - skip_metadata = False & use_extended = True  -> Extended scan (Ctrl+Shift)

        """
        from oncutf.core.pyqt_imports import QApplication, Qt

        modifiers = modifier_state
        if modifiers is None:
            if self.parent_window and hasattr(self.parent_window, "modifier_state"):
                modifiers = self.parent_window.modifier_state
            else:
                modifiers = QApplication.keyboardModifiers()

        if modifiers == Qt.NoModifier:
            modifiers = QApplication.keyboardModifiers()  # fallback to current

        ctrl = bool(modifiers & Qt.ControlModifier)
        shift = bool(modifiers & Qt.ShiftModifier)

        # - No modifiers: skip metadata
        # - With Ctrl: load basic metadata
        # - With Ctrl+Shift: load extended metadata
        skip_metadata = not ctrl
        use_extended = ctrl and shift

        logger.debug(
            "[MetadataShortcutHandler] modifiers=%d, ctrl=%s, shift=%s, "
            "skip_metadata=%s, use_extended=%s",
            int(modifiers),
            ctrl,
            shift,
            skip_metadata,
            use_extended,
        )

        return skip_metadata, use_extended

    def should_use_extended_metadata(self, modifier_state: Any = None) -> bool:
        """Returns True if Ctrl+Shift are both held.

        Used in cases where metadata is always loaded (drag & drop).
        This assumes that metadata will be loaded - we only decide if it's fast or extended.

        Args:
            modifier_state: Qt.KeyboardModifiers to use, or None for current state

        Returns:
            bool: True if extended metadata should be used

        """
        from oncutf.core.pyqt_imports import QApplication, Qt

        modifiers = modifier_state
        if modifiers is None:
            if self.parent_window and hasattr(self.parent_window, "modifier_state"):
                modifiers = self.parent_window.modifier_state
            else:
                modifiers = QApplication.keyboardModifiers()

        ctrl = bool(modifiers & Qt.ControlModifier)
        shift = bool(modifiers & Qt.ShiftModifier)
        return ctrl and shift

    # =========================================================================
    # Shortcut Methods - Selected Files
    # =========================================================================

    def shortcut_load_metadata(self) -> None:
        """Load standard (non-extended) metadata for currently selected files.

        Triggered by keyboard shortcut (e.g., M key).
        """
        if not self.parent_window:
            return

        # Use unified selection method
        selected_files = self._get_selected_files()

        if not selected_files:
            logger.info("[MetadataShortcut] No files selected for metadata loading")
            return

        # Analyze metadata state
        metadata_analysis = self._analyze_metadata_state(selected_files)

        if not metadata_analysis["enable_fast_selected"]:
            # All files already have fast metadata or better
            from oncutf.utils.ui.dialog_utils import show_info_message

            message = (
                f"All {len(selected_files)} selected file(s) already have "
                f"fast metadata or better."
            )
            if metadata_analysis.get("fast_tooltip"):
                message += f"\n\n{metadata_analysis['fast_tooltip']}"

            show_info_message(
                self.parent_window,
                "Fast Metadata Loading",
                message,
            )
            return

        logger.info("[MetadataShortcut] Loading basic metadata for %d files", len(selected_files))
        # Delegate to manager for actual loading
        self._manager.load_metadata_for_items(selected_files, use_extended=False, source="shortcut")

    def shortcut_load_extended_metadata(self) -> None:
        """Load extended metadata for selected files.

        Triggered by keyboard shortcut (e.g., Shift+M).
        """
        if not self.parent_window:
            return

        if self._manager.is_running_metadata_task():
            logger.warning("[MetadataShortcut] Metadata scan already running - shortcut ignored.")
            return

        # Use unified selection method
        selected_files = self._get_selected_files()

        if not selected_files:
            logger.info("[MetadataShortcut] No files selected for extended metadata loading")
            return

        # Analyze metadata state
        metadata_analysis = self._analyze_metadata_state(selected_files)

        if not metadata_analysis["enable_extended_selected"]:
            # All files already have extended metadata
            from oncutf.utils.ui.dialog_utils import show_info_message

            message = f"All {len(selected_files)} selected file(s) already have extended metadata."
            if metadata_analysis.get("extended_tooltip"):
                message += f"\n\n{metadata_analysis['extended_tooltip']}"

            show_info_message(
                self.parent_window,
                "Extended Metadata Loading",
                message,
            )
            return

        # Check if we have files with fast metadata that can be upgraded
        stats = metadata_analysis.get("stats", {})
        fast_count = stats.get("fast_metadata", 0)

        if fast_count > 0:
            from oncutf.utils.ui.dialog_utils import show_question_message

            message = (
                f"Found {fast_count} file(s) with fast metadata.\n\n"
                f"Do you want to upgrade them to extended metadata?"
            )
            if metadata_analysis.get("extended_tooltip"):
                message += f"\n\nDetails: {metadata_analysis['extended_tooltip']}"

            result = show_question_message(
                self.parent_window,
                "Upgrade to Extended Metadata",
                message,
            )

            if not result:
                return

        logger.info(
            "[MetadataShortcut] Loading extended metadata for %d files", len(selected_files)
        )
        # Delegate to manager for actual loading
        self._manager.load_metadata_for_items(selected_files, use_extended=True, source="shortcut")

    # =========================================================================
    # Shortcut Methods - All Files
    # =========================================================================

    def shortcut_load_metadata_all(self) -> None:
        """Load basic metadata for ALL files in current folder.

        Triggered by keyboard shortcut (e.g., Ctrl+M).
        """
        if not self.parent_window:
            return

        if self._manager.is_running_metadata_task():
            logger.warning("[MetadataShortcut] Metadata scan already running - shortcut ignored.")
            return

        all_files = self._get_all_files()

        if not all_files:
            logger.info("[MetadataShortcut] No files available for metadata loading")
            if hasattr(self.parent_window, "status_manager"):
                self.parent_window.status_manager.set_selection_status(
                    "No files available", selected_count=0, total_count=0, auto_reset=True
                )
            return

        # Analyze metadata state to avoid loading if all files already have metadata
        metadata_analysis = self._analyze_metadata_state(all_files)

        if not metadata_analysis["enable_fast_selected"]:
            # All files already have fast metadata or better
            from oncutf.utils.ui.dialog_utils import show_info_message

            message = f"All {len(all_files)} file(s) already have fast metadata or better."
            if metadata_analysis.get("fast_tooltip"):
                message += f"\n\n{metadata_analysis['fast_tooltip']}"

            show_info_message(
                self.parent_window,
                "Fast Metadata Loading",
                message,
            )
            return

        logger.info("[MetadataShortcut] Loading basic metadata for all %d files", len(all_files))
        self._manager.load_metadata_for_items(all_files, use_extended=False, source="shortcut_all")

    def shortcut_load_extended_metadata_all(self) -> None:
        """Load extended metadata for ALL files in current folder.

        Triggered by keyboard shortcut (e.g., Ctrl+Shift+M).
        """
        if not self.parent_window:
            return

        if self._manager.is_running_metadata_task():
            logger.warning("[MetadataShortcut] Metadata scan already running - shortcut ignored.")
            return

        all_files = self._get_all_files()

        if not all_files:
            logger.info("[MetadataShortcut] No files available for extended metadata loading")
            if hasattr(self.parent_window, "status_manager"):
                self.parent_window.status_manager.set_selection_status(
                    "No files available", selected_count=0, total_count=0, auto_reset=True
                )
            return

        # Analyze metadata state to avoid loading if all files already have extended metadata
        metadata_analysis = self._analyze_metadata_state(all_files)

        if not metadata_analysis["enable_extended_selected"]:
            # All files already have extended metadata
            from oncutf.utils.ui.dialog_utils import show_info_message

            message = f"All {len(all_files)} file(s) already have extended metadata."
            if metadata_analysis.get("extended_tooltip"):
                message += f"\n\n{metadata_analysis['extended_tooltip']}"

            show_info_message(
                self.parent_window,
                "Extended Metadata Loading",
                message,
            )
            return

        logger.info(
            "[MetadataShortcut] Loading extended metadata for all %d files",
            len(all_files),
        )
        self._manager.load_metadata_for_items(all_files, use_extended=True, source="shortcut_all")

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _get_selected_files(self) -> list[FileItem]:
        """Get currently selected files from parent window."""
        if self.parent_window and hasattr(self.parent_window, "get_selected_files_ordered"):
            result = self.parent_window.get_selected_files_ordered()
            return result if isinstance(result, list) else []
        return []

    def _get_all_files(self) -> list[FileItem]:
        """Get all files from the application context."""
        from oncutf.core.application_context import ApplicationContext

        context = ApplicationContext()
        return context.file_store.get_loaded_files()

    def _analyze_metadata_state(self, files: list[FileItem]) -> dict[str, Any]:
        """Analyze metadata state of files using event handler manager.

        Args:
            files: List of files to analyze

        Returns:
            Dictionary with metadata analysis results

        """
        if (
            self.parent_window
            and hasattr(self.parent_window, "event_handler_manager")
            and hasattr(self.parent_window.event_handler_manager, "_analyze_metadata_state")
        ):
            result = self.parent_window.event_handler_manager._analyze_metadata_state(files)
            return result if isinstance(result, dict) else {}

        # Fallback: return permissive defaults
        return {
            "enable_fast_selected": True,
            "enable_extended_selected": True,
            "fast_tooltip": None,
            "extended_tooltip": None,
            "stats": {},
        }
