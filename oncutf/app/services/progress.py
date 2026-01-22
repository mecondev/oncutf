"""Progress dialog service - Application layer facade.

Provides Qt-independent progress dialog creation for core modules.
Delegates to ProgressDialogPort implementations.

This module breaks core→ui dependency cycles by inverting control:
- core/ imports this (app layer, no Qt)
- ui/ provides concrete implementations via ports

Author: Michael Economou
Date: 2026-01-22
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QWidget

    from oncutf.app.ports.user_interaction import OperationType, ProgressDialogPort


def create_progress_dialog(
    parent: QWidget | None = None,
    operation_type: OperationType = "metadata_basic",
    cancel_callback: object | None = None,
    show_enhanced_info: bool = False,
    is_exit_save: bool = False,
) -> ProgressDialogPort:
    """Create a progress dialog using registered adapter or fallback to legacy.
    
    Args:
        parent: Parent widget (may be None)
        operation_type: Type of operation (metadata_basic, metadata_extended, etc.)
        cancel_callback: Callback function for user cancellation
        show_enhanced_info: Whether to show enhanced information
        is_exit_save: Whether this is an exit save operation
        
    Returns:
        ProgressDialogPort implementation
        
    Note:
        This function is a bridge - core modules can call it without
        importing Qt directly. The actual dialog is created by the adapter.
    """
    # For now, always use Qt adapter directly (registration can be added later)
    from oncutf.ui.adapters.qt_user_interaction import QtProgressDialogAdapter

    return QtProgressDialogAdapter(
        parent=parent,
        operation_type=operation_type,
        cancel_callback=cancel_callback,
        show_enhanced_info=show_enhanced_info,
        is_exit_save=is_exit_save,
    )


def create_metadata_dialog(
    parent: QWidget | None = None,
    is_extended: bool = False,
    cancel_callback: object | None = None,
    show_enhanced_info: bool = True,
    use_size_based_progress: bool = True,
) -> ProgressDialogPort:
    """Create a progress dialog preconfigured for metadata operations.

    Args:
        parent: Parent widget
        is_extended: True for extended metadata, False for basic
        cancel_callback: Function to call when user cancels
        show_enhanced_info: Whether to show enhanced size/time tracking
        use_size_based_progress: Whether to use size-based progress bar

    Returns:
        ProgressDialogPort configured for metadata operations

    """
    from oncutf.utils.ui.progress_dialog import ProgressDialog

    # Use legacy factory method with all special configuration
    dialog = ProgressDialog.create_metadata_dialog(
        parent=parent,
        is_extended=is_extended,
        cancel_callback=cancel_callback,
        show_enhanced_info=show_enhanced_info,
        use_size_based_progress=use_size_based_progress,
    )

    # Wrap in adapter without re-creating the dialog
    from oncutf.ui.adapters.qt_user_interaction import QtProgressDialogAdapter

    adapter = QtProgressDialogAdapter.__new__(QtProgressDialogAdapter)
    adapter._dialog = dialog  # Inject pre-created dialog
    return adapter


def create_hash_dialog(
    parent: QWidget | None = None,
    cancel_callback: object | None = None,
    show_enhanced_info: bool = True,
    use_size_based_progress: bool = True,
) -> ProgressDialogPort:
    """Create a progress dialog preconfigured for hash/checksum operations.

    Args:
        parent: Parent widget
        cancel_callback: Function to call when user cancels
        show_enhanced_info: Whether to show enhanced size/time tracking
        use_size_based_progress: Whether to use size-based progress bar

    Returns:
        ProgressDialogPort configured for hash operations

    """
    from oncutf.utils.ui.progress_dialog import ProgressDialog

    # Use legacy factory method with all special configuration
    dialog = ProgressDialog.create_hash_dialog(
        parent=parent,
        cancel_callback=cancel_callback,
        show_enhanced_info=show_enhanced_info,
        use_size_based_progress=use_size_based_progress,
    )

    # Wrap in adapter without re-creating the dialog
    from oncutf.ui.adapters.qt_user_interaction import QtProgressDialogAdapter

    adapter = QtProgressDialogAdapter.__new__(QtProgressDialogAdapter)
    adapter._dialog = dialog  # Inject pre-created dialog
    return adapter


def create_file_loading_dialog(
    parent: QWidget | None = None,
    cancel_callback: object | None = None,
    show_enhanced_info: bool = True,
) -> ProgressDialogPort:
    """Create a progress dialog preconfigured for file loading operations.

    Args:
        parent: Parent widget
        cancel_callback: Function to call when user cancels
        show_enhanced_info: Whether to show enhanced size/time tracking

    Returns:
        ProgressDialogPort configured for file loading

    """
    return create_progress_dialog(
        parent=parent,
        operation_type="file_loading",
        cancel_callback=cancel_callback,
        show_enhanced_info=show_enhanced_info,
    )
