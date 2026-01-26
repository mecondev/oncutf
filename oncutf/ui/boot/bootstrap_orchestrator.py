"""Module: initialization_orchestrator.py.

Author: Michael Economou
Date: 2025-11-21

Orchestrates MainWindow initialization in a structured, maintainable way.
Separates initialization logic from MainWindow class to reduce complexity.
"""

from typing import TYPE_CHECKING, Any

from PyQt5.QtCore import Qt

from oncutf.app.services.icons import (
    create_colored_icon,
    get_icons_loader,
    load_metadata_icons,
    load_preview_status_icons,
    prepare_status_icons,
)
from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.ui.main_window import MainWindow

logger = get_cached_logger(__name__)


class BootstrapOrchestrator:
    """Orchestrates MainWindow initialization in phases.

    This class breaks down the complex initialization into logical phases,
    making it easier to understand, maintain, and modify.

    Benefits:
    - Clear initialization phases
    - Reduced MainWindow __init__ complexity
    - Better error handling per phase
    - Easier to add new initialization steps
    """

    def __init__(self, main_window: "MainWindow"):
        """Initialize orchestrator with MainWindow reference.

        Args:
            main_window: MainWindow instance being initialized

        """
        self.window = main_window
        logger.debug("BootstrapOrchestrator created", extra={"dev_only": True})

    def orchestrate_initialization(self, theme_callback: Any = None) -> None:
        """Orchestrate complete initialization in phases.

        Args:
            theme_callback: Optional callback to apply theme before enabling updates

        Phases:
        1. Core infrastructure (context, managers, database)
        2. Attributes and state
        3. UI setup
        4. Configuration and finalization (with theme application)

        """
        self._phase1_core_infrastructure()
        self._phase2_attributes_and_state()
        self._phase3_ui_setup()
        self._phase4_configuration_and_finalization(theme_callback)
        logger.info("[MAINWINDOW] MainWindow initialization orchestration complete")

    def _phase1_core_infrastructure(self) -> None:
        """Phase 1: Initialize core infrastructure.

        - Application context
        - Singleton managers (drag, preview, rename engine)
        - Database system
        - Core managers
        """
        from oncutf.app.services import get_rename_history_manager
        from oncutf.core.application_context import ApplicationContext
        from oncutf.core.backup_manager import get_backup_manager
        from oncutf.core.cache.persistent_hash_cache import get_persistent_hash_cache
        from oncutf.core.cache.persistent_metadata_cache import get_persistent_metadata_cache
        from oncutf.core.database import initialize_database
        from oncutf.core.file import FileOperationsManager
        from oncutf.core.metadata import (
            MetadataStagingManager,
            set_metadata_staging_manager,
        )
        from oncutf.core.rename.unified_rename_engine import UnifiedRenameEngine
        from oncutf.ui.drag.drag_manager import DragManager

        # Core Application Context
        self.window.context = ApplicationContext.create_instance(parent=self.window)

        # Register UI adapters for dependency inversion
        from oncutf.ui.adapters.qt_file_load_ui import QtFileLoadUIAdapter
        from oncutf.ui.adapters.qt_user_interaction import QtCursorAdapter, QtUserDialogAdapter

        self.window.context.register_manager("user_dialog", QtUserDialogAdapter(self.window))
        self.window.context.register_manager("cursor", QtCursorAdapter())
        self.window.context.register_manager("file_load_ui", QtFileLoadUIAdapter(self.window))

        # Initialize singleton managers
        self.window.drag_manager = DragManager.get_instance()
        self.window.unified_rename_engine = UnifiedRenameEngine()
        self.window.file_operations_manager = FileOperationsManager(parent_window=self.window)
        self.window.metadata_staging_manager = MetadataStagingManager(parent=self.window)

        # Set as global instance
        set_metadata_staging_manager(self.window.metadata_staging_manager)

        # Deferred initialization markers
        self.window.status_manager = None
        self.window.metadata_manager = None

        # Database System Initialization
        self.window.db_manager = initialize_database()
        self.window.metadata_cache = get_persistent_metadata_cache()
        self.window.hash_cache = get_persistent_hash_cache()
        self.window.rename_history_manager = get_rename_history_manager()
        self.window.backup_manager = get_backup_manager(str(self.window.db_manager.db_path))

        # Thumbnail System Initialization
        from oncutf.core.thumbnail.thumbnail_manager import ThumbnailManager

        self.window.thumbnail_manager = ThumbnailManager(db_store=self.window.db_manager.thumbnail_store)

        logger.debug("Phase 1: Core infrastructure initialized", extra={"dev_only": True})

    def _phase2_attributes_and_state(self) -> None:
        """Phase 2: Initialize attributes and application state.

        - File model
        - Metadata system
        - Selection manager
        - Icon maps and utilities
        - State tracking attributes
        """
        from oncutf.core.metadata import get_unified_metadata_manager
        from oncutf.core.selection.selection_manager import SelectionManager
        from oncutf.models.file_table_model import FileTableModel

        # Thread attributes
        self.window.metadata_thread = None
        self.window.metadata_worker = None

        # Icon maps
        self.window.metadata_icon_map = load_metadata_icons()
        self.window.preview_icons = load_preview_status_icons()

        # Core models
        self.window.force_extended_metadata = False
        self.window.file_model = FileTableModel(parent_window=self.window)

        # Metadata system
        self.window.metadata_manager = get_unified_metadata_manager(self.window)
        self.window.selection_manager = SelectionManager(parent_window=self.window)

        # Theme setup
        icons_loader = get_icons_loader()
        icons_loader.set_theme("dark")

        # UI state attributes
        self.window.loading_dialog = None
        self.window.results_dialog = None
        self.window.modifier_state = Qt.NoModifier
        self.window.create_colored_icon = create_colored_icon
        self.window.icon_paths = prepare_status_icons()

        # Application state
        self.window.last_action = None
        # Initialize sort state from config (will be loaded from saved preferences)
        self.window.current_sort_column = 2  # Default, will be overridden from config
        self.window.current_sort_order = Qt.AscendingOrder
        self.window.preview_map = {}
        self.window._selection_sync_mode = "normal"
        self.window.pending_completion_dialog = None

        logger.debug("Phase 2: Attributes and state initialized", extra={"dev_only": True})

    def _phase3_ui_setup(self) -> None:
        """Phase 3: Setup user interface.

        - Initialize all managers
        - Setup UI layout (via UIManager)
        - Configure window
        - Setup timers
        """
        from oncutf.controllers.file_load_controller import FileLoadController
        from oncutf.controllers.metadata_controller import MetadataController
        from oncutf.controllers.ui import (
            LayoutController,
            ShortcutController,
            SignalController,
            WindowSetupController,
        )
        from oncutf.core.file import get_file_validation_manager
        from oncutf.core.file.load_manager import FileLoadManager
        from oncutf.core.rename.rename_manager import RenameManager
        from oncutf.ui.boot.bootstrap_manager import BootstrapManager
        from oncutf.ui.drag.drag_cleanup_manager import DragCleanupManager
        from oncutf.ui.events.event_coordinator import EventCoordinator
        from oncutf.ui.managers.column_manager import ColumnManager
        from oncutf.ui.managers.shortcut_manager import ShortcutManager
        from oncutf.ui.managers.splitter_manager import SplitterManager
        from oncutf.ui.managers.table_manager import TableManager
        from oncutf.ui.managers.window_config_manager import WindowConfigManager
        from oncutf.ui.services.dialog_manager import DialogManager
        from oncutf.ui.services.utility_manager import UtilityManager
        from oncutf.utils.shared.json_config_manager import get_app_config_manager

        # Initialize all managers
        self.window.dialog_manager = DialogManager()
        self.window.event_handler_manager = EventCoordinator(self.window)
        self.window.file_load_manager = FileLoadManager(self.window)
        self.window.file_validation_manager = get_file_validation_manager()
        self.window.table_manager = TableManager(self.window)

        # Phase 1A: Initialize FileLoadController (orchestration layer)
        self.window.file_load_controller = FileLoadController(
            file_load_manager=self.window.file_load_manager,
            file_store=self.window.file_model,  # FileTableModel acts as FileStore
            table_manager=self.window.table_manager,
            context=self.window.context,
        )
        logger.info("[Phase1A] FileLoadController initialized", extra={"dev_only": True})

        # Phase 1B: Initialize MetadataController (orchestration layer)
        # Get StructuredMetadataManager from UnifiedMetadataManager
        structured_metadata_mgr = self.window.metadata_manager.structured
        self.window.metadata_controller = MetadataController(
            unified_metadata_manager=self.window.metadata_manager,
            structured_metadata_manager=structured_metadata_mgr,
            app_context=self.window.context,
        )
        logger.info("[Phase1B] MetadataController initialized", extra={"dev_only": True})

        self.window.utility_manager = UtilityManager(self.window)
        self.window.rename_manager = RenameManager(self.window)

        # Phase 1C: Initialize RenameController (orchestration layer)
        from oncutf.controllers.rename_controller import RenameController

        self.window.rename_controller = RenameController(
            unified_rename_engine=self.window.unified_rename_engine,
            rename_manager=self.window.rename_manager,
            file_store=self.window.file_model,  # FileTableModel acts as FileStore
            context=self.window.context,
        )
        logger.info("[Phase1C] RenameController initialized", extra={"dev_only": True})

        # Phase 1D: Initialize MainWindowController (orchestration layer)
        from oncutf.controllers.main_window_controller import MainWindowController

        self.window.main_window_controller = MainWindowController(
            app_context=self.window.context,
            file_load_controller=self.window.file_load_controller,
            metadata_controller=self.window.metadata_controller,
            rename_controller=self.window.rename_controller,
        )
        logger.info("[Phase1D] MainWindowController initialized", extra={"dev_only": True})

        self.window.rename_manager = RenameManager(self.window)
        self.window.drag_cleanup_manager = DragCleanupManager(self.window)
        self.window.shortcut_manager = ShortcutManager(self.window)
        self.window.splitter_manager = SplitterManager(self.window)
        self.window.initialization_manager = BootstrapManager(self.window)
        self.window.column_manager = ColumnManager(self.window)

        # Phase 4A: Initialize UI Handlers (extracted from MainWindow)
        from oncutf.ui.handlers.config_column_handler import ConfigColumnHandler
        from oncutf.ui.handlers.metadata_signal_handler import MetadataSignalHandler
        from oncutf.ui.handlers.shortcut_command_handler import ShortcutCommandHandler
        from oncutf.ui.handlers.shutdown_lifecycle_handler import ShutdownLifecycleHandler
        from oncutf.ui.handlers.window_event_handler import WindowEventHandler

        self.window.shortcut_handler = ShortcutCommandHandler(self.window)
        self.window.metadata_signal_handler = MetadataSignalHandler(self.window)
        self.window.config_column_handler = ConfigColumnHandler(self.window)
        self.window.window_event_handler = WindowEventHandler(self.window)
        self.window.shutdown_handler = ShutdownLifecycleHandler(self.window)
        logger.info("[Phase4A] UI Handlers initialized", extra={"dev_only": True})

        # Config managers
        self.window.config_manager = get_app_config_manager()
        self.window.window_config_manager = WindowConfigManager(self.window)

        # Initialize UI controllers (replaces UIManager)
        self.window.window_setup_controller = WindowSetupController(self.window)
        self.window.layout_controller = LayoutController(self.window)
        self.window.signal_controller = SignalController(self.window)
        self.window.shortcut_controller = ShortcutController(self.window)
        logger.info("[Phase4B] UI Controllers initialized", extra={"dev_only": True})

        # Register managers in context BEFORE UI setup
        # (They are all created by this point)
        self._register_managers_for_ui()

        # Setup UI in correct order (replaces ui_manager.setup_all_ui())
        # Disable updates during setup to prevent flickering
        self.window.setUpdatesEnabled(False)

        self.window.window_setup_controller.setup()
        self.window.layout_controller.setup()
        self.window.signal_controller.setup()
        self.window.shortcut_controller.setup()

        # Re-enable updates after UI is fully constructed
        self.window.setUpdatesEnabled(True)
        logger.info("[Phase4C] UI setup completed via controllers", extra={"dev_only": True})

        logger.debug("Phase 3: UI setup complete", extra={"dev_only": True})

    def _phase4_configuration_and_finalization(self, theme_callback: Any = None) -> None:
        """Phase 4: Apply configuration and finalize.

        Args:
            theme_callback: Optional callback to apply theme before enabling updates

        - Load window configuration
        - Initialize service layer
        - Setup coordinators
        - Register managers in context
        - Connect signals
        - Apply theme (if callback provided)
        - Enable updates

        """
        from oncutf.core.application_service import initialize_application_service
        from oncutf.core.shutdown_coordinator import get_shutdown_coordinator
        from oncutf.ui.events.signal_coordinator import SignalCoordinator
        from oncutf.utils.shared.timer_manager import schedule_resize_adjust

        # Load and apply window configuration
        self.window.window_config_manager.load_window_config()
        self.window._initial_geometry = self.window.geometry()
        self.window.window_config_manager.apply_loaded_config()

        # Ensure initial column sizing
        schedule_resize_adjust(self.window._ensure_initial_column_sizing, 50)

        # Initialize service layer and coordinators
        self.window.app_service = initialize_application_service(self.window)

        from oncutf.core.batch import get_batch_manager

        self.window.batch_manager = get_batch_manager(self.window)

        self.window.signal_coordinator = SignalCoordinator(self.window)
        self.window.shutdown_coordinator = get_shutdown_coordinator()

        # Register remaining managers in context AFTER app_service creation
        self._register_managers_remaining()

        # Register shutdown components
        self.window._register_shutdown_components()

        # Setup all signal connections
        self.window.signal_coordinator.setup_all_signals()

        # Apply theme BEFORE enabling updates (prevents light theme flash)
        if theme_callback:
            logger.debug("Applying theme before enabling updates", extra={"dev_only": True})
            theme_callback(self.window)

        # Enable updates and finalize layout before show()
        self.window.setUpdatesEnabled(True)
        from PyQt5.QtWidgets import QApplication

        QApplication.processEvents()

        logger.info("Phase 4: Configuration and finalization complete", extra={"dev_only": True})

    def _register_managers_for_ui(self) -> None:
        """Register managers needed for UI setup (Phase 3).

        These managers are created before UI setup and must be available
        to the context before setup_all_ui() is called.
        """
        self.window.context.register_manager("dialog", self.window.dialog_manager)
        self.window.context.register_manager("event_handler", self.window.event_handler_manager)
        self.window.context.register_manager("file_load", self.window.file_load_manager)
        self.window.context.register_manager("file_validation", self.window.file_validation_manager)
        self.window.context.register_manager(
            "metadata_staging", self.window.metadata_staging_manager
        )
        self.window.context.register_manager("table", self.window.table_manager)
        self.window.context.register_manager("utility", self.window.utility_manager)
        self.window.context.register_manager("rename", self.window.rename_manager)
        self.window.context.register_manager("drag_cleanup", self.window.drag_cleanup_manager)
        self.window.context.register_manager("shortcut", self.window.shortcut_manager)
        self.window.context.register_manager("splitter", self.window.splitter_manager)
        self.window.context.register_manager("initialization", self.window.initialization_manager)
        self.window.context.register_manager("column", self.window.column_manager)
        self.window.context.register_manager("config", self.window.config_manager)
        self.window.context.register_manager("window_config", self.window.window_config_manager)
        self.window.context.register_manager("thumbnail", self.window.thumbnail_manager)

        logger.debug("UI managers registered in context", extra={"dev_only": True})

    def _register_managers_remaining(self) -> None:
        """Register remaining managers after app_service creation (Phase 4).

        These managers depend on app_service and other Phase 4 components.
        """
        self.window.context.register_manager("app_service", self.window.app_service)
        self.window.context.register_manager("batch", self.window.batch_manager)
        self.window.context.register_manager("signal_coordinator", self.window.signal_coordinator)
        self.window.context.register_manager(
            "shutdown_coordinator", self.window.shutdown_coordinator
        )

        logger.debug("Remaining managers registered in context", extra={"dev_only": True})
