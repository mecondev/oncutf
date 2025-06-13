"""
InitializationManager - Handles initialization and setup operations

Author: Michael Economou
Date: 2025-01-27

This manager centralizes initialization and setup operations including:
- Metadata status display
- SelectionStore mode initialization
- Application component setup
- Status and display management
"""

from typing import TYPE_CHECKING

from utils.logger_helper import get_logger

if TYPE_CHECKING:
    from main_window import MainWindow

logger = get_logger(__name__)


class InitializationManager:
    """
    Manages initialization and setup operations for the main window.

    This manager handles:
    - Metadata status display logic
    - SelectionStore mode initialization
    - Application component setup
    - Status and display management
    """

    def __init__(self, main_window: 'MainWindow'):
        """
        Initialize the InitializationManager.

        Args:
            main_window: Reference to the main window instance
        """
        self.main_window = main_window
        logger.debug("[InitializationManager] Initialized", extra={"dev_only": True})

    def show_metadata_status(self) -> None:
        """
        Shows a status bar message indicating the number of loaded files
        and the type of metadata scan performed (skipped, basic, extended).
        """
        num_files = len(self.main_window.file_model.files)
        self.main_window.status_manager.show_metadata_status(
            num_files,
            self.main_window.skip_metadata_mode,
            self.main_window.force_extended_metadata
        )

    def enable_selection_store_mode(self):
        """Enable SelectionStore mode in FileTableView once ApplicationContext is ready."""
        try:
            self.main_window.file_table_view.enable_selection_store_mode()

            # Connect SelectionStore signals to MainWindow handlers
            from core.application_context import get_app_context
            context = get_app_context()
            if context and context.selection_store:
                # Connect selection changed signal to existing preview update
                context.selection_store.selection_changed.connect(self.main_window.update_preview_from_selection)
                logger.debug("[MainWindow] Connected SelectionStore signals", extra={"dev_only": True})

            logger.info("[MainWindow] SelectionStore mode enabled in FileTableView")
        except Exception as e:
            logger.warning(f"[MainWindow] Failed to enable SelectionStore mode: {e}")

    def update_status_from_preview(self, status_html: str) -> None:
        """
        Updates status from preview widgets.
        Delegates to PreviewManager for status updates from preview.
        """
        self.main_window.preview_manager.update_status_from_preview(status_html)

    def setup_application_components(self) -> None:
        """
        Setup and initialize application components.
        This can be extended with other initialization logic.
        """
        logger.debug("[InitializationManager] Setting up application components", extra={"dev_only": True})

        # Enable SelectionStore mode
        self.enable_selection_store_mode()

        # Additional setup can be added here
        logger.debug("[InitializationManager] Application components setup completed", extra={"dev_only": True})

    def get_initialization_status(self) -> dict:
        """
        Get current initialization status.

        Returns:
            Dictionary with initialization status information
        """
        return {
            "has_files": len(self.main_window.file_model.files) > 0,
            "current_folder": self.main_window.current_folder_path,
            "skip_metadata_mode": self.main_window.skip_metadata_mode,
            "force_extended_metadata": self.main_window.force_extended_metadata,
            "has_status_manager": self.main_window.status_manager is not None,
            "has_file_table_view": hasattr(self.main_window, 'file_table_view')
        }

    def validate_initialization(self) -> bool:
        """
        Validate that all required components are properly initialized.

        Returns:
            True if initialization is valid, False otherwise
        """
        required_components = [
            'status_manager',
            'file_model',
            'file_table_view',
            'preview_manager'
        ]

        for component in required_components:
            if not hasattr(self.main_window, component) or getattr(self.main_window, component) is None:
                logger.warning(f"[InitializationManager] Missing required component: {component}")
                return False

        logger.debug("[InitializationManager] All required components are initialized", extra={"dev_only": True})
        return True
