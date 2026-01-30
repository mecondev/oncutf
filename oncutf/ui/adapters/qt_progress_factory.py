"""Qt Progress Dialog Factory Adapter.

Provides concrete implementation of progress dialog creation for the app layer.
Implements dependency inversion to break core→ui dependencies.

Author: Michael Economou
Date: 2026-01-30
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from oncutf.ui.helpers.progress_dialog import ProgressDialog

if TYPE_CHECKING:
    from collections.abc import Callable

    from oncutf.app.ports.user_interaction import OperationType


class QtProgressFactory:
    """Factory for creating Qt-based progress dialogs.

    Registered with AppContext as 'progress_factory' to enable
    Qt-independent progress dialog creation from core/ layer.
    """

    def create_dialog(
        self,
        parent: Any = None,
        operation_type: OperationType = "metadata_basic",
        cancel_callback: Callable[[], None] | None = None,
        show_enhanced_info: bool = False,
        is_exit_save: bool = False,
    ) -> ProgressDialog:
        """Create a Qt progress dialog.

        Args:
            parent: Parent widget (may be None)
            operation_type: Type of operation for appropriate theming
            cancel_callback: Callback for user cancellation
            show_enhanced_info: Whether to show enhanced progress info
            is_exit_save: Whether this is an exit save operation

        Returns:
            Concrete ProgressDialog instance

        """
        return ProgressDialog.create_by_type(
            parent=parent,
            operation_type=operation_type,
            cancel_callback=cancel_callback,
            show_enhanced_info=show_enhanced_info,
            is_exit_save=is_exit_save,
        )
