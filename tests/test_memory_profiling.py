"""
Memory Profiling Test Suite

This module provides detailed memory usage analysis and leak detection
for OnCutF optimization systems. It helps identify memory bottlenecks
and validates memory optimization improvements.

Features:
- Memory leak detection
- Memory usage profiling
- Cache efficiency analysis
- Memory growth tracking
- Detailed memory reports

Author: Michael Economou
Date: 2025-07-06
"""

import gc
import time
import psutil
import threading
import tracemalloc
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import unittest

# Import optimization systems
from core.memory_manager import MemoryManager, LRUCache
from utils.smart_icon_cache import SmartIconCache
from core.optimized_database_manager import OptimizedDatabaseManager
from core.async_operations_manager import AsyncOperationsManager
from core.thread_pool_manager import ThreadPoolManager
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


@dataclass
class MemorySnapshot:
    """Represents a memory usage snapshot."""
    timestamp: float
    rss_mb: float
    vms_mb: float
    percent: float
    tracemalloc_current: Optional[int] = None
    tracemalloc_peak: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp,
            'rss_mb': self.rss_mb,
            'vms_mb': self.vms_mb,
            'percent': self.percent,
            'tracemalloc_current': self.tracemalloc_current,
            'tracemalloc_peak': self.tracemalloc_peak
        }


@dataclass
class MemoryProfileResult:
    """Results from memory profiling."""
    test_name: str
    initial_memory: MemorySnapshot
    peak_memory: MemorySnapshot
    final_memory: MemorySnapshot
    snapshots: List[MemorySnapshot] = field(default_factory=list)

    @property
    def memory_growth_mb(self) -> float:
        """Calculate memory growth from initial to final."""
        return self.final_memory.rss_mb - self.initial_memory.rss_mb

    @property
    def peak_memory_usage_mb(self) -> float:
        """Get peak memory usage."""
        return self.peak_memory.rss_mb

    @property
    def memory_efficiency_score(self) -> float:
        """Calculate memory efficiency score (0-100)."""
        if self.memory_growth_mb <= 0:
            return 100.0

        # Score based on memory growth relative to initial memory
        growth_ratio = self.memory_growth_mb / self.initial_memory.rss_mb
        score = max(0, 100 - (growth_ratio * 100))
        return min(100, score)


