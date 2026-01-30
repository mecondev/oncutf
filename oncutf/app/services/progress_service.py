"""Progress dialog service - Application layer facade.

Provides Qt-independent progress dialog creation for core modules.
Delegates to ProgressDialogPort implementations.

This module breaks core→ui dependency cycles by inverting control:
- core/ imports this (app layer, no Qt)
- ui/ provides concrete implementations via ports

Author: Michael Economou
Date: 2026-01-22
Moved to app layer: 2026-01-30
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from collections.abc import Callable

    from oncutf.app.ports.user_interaction import OperationType

logger = get_cached_logger(__name__)


class ProgressDialogProtocol(Protocol):
    """Protocol matching ProgressDialogPort for type checking.

    This local protocol allows proper return type annotation without
    importing Qt-dependent types at runtime.
    """

    def show(self) -> None:
        """Show the progress dialog."""
        ...

    def close(self) -> None:
        """Close the progress dialog."""
        ...

    def set_progress(self, current: int, total: int) -> None:
        """Update progress indicator."""
        ...

    def set_count(self, current: int, total: int) -> None:
        """Set the current/total count display."""
        ...

    def set_filename(self, filename: str) -> None:
        """Set the filename being processed."""
        ...

    def set_status(self, message: str) -> None:
        """Update status message shown in dialog."""
        ...

    def is_cancelled(self) -> bool:
        """Check if user cancelled the operation."""
        ...


def _get_progress_adapter() -> Any:
    """Get the registered progress dialog factory.

    Returns:
        The registered adapter class or None if not registered.

    """
    from oncutf.app.state.context import AppContext

    try:
        ctx = AppContext.get_instance()
        return ctx.get_manager("progress_factory") if ctx.has_manager("progress_factory") else None
    except RuntimeError:
        return None


class NullProgressDialog:
    """Null object pattern for progress dialog when no adapter is registered.

    Implements ProgressDialogProtocol with no-op methods.
    """

    def __init__(self) -> None:
        """Initialize null dialog."""
        self._cancelled = False

    def show(self) -> None:
        """No-op show."""

    def close(self) -> None:
        """No-op close."""

    def set_filename(self, filename: str) -> None:
        """No-op set filename."""

    def set_count(self, current: int, total: int) -> None:
        """No-op set count."""

    def set_progress(self, current: int, total: int) -> None:
        """No-op set progress."""

    def set_status(self, message: str) -> None:
        """No-op set status."""

    def is_cancelled(self) -> bool:
        """Return cancelled state."""
        return self._cancelled

    def request_cancel(self) -> None:
        """Mark as cancelled."""
        self._cancelled = True

    def activateWindow(self) -> None:
        """No-op activate window."""

    def setFocus(self) -> None:
        """No-op set focus."""

    def raise_(self) -> None:
        """No-op raise window."""

    def start_progress_tracking(self, total_size: int = 0) -> None:
        """No-op start progress tracking."""

    def update_progress(
        self,
        file_count: int = 0,
        total_files: int = 0,
        processed_bytes: int = 0,
        total_bytes: int = 0,
    ) -> None:
        """No-op update progress."""


def create_progress_dialog(
    parent: Any = None,
    operation_type: OperationType = "metadata_basic",
    cancel_callback: object | None = None,
    show_enhanced_info: bool = False,
    is_exit_save: bool = False,
) -> ProgressDialogProtocol:
    """Create a progress dialog using registered adapter or fallback to null.

    Args:
        parent: Parent widget (may be None)
        operation_type: Type of operation (metadata_basic, metadata_extended, etc.)
        cancel_callback: Callback function for user cancellation
        show_enhanced_info: Whether to show enhanced information
        is_exit_save: Whether this is an exit save operation

    Returns:
        ProgressDialogProtocol implementation (or NullProgressDialog if no adapter)

    """
    factory = _get_progress_adapter()

    if factory:
        result: ProgressDialogProtocol = factory.create_progress_dialog(
            parent=parent,
            operation_type=operation_type,
            cancel_callback=cancel_callback,
            show_enhanced_info=show_enhanced_info,
            is_exit_save=is_exit_save,
        )
        return result

    logger.debug(
        "[progress_service] No progress factory registered, using NullProgressDialog",
        extra={"dev_only": True},
    )
    return NullProgressDialog()


def create_metadata_dialog(
    parent: Any = None,
    is_extended: bool = False,
    cancel_callback: Callable[[], None] | None = None,
    show_enhanced_info: bool = True,
    use_size_based_progress: bool = True,
) -> ProgressDialogProtocol:
    """Create a progress dialog preconfigured for metadata operations.

    Args:
        parent: Parent widget
        is_extended: True for extended metadata, False for basic
        cancel_callback: Function to call when user cancels
        show_enhanced_info: Whether to show enhanced size/time tracking
        use_size_based_progress: Whether to use size-based progress bar

    Returns:
        ProgressDialogProtocol configured for metadata operations

    """
    factory = _get_progress_adapter()

    if factory and hasattr(factory, "create_metadata_dialog"):
        result: ProgressDialogProtocol = factory.create_metadata_dialog(
            parent=parent,
            is_extended=is_extended,
            cancel_callback=cancel_callback,
            show_enhanced_info=show_enhanced_info,
            use_size_based_progress=use_size_based_progress,
        )
        return result

    logger.debug(
        "[progress_service] No progress factory registered, using NullProgressDialog",
        extra={"dev_only": True},
    )
    return NullProgressDialog()


def create_hash_dialog(
    parent: Any = None,
    cancel_callback: Callable[[], None] | None = None,
    show_enhanced_info: bool = True,
    use_size_based_progress: bool = True,
) -> ProgressDialogProtocol:
    """Create a progress dialog preconfigured for hash/checksum operations.

    Args:
        parent: Parent widget
        cancel_callback: Function to call when user cancels
        show_enhanced_info: Whether to show enhanced size/time tracking
        use_size_based_progress: Whether to use size-based progress bar

    Returns:
        ProgressDialogProtocol configured for hash operations

    """
    factory = _get_progress_adapter()

    if factory and hasattr(factory, "create_hash_dialog"):
        result: ProgressDialogProtocol = factory.create_hash_dialog(
            parent=parent,
            cancel_callback=cancel_callback,
            show_enhanced_info=show_enhanced_info,
            use_size_based_progress=use_size_based_progress,
        )
        return result

    logger.debug(
        "[progress_service] No progress factory registered, using NullProgressDialog",
        extra={"dev_only": True},
    )
    return NullProgressDialog()


def create_file_loading_dialog(
    parent: Any = None,
    cancel_callback: object | None = None,
    show_enhanced_info: bool = True,
) -> ProgressDialogProtocol:
    """Create a progress dialog preconfigured for file loading operations.

    Args:
        parent: Parent widget
        cancel_callback: Function to call when user cancels
        show_enhanced_info: Whether to show enhanced size/time tracking

    Returns:
        ProgressDialogProtocol configured for file loading

    """
    factory = _get_progress_adapter()

    if factory and hasattr(factory, "create_file_loading_dialog"):
        result: ProgressDialogProtocol = factory.create_file_loading_dialog(
            parent=parent,
            cancel_callback=cancel_callback,
            show_enhanced_info=show_enhanced_info,
        )
        return result

    logger.debug(
        "[progress_service] No progress factory registered, using NullProgressDialog",
        extra={"dev_only": True},
    )
    return NullProgressDialog()
