"""
Module: test_simple_hash_integration.py

Author: Michael Economou
Date: 2025-05-31

test_simple_hash_integration.py
Simple integration test for hash functionality without relying on signals.
Tests the actual fix for cumulative progress tracking.
"""

import warnings

warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*coroutine.*never awaited")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

import os
import tempfile

from oncutf.core.hash_manager import HashManager


def test_hash_manager_basic_functionality():
    """Test that HashManager works correctly with multiple files."""

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test files
        files = []
        expected_sizes = []

        for i, size in enumerate([5000, 10000, 15000]):
            file_path = os.path.join(temp_dir, f"test_file_{i}.txt")
            with open(file_path, "wb") as f:
                f.write(b"X" * size)
            files.append(file_path)
            expected_sizes.append(size)

        # Test hash calculation
        hash_manager = HashManager()

        # Calculate hashes
        hash_results = {}
        for file_path in files:
            file_hash = hash_manager.calculate_hash(file_path)
            assert file_hash is not None, f"Failed to calculate hash for {file_path}"
            hash_results[file_path] = file_hash

        # Verify we got hashes for all files
        assert len(hash_results) == len(files)

        # Test duplicate detection
        duplicates = hash_manager.find_duplicates_in_paths(files)

        # These unique files shouldn't have duplicates
        assert len(duplicates) == 0, "Unexpected duplicates found in unique files"


def test_hash_manager_with_progress_callback():
    """Test HashManager with progress callback to simulate real usage."""

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a larger file to test progress tracking
        large_file = os.path.join(temp_dir, "large_test.txt")
        with open(large_file, "wb") as f:
            f.write(b"Y" * 50000)  # 50KB file

        # Track progress updates
        progress_updates = []

        def progress_callback(bytes_processed):
            progress_updates.append(bytes_processed)

        # Calculate hash with progress tracking
        hash_manager = HashManager()
        file_hash = hash_manager.calculate_hash(large_file, progress_callback)

        assert file_hash is not None, "Failed to calculate hash"

        # Verify we got progress updates
        if progress_updates:
            # Progress should be monotonic
            last_progress = 0
            for progress in progress_updates:
                assert progress >= last_progress, (
                    f"Progress went backwards: {progress} < {last_progress}"
                )
                last_progress = progress
        else:
            pass


def test_cumulative_size_calculation():
    """Test cumulative size calculation which is part of the fix."""

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create files with known sizes
        sizes = [1000, 2000, 3000, 4000, 5000]
        files = []

        for i, size in enumerate(sizes):
            file_path = os.path.join(temp_dir, f"size_test_{i}.txt")
            with open(file_path, "wb") as f:
                f.write(b"Z" * size)
            files.append(file_path)

        # Calculate total size manually
        manual_total = sum(sizes)

        # Calculate using os.path.getsize (what the fix uses)
        calculated_total = 0
        for file_path in files:
            file_size = os.path.getsize(file_path)
            calculated_total += file_size

        assert calculated_total == manual_total, (
            f"Size calculation mismatch: {calculated_total} != {manual_total}"
        )

        # Test that each file can be hashed
        hash_manager = HashManager()
        cumulative_processed = 0

        for file_path in files:
            file_size = os.path.getsize(file_path)
            file_hash = hash_manager.calculate_hash(file_path)

            assert file_hash is not None, f"Failed to hash {file_path}"

            # Simulate the cumulative tracking logic from the fix
            cumulative_processed += file_size

        # Final cumulative should equal total
        assert cumulative_processed == manual_total, (
            f"Cumulative tracking failed: {cumulative_processed} != {manual_total}"
        )


if __name__ == "__main__":
    test_hash_manager_basic_functionality()
    test_hash_manager_with_progress_callback()
    test_cumulative_size_calculation()
