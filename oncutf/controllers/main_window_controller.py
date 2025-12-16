"""
Module: main_window_controller.py

Author: Michael Economou
Date: 2025-12-16

MainWindowController: High-level orchestration controller.

This controller coordinates all sub-controllers (FileLoad, Metadata, Rename)
and manages complex workflows that involve multiple domains. It handles:
- Multi-controller workflows (e.g., load files → load metadata)
- Application-level state coordination
- Complex user actions that span multiple domains
- Event propagation between controllers

The controller is UI-agnostic and focuses on orchestration logic.

Architecture:
    MainWindow (UI) → MainWindowController (orchestration)
                    ├→ FileLoadController (file operations)
                    ├→ MetadataController (metadata operations)
                    └→ RenameController (rename operations)

Each controller is UI-agnostic and testable independently.
MainWindowController coordinates complex workflows that span multiple domains.
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from oncutf.controllers.file_load_controller import FileLoadController
    from oncutf.controllers.metadata_controller import MetadataController
    from oncutf.controllers.rename_controller import RenameController
    from oncutf.core.application_context import ApplicationContext

logger = logging.getLogger(__name__)


class MainWindowController:
    """
    High-level orchestration controller.

    Coordinates FileLoadController, MetadataController, and RenameController
    to handle complex workflows that span multiple domains.

    Responsibilities:
    - Orchestrate multi-step workflows
    - Coordinate between sub-controllers
    - Manage application-level state
    - Handle complex user actions

    This controller does NOT:
    - Interact directly with UI widgets
    - Contain domain-specific logic (that's in sub-controllers)
    - Duplicate logic from sub-controllers

    Attributes:
        _app_context: Application context with shared services
        _file_load_controller: Controller for file loading operations
        _metadata_controller: Controller for metadata operations
        _rename_controller: Controller for rename operations
    """

    def __init__(
        self,
        app_context: "ApplicationContext",
        file_load_controller: "FileLoadController",
        metadata_controller: "MetadataController",
        rename_controller: "RenameController",
    ) -> None:
        """
        Initialize MainWindowController.

        Args:
            app_context: Application context with shared services
            file_load_controller: Controller for file loading operations
            metadata_controller: Controller for metadata operations
            rename_controller: Controller for rename operations
        """
        self._app_context = app_context
        self._file_load_controller = file_load_controller
        self._metadata_controller = metadata_controller
        self._rename_controller = rename_controller

        logger.info("[MainWindowController] Initialized")

    # Orchestration methods will be added in next steps
