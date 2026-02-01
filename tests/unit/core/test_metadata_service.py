"""Tests for MetadataService implementation.

Author: Michael Economou
Date: February 1, 2026

Tests verify that MetadataService correctly delegates to UnifiedMetadataManager
and properly manages staging operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, Mock, patch

import pytest

from oncutf.core.metadata.metadata_service import MetadataService, get_metadata_service

if TYPE_CHECKING:
    from oncutf.core.metadata.unified_metadata_protocol import (
        UnifiedMetadataManagerProtocol,
    )


@pytest.fixture
def mock_unified_manager() -> Mock:
    """Create a mock UnifiedMetadataManager."""
    manager = Mock(spec=["get_structured_metadata", "get_field_value"])
    manager.get_structured_metadata.return_value = {
        "Title": "Test Title",
        "Artist": "Test Artist",
        "Album": "Test Album",
    }
    manager.get_field_value.return_value = "Test Value"
    return manager


@pytest.fixture
def metadata_service(mock_unified_manager: Mock) -> MetadataService:
    """Create a MetadataService instance with mocked dependencies."""
    return MetadataService(unified_manager=mock_unified_manager)


class TestMetadataServiceDelegation:
    """Test MetadataService delegation to UnifiedMetadataManager."""

    def test_get_metadata_delegates_to_unified_manager(
        self, metadata_service: MetadataService, mock_unified_manager: Mock
    ) -> None:
        """Test get_metadata delegates to unified_manager.get_structured_metadata."""
        test_path = "/test/file.mp3"
        result = metadata_service.get_metadata(test_path)

        mock_unified_manager.get_structured_metadata.assert_called_once_with(test_path)
        assert result == {
            "Title": "Test Title",
            "Artist": "Test Artist",
            "Album": "Test Album",
        }

    def test_get_field_delegates_to_unified_manager(
        self, metadata_service: MetadataService, mock_unified_manager: Mock
    ) -> None:
        """Test get_field delegates to unified_manager.get_field_value."""
        test_path = "/test/file.mp3"
        test_key = "Title"
        result = metadata_service.get_field(test_path, test_key)

        mock_unified_manager.get_field_value.assert_called_once_with(test_path, test_key)
        assert result == "Test Value"

    def test_get_metadata_returns_empty_dict_when_no_metadata(
        self, metadata_service: MetadataService, mock_unified_manager: Mock
    ) -> None:
        """Test get_metadata returns empty dict when no metadata exists."""
        mock_unified_manager.get_structured_metadata.return_value = {}
        test_path = "/test/file.mp3"
        result = metadata_service.get_metadata(test_path)

        assert result == {}

    def test_get_field_returns_none_when_field_not_found(
        self, metadata_service: MetadataService, mock_unified_manager: Mock
    ) -> None:
        """Test get_field returns None when field doesn't exist."""
        mock_unified_manager.get_field_value.return_value = None
        test_path = "/test/file.mp3"
        test_key = "NonExistentKey"
        result = metadata_service.get_field(test_path, test_key)

        assert result is None


