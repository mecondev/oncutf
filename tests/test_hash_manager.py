#!/usr/bin/env python3
"""
test_hash_manager.py

Author: Michael Economou
Date: 2025-05-22

Test module for hash calculation functionality.
"""

import hashlib
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from core.hash_manager import HashManager, calculate_sha256, compare_folders
from tests.mocks import MockFileItem


class TestHashManager:
    """Test cases for HashManager class."""

    def test_init(self):
        """Test HashManager initialization."""
        manager = HashManager()
        assert manager._hash_cache == {}

    def test_calculate_sha256_success(self):
        """Test successful SHA-256 calculation."""
        manager = HashManager()

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test")
            temp_path = f.name

        try:
            result = manager.calculate_sha256(temp_path)
            expected = hashlib.sha256(b"test").hexdigest()
            assert result == expected
        finally:
            Path(temp_path).unlink()

    def test_calculate_sha256_cached(self):
        """Test that cached hashes are returned."""
        manager = HashManager()

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("cached content")
            temp_path = f.name

        try:
            # First call
            result1 = manager.calculate_sha256(temp_path)

            # Second call should use cache
            with patch('builtins.open') as mock_open:
                result2 = manager.calculate_sha256(temp_path)
                mock_open.assert_not_called()  # File should not be opened again
                assert result1 == result2
        finally:
            Path(temp_path).unlink()

    def test_calculate_sha256_file_not_exists(self):
        """Test handling of non-existent files."""
        manager = HashManager()
        result = manager.calculate_sha256("/non/existent.txt")
        assert result is None

    def test_calculate_sha256_directory(self):
        """Test handling of directories."""
        manager = HashManager()
        with tempfile.TemporaryDirectory() as temp_dir:
            result = manager.calculate_sha256(temp_dir)
            assert result is None

    def test_calculate_sha256_permission_error(self):
        """Test handling of permission errors."""
        manager = HashManager()

        with patch('pathlib.Path.open', side_effect=PermissionError("Access denied")):
            with patch('pathlib.Path.exists', return_value=True):
                with patch('pathlib.Path.is_file', return_value=True):
                    result = manager.calculate_sha256("/mock/path/file.txt")
                    assert result is None

    def test_calculate_sha256_string_path(self):
        """Test SHA-256 calculation with string path."""
        manager = HashManager()

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("string path test")
            temp_path = f.name

        try:
            # Test with string path
            result = manager.calculate_sha256(temp_path)
            expected_hash = hashlib.sha256(b"string path test").hexdigest()
            assert result == expected_hash
        finally:
            Path(temp_path).unlink()

    def test_find_duplicates_in_list_no_duplicates(self):
        """Test duplicate detection with no duplicates."""
        manager = HashManager()

        with patch.object(manager, 'calculate_sha256') as mock_calc:
            mock_calc.side_effect = ["hash1", "hash2"]

            files = [
                MockFileItem(filename="file1.txt"),
                MockFileItem(filename="file2.txt")
            ]

            result = manager.find_duplicates_in_list(files)
            assert result == {}

    def test_find_duplicates_in_list_with_duplicates(self):
        """Test duplicate detection with duplicates found."""
        manager = HashManager()

        files = [
            MockFileItem(filename="file1.txt"),
            MockFileItem(filename="file2.txt")
        ]

        with patch.object(manager, 'calculate_sha256') as mock_calc:
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

        with patch.object(manager, 'calculate_sha256', return_value=None):
            result = manager.find_duplicates_in_list(files)
            assert result == {}

    def test_compare_folders_success(self):
        """Test successful folder comparison."""
        manager = HashManager()

        with tempfile.TemporaryDirectory() as temp_dir1:
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

        with tempfile.TemporaryDirectory() as temp_dir1:
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

        with tempfile.TemporaryDirectory() as temp_dir1:
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
        """Test successful file integrity verification."""
        manager = HashManager()

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("integrity test")
            temp_path = f.name

        try:
            expected_hash = hashlib.sha256(b"integrity test").hexdigest()
            result = manager.verify_file_integrity(temp_path, expected_hash)
            assert result is True
        finally:
            Path(temp_path).unlink()

    def test_verify_file_integrity_mismatch(self):
        """Test file integrity verification with hash mismatch."""
        manager = HashManager()

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            temp_path = f.name

        try:
            wrong_hash = "wrong_hash_value"
            result = manager.verify_file_integrity(temp_path, wrong_hash)
            assert result is False
        finally:
            Path(temp_path).unlink()

    def test_verify_file_integrity_case_insensitive(self):
        """Test file integrity verification is case insensitive."""
        manager = HashManager()

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("case test")
            temp_path = f.name

        try:
            expected_hash = hashlib.sha256(b"case test").hexdigest()
            upper_hash = expected_hash.upper()

            result = manager.verify_file_integrity(temp_path, upper_hash)
            assert result is True
        finally:
            Path(temp_path).unlink()

    def test_clear_cache(self):
        """Test cache clearing functionality."""
        manager = HashManager()
        manager._hash_cache = {"test": "hash"}

        manager.clear_cache()
        assert manager._hash_cache == {}

    def test_get_cache_info(self):
        """Test cache information retrieval."""
        manager = HashManager()
        manager._hash_cache = {"file1": "hash1", "file2": "hash2"}

        info = manager.get_cache_info()
        assert info["cache_size"] == 2
        assert "memory_usage_approx" in info


class TestConvenienceFunctions:
    """Test cases for convenience functions."""

    def test_calculate_sha256_function(self):
        """Test standalone calculate_sha256 function."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("convenience test")
            temp_path = f.name

        try:
            result = calculate_sha256(temp_path)
            expected_hash = hashlib.sha256(b"convenience test").hexdigest()
            assert result == expected_hash
        finally:
            Path(temp_path).unlink()

    def test_compare_folders_function(self):
        """Test standalone compare_folders function."""
        with tempfile.TemporaryDirectory() as temp_dir1:
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
        from core.event_handler_manager import EventHandlerManager

        mock_parent = Mock()
        mock_parent.set_status = Mock()

        handler = EventHandlerManager(mock_parent)

        # Verify basic initialization
        assert handler.parent_window == mock_parent
        assert hasattr(handler, '_handle_find_duplicates')
        assert hasattr(handler, '_handle_calculate_hashes')

    def test_hash_manager_integration(self):
        """Test that HashManager can be imported and used."""
        from core.hash_manager import HashManager

        # This is a basic integration test
        manager = HashManager()
        assert hasattr(manager, 'calculate_sha256')
        assert hasattr(manager, 'find_duplicates_in_list')
        assert hasattr(manager, 'compare_folders')


class TestErrorHandling:
    """Test cases for error handling scenarios."""

    def test_hash_manager_exception_handling(self):
        """Test HashManager handles exceptions gracefully."""
        manager = HashManager()

        with patch('pathlib.Path.open', side_effect=Exception("Unexpected error")):
            with patch('pathlib.Path.exists', return_value=True):
                with patch('pathlib.Path.is_file', return_value=True):
                    result = manager.calculate_sha256("/mock/path")
                    assert result is None

    def test_find_duplicates_with_exception(self):
        """Test duplicate detection handles file errors gracefully."""
        manager = HashManager()

        files = [MockFileItem(filename="error_file.txt")]

        with patch.object(manager, 'calculate_sha256', side_effect=Exception("Hash error")):
            result = manager.find_duplicates_in_list(files)
            assert result == {}
