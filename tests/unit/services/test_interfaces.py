"""Tests for service protocol interfaces.

Author: Michael Economou
Date: December 18, 2025

Tests verify that protocol definitions are correct and that
isinstance() works with runtime_checkable protocols.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from oncutf.services.interfaces import (
    FilesystemServiceProtocol,
    HashServiceProtocol,
    MetadataServiceProtocol,
)


class TestMetadataServiceProtocol:
    """Tests for MetadataServiceProtocol."""

    def test_mock_implementation_is_instance(self) -> None:
        """Test that a mock class implementing the protocol is recognized."""

        class MockMetadataService:
            def load_metadata(self, path: Path) -> dict[str, Any]:
                _ = path  # Used to satisfy protocol
                return {"test": "value"}

            def load_metadata_batch(self, paths: list[Path]) -> dict[Path, dict[str, Any]]:
                return {p: {"test": "value"} for p in paths}

        mock = MockMetadataService()
        assert isinstance(mock, MetadataServiceProtocol)

    def test_incomplete_implementation_not_instance(self) -> None:
        """Test that incomplete implementation is not recognized."""

        class IncompleteService:
            def load_metadata(self, path: Path) -> dict[str, Any]:
                _ = path  # Used to satisfy protocol
                return {}

            # Missing load_metadata_batch

        incomplete = IncompleteService()
        assert not isinstance(incomplete, MetadataServiceProtocol)


class TestHashServiceProtocol:
    """Tests for HashServiceProtocol."""

    def test_mock_implementation_is_instance(self) -> None:
        """Test that a mock class implementing the protocol is recognized."""

        class MockHashService:
            def compute_hash(self, path: Path, algorithm: str = "crc32") -> str:
                _ = (path, algorithm)  # Used to satisfy protocol
                return "abc123"

            def compute_hashes_batch(
                self, paths: list[Path], algorithm: str = "crc32"
            ) -> dict[Path, str]:
                _ = algorithm  # Used to satisfy protocol
                return dict.fromkeys(paths, "abc123")

        mock = MockHashService()
        assert isinstance(mock, HashServiceProtocol)


class TestFilesystemServiceProtocol:
    """Tests for FilesystemServiceProtocol."""

    def test_mock_implementation_is_instance(self) -> None:
        """Test that a mock class implementing the protocol is recognized."""

        class MockFilesystemService:
            def rename_file(self, source: Path, target: Path) -> bool:
                _ = (source, target)  # Used to satisfy protocol
                return True

            def file_exists(self, path: Path) -> bool:
                _ = path  # Used to satisfy protocol
                return True

            def get_file_info(self, path: Path) -> dict[str, Any]:
                _ = path  # Used to satisfy protocol
                return {"size": 1000}

        mock = MockFilesystemService()
        assert isinstance(mock, FilesystemServiceProtocol)
