"""Service registry for dependency injection.

Author: Michael Economou
Date: December 18, 2025

This module provides a simple service locator pattern for dependency injection.
Services can be registered by their protocol type and retrieved later.

Usage:
    from oncutf.services.registry import ServiceRegistry, get_service_registry
    from oncutf.services.interfaces import MetadataServiceProtocol
    from oncutf.services.exiftool_service import ExifToolService

    # Register a service
    registry = get_service_registry()
    registry.register(MetadataServiceProtocol, ExifToolService())

    # Retrieve a service
    metadata_service = registry.get(MetadataServiceProtocol)
"""

from __future__ import annotations

from typing import Any, ClassVar, TypeVar

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)

T = TypeVar("T")


class ServiceRegistry:
    """Simple service locator for dependency injection.

    Provides registration and retrieval of services by their protocol types.
    Supports singleton pattern for global access.

    Thread-safety note: This implementation is not thread-safe. For multi-threaded
    scenarios, external synchronization should be used.
    """

    _instance: ClassVar[ServiceRegistry | None] = None

    def __init__(self) -> None:
        """Initialize the service registry."""
        self._services: dict[type, Any] = {}
        self._factories: dict[type, Any] = {}

    @classmethod
    def instance(cls) -> ServiceRegistry:
        """Get the singleton instance of ServiceRegistry.

        Returns:
            The global ServiceRegistry instance.

        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (useful for testing)."""
        cls._instance = None

    def register(self, protocol: type[Any], implementation: Any) -> None:
        """Register a service implementation for a protocol.

        Args:
            protocol: The protocol/interface type.
            implementation: The concrete implementation instance.

        """
        self._services[protocol] = implementation
        logger.debug(
            "Registered service: %s -> %s",
            protocol.__name__,
            type(implementation).__name__,
        )

    def register_factory(self, protocol: type[Any], factory: Any) -> None:
        """Register a factory for lazy instantiation.

        The factory will be called to create the service on first access.

        Args:
            protocol: The protocol/interface type.
            factory: A callable that returns an implementation instance,
                     or a class to instantiate.

        """
        self._factories[protocol] = factory
        logger.debug(
            "Registered factory for: %s",
            protocol.__name__,
        )

    def get(self, protocol: type[Any]) -> Any | None:
        """Get a service implementation for a protocol.

        Args:
            protocol: The protocol/interface type.

        Returns:
            The registered implementation, or None if not found.

        """
        # Check direct registrations first
        if protocol in self._services:
            service: Any = self._services[protocol]
            return service

        # Check factories
        if protocol in self._factories:
            factory: Any = self._factories[protocol]
            implementation: Any = factory()
            self._services[protocol] = implementation
            del self._factories[protocol]
            logger.debug(
                "Created service from factory: %s -> %s",
                protocol.__name__,
                type(implementation).__name__,
            )
            return implementation

        logger.warning("No service registered for: %s", protocol.__name__)
        return None

    def get_required(self, protocol: type[Any]) -> Any:
        """Get a service implementation, raising if not found.

        Args:
            protocol: The protocol/interface type.

        Returns:
            The registered implementation.

        Raises:
            KeyError: If no service is registered for the protocol.

        """
        service = self.get(protocol)
        if service is None:
            raise KeyError(f"No service registered for: {protocol.__name__}")
        return service

    def has(self, protocol: type) -> bool:
        """Check if a service is registered for a protocol.

        Args:
            protocol: The protocol/interface type.

        Returns:
            True if a service or factory is registered.

        """
        return protocol in self._services or protocol in self._factories

    def unregister(self, protocol: type) -> bool:
        """Unregister a service.

        Args:
            protocol: The protocol/interface type.

        Returns:
            True if a service was unregistered, False if none existed.

        """
        removed = False
        if protocol in self._services:
            del self._services[protocol]
            removed = True
        if protocol in self._factories:
            del self._factories[protocol]
            removed = True

        if removed:
            logger.debug("Unregistered service: %s", protocol.__name__)
        return removed

    def clear(self) -> None:
        """Clear all registered services."""
        self._services.clear()
        self._factories.clear()
        logger.debug("Cleared all services")

    def list_services(self) -> list[str]:
        """List all registered service protocol names.

        Returns:
            List of protocol names.

        """
        registered = set(self._services.keys()) | set(self._factories.keys())
        return [p.__name__ for p in registered]


def get_service_registry() -> ServiceRegistry:
    """Get the global service registry instance.

    This is a convenience function for accessing the singleton.

    Returns:
        The global ServiceRegistry instance.

    """
    return ServiceRegistry.instance()


def configure_default_services(registry: ServiceRegistry | None = None) -> None:
    """Configure default service implementations.

    This function registers the standard service implementations.
    Call this during application startup.

    Args:
        registry: Optional registry to configure. Uses global if None.

    """
    if registry is None:
        registry = get_service_registry()

    # Import protocols and implementations
    from oncutf.services.cached_hash_service import CachedHashService
    from oncutf.services.exiftool_service import ExifToolService
    from oncutf.services.filesystem_service import FilesystemService
    from oncutf.services.interfaces import (
        FilesystemServiceProtocol,
        HashServiceProtocol,
        MetadataServiceProtocol,
    )

    # Register default implementations using factories for lazy init
    registry.register_factory(MetadataServiceProtocol, ExifToolService)
    registry.register_factory(HashServiceProtocol, CachedHashService)
    registry.register_factory(FilesystemServiceProtocol, FilesystemService)

    logger.debug("Default services configured")