class TestMetadataServiceStagingOperations:
    """Test MetadataService staging manager operations."""

    def test_get_staged_value_returns_staged_data(self, metadata_service: MetadataService) -> None:
        """Test get_staged_value returns staged changes."""
        test_path = "/test/file.mp3"
        test_key = "Title"
        expected_value = "Staged Title"

        mock_staging = Mock()
        mock_staging.get_staged_changes.return_value = {test_key: expected_value}
        metadata_service._staging_manager = mock_staging

        result = metadata_service.get_staged_value(test_path, test_key)

        mock_staging.get_staged_changes.assert_called_once_with(test_path)
        assert result == expected_value

    def test_get_staged_value_returns_none_when_no_changes(
        self, metadata_service: MetadataService
    ) -> None:
        """Test get_staged_value returns None when no staged changes."""
        test_path = "/test/file.mp3"
        test_key = "Title"

        mock_staging = Mock()
        mock_staging.get_staged_changes.return_value = None
        metadata_service._staging_manager = mock_staging

        result = metadata_service.get_staged_value(test_path, test_key)

        assert result is None

    def test_has_staged_changes_delegates_to_staging_manager(
        self, metadata_service: MetadataService
    ) -> None:
        """Test has_staged_changes delegates correctly."""
        test_path = "/test/file.mp3"

        mock_staging = Mock()
        mock_staging.has_staged_changes.return_value = True
        metadata_service._staging_manager = mock_staging

        result = metadata_service.has_staged_changes(test_path)

        mock_staging.has_staged_changes.assert_called_once_with(test_path)
        assert result is True

    def test_clear_staged_changes_for_specific_file(
        self, metadata_service: MetadataService
    ) -> None:
        """Test clear_staged_changes for a specific file."""
        test_path = "/test/file.mp3"

        mock_staging = Mock()
        metadata_service._staging_manager = mock_staging

        metadata_service.clear_staged_changes(test_path)

        mock_staging.clear_staged_changes.assert_called_once_with(test_path)
        mock_staging.clear_all.assert_not_called()

    def test_clear_staged_changes_for_all_files(self, metadata_service: MetadataService) -> None:
        """Test clear_staged_changes clears all files when path is None."""
        mock_staging = Mock()
        metadata_service._staging_manager = mock_staging

        metadata_service.clear_staged_changes(None)

        mock_staging.clear_all.assert_called_once()
        mock_staging.clear_staged_changes.assert_not_called()


class TestMetadataServiceSingleton:
    """Test MetadataService singleton pattern."""

    def test_get_metadata_service_requires_manager_on_first_call(self) -> None:
        """Test get_metadata_service raises error if manager not provided on first call."""
        # Reset singleton
        import oncutf.core.metadata.metadata_service as service_module

        service_module._metadata_service = None

        with pytest.raises(RuntimeError, match="UnifiedMetadataManager must be provided"):
            get_metadata_service()

    def test_get_metadata_service_returns_singleton(self, mock_unified_manager: Mock) -> None:
        """Test get_metadata_service returns same instance on subsequent calls."""
        # Reset singleton
        import oncutf.core.metadata.metadata_service as service_module

        service_module._metadata_service = None

        # First call with manager
        service1 = get_metadata_service(unified_manager=mock_unified_manager)

        # Second call without manager
        service2 = get_metadata_service()

        assert service1 is service2

    def test_get_metadata_service_ignores_manager_after_initialization(
        self, mock_unified_manager: Mock
    ) -> None:
        """Test get_metadata_service ignores manager parameter after first initialization."""
        # Reset singleton
        import oncutf.core.metadata.metadata_service as service_module

        service_module._metadata_service = None

        # First call with manager
        service1 = get_metadata_service(unified_manager=mock_unified_manager)

        # Second call with different manager (should be ignored)
        different_manager = Mock()
        service2 = get_metadata_service(unified_manager=different_manager)

        # Should return same service, not create new one
        assert service1 is service2
        assert service1.unified_manager is mock_unified_manager
        assert service1.unified_manager is not different_manager


class TestMetadataServiceCommandCreation:
    """Test MetadataService command factory methods."""

    def test_create_edit_command(self, metadata_service: MetadataService) -> None:
        """Test create_edit_command creates proper command instance."""
        test_path = "/test/file.mp3"
        test_key = "Title"
        new_value = "New Title"
        old_value = "Old Title"

        command = metadata_service.create_edit_command(test_path, test_key, new_value, old_value)

        from oncutf.core.metadata.commands import EditMetadataFieldCommand

        assert isinstance(command, EditMetadataFieldCommand)
        assert command.file_path == test_path
        assert command.field_path == test_key
        assert command.new_value == new_value
        assert command.old_value == old_value

    def test_create_reset_command(self, metadata_service: MetadataService) -> None:
        """Test create_reset_command creates proper command instance."""
        test_path = "/test/file.mp3"
        test_key = "Title"
        staged_value = "Staged Title"
        original_value = "Original Title"

        command = metadata_service.create_reset_command(
            test_path, test_key, staged_value, original_value
        )

        from oncutf.core.metadata.commands import ResetMetadataFieldCommand

        assert isinstance(command, ResetMetadataFieldCommand)
        assert command.file_path == test_path
        assert command.field_path == test_key
        assert command.current_value == staged_value
        assert command.original_value == original_value
