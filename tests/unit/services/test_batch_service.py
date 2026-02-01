"""Tests for BatchService implementation.

Author: Michael Economou
Date: February 1, 2026

Tests verify that BatchService correctly delegates to BatchOperationsManager
and provides a clean UI-friendly API for batch operations.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from oncutf.app.services.batch_service import BatchService, get_batch_service


@pytest.fixture
def mock_batch_manager() -> Mock:
    """Create a mock BatchOperationsManager."""
    manager = Mock()
    manager.queue_metadata_set = Mock()
    manager.queue_hash_store = Mock()
    manager.queue_file_operation = Mock()
    manager.flush_all = Mock(return_value={"metadata_set": 5, "hash_store": 3})
    manager.get_pending_operations = Mock(return_value={"metadata_set": 2, "hash_store": 1})

    # Mock stats object
    stats = Mock()
    stats.total_operations = 100
    stats.batched_operations = 95
    stats.batch_flushes = 10
    stats.average_batch_size = 9.5
    stats.total_time_saved = 0.5
    manager.get_stats = Mock(return_value=stats)

    return manager


@pytest.fixture
def batch_service(mock_batch_manager: Mock) -> BatchService:
    """Create a BatchService instance with mocked manager."""
    service = BatchService()
    service._batch_manager = mock_batch_manager
    return service


class TestBatchServiceProcessBatch:
    """Test BatchService.process_batch() method."""

    def test_process_metadata_batch_queues_operations(
        self, batch_service: BatchService, mock_batch_manager: Mock
    ) -> None:
        """Test process_batch queues metadata operations correctly."""
        files = ["/test/file1.mp3", "/test/file2.mp3"]
        metadata = {"Title": "Test", "Artist": "Test Artist"}

        result = batch_service.process_batch(
            files, "metadata_set", metadata=metadata, is_extended=True
        )

        assert result["success"] is True
        assert result["queued"] == 2
        assert mock_batch_manager.queue_metadata_set.call_count == 2
        mock_batch_manager.queue_metadata_set.assert_any_call("/test/file1.mp3", metadata, True)
        mock_batch_manager.queue_metadata_set.assert_any_call("/test/file2.mp3", metadata, True)

    def test_process_hash_batch_queues_operations(
        self, batch_service: BatchService, mock_batch_manager: Mock
    ) -> None:
        """Test process_batch queues hash operations correctly."""
        files = ["/test/file1.mp3", "/test/file2.mp3"]

        result = batch_service.process_batch(
            files, "hash_store", hash_value="abc123", algorithm="crc32"
        )

        assert result["success"] is True
        assert result["queued"] == 2
        assert mock_batch_manager.queue_hash_store.call_count == 2
        mock_batch_manager.queue_hash_store.assert_any_call("/test/file1.mp3", "abc123", "crc32")

    def test_process_file_io_batch_queues_operations(
        self, batch_service: BatchService, mock_batch_manager: Mock
    ) -> None:
        """Test process_batch queues file I/O operations correctly."""
        files = ["/test/file1.mp3"]

        result = batch_service.process_batch(
            files, "file_io", io_operation="read", buffer_size=4096
        )

        assert result["success"] is True
        assert result["queued"] == 1
        assert mock_batch_manager.queue_file_operation.call_count == 1

    def test_process_batch_with_flush(
        self, batch_service: BatchService, mock_batch_manager: Mock
    ) -> None:
        """Test process_batch flushes when flush=True."""
        files = ["/test/file1.mp3"]
        metadata = {"Title": "Test"}

        result = batch_service.process_batch(files, "metadata_set", metadata=metadata, flush=True)

        assert result["success"] is True
        assert "flushed" in result
        assert result["flushed"] == {"metadata_set": 5, "hash_store": 3}
        mock_batch_manager.flush_all.assert_called_once()

    def test_process_batch_unknown_operation(self, batch_service: BatchService) -> None:
        """Test process_batch returns error for unknown operation."""
        files = ["/test/file1.mp3"]

        result = batch_service.process_batch(files, "unknown_operation")

        assert result["success"] is False
        assert "Unknown operation" in result["error"]

    def test_process_batch_no_manager(self) -> None:
        """Test process_batch returns error when manager not initialized."""
        service = BatchService()
        service._batch_manager = None

        result = service.process_batch(["/test/file1.mp3"], "metadata_set")

        assert result["success"] is False
        assert "not initialized" in result["error"]


class TestBatchServiceGetOperationStatus:
    """Test BatchService.get_operation_status() method."""

    def test_get_all_status(self, batch_service: BatchService, mock_batch_manager: Mock) -> None:
        """Test get_operation_status returns full status for 'all'."""
        result = batch_service.get_operation_status("all")

        assert result["success"] is True
        assert result["pending_operations"] == {"metadata_set": 2, "hash_store": 1}
        assert result["total_pending"] == 3
        assert result["stats"]["total_operations"] == 100
        assert result["stats"]["batched_operations"] == 95
        assert result["stats"]["batch_flushes"] == 10
        assert result["stats"]["average_batch_size"] == 9.5

    def test_get_specific_operation_status(
        self, batch_service: BatchService, mock_batch_manager: Mock
    ) -> None:
        """Test get_operation_status returns status for specific operation."""
        result = batch_service.get_operation_status("metadata_set")

        assert result["success"] is True
        assert result["operation_type"] == "metadata_set"
        assert result["pending_count"] == 2

    def test_get_status_no_pending_operations(
        self, batch_service: BatchService, mock_batch_manager: Mock
    ) -> None:
        """Test get_operation_status when no pending operations."""
        mock_batch_manager.get_pending_operations.return_value = {}

        result = batch_service.get_operation_status("metadata_set")

        assert result["success"] is True
        assert result["pending_count"] == 0

    def test_get_status_no_manager(self) -> None:
        """Test get_operation_status returns error when manager not initialized."""
        service = BatchService()
        service._batch_manager = None

        result = service.get_operation_status("all")

        assert result["success"] is False
        assert "not initialized" in result["error"]


class TestBatchServiceSingleton:
    """Test BatchService singleton pattern."""

    def test_get_batch_service_returns_singleton(self) -> None:
        """Test get_batch_service returns same instance."""
        # Reset singleton
        import oncutf.app.services.batch_service as service_module

        service_module._batch_service = None

        service1 = get_batch_service()
        service2 = get_batch_service()

        assert service1 is service2

    def test_singleton_preserves_state(self) -> None:
        """Test singleton preserves manager state across calls."""
        # Reset singleton
        import oncutf.app.services.batch_service as service_module

        service_module._batch_service = None

        service1 = get_batch_service()
        mock_manager = Mock()
        service1._batch_manager = mock_manager

        service2 = get_batch_service()

        assert service2._batch_manager is mock_manager


class TestBatchServiceManagerProperty:
    """Test BatchService.batch_manager property."""

    def test_batch_manager_lazy_loads_from_factory(self) -> None:
        """Test batch_manager uses factory when not initialized."""
        import oncutf.app.services.batch_service as service_module

        # Mock factory
        mock_manager = Mock()
        mock_factory = Mock(return_value=mock_manager)
        service_module._batch_manager_factory = mock_factory

        service = BatchService()
        result = service.batch_manager

        mock_factory.assert_called_once()
        assert result is mock_manager

    def test_batch_manager_returns_none_when_no_factory(self) -> None:
        """Test batch_manager returns None when factory not registered."""
        import oncutf.app.services.batch_service as service_module

        service_module._batch_manager_factory = None

        service = BatchService()
        result = service.batch_manager

        assert result is None

    def test_batch_manager_caches_instance(self) -> None:
        """Test batch_manager caches instance after first call."""
        import oncutf.app.services.batch_service as service_module

        mock_manager = Mock()
        mock_factory = Mock(return_value=mock_manager)
        service_module._batch_manager_factory = mock_factory

        service = BatchService()
        _ = service.batch_manager
        _ = service.batch_manager

        # Factory should only be called once
        mock_factory.assert_called_once()
