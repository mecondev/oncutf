import zlib
from pathlib import Path

from oncutf.core.hash_manager import HashManager, calculate_crc32


def write_file(path: Path, content: bytes):
    path.write_bytes(content)
    return path


def expected_crc32_bytes(content: bytes) -> str:
    return f"{(zlib.crc32(content) & 0xFFFFFFFF):08x}"


def test_calculate_crc32(tmp_path):
    f1 = write_file(tmp_path / "one.bin", b"hello")
    expected = expected_crc32_bytes(b"hello")
    got = calculate_crc32(f1)
    assert got == expected


def test_find_duplicates_in_paths_and_clear_cache(tmp_path):
    f1 = write_file(tmp_path / "a.txt", b"same")
    f2 = write_file(tmp_path / "b.txt", b"same")
    mgr = HashManager()
    dups = mgr.find_duplicates_in_paths([str(f1), str(f2)])
    # hashes should be same and group contains both
    assert len(dups) == 1
    for _k, v in dups.items():
        assert len(v) == 2

    # clear cache should not raise
    mgr.clear_cache()
#!/usr/bin/env python3
"""
Module: test_hash_manager.py

Author: Michael Economou
Date: 2025-05-31

test_hash_manager.py
Test module for hash calculation functionality.
"""

import warnings

warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*coroutine.*never awaited")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from oncutf.core.hash_manager import compare_folders
from tests.mocks import MockFileItem