class MemoryProfiler:
    """Advanced memory profiler for optimization systems."""

    def __init__(self, enable_tracemalloc: bool = True):
        """
        Initialize memory profiler.

        Args:
            enable_tracemalloc: Whether to enable detailed memory tracing
        """
        self.enable_tracemalloc = enable_tracemalloc
        self.process = psutil.Process()
        self.monitoring = False
        self.snapshots = []
        self.monitor_thread = None

        if enable_tracemalloc:
            tracemalloc.start()

    def take_snapshot(self) -> MemorySnapshot:
        """Take a memory usage snapshot."""
        memory_info = self.process.memory_info()
        memory_percent = self.process.memory_percent()

        snapshot = MemorySnapshot(
            timestamp=time.time(),
            rss_mb=memory_info.rss / (1024 * 1024),
            vms_mb=memory_info.vms / (1024 * 1024),
            percent=memory_percent
        )

        if self.enable_tracemalloc:
            current, peak = tracemalloc.get_traced_memory()
            snapshot.tracemalloc_current = current
            snapshot.tracemalloc_peak = peak

        return snapshot

    def start_monitoring(self, interval: float = 0.5):
        """Start continuous memory monitoring."""
        self.monitoring = True
        self.snapshots = []
        self.monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval,))
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def stop_monitoring(self) -> List[MemorySnapshot]:
        """Stop monitoring and return collected snapshots."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)

        return self.snapshots.copy()

    def _monitor_loop(self, interval: float):
        """Monitoring loop running in separate thread."""
        while self.monitoring:
            try:
                snapshot = self.take_snapshot()
                self.snapshots.append(snapshot)
                time.sleep(interval)
            except Exception as e:
                logger.error(f"[MemoryProfiler] Monitoring error: {e}")
                break

    def profile_function(self, test_name: str, func: callable, *args, **kwargs) -> MemoryProfileResult:
        """
        Profile memory usage of a function.

        Args:
            test_name: Name of the test
            func: Function to profile
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Memory profile result
        """
        # Force garbage collection before profiling
        gc.collect()

        # Take initial snapshot
        initial_snapshot = self.take_snapshot()

        # Start monitoring
        self.start_monitoring()

        try:
            # Execute function
            result = func(*args, **kwargs)

            # Force garbage collection after execution
            gc.collect()

        finally:
            # Stop monitoring
            snapshots = self.stop_monitoring()

            # Take final snapshot
            final_snapshot = self.take_snapshot()

        # Find peak memory usage
        peak_snapshot = max(snapshots + [initial_snapshot, final_snapshot],
                           key=lambda s: s.rss_mb)

        return MemoryProfileResult(
            test_name=test_name,
            initial_memory=initial_snapshot,
            peak_memory=peak_snapshot,
            final_memory=final_snapshot,
            snapshots=snapshots
        )

    def detect_memory_leaks(self, baseline_mb: float, threshold_mb: float = 5.0) -> bool:
        """
        Detect potential memory leaks.

        Args:
            baseline_mb: Baseline memory usage
            threshold_mb: Leak detection threshold

        Returns:
            True if potential leak detected
        """
        current_snapshot = self.take_snapshot()
        growth = current_snapshot.rss_mb - baseline_mb

        return growth > threshold_mb

    def get_top_memory_allocations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top memory allocations using tracemalloc."""
        if not self.enable_tracemalloc:
            return []

        try:
            snapshot = tracemalloc.take_snapshot()
            top_stats = snapshot.statistics('lineno')

            allocations = []
            for stat in top_stats[:limit]:
                allocations.append({
                    'size_mb': stat.size / (1024 * 1024),
                    'count': stat.count,
                    'filename': stat.traceback.format()[0] if stat.traceback else 'unknown'
                })

            return allocations

        except Exception as e:
            logger.error(f"[MemoryProfiler] Error getting allocations: {e}")
            return []


