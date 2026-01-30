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

    def create_progress_dialog(
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

    def create_metadata_dialog(
        self,
        parent: Any = None,
        is_extended: bool = False,
        cancel_callback: Callable[[], None] | None = None,
        show_enhanced_info: bool = True,
        use_size_based_progress: bool = True,
    ) -> ProgressDialog:
        """Create a progress dialog preconfigured for metadata operations.

        Args:
            parent: Parent widget
            is_extended: True for extended metadata, False for basic
            cancel_callback: Function to call when user cancels
            show_enhanced_info: Whether to show enhanced size/time tracking
            use_size_based_progress: Whether to use size-based progress bar

        Returns:
            ProgressDialog configured for metadata operations

        """
        return ProgressDialog.create_metadata_dialog(
            parent=parent,
            is_extended=is_extended,
            cancel_callback=cancel_callback,
            show_enhanced_info=show_enhanced_info,
            use_size_based_progress=use_size_based_progress,
        )

    def create_hash_dialog(
        self,
        parent: Any = None,
        cancel_callback: Callable[[], None] | None = None,
        show_enhanced_info: bool = True,
        use_size_based_progress: bool = True,
    ) -> ProgressDialog:
        """Create a progress dialog preconfigured for hash operations.

        Args:
            parent: Parent widget
            cancel_callback: Function to call when user cancels
            show_enhanced_info: Whether to show enhanced size/time tracking
            use_size_based_progress: Whether to use size-based progress bar

        Returns:
            ProgressDialog configured for hash operations

        """
        return ProgressDialog.create_hash_dialog(
            parent=parent,
            cancel_callback=cancel_callback,
            show_enhanced_info=show_enhanced_info,
            use_size_based_progress=use_size_based_progress,
        )
