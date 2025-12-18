"""
Tests for ExifToolService.

Author: Michael Economou
Date: December 18, 2025

Tests the ExifTool-based metadata service implementation.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from oncutf.services.exiftool_service import ExifToolService
from oncutf.services.interfaces import MetadataServiceProtocol


class TestExifToolServiceProtocolCompliance:
    """Tests for protocol compliance."""

    def test_implements_metadata_service_protocol(self) -> None:
        """Test that ExifToolService implements MetadataServiceProtocol."""
        service = ExifToolService()
        assert isinstance(service, MetadataServiceProtocol)


class TestExifToolServiceAvailability:
    """Tests for ExifTool availability checking."""

    def test_is_available_caches_result(self) -> None:
        """Test that availability check is cached."""
        service = ExifToolService()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="12.0")

            # First call
            result1 = service.is_available()
            # Second call should use cache
            result2 = service.is_available()

            # Should only call subprocess once
            assert mock_run.call_count == 1
            assert result1 is True
            assert result2 is True

    def test_is_available_when_exiftool_missing(self) -> None:
        """Test availability when ExifTool is not installed."""
        service = ExifToolService()

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("exiftool not found")

            result = service.is_available()

            assert result is False

    def test_is_available_when_exiftool_fails(self) -> None:
        """Test availability when ExifTool returns error."""
        service = ExifToolService()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)

            result = service.is_available()

            assert result is False


class TestExifToolServiceLoadMetadata:
    """Tests for metadata loading."""

    def test_load_metadata_returns_empty_when_unavailable(self) -> None:
        """Test that load_metadata returns empty dict when ExifTool unavailable."""
        service = ExifToolService()
        service._available = False

        result = service.load_metadata(Path("/some/file.jpg"))

        assert result == {}

    def test_load_metadata_returns_empty_for_nonexistent_file(self, tmp_path: Path) -> None:
        """Test that load_metadata returns empty dict for non-existent file."""
        service = ExifToolService()
        service._available = True

        nonexistent = tmp_path / "nonexistent.jpg"
        result = service.load_metadata(nonexistent)

        assert result == {}

    def test_load_metadata_returns_empty_for_directory(self, tmp_path: Path) -> None:
        """Test that load_metadata returns empty dict for directory."""
        service = ExifToolService()
        service._available = True

        result = service.load_metadata(tmp_path)

        assert result == {}

    @pytest.mark.exiftool
    def test_load_metadata_with_real_file(self, tmp_path: Path) -> None:
        """Test metadata loading with a real file (requires ExifTool)."""
        service = ExifToolService()

        if not service.is_available():
            pytest.skip("ExifTool not available")

        # Create a simple text file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        result = service.load_metadata(test_file)

        # Should return some metadata (at least filename)
        assert isinstance(result, dict)


class TestExifToolServiceLoadMetadataBatch:
    """Tests for batch metadata loading."""

    def test_load_metadata_batch_returns_empty_when_unavailable(self) -> None:
        """Test batch loading returns empty dicts when unavailable."""
        service = ExifToolService()
        service._available = False

        paths = [Path("/file1.jpg"), Path("/file2.jpg")]
        result = service.load_metadata_batch(paths)

        assert all(v == {} for v in result.values())
        assert set(result.keys()) == set(paths)

    def test_load_metadata_batch_empty_list(self) -> None:
        """Test batch loading with empty list."""
        service = ExifToolService()
        service._available = True

        result = service.load_metadata_batch([])

        assert result == {}


class TestExifToolServiceClose:
    """Tests for service cleanup."""

    def test_close_without_wrapper(self) -> None:
        """Test that close() works when wrapper not initialized."""
        service = ExifToolService()
        # Should not raise
        service.close()

    def test_close_with_wrapper(self) -> None:
        """Test that close() closes the wrapper."""
        service = ExifToolService()
        mock_wrapper = MagicMock()
        service._wrapper = mock_wrapper

        service.close()

        mock_wrapper.close.assert_called_once()
        assert service._wrapper is None
