"""
Tests for ServiceRegistry.

Author: Michael Economou
Date: December 18, 2025

Tests the service registry for dependency injection.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import pytest

from oncutf.services.registry import (
    ServiceRegistry,
    configure_default_services,
    get_service_registry,
)


@runtime_checkable
class MockProtocol(Protocol):
    """Mock protocol for testing."""

    def do_something(self) -> str:
        ...


class MockImplementation:
    """Mock implementation for testing."""

    def do_something(self) -> str:
        return "done"


class TestServiceRegistryBasics:
    """Tests for basic registry operations."""

    def test_register_and_get(self) -> None:
        """Test basic register and get."""
        registry = ServiceRegistry()
        impl = MockImplementation()

        registry.register(MockProtocol, impl)
        result = registry.get(MockProtocol)

        assert result is impl

    def test_get_unregistered_returns_none(self) -> None:
        """Test that get returns None for unregistered protocol."""
        registry = ServiceRegistry()

        result = registry.get(MockProtocol)

        assert result is None

    def test_get_required_raises_for_unregistered(self) -> None:
        """Test that get_required raises KeyError."""
        registry = ServiceRegistry()

        with pytest.raises(KeyError, match="MockProtocol"):
            registry.get_required(MockProtocol)

    def test_has_returns_true_for_registered(self) -> None:
        """Test has() returns True for registered service."""
        registry = ServiceRegistry()
        registry.register(MockProtocol, MockImplementation())

        assert registry.has(MockProtocol) is True

    def test_has_returns_false_for_unregistered(self) -> None:
        """Test has() returns False for unregistered service."""
        registry = ServiceRegistry()

        assert registry.has(MockProtocol) is False


class TestServiceRegistryFactory:
    """Tests for factory registration."""

    def test_register_factory(self) -> None:
        """Test factory registration."""
        registry = ServiceRegistry()
        call_count = 0

        def factory() -> MockImplementation:
            nonlocal call_count
            call_count += 1
            return MockImplementation()

        registry.register_factory(MockProtocol, factory)

        # Factory not called yet
        assert call_count == 0

        # First get calls factory
        result1 = registry.get(MockProtocol)
        assert call_count == 1
        assert isinstance(result1, MockImplementation)

        # Second get uses cached instance
        result2 = registry.get(MockProtocol)
        assert call_count == 1
        assert result1 is result2

    def test_register_factory_with_class(self) -> None:
        """Test factory registration with class."""
        registry = ServiceRegistry()

        registry.register_factory(MockProtocol, MockImplementation)
        result = registry.get(MockProtocol)

        assert isinstance(result, MockImplementation)

    def test_has_returns_true_for_factory(self) -> None:
        """Test has() returns True for factory registration."""
        registry = ServiceRegistry()
        registry.register_factory(MockProtocol, MockImplementation)

        assert registry.has(MockProtocol) is True


class TestServiceRegistryUnregister:
    """Tests for unregistration."""

    def test_unregister_service(self) -> None:
        """Test unregistering a service."""
        registry = ServiceRegistry()
        registry.register(MockProtocol, MockImplementation())

        result = registry.unregister(MockProtocol)

        assert result is True
        assert registry.has(MockProtocol) is False

    def test_unregister_nonexistent(self) -> None:
        """Test unregistering non-existent service."""
        registry = ServiceRegistry()

        result = registry.unregister(MockProtocol)

        assert result is False

    def test_clear(self) -> None:
        """Test clearing all services."""
        registry = ServiceRegistry()
        registry.register(MockProtocol, MockImplementation())

        registry.clear()

        assert registry.has(MockProtocol) is False


class TestServiceRegistryListServices:
    """Tests for listing services."""

    def test_list_services(self) -> None:
        """Test listing registered services."""
        registry = ServiceRegistry()
        registry.register(MockProtocol, MockImplementation())

        services = registry.list_services()

        assert "MockProtocol" in services


class TestServiceRegistrySingleton:
    """Tests for singleton pattern."""

    def test_instance_returns_same_object(self) -> None:
        """Test that instance() returns same object."""
        ServiceRegistry.reset_instance()

        instance1 = ServiceRegistry.instance()
        instance2 = ServiceRegistry.instance()

        assert instance1 is instance2

    def test_reset_instance(self) -> None:
        """Test reset_instance creates new instance."""
        ServiceRegistry.reset_instance()
        instance1 = ServiceRegistry.instance()

        ServiceRegistry.reset_instance()
        instance2 = ServiceRegistry.instance()

        assert instance1 is not instance2


class TestGetServiceRegistry:
    """Tests for get_service_registry helper."""

    def test_returns_singleton(self) -> None:
        """Test that get_service_registry returns singleton."""
        ServiceRegistry.reset_instance()

        registry1 = get_service_registry()
        registry2 = get_service_registry()

        assert registry1 is registry2


class TestConfigureDefaultServices:
    """Tests for default service configuration."""

    def test_configures_metadata_service(self) -> None:
        """Test that metadata service is configured."""
        registry = ServiceRegistry()
        configure_default_services(registry)

        from oncutf.services.interfaces import MetadataServiceProtocol

        assert registry.has(MetadataServiceProtocol)

    def test_configures_hash_service(self) -> None:
        """Test that hash service is configured."""
        registry = ServiceRegistry()
        configure_default_services(registry)

        from oncutf.services.interfaces import HashServiceProtocol

        assert registry.has(HashServiceProtocol)

    def test_configures_filesystem_service(self) -> None:
        """Test that filesystem service is configured."""
        registry = ServiceRegistry()
        configure_default_services(registry)

        from oncutf.services.interfaces import FilesystemServiceProtocol

        assert registry.has(FilesystemServiceProtocol)

    def test_uses_global_registry_if_none_provided(self) -> None:
        """Test that configure uses global registry when None."""
        ServiceRegistry.reset_instance()
        configure_default_services()

        from oncutf.services.interfaces import MetadataServiceProtocol

        assert get_service_registry().has(MetadataServiceProtocol)
