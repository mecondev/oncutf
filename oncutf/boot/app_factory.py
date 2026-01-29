"""Application factory - Creates fully configured application.

This module provides the main entry point for creating a configured
application instance. UI code should use create_app() to get a
fully-wired application without importing infra directly.

Author: Michael Economou
Date: 2026-01-30
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from oncutf.boot.infra_wiring import (
    get_hash_cache_instance,
    get_metadata_cache_instance,
    register_infra_factories,
    wire_service_registry,
)
from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.ui.adapters.application_context import ApplicationContext

logger = get_cached_logger(__name__)


class AppComponents:
    """Container for core application components.

    This class holds references to the main infrastructure components
    needed by the application, obtained via the boot layer.
    """

    def __init__(self) -> None:
        """Initialize app components container."""
        self.db_manager: Any = None
        self.metadata_cache: Any = None
        self.hash_cache: Any = None
        self.backup_manager: Any = None
        self.rename_history_manager: Any = None


def create_app_context(parent: Any = None) -> ApplicationContext:
    """Create and configure the ApplicationContext.

    This is the main entry point for UI code to get a configured
    application context without importing infra directly.

    Args:
        parent: Optional parent QObject

    Returns:
        Configured ApplicationContext instance

    """
    # First, register all infra factories
    register_infra_factories()
    wire_service_registry()

    # Create the context
    from oncutf.ui.adapters.application_context import ApplicationContext

    context = ApplicationContext.create_instance(parent=parent)

    logger.info("[boot] Application context created")
    return context


def create_app() -> AppComponents:
    """Create a fully configured application with all components.

    This function:
    1. Registers infra factories with app services
    2. Wires the service registry
    3. Initializes database and caches
    4. Returns container with all components

    Returns:
        AppComponents with all infrastructure wired

    """
    # Register factories first
    register_infra_factories()
    wire_service_registry()

    # Initialize core infrastructure
    from oncutf.app.services import get_rename_history_manager
    from oncutf.core.backup_manager import get_backup_manager
    from oncutf.core.database import initialize_database

    components = AppComponents()

    # Database and caches
    components.db_manager = initialize_database()
    components.metadata_cache = get_metadata_cache_instance()
    components.hash_cache = get_hash_cache_instance()

    # Managers
    components.rename_history_manager = get_rename_history_manager()
    components.backup_manager = get_backup_manager(str(components.db_manager.db_path))

    logger.info("[boot] Application created with all components")
    return components


def initialize_infrastructure() -> None:
    """Initialize infrastructure without creating full app.

    Useful for tests or scripts that need infrastructure
    but not the full UI application.
    """
    register_infra_factories()
    wire_service_registry()
    logger.debug("[boot] Infrastructure initialized", extra={"dev_only": True})
