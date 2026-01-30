"""Module: test_hash_worker_progress.py

Author: Michael Economou
Date: 2025-05-31

test_hash_worker_progress.py
Tests for HashWorker cumulative progress tracking.
Ensures that progress never goes backwards and accumulates correctly.
"""

import os
import tempfile
import time

import pytest
from PyQt5.QtCore import QCoreApplication

from oncutf.core.hash.hash_worker import HashWorker


class TestHashWorkerProgress:
    """Test HashWorker cumulative progress tracking fixes."""

    def setup_method(self):
        """Set up test fixtures."""
        self.worker = HashWorker()

    def teardown_method(self):
        """Clean up after tests."""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(1000)

    def test_worker_internal_state(self):
        """Test that worker internal state is managed correctly."""
        files = []

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            for i, size in enumerate([10000, 20000, 30000]):
                file_path = os.path.join(temp_dir, f"test_file_{i}.txt")
                with open(file_path, "wb") as f:
                    f.write(b"A" * size)
                files.append(file_path)

            total_size = 60000

            # Setup worker
            self.worker.setup_checksum_calculation(files)
            self.worker.set_total_size(total_size)

            # Check initial state
            assert self.worker._cumulative_processed_bytes == 0
            assert self.worker._total_bytes == total_size

            # Start worker and wait for completion
            self.worker.start()

            deadline = time.time() + 10
            while self.worker.isRunning() and time.time() < deadline:
                QCoreApplication.processEvents()
                time.sleep(0.01)

            if self.worker.isRunning():
                self.worker.cancel()
                self.worker.wait(2000)

            # Process any remaining events
            for _ in range(10):
                QCoreApplication.processEvents()
                time.sleep(0.01)

            # Check final state - cumulative bytes should equal total
            assert self.worker._cumulative_processed_bytes == total_size, (
                f"Expected cumulative bytes {total_size}, got {self.worker._cumulative_processed_bytes}"
            )

    def test_worker_overflow_protection(self):
        """Test that worker handles large files without overflow."""
        files = []

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a moderately large file
            file_path = os.path.join(temp_dir, "large_file.txt")
            size = 50_000_000  # 50MB
            with open(file_path, "wb") as f:
                f.write(b"B" * size)
            files.append(file_path)

            # Setup worker
            self.worker.setup_checksum_calculation(files)
            self.worker.set_total_size(size)

            # Check initial state
            assert self.worker._cumulative_processed_bytes == 0
            assert self.worker._total_bytes == size

            # Start worker
            self.worker.start()

            deadline = time.time() + 15  # Longer timeout for larger file
            while self.worker.isRunning() and time.time() < deadline:
                QCoreApplication.processEvents()
                time.sleep(0.01)

            if self.worker.isRunning():
                self.worker.cancel()
                self.worker.wait(3000)

            # Process remaining events
            for _ in range(20):
                QCoreApplication.processEvents()
                time.sleep(0.01)

            # Check that we didn't overflow (no negative values)
            assert self.worker._cumulative_processed_bytes >= 0, (
                f"Cumulative bytes went negative: {self.worker._cumulative_processed_bytes}"
            )

            # Should have processed the full file
            assert self.worker._cumulative_processed_bytes == size, (
                f"Expected {size} bytes processed, got {self.worker._cumulative_processed_bytes}"
            )

    def test_duplicate_scan_functionality(self):
        """Test that duplicate scan maintains correct state."""
        files = []

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create files for duplicate scanning
            file1_path = os.path.join(temp_dir, "file1.txt")
            file2_path = os.path.join(temp_dir, "file2.txt")

            with open(file1_path, "wb") as f:
                f.write(b"X" * 15000)
            with open(file2_path, "wb") as f:
                f.write(b"Y" * 10000)

            files = [file1_path, file2_path]
            total_size = 25000

            # Setup worker for duplicate scan
            self.worker.setup_duplicate_scan(files)
            self.worker.set_total_size(total_size)

            # Check initial state
            assert self.worker._cumulative_processed_bytes == 0
            assert self.worker._total_bytes == total_size

            # Start worker
            self.worker.start()

            deadline = time.time() + 10
            while self.worker.isRunning() and time.time() < deadline:
                QCoreApplication.processEvents()
                time.sleep(0.01)

            if self.worker.isRunning():
                self.worker.cancel()
                self.worker.wait(2000)

            # Process remaining events
            for _ in range(10):
                QCoreApplication.processEvents()
                time.sleep(0.01)

            # Check final state
            assert self.worker._cumulative_processed_bytes == total_size, (
                f"Expected {total_size} bytes processed, got {self.worker._cumulative_processed_bytes}"
            )

    def test_worker_cancellation(self):
        """Test that worker can be cancelled properly."""
        files = []

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create multiple files
            for i in range(5):
                file_path = os.path.join(temp_dir, f"cancel_test_{i}.txt")
                with open(file_path, "wb") as f:
                    f.write(b"C" * 10000)
                files.append(file_path)

            total_size = 50000

            # Setup worker
            self.worker.setup_checksum_calculation(files)
            self.worker.set_total_size(total_size)

            # Start worker
            self.worker.start()

            # Let it run briefly then cancel
            time.sleep(0.1)
            self.worker.cancel()

            # Wait for cancellation
            deadline = time.time() + 5
            while self.worker.isRunning() and time.time() < deadline:
                QCoreApplication.processEvents()
                time.sleep(0.01)

            # Should have stopped
            assert not self.worker.isRunning(), "Worker should have stopped after cancellation"

            # Check that cancellation flag is set
            assert self.worker.is_cancelled(), "Worker should report as cancelled"

    def test_multiple_operations_state_reset(self):
        """Test that worker state is properly reset between operations."""
        files = []

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            for i in range(3):
                file_path = os.path.join(temp_dir, f"reset_test_{i}.txt")
                with open(file_path, "wb") as f:
                    f.write(b"D" * 5000)
                files.append(file_path)

            total_size = 15000

            # First operation
            self.worker.setup_checksum_calculation(files)
            self.worker.set_total_size(total_size)

            self.worker.start()
            deadline = time.time() + 10
            while self.worker.isRunning() and time.time() < deadline:
                QCoreApplication.processEvents()
                time.sleep(0.01)

            if self.worker.isRunning():
                self.worker.cancel()
                self.worker.wait(2000)

            # Check first operation completed
            first_result = self.worker._cumulative_processed_bytes
            assert first_result == total_size

            # Second operation with different setup
            self.worker.setup_duplicate_scan(files[:2])  # Only 2 files
            self.worker.set_total_size(10000)  # Different total

            # Check that state was reset
            assert self.worker._cumulative_processed_bytes == 0
            assert self.worker._total_bytes == 10000

            self.worker.start()
            deadline = time.time() + 10
            while self.worker.isRunning() and time.time() < deadline:
                QCoreApplication.processEvents()
                time.sleep(0.01)

            if self.worker.isRunning():
                self.worker.cancel()
                self.worker.wait(2000)

            # Check second operation completed correctly
            assert self.worker._cumulative_processed_bytes == 10000


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
