"""Module: main_window.py.

Author: Michael Economou
Date: 2025-05-01

Main application window for oncutf.

This class only contains initialization logic.
All operations are delegated to handlers via delegate classes in main_window_delegates/.

Provides the primary UI including:
- File table for loaded files display
- Metadata tree view
- Rename modules panel
- Folder tree navigation
"""

# type: ignore[attr-defined]


# Import all config constants from centralized module
# Core application modules
from oncutf.core.config_imports import *

# Import all PyQt5 classes from centralized module
from oncutf.core.pyqt_imports import *

# Data models and business logic modules
# Phase 4A UI Handlers
from oncutf.ui.handlers.shutdown_lifecycle_handler import ShutdownLifecycleHandler  # noqa: F401

# Import delegate classes
from oncutf.ui.main_window_delegates import (
    EventDelegates,
    FileOperationDelegates,
    MetadataDelegates,
    PreviewDelegates,
    SelectionDelegates,
    TableDelegates,
    UtilityDelegates,
    ValidationDelegates,
    WindowDelegates,
)

# Utility functions and helpers
from oncutf.utils.logging.logger_factory import get_cached_logger

# UI widgets and custom components

logger = get_cached_logger(__name__)


class MainWindow(
    SelectionDelegates,
    MetadataDelegates,
    FileOperationDelegates,
    PreviewDelegates,
    TableDelegates,
    EventDelegates,
    UtilityDelegates,
    ValidationDelegates,
    WindowDelegates,
    QMainWindow,
):
    """Main application window for oncutf file renaming tool.

    This class inherits from delegate classes that provide method forwarding
    to handlers and managers. The MainWindow itself only contains initialization logic.
    """

    def __init__(self, theme_callback=None) -> None:
        """Initializes the main window and sets up the layout.

        Args:
            theme_callback: Optional callback to apply theme before enabling updates

        """
        super().__init__()

        # Prevent repaints during initialization (seamless display)
        self.setUpdatesEnabled(False)

        # Preview debounce timer ID (managed by TimerManager)
        self._preview_debounce_timer_id: str | None = None
        self._preview_pending = False

        # Use InitializationOrchestrator for structured initialization
        from oncutf.core.initialization.initialization_orchestrator import (
            InitializationOrchestrator,
        )

        orchestrator = InitializationOrchestrator(self)
        orchestrator.orchestrate_initialization(theme_callback)

    # Note: All other methods are inherited from delegate classes in main_window_delegates/
    # See: selection_delegates, metadata_delegates, file_operation_delegates, etc.
