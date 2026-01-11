"""Preview operation delegates for MainWindow.

Author: Michael Economou
Date: 2026-01-10
"""
from oncutf.utils.shared.timer_manager import cancel_timer, schedule_preview_update


class PreviewDelegates:
    """Delegate class for preview operations.

    All methods delegate to preview_manager or utility_manager.
    """

    def request_preview_update(self) -> None:
        """Request preview update via UtilityManager."""
        self.utility_manager.request_preview_update()

    def request_preview_update_debounced(self) -> None:
        """Request preview update with 300ms debounce.

        Day 1-2 Performance Optimization: Prevents redundant preview recalculations
        during rapid user input (e.g., typing, slider adjustments).

        Usage:
        - Module parameter changes (typing, sliders, dropdowns)
        - Final transform changes (greeklish, case, separator)

        The timer resets on each call, so only the final state triggers preview.
        """
        self._preview_pending = True

        # Cancel existing timer
        if self._preview_debounce_timer_id:
            cancel_timer(self._preview_debounce_timer_id)

        # Schedule preview update with 300ms debounce via TimerManager
        self._preview_debounce_timer_id = schedule_preview_update(
            self._execute_pending_preview, delay=300
        )

    def _execute_pending_preview(self) -> None:
        """Execute pending preview update after debounce delay."""
        if self._preview_pending:
            self._preview_pending = False
            self.utility_manager.request_preview_update()

    def generate_preview_names(self) -> None:
        """Generate preview names via UtilityManager."""
        self.utility_manager.generate_preview_names()

    def get_identity_name_pairs(self) -> list[tuple[str, str]]:
        """Get identity name pairs via PreviewManager."""
        return self.preview_manager.get_identity_name_pairs(self.file_model.files)

    def update_preview_tables_from_pairs(self, name_pairs: list[tuple[str, str]]) -> None:
        """Update preview tables from pairs via PreviewManager."""
        self.preview_manager.update_preview_tables_from_pairs(name_pairs)

    def compute_max_filename_width(self, file_list: list) -> int:
        """Compute max filename width via PreviewManager."""
        return self.preview_manager.compute_max_filename_width(file_list)

    def _update_status_from_preview(self, status_html: str) -> None:
        """Delegates to InitializationManager for status updates from preview."""
        self.initialization_manager.update_status_from_preview(status_html)

    def update_module_dividers(self) -> None:
        """Delegates to RenameManager for module dividers update."""
        self.rename_manager.update_module_dividers()