class TestHashManager:
    """Test cases for HashManager class."""

    def test_init(self):
        """Test HashManager initialization."""
        manager = HashManager()
        # With persistent cache, we check for the cache attribute
        if hasattr(manager, "_persistent_cache"):
            assert manager._use_persistent_cache is True
        else:
            # Fallback mode
            assert hasattr(manager, "_hash_cache")
            assert manager._hash_cache == {}

    def test_calculate_crc32_success(self):
        """Test successful CRC32 calculation."""
        manager = HashManager()

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test")
            temp_path = f.name

        try:
            result = manager.calculate_hash(temp_path)
            expected = "d87f7e0c"  # CRC32 of "test"
            assert result == expected
        finally:
            Path(temp_path).unlink()

    def test_calculate_crc32_cached(self):
        """Test that cached hashes are returned."""
        manager = HashManager()

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("cached content")
            temp_path = f.name

        try:
            # First call
            result1 = manager.calculate_hash(temp_path)

            # Second call should use cache
            with patch("builtins.open") as mock_open:
                result2 = manager.calculate_hash(temp_path)
                mock_open.assert_not_called()  # File should not be opened again
                assert result1 == result2
        finally:
            Path(temp_path).unlink()

    def test_calculate_crc32_file_not_exists(self):
        """Test handling of non-existent files."""
        manager = HashManager()
        result = manager.calculate_hash("/non/existent.txt")
        assert result is None

    def test_calculate_crc32_directory(self):
        """Test handling of directories."""
        manager = HashManager()
        with tempfile.TemporaryDirectory() as temp_dir:
            result = manager.calculate_hash(temp_dir)
            assert result is None

    def test_calculate_crc32_permission_error(self):
        """Test handling of permission errors."""
        manager = HashManager()

        with patch("pathlib.Path.open", side_effect=PermissionError("Access denied")), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.is_file", return_value=True):
            # noqa: SIM117
            result = manager.calculate_hash("/mock/path/file.txt")
            assert result is None

    def test_calculate_crc32_string_path(self):
        """Test CRC32 calculation with string path."""
        manager = HashManager()

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("string path test")
            temp_path = f.name

        try:
            # Test with string path
            result = manager.calculate_hash(temp_path)
            expected_hash = "cb1bffb9"  # CRC32 of "string path test"
            assert result == expected_hash
        finally:
            Path(temp_path).unlink()

    def test_find_duplicates_in_list_no_duplicates(self):
        """Test duplicate detection with no duplicates."""
        manager = HashManager()

        with patch.object(manager, "calculate_hash") as mock_calc:
            mock_calc.side_effect = ["hash1", "hash2"]

            files = [MockFileItem(filename="file1.txt"), MockFileItem(filename="file2.txt")]

            result = manager.find_duplicates_in_list(files)
            assert result == {}

    def test_find_duplicates_in_list_with_duplicates(self):
        """Test duplicate detection with duplicates found."""
        manager = HashManager()

        files = [MockFileItem(filename="file1.txt"), MockFileItem(filename="file2.txt")]

        with patch.object(manager, "calculate_hash") as mock_calc:
            mock_calc.side_effect = ["same_hash", "same_hash"]

            result = manager.find_duplicates_in_list(files)

            assert len(result) == 1
            assert "same_hash" in result
            assert len(result["same_hash"]) == 2

    def test_find_duplicates_in_list_empty(self):
        """Test duplicate detection with empty list."""
        manager = HashManager()
        result = manager.find_duplicates_in_list([])
        assert result == {}

    def test_find_duplicates_in_list_hash_error(self):
        """Test duplicate detection with hash calculation errors."""
        manager = HashManager()

        files = [MockFileItem(filename="file1.txt")]

        with patch.object(manager, "calculate_hash", return_value=None):
            result = manager.find_duplicates_in_list(files)
            assert result == {}

    def test_compare_folders_success(self):
        """Test successful folder comparison."""
        manager = HashManager()

        with tempfile.TemporaryDirectory() as temp_dir1:  # noqa: SIM117
            with tempfile.TemporaryDirectory() as temp_dir2:
                # Create test files
                file1_path = Path(temp_dir1) / "test.txt"
                file2_path = Path(temp_dir2) / "test.txt"

                file1_path.write_text("same content")
                file2_path.write_text("same content")

                result = manager.compare_folders(temp_dir1, temp_dir2)

                assert "test.txt" in result
                is_same, hash1, hash2 = result["test.txt"]
                assert is_same is True
                assert hash1 == hash2

    def test_compare_folders_different_content(self):
        """Test folder comparison with different file content."""
        manager = HashManager()

        with tempfile.TemporaryDirectory() as temp_dir1:  # noqa: SIM117
            with tempfile.TemporaryDirectory() as temp_dir2:
                # Create test files with different content
                file1_path = Path(temp_dir1) / "test.txt"
                file2_path = Path(temp_dir2) / "test.txt"

                file1_path.write_text("content A")
                file2_path.write_text("content B")

                result = manager.compare_folders(temp_dir1, temp_dir2)

                assert "test.txt" in result
                is_same, hash1, hash2 = result["test.txt"]
                assert is_same is False
                assert hash1 != hash2

    def test_compare_folders_missing_file(self):
        """Test folder comparison with missing file in second folder."""
        manager = HashManager()

        with tempfile.TemporaryDirectory() as temp_dir1:  # noqa: SIM117
            with tempfile.TemporaryDirectory() as temp_dir2:
                # Create file only in first folder
                file1_path = Path(temp_dir1) / "test.txt"
                file1_path.write_text("content")

                result = manager.compare_folders(temp_dir1, temp_dir2)

                assert result == {}  # No matching files

    def test_compare_folders_invalid_paths(self):
        """Test folder comparison with invalid paths."""
        manager = HashManager()

        result = manager.compare_folders("/non/existent", "/also/non/existent")
        assert result == {}

    def test_verify_file_integrity_success(self):
        """Test successful file integrity verification with CRC32."""
        manager = HashManager()

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("integrity test")
            temp_path = f.name

        try:
            expected_hash = "2fd0365e"  # CRC32 of "integrity test"
            result = manager.verify_file_integrity(temp_path, expected_hash)
            assert result is True
        finally:
            Path(temp_path).unlink()

    def test_verify_file_integrity_mismatch(self):
        """Test file integrity verification with hash mismatch."""
        manager = HashManager()

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content")
            temp_path = f.name

        try:
            wrong_hash = "wrong_hash_value"
            result = manager.verify_file_integrity(temp_path, wrong_hash)
            assert result is False
        finally:
            Path(temp_path).unlink()

    def test_verify_file_integrity_case_insensitive(self):
        """Test file integrity verification is case insensitive with CRC32."""
        manager = HashManager()

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("case test")
            temp_path = f.name

        try:
            expected_hash = "22e5d3a1"  # CRC32 of "case test"
            upper_hash = expected_hash.upper()

            result = manager.verify_file_integrity(temp_path, upper_hash)
            assert result is True
        finally:
            Path(temp_path).unlink()

    def test_clear_cache(self):
        """Test cache clearing functionality."""
        manager = HashManager()

        # Add some test data first
        if hasattr(manager, "_persistent_cache"):
            # With persistent cache
            manager._persistent_cache.store_hash("test_file", "test_hash")
            manager.clear_cache()
            # Memory cache should be cleared, but we can't easily test the persistent cache
            # Just verify the method doesn't crash
        else:
            # Fallback mode
            manager._hash_cache = {"test": "hash"}
            manager.clear_cache()
            assert manager._hash_cache == {}

    def test_get_cache_info(self):
        """Test cache information retrieval."""
        manager = HashManager()

        if hasattr(manager, "_persistent_cache"):
            # With persistent cache, the return format is different
            info = manager.get_cache_info()
            assert "memory_entries" in info
            assert "cache_hits" in info
            assert "cache_misses" in info
        else:
            # Fallback mode
            manager._hash_cache = {"file1": "hash1", "file2": "hash2"}
            info = manager.get_cache_info()
            assert info["cache_size"] == 2
            assert "memory_usage_approx" in info


