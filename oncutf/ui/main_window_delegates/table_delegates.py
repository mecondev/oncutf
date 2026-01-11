"""Table operation delegates for MainWindow.

Author: Michael Economou
Date: 2026-01-10
"""


class TableDelegates:
    """Delegate class for table operations.

    All methods delegate to table_manager.
    """

    def sort_by_column(self, column: int, order=None, force_order=None) -> None:
        """Sort by column via TableManager."""
        self.table_manager.sort_by_column(column, order, force_order)

    def prepare_file_table(self, file_items: list) -> None:
        """Prepare file table via TableManager."""
        self.table_manager.prepare_file_table(file_items)

    def set_fields_from_list(self, field_names: list[str]) -> None:
        """Set fields from list via TableManager."""
        self.table_manager.set_fields_from_list(field_names)

    def after_check_change(self) -> None:
        """Handle check change via TableManager."""
        self.table_manager.after_check_change()
