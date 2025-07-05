#!/usr/bin/env python3
"""
test_batch_optimization.py

Author: Michael Economou
Date: 2025-01-31

Test script to demonstrate the Batch Operations Optimization system.
Shows performance improvements for metadata and hash operations.

Usage:
    python test_batch_optimization.py
"""

import sys
import os
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.batch_operations_manager import BatchOperationsManager, BatchStats
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class MockMetadataCache:
    """Mock metadata cache for testing."""

    def __init__(self):
        self.operations = []
        self.batch_mode = False

    def set(self, file_path: str, metadata: dict, is_extended: bool = False):
        """Mock metadata set operation."""
        operation_time = 0.01  # Simulate 10ms per operation
        time.sleep(operation_time)

        self.operations.append({
            'type': 'metadata_set',
            'file_path': file_path,
            'metadata': metadata,
            'is_extended': is_extended,
            'timestamp': time.time()
        })

        logger.debug(f"[MockCache] Set metadata for: {os.path.basename(file_path)}")

    def begin_batch(self):
        """Begin batch mode."""
        self.batch_mode = True
        logger.debug("[MockCache] Begin batch mode")

    def commit_batch(self):
        """Commit batch mode."""
        self.batch_mode = False
        logger.debug("[MockCache] Commit batch mode")

    def rollback_batch(self):
        """Rollback batch mode."""
        self.batch_mode = False
        logger.debug("[MockCache] Rollback batch mode")


class MockHashCache:
    """Mock hash cache for testing."""

    def __init__(self):
        self.operations = []
        self.batch_mode = False

    def store_hash(self, file_path: str, hash_value: str, algorithm: str = 'md5'):
        """Mock hash store operation."""
        operation_time = 0.008  # Simulate 8ms per operation
        time.sleep(operation_time)

        self.operations.append({
            'type': 'hash_store',
            'file_path': file_path,
            'hash_value': hash_value,
            'algorithm': algorithm,
            'timestamp': time.time()
        })

        logger.debug(f"[MockHashCache] Stored hash for: {os.path.basename(file_path)}")

    def begin_batch(self):
        """Begin batch mode."""
        self.batch_mode = True
        logger.debug("[MockHashCache] Begin batch mode")

    def commit_batch(self):
        """Commit batch mode."""
        self.batch_mode = False
        logger.debug("[MockHashCache] Commit batch mode")

    def rollback_batch(self):
        """Rollback batch mode."""
        self.batch_mode = False
        logger.debug("[MockHashCache] Rollback batch mode")


class MockMainWindow:
    """Mock main window for testing."""

    def __init__(self):
        self.metadata_cache = MockMetadataCache()
        self.hash_cache = MockHashCache()
        self.db_manager = None  # Not needed for this test


def test_individual_operations(file_count: int = 100) -> float:
    """Test individual operations without batching."""
    print(f"\n🔄 Testing {file_count} individual operations...")

    # Create mock window and cache
    mock_window = MockMainWindow()

    # Generate test data
    test_files = [f"/test/path/file_{i:03d}.jpg" for i in range(file_count)]
    test_metadata = [{'camera': f'Camera_{i}', 'date': f'2025-01-{i%30+1:02d}'} for i in range(file_count)]
    test_hashes = [f"hash_{i:032x}" for i in range(file_count)]

    start_time = time.time()

    # Perform individual metadata operations
    for i, (file_path, metadata) in enumerate(zip(test_files, test_metadata)):
        mock_window.metadata_cache.set(file_path, metadata, is_extended=i % 3 == 0)

    # Perform individual hash operations
    for file_path, hash_value in zip(test_files, test_hashes):
        mock_window.hash_cache.store_hash(file_path, hash_value, 'crc32')

    total_time = time.time() - start_time

    print(f"✅ Individual operations completed in {total_time:.3f}s")
    print(f"   - Metadata operations: {len(mock_window.metadata_cache.operations)}")
    print(f"   - Hash operations: {len(mock_window.hash_cache.operations)}")
    print(f"   - Average time per operation: {(total_time / (file_count * 2)) * 1000:.1f}ms")

    return total_time


