"""Module: initialization_orchestrator.py

Author: Michael Economou
Date: 2025-11-21

Orchestrates MainWindow initialization in a structured, maintainable way.
Separates initialization logic from MainWindow class to reduce complexity.
"""

from typing import TYPE_CHECKING

from oncutf.core.pyqt_imports import Qt, QTimer
from oncutf.utils.icon_cache import load_preview_status_icons, prepare_status_icons
from oncutf.utils.icon_utilities import create_colored_icon
from oncutf.utils.icons_loader import icons_loader, load_metadata_icons
from oncutf.utils.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.ui.main_window import MainWindow

logger = get_cached_logger(__name__)


class InitializationOrchestrator:
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
        logger.debug("InitializationOrchestrator created", extra={"dev_only": True})

    def orchestrate_initialization(self, theme_callback=None) -> None:
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
        logger.info("MainWindow initialization orchestration complete")

    def _phase1_core_infrastructure(self) -> None:
        """Phase 1: Initialize core infrastructure.

        - Application context
        - Singleton managers (drag, preview, rename engine)
        - Database system
        - Core managers
        """
        from oncutf.core.application_context import ApplicationContext
        from oncutf.core.backup_manager import get_backup_manager
        from oncutf.core.cache.persistent_hash_cache import get_persistent_hash_cache
        from oncutf.core.cache.persistent_metadata_cache import get_persistent_metadata_cache
        from oncutf.core.database.database_manager import initialize_database
        from oncutf.core.drag.drag_manager import DragManager
        from oncutf.core.file_operations_manager import FileOperationsManager
        from oncutf.core.metadata_staging_manager import (
            MetadataStagingManager,
            set_metadata_staging_manager,
        )
        from oncutf.core.preview_manager import PreviewManager
        from oncutf.core.rename.rename_history_manager import get_rename_history_manager
        from oncutf.core.rename.unified_rename_engine import UnifiedRenameEngine

        # Core Application Context
        self.window.context = ApplicationContext.create_instance(parent=self.window)

        # Initialize singleton managers
        self.window.drag_manager = DragManager.get_instance()
        self.window.preview_manager = PreviewManager(parent_window=self.window)
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

        logger.debug("Phase 1: Core infrastructure initialized", extra={"dev_only": True})

    def _phase2_attributes_and_state(self) -> None:
        """Phase 2: Initialize attributes and application state.

        - File model
        - Metadata system
        - Selection manager
        - Icon maps and utilities
        - State tracking attributes
        """
        from oncutf.core.selection.selection_manager import SelectionManager
        from oncutf.core.unified_metadata_manager import get_unified_metadata_manager
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
        self.window.metadata_manager.initialize_cache_helper()
        self.window.selection_manager = SelectionManager(parent_window=self.window)

        # Theme setup
        icons_loader.set_theme("dark")

        # UI state attributes
        self.window.loading_dialog = None
        self.window.results_dialog = None
        self.window.modifier_state = Qt.NoModifier  # type: ignore
        self.window.create_colored_icon = create_colored_icon
        self.window.icon_paths = prepare_status_icons()

        # Application state
        self.window.last_action = None
        # TODO: When last_state restoration is implemented, restore saved sort column
        # For now, default to filename column (index 2) instead of color (index 1)
        self.window.current_sort_column = 2
        self.window.current_sort_order = Qt.AscendingOrder  # type: ignore
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
        from oncutf.core.dialog_manager import DialogManager
        from oncutf.core.drag.drag_cleanup_manager import DragCleanupManager
        from oncutf.core.event_handler_manager import EventHandlerManager
        from oncutf.core.file_load_manager import FileLoadManager
        from oncutf.core.file_validation_manager import get_file_validation_manager
        from oncutf.core.initialization.initialization_manager import InitializationManager
        from oncutf.core.rename.rename_manager import RenameManager
        from oncutf.core.ui_managers.column_manager import ColumnManager
        from oncutf.core.ui_managers.shortcut_manager import ShortcutManager
        from oncutf.core.ui_managers.splitter_manager import SplitterManager
        from oncutf.core.ui_managers.table_manager import TableManager
        from oncutf.core.ui_managers.ui_manager import UIManager
        from oncutf.core.ui_managers.window_config_manager import WindowConfigManager
        from oncutf.core.utility_manager import UtilityManager
        from oncutf.utils.json_config_manager import get_app_config_manager

        # Initialize all managers
        self.window.dialog_manager = DialogManager()
        self.window.event_handler_manager = EventHandlerManager(self.window)
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
            preview_manager=self.window.preview_manager,
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
        self.window.initialization_manager = InitializationManager(self.window)
        self.window.column_manager = ColumnManager(self.window)

        # Config managers
        self.window.config_manager = get_app_config_manager()
        self.window.window_config_manager = WindowConfigManager(self.window)

        # Create UIManager (but don't setup UI yet)
        self.window.ui_manager = UIManager(parent_window=self.window)

        # Register managers in context BEFORE setup_all_ui
        # (They are all created by this point)
        self._register_managers_for_ui()

        # Setup UI (now managers are available via context)
        self.window.ui_manager.setup_all_ui()

        # Preview update timer
        self.window.preview_update_timer = QTimer(self.window)
        self.window.preview_update_timer.setSingleShot(True)
        self.window.preview_update_timer.setInterval(100)

        logger.debug("Phase 3: UI setup complete", extra={"dev_only": True})

    def _phase4_configuration_and_finalization(self, theme_callback=None) -> None:
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
        from oncutf.core.signal_coordinator import SignalCoordinator
        from oncutf.utils.timer_manager import schedule_resize_adjust

        # Load and apply window configuration
        self.window.window_config_manager.load_window_config()
        self.window._initial_geometry = self.window.geometry()
        self.window.window_config_manager.apply_loaded_config()

        # Ensure initial column sizing
        schedule_resize_adjust(self.window._ensure_initial_column_sizing, 50)

        # Initialize service layer and coordinators
        self.window.app_service = initialize_application_service(self.window)

        from oncutf.core.batch_operations_manager import get_batch_manager

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
        from oncutf.core.pyqt_imports import QApplication

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
