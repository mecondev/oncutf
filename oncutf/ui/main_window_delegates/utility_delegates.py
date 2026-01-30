"""Utility operation delegates for MainWindow.

Author: Michael Economou
Date: 2026-01-10
"""


class UtilityDelegates:
    """Delegate class for utility operations.

    All methods delegate to utility_manager or other managers.
    """

    def get_modifier_flags(self) -> tuple[bool, bool]:
        """Get modifier flags via UtilityManager."""
        return self.utility_manager.get_modifier_flags()

    def update_files_label(self) -> None:
        """Update files label via UtilityManager."""
        self.utility_manager.update_files_label()

    def _find_consecutive_ranges(self, indices: list[int]) -> list[tuple[int, int]]:
        """Delegates to UtilityManager for consecutive ranges calculation."""
        return self.utility_manager.find_consecutive_ranges(indices)

    def set_status(
        self,
        text: str,
        color: str = "",
        auto_reset: bool = False,
        reset_delay: int = 3000,
    ) -> None:
        """Set status text and color via StatusManager."""
        self.status_manager.set_status(text, color, auto_reset, reset_delay)

    def _enable_selection_store_mode(self):
        """Enable SelectionStore mode in FileTableView."""
        from oncutf.utils.logging.logger_factory import get_cached_logger

        logger = get_cached_logger(__name__)

        if hasattr(self, "initialization_manager"):
            self.initialization_manager.enable_selection_store_mode()
        if hasattr(self, "file_table_view"):
            logger.debug(
                "[MainWindow] Enabling SelectionStore mode in FileTableView",
                extra={"dev_only": True},
            )
            self.file_table_view.enable_selection_store_mode()

    def global_undo(self) -> None:
        """Global undo handler (Ctrl+Z).

        Note: Unified undo/redo system not yet implemented.
        """
        return self.shortcut_handler.global_undo()

    def global_redo(self) -> None:
        """Global redo handler (Ctrl+Shift+Z).

        Note: Unified undo/redo system not yet implemented.
        """
        return self.shortcut_handler.global_redo()

    def show_command_history(self) -> None:
        """Show command history dialog (Ctrl+Y).

        Currently shows MetadataHistoryDialog for metadata operations.
        """
        return self.shortcut_handler.show_command_history()