def test_batch_operations(file_count: int = 100) -> tuple[float, BatchStats]:
    """Test batch operations with optimization."""
    print(f"\n⚡ Testing {file_count} batch operations...")

    # Create mock window and batch manager
    mock_window = MockMainWindow()
    batch_manager = BatchOperationsManager(mock_window)

    # Configure for faster batching in test
    batch_manager.set_config(
        max_batch_size=25,  # Smaller batches for testing
        max_batch_age=0.5,  # Faster auto-flush
        auto_flush=True
    )

    # Generate test data
    test_files = [f"/test/path/file_{i:03d}.jpg" for i in range(file_count)]
    test_metadata = [{'camera': f'Camera_{i}', 'date': f'2025-01-{i%30+1:02d}'} for i in range(file_count)]
    test_hashes = [f"hash_{i:032x}" for i in range(file_count)]

    start_time = time.time()

    # Queue metadata operations for batching
    for i, (file_path, metadata) in enumerate(zip(test_files, test_metadata)):
        batch_manager.queue_metadata_set(
            file_path=file_path,
            metadata=metadata,
            is_extended=i % 3 == 0,
            priority=10
        )

    # Queue hash operations for batching
    for file_path, hash_value in zip(test_files, test_hashes):
        batch_manager.queue_hash_store(
            file_path=file_path,
            hash_value=hash_value,
            algorithm='crc32',
            priority=10
        )

    # Flush all batches
    results = batch_manager.flush_all()

    total_time = time.time() - start_time
    stats = batch_manager.get_stats()

    print(f"✅ Batch operations completed in {total_time:.3f}s")
    print(f"   - Batches flushed: {results}")
    print(f"   - Total batched operations: {stats.batched_operations}")
    print(f"   - Number of batch flushes: {stats.batch_flushes}")
    print(f"   - Average batch size: {stats.average_batch_size:.1f}")
    print(f"   - Estimated time saved: {stats.total_time_saved:.3f}s")
    print(f"   - Metadata operations: {len(mock_window.metadata_cache.operations)}")
    print(f"   - Hash operations: {len(mock_window.hash_cache.operations)}")

    return total_time, stats


def test_mixed_priority_operations() -> None:
    """Test operations with different priorities."""
    print(f"\n🎯 Testing mixed priority operations...")

    mock_window = MockMainWindow()
    batch_manager = BatchOperationsManager(mock_window)

    # Configure for manual flushing
    batch_manager.set_config(auto_flush=False)

    # Queue operations with different priorities
    files_high = [f"/high/priority/file_{i}.jpg" for i in range(5)]
    files_low = [f"/low/priority/file_{i}.jpg" for i in range(5)]

    # Queue low priority first
    for file_path in files_low:
        batch_manager.queue_metadata_set(
            file_path=file_path,
            metadata={'priority': 'low'},
            priority=90  # Low priority
        )

    # Queue high priority after
    for file_path in files_high:
        batch_manager.queue_metadata_set(
            file_path=file_path,
            metadata={'priority': 'high'},
            priority=10  # High priority
        )

    # Flush and check order
    results = batch_manager.flush_all()

    print(f"✅ Mixed priority test completed")
    print(f"   - Operations processed: {results}")
    print(f"   - Check logs to verify high priority files processed first")


def test_auto_flush_behavior() -> None:
    """Test automatic flush behavior."""
    print(f"\n⏰ Testing auto-flush behavior...")

    mock_window = MockMainWindow()
    batch_manager = BatchOperationsManager(mock_window)

    # Configure for aggressive auto-flushing
    batch_manager.set_config(
        max_batch_size=3,  # Very small batch size
        max_batch_age=1.0,  # 1 second max age
        auto_flush=True
    )

    print("   - Adding operations one by one (watch for auto-flush)...")

    # Add operations slowly to trigger auto-flush
    for i in range(8):
        batch_manager.queue_metadata_set(
            file_path=f"/auto/flush/file_{i}.jpg",
            metadata={'index': i},
            priority=50
        )

        # Check pending operations
        pending = batch_manager.get_pending_operations()
        print(f"     Operation {i+1}: Pending = {pending}")

        # Small delay to see auto-flush in action
        time.sleep(0.2)

    # Final flush
    final_results = batch_manager.flush_all()
    final_stats = batch_manager.get_stats()

    print(f"✅ Auto-flush test completed")
    print(f"   - Final flush results: {final_results}")
    print(f"   - Total batch flushes: {final_stats.batch_flushes}")


def main():
    """Main test function."""
    print("🚀 Batch Operations Optimization Test Suite")
    print("=" * 50)

    # Test different file counts
    test_counts = [50, 100, 200]

    for count in test_counts:
        print(f"\n📊 Performance Comparison - {count} files")
        print("-" * 40)

        # Test individual operations
        individual_time = test_individual_operations(count)

        # Test batch operations
        batch_time, batch_stats = test_batch_operations(count)

        # Calculate improvement
        improvement = ((individual_time - batch_time) / individual_time) * 100
        speedup = individual_time / batch_time if batch_time > 0 else 0

        print(f"\n📈 Performance Results:")
        print(f"   - Individual time: {individual_time:.3f}s")
        print(f"   - Batch time: {batch_time:.3f}s")
        print(f"   - Improvement: {improvement:.1f}%")
        print(f"   - Speedup: {speedup:.2f}x")
        print(f"   - Time saved: {individual_time - batch_time:.3f}s")

    # Test special cases
    test_mixed_priority_operations()
    test_auto_flush_behavior()

    print(f"\n🎉 All tests completed!")
    print("Check the logs above to see batch optimization in action.")


if __name__ == "__main__":
    main()