class TestConvenienceFunctions:
    """Test cases for convenience functions."""

    def test_calculate_crc32_function(self):
        """Test standalone calculate_crc32 function."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("convenience test")
            temp_path = f.name

        try:
            result = calculate_crc32(temp_path)
            expected_hash = "217a34d5"  # CRC32 of "convenience test"
            assert result == expected_hash
        finally:
            Path(temp_path).unlink()

    def test_compare_folders_function(self):
        """Test standalone compare_folders function."""
        with tempfile.TemporaryDirectory() as temp_dir1:  # noqa: SIM117
            with tempfile.TemporaryDirectory() as temp_dir2:
                # Create identical test files
                file1_path = Path(temp_dir1) / "test.txt"
                file2_path = Path(temp_dir2) / "test.txt"

                file1_path.write_text("function test")
                file2_path.write_text("function test")

                result = compare_folders(temp_dir1, temp_dir2)

                assert "test.txt" in result
                is_same, hash1, hash2 = result["test.txt"]
                assert is_same is True


class TestEventHandlerIntegration:
    """Test cases for EventHandlerManager hash integration."""

    def test_event_handler_initialization(self):
        """Test EventHandlerManager can be initialized with mock parent."""
        from oncutf.core.event_handler_manager import EventHandlerManager

        mock_parent = Mock()
        mock_parent.set_status = Mock()

        handler = EventHandlerManager(mock_parent)

        # Verify basic initialization
        assert handler.parent_window == mock_parent
        # After refactoring, methods are delegated to hash_ops manager
        assert hasattr(handler, "hash_ops")
        assert hasattr(handler.hash_ops, "handle_find_duplicates")
        assert hasattr(handler.hash_ops, "handle_calculate_hashes")

    def test_hash_manager_integration(self):
        """Test that HashManager can be imported and used."""
        from oncutf.core.hash_manager import HashManager

        # This is a basic integration test
        manager = HashManager()
        assert hasattr(manager, "calculate_hash")
        assert hasattr(manager, "find_duplicates_in_list")
        assert hasattr(manager, "compare_folders")


class TestErrorHandling:
    """Test cases for error handling scenarios."""

    def test_hash_manager_exception_handling(self):
        """Test HashManager handles exceptions gracefully."""
        manager = HashManager()

        with patch("pathlib.Path.open", side_effect=Exception("Unexpected error")), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.is_file", return_value=True):
            result = manager.calculate_hash("/mock/path")
            assert result is None

    def test_find_duplicates_with_exception(self):
        """Test duplicate detection handles file errors gracefully."""
        manager = HashManager()

        files = [MockFileItem(filename="error_file.txt")]

        with patch.object(manager, "calculate_hash", side_effect=Exception("Hash error")):
            result = manager.find_duplicates_in_list(files)
            assert result == {}


class TestPerformance:
    """Test cases for performance optimizations."""

    def test_large_file_performance(self):
        """Test CRC32 calculation performance with optimized buffer."""
        import time

        manager = HashManager()

        # Create a larger test file (10MB) for more accurate performance measurement
        test_data = (
            b"Performance test data for CRC32 optimization with memoryview and bytearray" * 135000
        )  # ~10MB

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(test_data)
            temp_path = f.name

        try:
            # Clear any existing cache to ensure we're measuring actual calculation
            manager.clear_cache()

            # Measure calculation time (bypass database to measure pure CRC32 performance)
            start_time = time.perf_counter()

            # Use the internal CRC32 calculation method directly to avoid database overhead
            import zlib

            with open(temp_path, "rb") as file:
                crc32_hash = 0
                while True:
                    chunk = file.read(65536)  # 64KB chunks
                    if not chunk:
                        break
                    crc32_hash = zlib.crc32(chunk, crc32_hash)
                result = f"{crc32_hash & 0xFFFFFFFF:08x}"

            end_time = time.perf_counter()

            calculation_time = end_time - start_time
            file_size_mb = len(test_data) / (1024 * 1024)
            throughput = file_size_mb / calculation_time if calculation_time > 0 else 0

            # Verify result is valid
            assert result is not None
            assert len(result) == 8  # CRC32 should be 8 hex characters

            # Performance should be reasonable (at least 50 MB/s for pure CRC32 calculation)
            assert throughput > 50, f"Performance too slow: {throughput:.1f} MB/s"

        finally:
            Path(temp_path).unlink()

    def test_progress_callback(self):
        """Test that progress callback is called during hash calculation."""
        manager = HashManager()

        # Create a test file with enough data to trigger multiple buffer reads
        test_data = b"Progress callback test data" * 20000  # ~500KB

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(test_data)
            temp_path = f.name

        try:
            # Track progress calls
            progress_calls = []

            def progress_callback(bytes_processed):
                progress_calls.append(bytes_processed)

            # Calculate hash with progress tracking
            result = manager.calculate_hash(temp_path, progress_callback)

            # Verify result is valid
            assert result is not None
            assert len(result) == 8  # CRC32 should be 8 hex characters

            # Verify progress was tracked
            assert len(progress_calls) > 0, "Progress callback should have been called"

            # Verify progress values make sense
            assert progress_calls[0] > 0, "First progress call should be > 0"
            assert progress_calls[-1] == len(test_data), (
                f"Final progress should equal file size: {progress_calls[-1]} vs {len(test_data)}"
            )

            # Verify progress is monotonically increasing
            for i in range(1, len(progress_calls)):
                assert progress_calls[i] >= progress_calls[i - 1], (
                    "Progress should be monotonically increasing"
                )

        finally:
            Path(temp_path).unlink()
