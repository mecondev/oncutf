"""Infrastructure wiring - Concrete implementation registration.

This module is the ONLY place where infra implementations are imported
and registered with app-layer factories. This keeps infra imports
isolated to the boot layer.

Author: Michael Economou
Date: 2026-01-30
"""

from __future__ import annotations

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


def register_infra_factories() -> None:
    """Register infrastructure factories for dependency inversion.

    This must run before any app services are used, as they depend on
    these factories being registered.

    This function imports concrete infra implementations and registers
    them with the app-layer factory registration functions.
    """
    # Import infra implementations (ONLY in boot layer)
    # Import app service registration functions
    from oncutf.app.services.batch_service import register_batch_manager_factory
    from oncutf.app.services.cache_service import (
        register_hash_cache_factory,
        register_metadata_cache_factory,
    )
    from oncutf.app.services.database_service import register_database_manager_factory
    from oncutf.app.services.folder_color_service import (
        register_auto_color_command_factory,
    )
    from oncutf.app.services.rename_history_service import (
        register_database_manager_factory_for_history,
    )
    from oncutf.infra.batch import BatchOperationsManager
    from oncutf.infra.cache.persistent_hash_cache import get_persistent_hash_cache
    from oncutf.infra.cache.persistent_metadata_cache import (
        get_persistent_metadata_cache,
    )
    from oncutf.infra.db.database_manager import get_database_manager
    from oncutf.infra.folder_color_command import AutoColorByFolderCommand

    # Register factories
    register_database_manager_factory(get_database_manager)
    register_database_manager_factory_for_history(get_database_manager)
    register_hash_cache_factory(get_persistent_hash_cache)
    register_metadata_cache_factory(get_persistent_metadata_cache)
    register_batch_manager_factory(BatchOperationsManager)
    register_auto_color_command_factory(AutoColorByFolderCommand)

    logger.debug("[boot] Infra factories registered", extra={"dev_only": True})


def wire_service_registry() -> None:
    """Wire the service registry with concrete implementations.

    Registers protocol implementations in the ServiceRegistry for
    dependency injection throughout the application.
    """
    from oncutf.app.ports.service_registry import configure_default_services
    from oncutf.infra.cache.cached_hash_service import CachedHashService
    from oncutf.infra.external.exiftool_client import ExifToolClient
    from oncutf.infra.filesystem.filesystem_service import FilesystemService

    configure_default_services(
        metadata_service_factory=ExifToolClient,
        hash_service_factory=CachedHashService,
        filesystem_service_factory=FilesystemService,
    )

    logger.debug("[boot] Service registry wired", extra={"dev_only": True})


def get_database_manager_instance() -> object:
    """Get the database manager instance.

    Returns:
        DatabaseManager instance

    """
    from oncutf.infra.db.database_manager import get_database_manager

    return get_database_manager()


def get_hash_cache_instance() -> object:
    """Get the hash cache instance.

    Returns:
        PersistentHashCache instance

    """
    from oncutf.infra.cache.persistent_hash_cache import get_persistent_hash_cache

    return get_persistent_hash_cache()


def get_metadata_cache_instance() -> object:
    """Get the metadata cache instance.

    Returns:
        PersistentMetadataCache instance or None

    """
    from oncutf.infra.cache.persistent_metadata_cache import (
        get_persistent_metadata_cache,
    )

    return get_persistent_metadata_cache()


def get_exiftool_wrapper() -> type:
    """Get the ExifTool wrapper class.

    Returns:
        ExifToolWrapper class (not instance)

    """
    from oncutf.infra.external.exiftool_wrapper import ExifToolWrapper

    return ExifToolWrapper


def create_exiftool_wrapper() -> object:
    """Create a new ExifTool wrapper instance.

    Returns:
        New ExifToolWrapper instance

    """
    from oncutf.infra.external.exiftool_wrapper import ExifToolWrapper

    return ExifToolWrapper()


def get_batch_manager_instance(parent: object = None) -> object:
    """Get the batch manager instance.

    Args:
        parent: Parent object for the batch manager

    Returns:
        BatchOperationsManager instance

    """
    from oncutf.infra.batch import get_batch_manager

    return get_batch_manager(parent)
