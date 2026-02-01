"""Selection operation delegates for MainWindow.

Author: Michael Economou
Date: 2026-01-10
"""


class SelectionDelegates:
    """Delegate class for selection operations.

    All methods delegate to shortcut_handler or selection_manager.
    """

    def select_all_rows(self) -> None:
        """Select all rows via Application Service."""
        return self.shortcut_handler.select_all_rows()

    def clear_all_selection(self) -> None:
        """Clear all selection via Application Service."""
        return self.shortcut_handler.clear_all_selection()

    def invert_selection(self) -> None:
        """Invert selection via Application Service."""
        return self.shortcut_handler.invert_selection()

    def get_selected_files(self) -> list:
        """Get selected files via TableManager."""
        return self.table_manager.get_selected_files()

    def get_selected_rows_files(self) -> list:
        """Get selected rows as files via UtilityManager."""
        return self.utility_manager.get_selected_rows_files()

    def get_selected_files_ordered(self) -> list:
        """Unified method to get selected files in table display order.

        Returns:
            List of FileItem objects sorted by their row position in the table

        """
        if not (hasattr(self, "file_table_view") and hasattr(self, "file_model")):
            return []

        if not self.file_model or not self.file_model.files:
            return []

        # Get current selection and sort to maintain display order
        selected_rows = self.file_table_view._selection_behavior.get_current_selection()
        selected_rows_sorted = sorted(selected_rows)

        # Convert to FileItem objects with bounds checking
        return [
            self.file_model.files[row]
            for row in selected_rows_sorted
            if 0 <= row < len(self.file_model.files)
        ]

    def update_preview_from_selection(self, selected_rows: list[int]) -> None:
        """Update preview from selection via SelectionManager."""
        self.selection_manager.update_preview_from_selection(selected_rows)
