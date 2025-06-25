"""
test_hash_worker_progress.py

Tests for HashWorker cumulative progress tracking.
Ensures that progress never goes backwards and accumulates correctly.
"""

import os
import tempfile
import pytest
import time
from PyQt5.QtCore import QCoreApplication

from core.hash_worker import HashWorker


class TestHashWorkerProgress:
    """Test HashWorker cumulative progress tracking fixes."""

    def setup_method(self):
        """Set up test fixtures."""
        self.worker = HashWorker()
        self.progress_updates = []
        self.size_updates = []

        # Connect signals to capture updates
        self.worker.progress_updated.connect(self._capture_progress)
        self.worker.size_progress.connect(self._capture_size_progress)

    def _capture_progress(self, current, total, filename):
        """Capture progress updates for testing."""
        self.progress_updates.append((current, total, filename))

    def _capture_size_progress(self, processed, total):
        """Capture size progress updates for testing."""
        self.size_updates.append((processed, total))

    def teardown_method(self):
        """Clean up after tests."""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(1000)  # Wait up to 1 second

    def test_cumulative_progress_basic(self):
        """Test basic cumulative progress functionality."""
        files = []

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files with larger sizes to ensure progress tracking
            for i, size in enumerate([10000, 20000, 30000]):  # 10KB, 20KB, 30KB
                file_path = os.path.join(temp_dir, f"test_file_{i}.txt")
                with open(file_path, 'wb') as f:
                    f.write(b'A' * size)  # Write size bytes
                files.append(file_path)

            total_size = 60000

            # Setup worker for checksum calculation
            self.worker.setup_checksum_calculation(files)
            self.worker.set_total_size(total_size)

            # Start worker
            self.worker.start()

            # Wait for completion with event processing
            deadline = time.time() + 10  # 10 second timeout
            while self.worker.isRunning() and time.time() < deadline:
                QCoreApplication.processEvents()
                time.sleep(0.01)

            # Ensure worker finished
            if self.worker.isRunning():
                self.worker.cancel()
                self.worker.wait(1000)

            # Give signals time to arrive
            for _ in range(10):  # Process events for signal delivery
                QCoreApplication.processEvents()
                time.sleep(0.01)

            print(f"Debug: Received {len(self.size_updates)} size updates")
            print(f"Debug: Size updates: {self.size_updates}")

            # Test 1: We should get at least the final completion signal
            assert len(self.size_updates) >= 1, f"Expected at least 1 progress update, got {len(self.size_updates)}"

            # Test 2: Progress should never go backwards
            last_processed = 0
            for processed, total in self.size_updates:
                assert processed >= last_processed, f"Progress went backwards: {processed} < {last_processed}"
                assert processed <= total_size, f"Progress exceeded total: {processed} > {total_size}"
                last_processed = processed

            # Test 3: Final progress should equal total size
            final_processed, final_total = self.size_updates[-1]
            assert final_processed == total_size, f"Final progress mismatch: {final_processed} != {total_size}"

    def test_multiple_files_cumulative_progress(self):
        """Test cumulative progress with multiple files."""
        files = []

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create 5 small files to ensure we get per-file progress updates
            sizes = [5000, 8000, 12000, 15000, 20000]  # Various sizes
            for i, size in enumerate(sizes):
                file_path = os.path.join(temp_dir, f"multi_file_{i}.txt")
                with open(file_path, 'wb') as f:
                    f.write(b'B' * size)
                files.append(file_path)

            total_expected = sum(sizes)  # 60000 bytes total

            # Setup and run worker
            self.worker.setup_checksum_calculation(files)
            self.worker.set_total_size(total_expected)

            self.worker.start()

            # Wait with event processing
            deadline = time.time() + 10
            while self.worker.isRunning() and time.time() < deadline:
                QCoreApplication.processEvents()
                time.sleep(0.01)

            if self.worker.isRunning():
                self.worker.cancel()
                self.worker.wait(1000)

            # Process remaining events
            for _ in range(10):
                QCoreApplication.processEvents()
                time.sleep(0.01)

            print(f"Debug: Multiple files test - {len(self.size_updates)} updates")

            # Verify monotonic increase
            if len(self.size_updates) > 1:
                last_processed = 0
                for processed, total in self.size_updates:
                    assert processed >= last_processed
                    last_processed = processed

            # Should reach total
            assert len(self.size_updates) >= 1
            final_processed, final_total = self.size_updates[-1]
            assert final_processed == total_expected

    def test_worker_state_consistency(self):
        """Test that internal worker state remains consistent."""
        files = []

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            file_path = os.path.join(temp_dir, "consistency_test.txt")
            with open(file_path, 'wb') as f:
                f.write(b'C' * 15000)  # 15KB file
            files.append(file_path)

            # Setup worker
            self.worker.setup_duplicate_scan(files)
            self.worker.set_total_size(15000)

            # Check initial state
            assert self.worker._cumulative_processed_bytes == 0
            assert self.worker._total_bytes == 15000

            # Start worker
            self.worker.start()

            # Wait for completion
            deadline = time.time() + 10
            while self.worker.isRunning() and time.time() < deadline:
                QCoreApplication.processEvents()
                time.sleep(0.01)

            if self.worker.isRunning():
                self.worker.cancel()
                self.worker.wait(1000)

            # Process events
            for _ in range(10):
                QCoreApplication.processEvents()
                time.sleep(0.01)

            print(f"Debug: State consistency test - {len(self.size_updates)} updates")

            # After completion, should have progress updates
            assert len(self.size_updates) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
