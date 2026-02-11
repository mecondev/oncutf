"""Event handling delegates for MainWindow.

Author: Michael Economou
Date: 2026-01-10
"""


class EventDelegates:
    """Delegate class for event handling operations.

    All methods delegate to event_handler_manager or utility_manager.
    """

    def handle_table_context_menu(self, position, source_widget=None) -> None:
        """Handle table context menu via EventCoordinator."""
        self.event_handler_manager.handle_table_context_menu(position, source_widget)

    def handle_file_double_click(self, index, modifiers=None) -> None:
        """Handle file double click via EventCoordinator."""
        from PyQt5.QtCore import Qt

        if modifiers is None:
            modifiers = Qt.NoModifier

        self.event_handler_manager.handle_file_double_click(index, modifiers)

    def on_table_row_clicked(self, index) -> None:
        """Handle table row click via EventCoordinator."""
        self.event_handler_manager.on_table_row_clicked(index)

    def handle_header_toggle(self, _) -> None:
        """Handle header toggle via EventCoordinator."""
        self.event_handler_manager.handle_header_toggle(_)

    def on_horizontal_splitter_moved(self, pos: int, index: int) -> None:
        """Handle horizontal splitter movement via SplitterManager."""
        self.splitter_manager.on_horizontal_splitter_moved(pos, index)

    def on_vertical_splitter_moved(self, pos: int, index: int) -> None:
        """Handle vertical splitter movement via SplitterManager."""
        self.splitter_manager.on_vertical_splitter_moved(pos, index)

    # Note: eventFilter is NOT delegated here to avoid infinite recursion.
    # UtilityManager.event_filter() calls super() which will correctly resolve
    # to QMainWindow.eventFilter() via MRO (Method Resolution Order).

    def force_drag_cleanup(self) -> None:
        """Force drag cleanup via Application Service."""
        return self.shortcut_handler.force_drag_cleanup()

    def _cleanup_widget_drag_states(self) -> None:
        """Delegates to DragCleanupManager for widget drag states cleanup."""
        self.drag_cleanup_manager._cleanup_widget_drag_states()

    def _emergency_drag_cleanup(self) -> None:
        """Delegates to DragCleanupManager for emergency drag cleanup."""
        self.drag_cleanup_manager.emergency_drag_cleanup()
