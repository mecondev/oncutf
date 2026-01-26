"""Module: signal_coordinator.py.

Author: Michael Economou
Date: 2025-11-21

Centralized signal connection management for the application.
Handles all signal-slot connections in a structured, maintainable way.
"""

from typing import TYPE_CHECKING

from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.ui.main_window import MainWindow

logger = get_cached_logger(__name__)


class SignalCoordinator:
    """Centralized coordinator for all application signal connections.

    This class manages all signal-slot connections in one place, making it easier
    to understand signal flow and debug connection issues.

    Benefits:
    - Single source of truth for signal connections
    - Easier to debug signal flow
    - Clear separation of concerns
    - Better error handling for connection failures
    """

    def __init__(self, parent_window: "MainWindow"):
        """Initialize SignalCoordinator with parent window reference.

        Args:
            parent_window: MainWindow instance

        """
        self.parent_window = parent_window
        self._connected_signals: list[str] = []
        logger.debug("SignalCoordinator initialized", extra={"dev_only": True})

    def setup_all_signals(self) -> None:
        """Setup all signal connections.

        Called after all components are initialized.
        """
        self.setup_metadata_refresh_signals()
        self.setup_timer_signals()
        logger.info(
            "SignalCoordinator: Connected %d signals",
            len(self._connected_signals),
            extra={"dev_only": True},
        )

    def setup_metadata_refresh_signals(self) -> None:
        """Connect signals for hash, selection, and metadata changes to refresh metadata widgets.

        This ensures metadata widgets stay synchronized with:
        - Hash calculation results
        - Selection changes
        - Metadata modifications
        """
        # Hash refresh - only connect if hash_worker exists and is not None
        if (
            hasattr(self.parent_window, "event_handler_manager")
            and hasattr(self.parent_window.event_handler_manager, "hash_worker")
            and self.parent_window.event_handler_manager.hash_worker is not None
        ):
            try:
                self.parent_window.event_handler_manager.hash_worker.file_hash_calculated.connect(
                    self.parent_window.refresh_metadata_widgets
                )
                self._connected_signals.append(
                    "hash_worker.file_hash_calculated → refresh_metadata_widgets"
                )
                logger.debug(
                    "[SignalCoordinator] Connected hash_worker.file_hash_calculated signal",
                    extra={"dev_only": True},
                )
            except Exception as e:
                logger.warning("[SignalCoordinator] Failed to connect hash_worker signal: %s", e)
        else:
            logger.debug(
                "[SignalCoordinator] hash_worker not available for signal connection",
                extra={"dev_only": True},
            )

        # Selection refresh
        if hasattr(self.parent_window, "selection_store"):
            self.parent_window.selection_store.selection_changed.connect(
                lambda _: self.parent_window.refresh_metadata_widgets()
            )
            self._connected_signals.append(
                "selection_store.selection_changed → refresh_metadata_widgets"
            )

            self.parent_window.selection_store.selection_changed.connect(
                lambda _: self.parent_window.update_active_metadata_widget_options()
            )
            self._connected_signals.append(
                "selection_store.selection_changed → update_active_metadata_widget_options"
            )

            logger.debug(
                "[SignalCoordinator] Connected selection_store signals", extra={"dev_only": True}
            )

        # Metadata refresh (try ApplicationContext or UnifiedMetadataManager)
        try:
            from oncutf.ui.adapters.application_context import get_app_context

            context = get_app_context()
            if context and hasattr(context, "metadata_changed"):
                context.metadata_changed.connect(
                    lambda *_: self.parent_window.refresh_metadata_widgets()
                )
                self._connected_signals.append(
                    "context.metadata_changed → refresh_metadata_widgets"
                )
                logger.debug(
                    "[SignalCoordinator] Connected context.metadata_changed signal",
                    extra={"dev_only": True},
                )
        except Exception as e:
            logger.debug(
                "[SignalCoordinator] ApplicationContext metadata_changed not available: %s",
                e,
            )

        try:
            if hasattr(self.parent_window, "unified_metadata_manager") and hasattr(
                self.parent_window.unified_metadata_manager, "metadata_changed"
            ):
                self.parent_window.unified_metadata_manager.metadata_changed.connect(
                    lambda *_: self.parent_window.refresh_metadata_widgets()
                )
                self._connected_signals.append(
                    "unified_metadata_manager.metadata_changed → refresh_metadata_widgets"
                )
                logger.debug(
                    "[SignalCoordinator] Connected unified_metadata_manager.metadata_changed signal",
                    extra={"dev_only": True},
                )
        except Exception as e:
            logger.debug(
                "[SignalCoordinator] UnifiedMetadataManager metadata_changed not available: %s",
                e,
            )

    def setup_timer_signals(self) -> None:
        """Connect timer signals for debounced operations.

        Note: Preview update timing is now handled by UtilityManager via TimerManager
        instead of a central preview_update_timer, providing better decoupling.
        """
        # Preview update timer signals are now handled by UtilityManager.request_preview_update()
        # via TimerManager.schedule_preview_update() for better architecture
        logger.debug(
            "[SignalCoordinator] Timer signals setup (preview handled by UtilityManager)",
            extra={"dev_only": True},
        )

    def get_connected_signals(self) -> list[str]:
        """Get list of all connected signals for debugging.

        Returns:
            List of signal connection descriptions

        """
        return self._connected_signals.copy()

    def disconnect_all(self) -> None:
        """Disconnect all signals (cleanup on shutdown).

        Note: Qt automatically disconnects signals when objects are destroyed,
        but this can be useful for testing or explicit cleanup.
        """
        logger.info("[SignalCoordinator] Disconnecting all signals", extra={"dev_only": True})
        # Qt handles disconnection automatically, but we clear our tracking
        self._connected_signals.clear()
