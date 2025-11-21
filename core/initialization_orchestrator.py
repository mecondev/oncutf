"""
Module: initialization_orchestrator.py

Author: Michael Economou
Date: 2025-11-21

Orchestrates MainWindow initialization in a structured, maintainable way.
Separates initialization logic from MainWindow class to reduce complexity.

Phase 4 of Application Context Migration: Complete Migration & Cleanup
"""

from typing import TYPE_CHECKING

from core.pyqt_imports import Qt, QTimer
from utils.icon_cache import load_preview_status_icons, prepare_status_icons
from utils.icon_utilities import create_colored_icon
from utils.icons_loader import icons_loader, load_metadata_icons
from utils.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from main_window import MainWindow

logger = get_cached_logger(__name__)


class InitializationOrchestrator:
    """
    Orchestrates MainWindow initialization in phases.

    This class breaks down the complex initialization into logical phases,
    making it easier to understand, maintain, and modify.

    Benefits:
    - Clear initialization phases
    - Reduced MainWindow __init__ complexity
    - Better error handling per phase
    - Easier to add new initialization steps
    """

    def __init__(self, main_window: "MainWindow"):
        """
        Initialize orchestrator with MainWindow reference.

        Args:
            main_window: MainWindow instance being initialized
        """
        self.window = main_window
        logger.debug("InitializationOrchestrator created", extra={"dev_only": True})

    def orchestrate_initialization(self) -> None:
        """
        Orchestrate complete initialization in phases.

        Phases:
        1. Core infrastructure (context, managers, database)
        2. Attributes and state
        3. UI setup
        4. Configuration and finalization
        """
        self._phase1_core_infrastructure()
        self._phase2_attributes_and_state()
        self._phase3_ui_setup()
        self._phase4_configuration_and_finalization()
        logger.info("MainWindow initialization orchestration complete")

    def _phase1_core_infrastructure(self) -> None:
        """
        Phase 1: Initialize core infrastructure.

        - Application context
        - Singleton managers (drag, preview, rename engine)
        - Database system
        - Core managers
        """
        from core.application_context import ApplicationContext
        from core.backup_manager import get_backup_manager
        from core.database_manager import initialize_database
        from core.drag_manager import DragManager
        from core.file_operations_manager import FileOperationsManager
        from core.persistent_hash_cache import get_persistent_hash_cache
        from core.persistent_metadata_cache import get_persistent_metadata_cache
        from core.preview_manager import PreviewManager
        from core.rename_history_manager import get_rename_history_manager
        from core.unified_rename_engine import UnifiedRenameEngine

        # Core Application Context
        self.window.context = ApplicationContext.create_instance(parent=self.window)

        # Initialize singleton managers
        self.window.drag_manager = DragManager.get_instance()
        self.window.preview_manager = PreviewManager(parent_window=self.window)
        self.window.unified_rename_engine = UnifiedRenameEngine()
        self.window.file_operations_manager = FileOperationsManager(parent_window=self.window)

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
        """
        Phase 2: Initialize attributes and application state.

        - File model
        - Metadata system
        - Selection manager
        - Icon maps and utilities
        - State tracking attributes
        """
        from core.selection_manager import SelectionManager
        from core.unified_metadata_manager import get_unified_metadata_manager
        from models.file_table_model import FileTableModel

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
        self.window.modifier_state = Qt.NoModifier  # type: ignore
        self.window.create_colored_icon = create_colored_icon
        self.window.icon_paths = prepare_status_icons()

        # Application state
        self.window.last_action = None
        self.window.current_sort_column = 1
        self.window.current_sort_order = Qt.AscendingOrder  # type: ignore
        self.window.preview_map = {}
        self.window._selection_sync_mode = "normal"
        self.window.pending_completion_dialog = None

        logger.debug("Phase 2: Attributes and state initialized", extra={"dev_only": True})

    def _phase3_ui_setup(self) -> None:
        """
        Phase 3: Setup user interface.

        - Initialize all managers
        - Setup UI layout (via UIManager)
        - Configure window
        - Setup timers
        """
        from core.column_manager import ColumnManager
        from core.dialog_manager import DialogManager
        from core.drag_cleanup_manager import DragCleanupManager
        from core.event_handler_manager import EventHandlerManager
        from core.file_load_manager import FileLoadManager
        from core.file_validation_manager import get_file_validation_manager
        from core.initialization_manager import InitializationManager
        from core.rename_manager import RenameManager
        from core.shortcut_manager import ShortcutManager
        from core.splitter_manager import SplitterManager
        from core.table_manager import TableManager
        from core.ui_manager import UIManager
        from core.utility_manager import UtilityManager
        from core.window_config_manager import WindowConfigManager
        from utils.json_config_manager import get_app_config_manager

        # Initialize all managers
        self.window.dialog_manager = DialogManager()
        self.window.event_handler_manager = EventHandlerManager(self.window)
        self.window.file_load_manager = FileLoadManager(self.window)
        self.window.file_validation_manager = get_file_validation_manager()
        self.window.table_manager = TableManager(self.window)
        self.window.utility_manager = UtilityManager(self.window)
        self.window.rename_manager = RenameManager(self.window)
        self.window.drag_cleanup_manager = DragCleanupManager(self.window)
        self.window.shortcut_manager = ShortcutManager(self.window)
        self.window.splitter_manager = SplitterManager(self.window)
        self.window.initialization_manager = InitializationManager(self.window)
        self.window.column_manager = ColumnManager(self.window)

        # Setup UI
        self.window.ui_manager = UIManager(parent_window=self.window)
        self.window.ui_manager.setup_all_ui()

        # Config managers
        self.window.config_manager = get_app_config_manager()
        self.window.window_config_manager = WindowConfigManager(self.window)

        # Preview update timer
        self.window.preview_update_timer = QTimer(self.window)
        self.window.preview_update_timer.setSingleShot(True)
        self.window.preview_update_timer.setInterval(100)

        logger.debug("Phase 3: UI setup complete", extra={"dev_only": True})

    def _phase4_configuration_and_finalization(self) -> None:
        """
        Phase 4: Apply configuration and finalize.

        - Load window configuration
        - Initialize service layer
        - Setup coordinators
        - Register managers in context
        - Connect signals
        """
        from core.application_service import initialize_application_service
        from core.shutdown_coordinator import get_shutdown_coordinator
        from core.signal_coordinator import SignalCoordinator
        from utils.timer_manager import schedule_resize_adjust

        # Load and apply window configuration
        self.window.window_config_manager.load_window_config()
        self.window._initial_geometry = self.window.geometry()
        self.window.window_config_manager.apply_loaded_config()

        # Ensure initial column sizing
        schedule_resize_adjust(self.window._ensure_initial_column_sizing, 50)

        # Initialize service layer and coordinators
        self.window.app_service = initialize_application_service(self.window)

        from core.batch_operations_manager import get_batch_manager

        self.window.batch_manager = get_batch_manager(self.window)

        self.window.signal_coordinator = SignalCoordinator(self.window)
        self.window.shutdown_coordinator = get_shutdown_coordinator()

        # Register shutdown components
        self.window._register_shutdown_components()

        # Register all managers in context
        self.window._register_managers_in_context()

        # Setup all signal connections
        self.window.signal_coordinator.setup_all_signals()

        logger.info("Phase 4: Configuration and finalization complete", extra={"dev_only": True})
