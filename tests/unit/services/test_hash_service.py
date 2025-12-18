"""
Tests for HashService.

Author: Michael Economou
Date: December 18, 2025

Tests the file hashing service implementation.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from oncutf.services.hash_service import SUPPORTED_ALGORITHMS, HashService
from oncutf.services.interfaces import HashServiceProtocol


class TestHashServiceProtocolCompliance:
    """Tests for protocol compliance."""

    def test_implements_hash_service_protocol(self) -> None:
        """Test that HashService implements HashServiceProtocol."""
        service = HashService()
        assert isinstance(service, HashServiceProtocol)


class TestHashServiceInitialization:
    """Tests for service initialization."""

    def test_default_initialization(self) -> None:
        """Test default initialization."""
        service = HashService()
        assert service._default_algorithm == "crc32"
        assert service._use_cache is True

    def test_custom_algorithm(self) -> None:
        """Test initialization with custom algorithm."""
        service = HashService(default_algorithm="md5")
        assert service._default_algorithm == "md5"

    def test_invalid_algorithm_raises(self) -> None:
        """Test that invalid algorithm raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported algorithm"):
            HashService(default_algorithm="invalid")

    def test_cache_disabled(self) -> None:
        """Test initialization with cache disabled."""
        service = HashService(use_cache=False)
        assert service._use_cache is False


class TestHashServiceComputeHash:
    """Tests for single file hash computation."""

    def test_compute_crc32_hash(self, tmp_path: Path) -> None:
        """Test CRC32 hash computation."""
        service = HashService()
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"test content")

        result = service.compute_hash(test_file, algorithm="crc32")

        assert result != ""
        assert len(result) == 8  # CRC32 is 8 hex chars

    def test_compute_md5_hash(self, tmp_path: Path) -> None:
        """Test MD5 hash computation."""
        service = HashService()
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"test content")

        result = service.compute_hash(test_file, algorithm="md5")

        assert result != ""
        assert len(result) == 32  # MD5 is 32 hex chars

    def test_compute_sha256_hash(self, tmp_path: Path) -> None:
        """Test SHA256 hash computation."""
        service = HashService()
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"test content")

        result = service.compute_hash(test_file, algorithm="sha256")

        assert result != ""
        assert len(result) == 64  # SHA256 is 64 hex chars

    def test_same_content_same_hash(self, tmp_path: Path) -> None:
        """Test that same content produces same hash."""
        service = HashService()
        content = b"identical content"

        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_bytes(content)
        file2.write_bytes(content)

        hash1 = service.compute_hash(file1)
        hash2 = service.compute_hash(file2)

        assert hash1 == hash2

    def test_different_content_different_hash(self, tmp_path: Path) -> None:
        """Test that different content produces different hash."""
        service = HashService()

        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_bytes(b"content 1")
        file2.write_bytes(b"content 2")

        hash1 = service.compute_hash(file1)
        hash2 = service.compute_hash(file2)

        assert hash1 != hash2

    def test_nonexistent_file_returns_empty(self, tmp_path: Path) -> None:
        """Test that non-existent file returns empty string."""
        service = HashService()
        nonexistent = tmp_path / "nonexistent.txt"

        result = service.compute_hash(nonexistent)

        assert result == ""

    def test_directory_returns_empty(self, tmp_path: Path) -> None:
        """Test that directory returns empty string."""
        service = HashService()

        result = service.compute_hash(tmp_path)

        assert result == ""

    def test_invalid_algorithm_returns_empty(self, tmp_path: Path) -> None:
        """Test that invalid algorithm returns empty string."""
        service = HashService()
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"test")

        result = service.compute_hash(test_file, algorithm="invalid")

        assert result == ""


class TestHashServiceCaching:
    """Tests for hash caching."""

    def test_cache_stores_result(self, tmp_path: Path) -> None:
        """Test that computed hash is cached."""
        service = HashService(use_cache=True)
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"test content")

        service.compute_hash(test_file)

        assert service.get_cache_size() == 1

    def test_cache_returns_cached_result(self, tmp_path: Path) -> None:
        """Test that cached result is returned."""
        service = HashService(use_cache=True)
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"test content")

        hash1 = service.compute_hash(test_file)
        hash2 = service.compute_hash(test_file)

        assert hash1 == hash2
        assert service.get_cache_size() == 1

    def test_cache_disabled_no_caching(self, tmp_path: Path) -> None:
        """Test that disabled cache does not store results."""
        service = HashService(use_cache=False)
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"test content")

        service.compute_hash(test_file)

        assert service.get_cache_size() == 0

    def test_clear_cache(self, tmp_path: Path) -> None:
        """Test clearing the cache."""
        service = HashService(use_cache=True)
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"test content")

        service.compute_hash(test_file)
        assert service.get_cache_size() == 1

        service.clear_cache()
        assert service.get_cache_size() == 0


class TestHashServiceBatch:
    """Tests for batch hash computation."""

    def test_compute_hashes_batch(self, tmp_path: Path) -> None:
        """Test batch hash computation."""
        service = HashService()

        files = []
        for i in range(3):
            f = tmp_path / f"file{i}.txt"
            f.write_bytes(f"content {i}".encode())
            files.append(f)

        results = service.compute_hashes_batch(files)

        assert len(results) == 3
        assert all(path in results for path in files)
        assert all(len(h) == 8 for h in results.values())

    def test_compute_hashes_batch_empty_list(self) -> None:
        """Test batch with empty list."""
        service = HashService()

        results = service.compute_hashes_batch([])

        assert results == {}

    def test_compute_hashes_batch_with_progress(self, tmp_path: Path) -> None:
        """Test batch with progress callback."""
        service = HashService()
        progress_calls: list[tuple[int, int]] = []

        def progress_callback(current: int, total: int) -> None:
            progress_calls.append((current, total))

        files = []
        for i in range(3):
            f = tmp_path / f"file{i}.txt"
            f.write_bytes(f"content {i}".encode())
            files.append(f)

        service.compute_hashes_batch(files, progress_callback=progress_callback)

        assert len(progress_calls) == 3
        assert progress_calls[-1] == (3, 3)


class TestHashServiceBufferSizing:
    """Tests for adaptive buffer sizing."""

    def test_small_file_buffer_size(self) -> None:
        """Test buffer size for small files."""
        service = HashService()

        # 1KB file
        buffer_size = service._get_optimal_buffer_size(1024)
        assert buffer_size == 1024  # min(1024, 8192)

        # 32KB file
        buffer_size = service._get_optimal_buffer_size(32 * 1024)
        assert buffer_size == 8 * 1024  # 8KB max for small files

    def test_medium_file_buffer_size(self) -> None:
        """Test buffer size for medium files."""
        service = HashService()

        # 1MB file
        buffer_size = service._get_optimal_buffer_size(1024 * 1024)
        assert buffer_size == 64 * 1024  # 64KB for medium files

    def test_large_file_buffer_size(self) -> None:
        """Test buffer size for large files."""
        service = HashService()

        # 100MB file
        buffer_size = service._get_optimal_buffer_size(100 * 1024 * 1024)
        assert buffer_size == 256 * 1024  # 256KB for large files


class TestSupportedAlgorithms:
    """Tests for algorithm support."""

    def test_supported_algorithms_constant(self) -> None:
        """Test that SUPPORTED_ALGORITHMS contains expected values."""
        assert "crc32" in SUPPORTED_ALGORITHMS
        assert "md5" in SUPPORTED_ALGORITHMS
        assert "sha256" in SUPPORTED_ALGORITHMS
        assert "sha1" in SUPPORTED_ALGORITHMS