class MemoryStressTests:
    """Memory stress tests for optimization systems."""

    def __init__(self):
        """Initialize memory stress tests."""
        self.profiler = MemoryProfiler()

    def test_lru_cache_memory_efficiency(self, cache_size: int = 1000,
                                       operations: int = 10000) -> MemoryProfileResult:
        """Test LRU cache memory efficiency under stress."""

        def stress_test():
            cache = LRUCache(max_size=cache_size, max_memory_mb=50.0)

            # Fill cache with varying data sizes
            for i in range(operations):
                key = f"key_{i % (cache_size // 2)}"
                value = f"value_{i}" * (i % 100 + 1)  # Varying sizes
                cache.set(key, value, len(value))

            # Access patterns to trigger evictions
            for i in range(operations // 2):
                key = f"key_{i % cache_size}"
                cache.get(key)

            return cache.get_stats()

        return self.profiler.profile_function("LRU_Cache_Memory_Stress", stress_test)

    def test_icon_cache_memory_growth(self, icons_count: int = 500) -> MemoryProfileResult:
        """Test icon cache memory growth patterns."""

        def stress_test():
            from core.qt_imports import QSize

            icon_cache = SmartIconCache(max_entries=200, max_memory_mb=20.0)

            # Load many icons with different sizes
            icon_names = ['file', 'folder', 'image', 'video', 'audio', 'document']
            sizes = [QSize(16, 16), QSize(24, 24), QSize(32, 32), QSize(48, 48), QSize(64, 64)]

            for i in range(icons_count):
                icon_name = icon_names[i % len(icon_names)]
                size = sizes[i % len(sizes)]
                icon = icon_cache.get_icon(icon_name, size)

            stats = icon_cache.get_stats()
            icon_cache.shutdown()

            return stats

        return self.profiler.profile_function("Icon_Cache_Memory_Growth", stress_test)

    def test_database_connection_pool_memory(self, connections: int = 10,
                                           queries: int = 1000) -> MemoryProfileResult:
        """Test database connection pool memory usage."""

        def stress_test():
            import tempfile
            import os

            with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
                db_path = tmp.name

            try:
                db_manager = OptimizedDatabaseManager(db_path, max_connections=connections)

                # Create test data
                test_data = [(i, f"data_{i}") for i in range(queries)]

                # Stress test with many queries
                for batch_start in range(0, queries, 100):
                    batch_end = min(batch_start + 100, queries)
                    batch = test_data[batch_start:batch_end]

                    db_manager.execute_batch(
                        "INSERT OR REPLACE INTO test_table (id, data) VALUES (?, ?)",
                        batch
                    )

                # Query stress test
                for i in range(queries // 10):
                    db_manager.execute_query(
                        "SELECT * FROM test_table WHERE id = ?",
                        (i,)
                    )

                stats = db_manager.get_query_stats()
                db_manager.close()

                return stats

            finally:
                os.unlink(db_path)

        return self.profiler.profile_function("Database_Pool_Memory_Stress", stress_test)

    def test_async_operations_memory_scaling(self, operations: int = 100) -> MemoryProfileResult:
        """Test async operations memory scaling."""

        def stress_test():
            import asyncio

            async def async_stress_test():
                async_manager = AsyncOperationsManager(max_workers=6)

                # Submit many async operations
                operation_ids = []
                for i in range(operations):
                    async def mock_operation(op_id=i):
                        await asyncio.sleep(0.01)
                        return f"result_{op_id}"

                    op_id = f"stress_op_{i}"
                    async_manager.task_manager.submit_task(op_id, mock_operation(), 'stress_test')
                    operation_ids.append(op_id)

                # Wait for completion
                await asyncio.sleep(3.0)

                stats = async_manager.get_stats()
                async_manager.shutdown()

                return stats

            return asyncio.run(async_stress_test())

        return self.profiler.profile_function("Async_Operations_Memory_Scaling", stress_test)

    def test_thread_pool_memory_overhead(self, tasks: int = 200) -> MemoryProfileResult:
        """Test thread pool memory overhead."""

        def stress_test():
            thread_pool = ThreadPoolManager(min_threads=4, max_threads=12)

            def memory_intensive_task(task_id: int) -> str:
                # Create some temporary data
                data = [f"data_{task_id}_{i}" for i in range(1000)]
                time.sleep(0.01)
                return f"task_{task_id}_completed"

            # Submit many tasks
            for i in range(tasks):
                thread_pool.submit_task(
                    f"memory_task_{i}",
                    memory_intensive_task,
                    args=(i,)
                )

            # Wait for completion
            start_time = time.time()
            while time.time() - start_time < 15.0:
                stats = thread_pool.get_stats()
                if stats.completed_tasks >= tasks:
                    break
                time.sleep(0.1)

            final_stats = thread_pool.get_stats()
            thread_pool.shutdown()

            return final_stats

        return self.profiler.profile_function("Thread_Pool_Memory_Overhead", stress_test)

    def test_memory_manager_effectiveness(self, cache_count: int = 5,
                                        entries_per_cache: int = 2000) -> MemoryProfileResult:
        """Test memory manager effectiveness with multiple caches."""

        def stress_test():
            memory_manager = MemoryManager()
            memory_manager.configure(
                memory_threshold_percent=70.0,
                cleanup_interval_seconds=1,
                cache_max_age_seconds=5,
                min_access_count=1
            )

            # Create multiple test caches
            caches = []
            for cache_id in range(cache_count):
                cache = {}
                for entry_id in range(entries_per_cache):
                    key = f"cache_{cache_id}_entry_{entry_id}"
                    value = f"data_{entry_id}" * (entry_id % 50 + 1)
                    cache[key] = value

                caches.append(cache)
                memory_manager.register_cache(f"test_cache_{cache_id}", cache)

            # Let memory manager work
            time.sleep(3.0)

            # Force cleanup
            cleaned = memory_manager.force_cleanup()

            # Get final statistics
            stats = memory_manager.get_cleanup_stats()
            memory_manager.shutdown()

            return {
                'caches_created': cache_count,
                'entries_per_cache': entries_per_cache,
                'cleaned_entries': cleaned,
                'cleanup_stats': stats
            }

        return self.profiler.profile_function("Memory_Manager_Effectiveness", stress_test)


class MemoryLeakDetector:
    """Detects memory leaks in optimization systems."""

    def __init__(self, threshold_mb: float = 10.0):
        """
        Initialize memory leak detector.

        Args:
            threshold_mb: Memory growth threshold for leak detection
        """
        self.threshold_mb = threshold_mb
        self.profiler = MemoryProfiler()
        self.baseline_memory = None

    def establish_baseline(self):
        """Establish memory usage baseline."""
        gc.collect()
        self.baseline_memory = self.profiler.take_snapshot()
        logger.info(f"[MemoryLeakDetector] Baseline established: {self.baseline_memory.rss_mb:.1f} MB")

    def check_for_leaks(self, operation_name: str) -> Dict[str, Any]:
        """
        Check for memory leaks after an operation.

        Args:
            operation_name: Name of the operation to check

        Returns:
            Leak detection results
        """
        if self.baseline_memory is None:
            self.establish_baseline()

        gc.collect()
        current_memory = self.profiler.take_snapshot()

        memory_growth = current_memory.rss_mb - self.baseline_memory.rss_mb
        leak_detected = memory_growth > self.threshold_mb

        result = {
            'operation': operation_name,
            'baseline_mb': self.baseline_memory.rss_mb,
            'current_mb': current_memory.rss_mb,
            'growth_mb': memory_growth,
            'leak_detected': leak_detected,
            'threshold_mb': self.threshold_mb
        }

        if leak_detected:
            logger.warning(f"[MemoryLeakDetector] Potential leak in {operation_name}: "
                         f"{memory_growth:.1f} MB growth")

            # Get top allocations for leak analysis
            allocations = self.profiler.get_top_memory_allocations()
            result['top_allocations'] = allocations

        return result

    def run_leak_detection_suite(self) -> List[Dict[str, Any]]:
        """Run comprehensive leak detection suite."""
        self.establish_baseline()

        leak_results = []
        stress_tests = MemoryStressTests()

        # Test each optimization system for leaks
        test_functions = [
            ('LRU_Cache', lambda: stress_tests.test_lru_cache_memory_efficiency(500, 5000)),
            ('Icon_Cache', lambda: stress_tests.test_icon_cache_memory_growth(200)),
            ('Database_Pool', lambda: stress_tests.test_database_connection_pool_memory(5, 500)),
            ('Async_Operations', lambda: stress_tests.test_async_operations_memory_scaling(50)),
            ('Thread_Pool', lambda: stress_tests.test_thread_pool_memory_overhead(100)),
            ('Memory_Manager', lambda: stress_tests.test_memory_manager_effectiveness(3, 1000))
        ]

        for test_name, test_func in test_functions:
            try:
                # Run test
                test_func()

                # Check for leaks
                leak_result = self.check_for_leaks(test_name)
                leak_results.append(leak_result)

                # Wait between tests
                time.sleep(1.0)

            except Exception as e:
                logger.error(f"[MemoryLeakDetector] Error testing {test_name}: {e}")
                leak_results.append({
                    'operation': test_name,
                    'error': str(e),
                    'leak_detected': False
                })

        return leak_results


class MemoryProfilingTestSuite(unittest.TestCase):
    """Comprehensive memory profiling test suite."""

    def setUp(self):
        """Set up memory profiling tests."""
        self.stress_tests = MemoryStressTests()
        self.leak_detector = MemoryLeakDetector(threshold_mb=15.0)
        logger.info("[MemoryProfilingTestSuite] Starting memory profiling tests...")

    def test_memory_efficiency_benchmarks(self):
        """Test memory efficiency of all optimization systems."""
        results = []

        # LRU Cache memory efficiency
        lru_result = self.stress_tests.test_lru_cache_memory_efficiency()
        results.append(lru_result)
        self.assertLess(lru_result.memory_growth_mb, 50.0, "LRU cache memory growth too high")

        # Icon cache memory growth
        icon_result = self.stress_tests.test_icon_cache_memory_growth()
        results.append(icon_result)
        self.assertLess(icon_result.memory_growth_mb, 30.0, "Icon cache memory growth too high")

        # Database pool memory
        db_result = self.stress_tests.test_database_connection_pool_memory()
        results.append(db_result)
        self.assertLess(db_result.memory_growth_mb, 25.0, "Database pool memory growth too high")

        # Print results summary
        print("\n" + "="*50)
        print("MEMORY EFFICIENCY RESULTS")
        print("="*50)
        for result in results:
            efficiency_score = result.memory_efficiency_score
            print(f"{result.test_name}:")
            print(f"  Memory Growth: {result.memory_growth_mb:.1f} MB")
            print(f"  Peak Usage: {result.peak_memory_usage_mb:.1f} MB")
            print(f"  Efficiency Score: {efficiency_score:.1f}/100")
            print()

    def test_memory_leak_detection(self):
        """Test for memory leaks in optimization systems."""
        leak_results = self.leak_detector.run_leak_detection_suite()

        # Check results
        leaks_detected = [r for r in leak_results if r.get('leak_detected', False)]

        print("\n" + "="*50)
        print("MEMORY LEAK DETECTION RESULTS")
        print("="*50)

        for result in leak_results:
            if 'error' in result:
                print(f"{result['operation']}: ERROR - {result['error']}")
            else:
                status = "LEAK DETECTED" if result['leak_detected'] else "OK"
                print(f"{result['operation']}: {status}")
                print(f"  Growth: {result['growth_mb']:.1f} MB")

                if result['leak_detected'] and 'top_allocations' in result:
                    print("  Top Allocations:")
                    for alloc in result['top_allocations'][:3]:
                        print(f"    {alloc['size_mb']:.1f} MB - {alloc['filename']}")
                print()

        # Assert no major leaks detected
        self.assertLess(len(leaks_detected), 2, f"Too many memory leaks detected: {len(leaks_detected)}")

    def test_memory_scalability(self):
        """Test memory usage scalability under increasing load."""

        # Test with different load levels
        load_levels = [
            {'cache_size': 500, 'operations': 2000, 'name': 'Light'},
            {'cache_size': 1000, 'operations': 5000, 'name': 'Medium'},
            {'cache_size': 2000, 'operations': 10000, 'name': 'Heavy'}
        ]

        scalability_results = []

        for load in load_levels:
            result = self.stress_tests.test_lru_cache_memory_efficiency(
                cache_size=load['cache_size'],
                operations=load['operations']
            )
            scalability_results.append((load['name'], result))

        print("\n" + "="*50)
        print("MEMORY SCALABILITY RESULTS")
        print("="*50)

        for load_name, result in scalability_results:
            print(f"{load_name} Load:")
            print(f"  Memory Growth: {result.memory_growth_mb:.1f} MB")
            print(f"  Peak Usage: {result.peak_memory_usage_mb:.1f} MB")
            print(f"  Efficiency Score: {result.memory_efficiency_score:.1f}/100")
            print()

        # Verify scalability (memory growth should be reasonable)
        for load_name, result in scalability_results:
            self.assertLess(result.memory_growth_mb, 100.0,
                          f"Memory growth too high for {load_name} load")


def run_memory_profiling_tests():
    """Run memory profiling test suite."""
    suite = unittest.TestLoader().loadTestsFromTestCase(MemoryProfilingTestSuite)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_memory_profiling_tests()
    exit(0 if success else 1)
