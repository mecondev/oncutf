"""
Performance Benchmarking Suite

This module provides comprehensive performance benchmarking for all OnCutF
optimization systems. It measures performance improvements and generates
detailed reports comparing optimized vs baseline implementations.

Features:
- Memory usage benchmarking
- Database performance testing
- Icon caching performance
- Async operations benchmarking
- Thread pool performance
- Integration scenario testing
- Automated report generation

Author: Michael Economou
Date: 2025-07-06
"""

import time
import psutil
import gc
import threading
import tempfile
import os
import json
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from pathlib import Path
from contextlib import contextmanager
import unittest
from unittest.mock import Mock, patch

# Import optimization systems
from core.memory_manager import MemoryManager, LRUCache
from utils.smart_icon_cache import SmartIconCache
from core.optimized_database_manager import OptimizedDatabaseManager
from core.async_operations_manager import AsyncOperationsManager
from core.thread_pool_manager import ThreadPoolManager, TaskPriority
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


@dataclass
class BenchmarkResult:
    """Represents a benchmark test result."""
    test_name: str
    duration: float
    memory_usage_mb: float
    cpu_usage_percent: float
    operations_per_second: float
    success_rate: float
    additional_metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'test_name': self.test_name,
            'duration': self.duration,
            'memory_usage_mb': self.memory_usage_mb,
            'cpu_usage_percent': self.cpu_usage_percent,
            'operations_per_second': self.operations_per_second,
            'success_rate': self.success_rate,
            'additional_metrics': self.additional_metrics
        }


@dataclass
class ComparisonResult:
    """Represents a comparison between baseline and optimized implementations."""
    test_name: str
    baseline_result: BenchmarkResult
    optimized_result: BenchmarkResult

    @property
    def performance_improvement(self) -> float:
        """Calculate performance improvement percentage."""
        if self.baseline_result.operations_per_second == 0:
            return 0.0
        return ((self.optimized_result.operations_per_second - self.baseline_result.operations_per_second)
                / self.baseline_result.operations_per_second) * 100

    @property
    def memory_improvement(self) -> float:
        """Calculate memory usage improvement percentage."""
        if self.baseline_result.memory_usage_mb == 0:
            return 0.0
        return ((self.baseline_result.memory_usage_mb - self.optimized_result.memory_usage_mb)
                / self.baseline_result.memory_usage_mb) * 100

    @property
    def speed_improvement(self) -> float:
        """Calculate speed improvement percentage."""
        if self.baseline_result.duration == 0:
            return 0.0
        return ((self.baseline_result.duration - self.optimized_result.duration)
                / self.baseline_result.duration) * 100


class PerformanceMonitor:
    """Monitors system performance during benchmarks."""

    def __init__(self):
        """Initialize performance monitor."""
        self.process = psutil.Process()
        self.monitoring = False
        self.samples = []
        self.monitor_thread = None

    def start_monitoring(self, interval: float = 0.1):
        """Start performance monitoring."""
        self.monitoring = True
        self.samples = []
        self.monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval,))
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def stop_monitoring(self) -> Dict[str, float]:
        """Stop monitoring and return average metrics."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)

        if not self.samples:
            return {'memory_mb': 0.0, 'cpu_percent': 0.0}

        avg_memory = sum(s['memory_mb'] for s in self.samples) / len(self.samples)
        avg_cpu = sum(s['cpu_percent'] for s in self.samples) / len(self.samples)

        return {
            'memory_mb': avg_memory,
            'cpu_percent': avg_cpu,
            'samples_count': len(self.samples)
        }

    def _monitor_loop(self, interval: float):
        """Monitoring loop running in separate thread."""
        while self.monitoring:
            try:
                memory_info = self.process.memory_info()
                cpu_percent = self.process.cpu_percent()

                self.samples.append({
                    'memory_mb': memory_info.rss / (1024 * 1024),
                    'cpu_percent': cpu_percent,
                    'timestamp': time.time()
                })

                time.sleep(interval)
            except Exception as e:
                logger.error(f"[PerformanceMonitor] Monitoring error: {e}")
                break


class BenchmarkRunner:
    """Runs performance benchmarks and collects results."""

    def __init__(self):
        """Initialize benchmark runner."""
        self.monitor = PerformanceMonitor()
        self.results = []

    @contextmanager
    def benchmark_context(self, test_name: str, operations_count: int = 1):
        """Context manager for running benchmarks."""
        # Force garbage collection before test
        gc.collect()

        # Start monitoring
        self.monitor.start_monitoring()
        start_time = time.time()

        try:
            yield
        finally:
            # Stop monitoring and collect results
            end_time = time.time()
            duration = end_time - start_time
            metrics = self.monitor.stop_monitoring()

            # Calculate operations per second
            ops_per_second = operations_count / duration if duration > 0 else 0

            # Create result
            result = BenchmarkResult(
                test_name=test_name,
                duration=duration,
                memory_usage_mb=metrics['memory_mb'],
                cpu_usage_percent=metrics['cpu_percent'],
                operations_per_second=ops_per_second,
                success_rate=100.0  # Default, can be overridden
            )

            self.results.append(result)
            logger.info(f"[BenchmarkRunner] {test_name}: {duration:.3f}s, {ops_per_second:.1f} ops/s")

    def run_benchmark(self, test_name: str, test_function: Callable,
                     operations_count: int = 1, **kwargs) -> BenchmarkResult:
        """Run a single benchmark test."""
        with self.benchmark_context(test_name, operations_count):
            result = test_function(**kwargs)

            # Update success rate if test function returns it
            if isinstance(result, dict) and 'success_rate' in result:
                self.results[-1].success_rate = result['success_rate']
            if isinstance(result, dict) and 'additional_metrics' in result:
                self.results[-1].additional_metrics = result['additional_metrics']

        return self.results[-1]


class MemoryBenchmarks:
    """Memory management benchmarks."""

    def __init__(self):
        """Initialize memory benchmarks."""
        self.runner = BenchmarkRunner()

    def test_lru_cache_performance(self, cache_size: int = 1000, operations: int = 10000):
        """Test LRU cache performance."""

        def baseline_dict_cache():
            """Baseline: simple dictionary cache."""
            cache = {}
            hits = 0
            misses = 0

            for i in range(operations):
                key = f"key_{i % (cache_size // 2)}"  # Create some hits
                if key in cache:
                    hits += 1
                    value = cache[key]
                else:
                    misses += 1
                    cache[key] = f"value_{i}"

                    # Simple eviction when cache gets too large
                    if len(cache) > cache_size:
                        # Remove oldest (first) entry
                        oldest_key = next(iter(cache))
                        del cache[oldest_key]

            return {'hit_rate': hits / (hits + misses) * 100, 'cache_size': len(cache)}

        def optimized_lru_cache():
            """Optimized: LRU cache implementation."""
            cache = LRUCache(max_size=cache_size)
            hits = 0
            misses = 0

            for i in range(operations):
                key = f"key_{i % (cache_size // 2)}"
                value = cache.get(key)
                if value is not None:
                    hits += 1
                else:
                    misses += 1
                    cache.set(key, f"value_{i}")

            stats = cache.get_stats()
            return {
                'hit_rate': stats['hit_rate'] * 100,
                'cache_size': stats['entries']
            }

        # Run benchmarks
        baseline_result = self.runner.run_benchmark(
            "Memory_LRU_Baseline", baseline_dict_cache, operations
        )

        optimized_result = self.runner.run_benchmark(
            "Memory_LRU_Optimized", optimized_lru_cache, operations
        )

        return ComparisonResult("LRU_Cache_Performance", baseline_result, optimized_result)

    def test_memory_cleanup_performance(self, cache_entries: int = 5000):
        """Test memory cleanup performance."""

        def baseline_manual_cleanup():
            """Baseline: manual cache cleanup."""
            cache = {}
            access_times = {}
            current_time = time.time()

            # Fill cache
            for i in range(cache_entries):
                key = f"entry_{i}"
                cache[key] = f"data_{i}" * 100  # Some data
                access_times[key] = current_time - (i * 0.001)  # Simulate age

            # Manual cleanup (remove entries older than 1 second)
            cleanup_threshold = current_time - 1.0
            keys_to_remove = [k for k, t in access_times.items() if t < cleanup_threshold]

            for key in keys_to_remove:
                del cache[key]
                del access_times[key]

            return {'cleaned_entries': len(keys_to_remove), 'remaining': len(cache)}

        def optimized_memory_manager():
            """Optimized: memory manager cleanup."""
            memory_manager = MemoryManager()

            # Create test cache
            test_cache = {}
            for i in range(cache_entries):
                key = f"entry_{i}"
                test_cache[key] = f"data_{i}" * 100

            memory_manager.register_cache('test_cache', test_cache)

            # Force cleanup
            cleaned = memory_manager.force_cleanup()

            return {'cleaned_entries': cleaned, 'remaining': len(test_cache)}

        # Run benchmarks
        baseline_result = self.runner.run_benchmark(
            "Memory_Cleanup_Baseline", baseline_manual_cleanup, cache_entries
        )

        optimized_result = self.runner.run_benchmark(
            "Memory_Cleanup_Optimized", optimized_memory_manager, cache_entries
        )

        return ComparisonResult("Memory_Cleanup_Performance", baseline_result, optimized_result)


class IconCacheBenchmarks:
    """Icon caching benchmarks."""

    def __init__(self):
        """Initialize icon cache benchmarks."""
        self.runner = BenchmarkRunner()

    def test_icon_loading_performance(self, icons_count: int = 100, sizes_count: int = 4):
        """Test icon loading performance."""

        def baseline_icon_loading():
            """Baseline: load icons without caching."""
            from core.qt_imports import QIcon, QPixmap, QSize

            icons_loaded = 0
            icon_names = ['file', 'folder', 'image', 'video', 'audio']
            sizes = [QSize(16, 16), QSize(24, 24), QSize(32, 32), QSize(48, 48)]

            for i in range(icons_count):
                icon_name = icon_names[i % len(icon_names)]
                size = sizes[i % len(sizes)]

                # Simulate icon loading (create empty icon)
                icon = QIcon()
                icons_loaded += 1

            return {'icons_loaded': icons_loaded, 'cache_hits': 0}

        def optimized_icon_cache():
            """Optimized: smart icon cache."""
            icon_cache = SmartIconCache(max_entries=200, max_memory_mb=10.0)

            from core.qt_imports import QSize

            icon_names = ['file', 'folder', 'image', 'video', 'audio']
            sizes = [QSize(16, 16), QSize(24, 24), QSize(32, 32), QSize(48, 48)]

            for i in range(icons_count):
                icon_name = icon_names[i % len(icon_names)]
                size = sizes[i % len(sizes)]

                icon = icon_cache.get_icon(icon_name, size)

            stats = icon_cache.get_stats()
            return {
                'icons_loaded': icons_count,
                'cache_hits': stats['hits'],
                'hit_rate': stats['hit_rate'] * 100
            }

        # Run benchmarks
        baseline_result = self.runner.run_benchmark(
            "Icon_Loading_Baseline", baseline_icon_loading, icons_count
        )

        optimized_result = self.runner.run_benchmark(
            "Icon_Loading_Optimized", optimized_icon_cache, icons_count
        )

        return ComparisonResult("Icon_Loading_Performance", baseline_result, optimized_result)


class DatabaseBenchmarks:
    """Database performance benchmarks."""

    def __init__(self):
        """Initialize database benchmarks."""
        self.runner = BenchmarkRunner()

    def test_query_performance(self, queries_count: int = 1000):
        """Test database query performance."""

        def baseline_sqlite():
            """Baseline: standard sqlite operations."""
            import sqlite3

            with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
                db_path = tmp.name

            try:
                # Setup database
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE test_table (
                        id INTEGER PRIMARY KEY,
                        data TEXT
                    )
                """)

                # Insert test data
                test_data = [(i, f"data_{i}") for i in range(queries_count)]
                cursor.executemany("INSERT INTO test_table (id, data) VALUES (?, ?)", test_data)
                conn.commit()

                # Query performance test
                successful_queries = 0
                for i in range(queries_count // 10):  # Query subset
                    cursor.execute("SELECT * FROM test_table WHERE id = ?", (i,))
                    result = cursor.fetchone()
                    if result:
                        successful_queries += 1

                conn.close()
                return {'successful_queries': successful_queries}

            finally:
                os.unlink(db_path)

        def optimized_database():
            """Optimized: optimized database manager."""
            with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
                db_path = tmp.name

            try:
                db_manager = OptimizedDatabaseManager(db_path, max_connections=3)

                # Insert test data using batch operations
                test_data = [(i, f"data_{i}") for i in range(queries_count)]
                success = db_manager.execute_batch(
                    "INSERT INTO test_table (id, data) VALUES (?, ?)",
                    test_data
                )

                # Query performance test with prepared statements
                successful_queries = 0
                for i in range(queries_count // 10):
                    results = db_manager.execute_query(
                        "SELECT * FROM test_table WHERE id = ?",
                        (i,),
                        use_prepared=True
                    )
                    if results:
                        successful_queries += 1

                stats = db_manager.get_query_stats()
                db_manager.close()

                return {
                    'successful_queries': successful_queries,
                    'avg_query_time': stats['avg_time'],
                    'total_queries': stats['total_queries']
                }

            finally:
                os.unlink(db_path)

        # Run benchmarks
        baseline_result = self.runner.run_benchmark(
            "Database_Query_Baseline", baseline_sqlite, queries_count
        )

        optimized_result = self.runner.run_benchmark(
            "Database_Query_Optimized", optimized_database, queries_count
        )

        return ComparisonResult("Database_Query_Performance", baseline_result, optimized_result)


class AsyncBenchmarks:
    """Async operations benchmarks."""

    def __init__(self):
        """Initialize async benchmarks."""
        self.runner = BenchmarkRunner()

    def test_async_operations_performance(self, operations_count: int = 50):
        """Test async operations performance."""

        def baseline_sync_operations():
            """Baseline: synchronous operations."""
            import hashlib

            def sync_hash_calculation(data: bytes) -> str:
                return hashlib.md5(data).hexdigest()

            completed_operations = 0
            test_data = [f"test_data_{i}".encode() * 1000 for i in range(operations_count)]

            for data in test_data:
                result = sync_hash_calculation(data)
                if result:
                    completed_operations += 1

            return {'completed_operations': completed_operations}

        def optimized_async_operations():
            """Optimized: async operations manager."""
            import asyncio

            async def async_test():
                async_manager = AsyncOperationsManager(max_workers=4)

                # Create test files (mock)
                test_files = [f"/tmp/test_file_{i}.txt" for i in range(operations_count)]

                # Submit async operations
                operation_ids = []
                for i, file_path in enumerate(test_files):
                    op_id = f"test_op_{i}"
                    # Mock async operation
                    async def mock_operation(op_id: int = i):
                        await asyncio.sleep(0.01)  # Simulate work
                        return f"result_{op_id}"

                    async_manager.task_manager.submit_task(op_id, mock_operation(i), 'test')
                    operation_ids.append(op_id)

                # Wait for completion
                await asyncio.sleep(2.0)  # Give time for operations to complete

                stats = async_manager.get_stats()
                async_manager.shutdown()

                return {
                    'completed_operations': stats['completed_tasks'],
                    'total_tasks': stats['total_tasks']
                }

            # Run async test
            return asyncio.run(async_test())

        # Run benchmarks
        baseline_result = self.runner.run_benchmark(
            "Async_Operations_Baseline", baseline_sync_operations, operations_count
        )

        optimized_result = self.runner.run_benchmark(
            "Async_Operations_Optimized", optimized_async_operations, operations_count
        )

        return ComparisonResult("Async_Operations_Performance", baseline_result, optimized_result)


class ThreadPoolBenchmarks:
    """Thread pool benchmarks."""

    def __init__(self):
        """Initialize thread pool benchmarks."""
        self.runner = BenchmarkRunner()

    def test_thread_pool_performance(self, tasks_count: int = 100):
        """Test thread pool performance."""

        def baseline_sequential_processing():
            """Baseline: sequential task processing."""
            def task_function(task_id: int, duration: float = 0.01) -> str:
                time.sleep(duration)
                return f"task_{task_id}_completed"

            completed_tasks = 0
            for i in range(tasks_count):
                result = task_function(i)
                if result:
                    completed_tasks += 1

            return {'completed_tasks': completed_tasks}

        def optimized_thread_pool():
            """Optimized: thread pool manager."""
            thread_pool = ThreadPoolManager(min_threads=2, max_threads=6)

            def task_function(task_id: int, duration: float = 0.01) -> str:
                time.sleep(duration)
                return f"task_{task_id}_completed"

            # Submit all tasks
            for i in range(tasks_count):
                thread_pool.submit_task(
                    f"benchmark_task_{i}",
                    task_function,
                    args=(i,),
                    priority=TaskPriority.NORMAL
                )

            # Wait for completion
            start_time = time.time()
            while time.time() - start_time < 10.0:  # Max 10 seconds wait
                stats = thread_pool.get_stats()
                if stats.completed_tasks >= tasks_count:
                    break
                time.sleep(0.1)

            final_stats = thread_pool.get_stats()
            thread_pool.shutdown()

            return {
                'completed_tasks': final_stats.completed_tasks,
                'active_threads': final_stats.active_threads,
                'avg_execution_time': final_stats.average_execution_time
            }

        # Run benchmarks
        baseline_result = self.runner.run_benchmark(
            "Thread_Pool_Baseline", baseline_sequential_processing, tasks_count
        )

        optimized_result = self.runner.run_benchmark(
            "Thread_Pool_Optimized", optimized_thread_pool, tasks_count
        )

        return ComparisonResult("Thread_Pool_Performance", baseline_result, optimized_result)


class IntegrationBenchmarks:
    """Integration scenario benchmarks."""

    def __init__(self):
        """Initialize integration benchmarks."""
        self.runner = BenchmarkRunner()

    def test_complete_integration_scenario(self, files_count: int = 50):
        """Test complete integration scenario performance."""

        def baseline_integration():
            """Baseline: traditional approach."""
            import sqlite3
            from core.qt_imports import QIcon

            # Database operations
            with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
                db_path = tmp.name

            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE files (
                        id INTEGER PRIMARY KEY,
                        path TEXT,
                        metadata TEXT
                    )
                """)

                # Process files sequentially
                processed_files = 0
                for i in range(files_count):
                    file_path = f"/test/file_{i}.jpg"
                    metadata = f'{{"file_type": "image", "size": {i * 1000}}}'

                    # Database insert
                    cursor.execute("INSERT INTO files (path, metadata) VALUES (?, ?)",
                                 (file_path, metadata))

                    # Icon loading (simulate)
                    icon = QIcon()

                    processed_files += 1

                conn.commit()
                conn.close()

                return {'processed_files': processed_files}

            finally:
                os.unlink(db_path)

        def optimized_integration():
            """Optimized: using all optimization systems."""
            import asyncio
            from core.qt_imports import QSize

            async def integration_test():
                # Initialize all systems
                memory_manager = MemoryManager()
                icon_cache = SmartIconCache(max_entries=100, max_memory_mb=5.0)

                with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
                    db_path = tmp.name

                try:
                    db_manager = OptimizedDatabaseManager(db_path, max_connections=3)
                    async_manager = AsyncOperationsManager(max_workers=3)
                    thread_pool = ThreadPoolManager(min_threads=2, max_threads=4)

                    # Register caches
                    memory_manager.register_cache('icon_cache', icon_cache)

                    # Batch database operations
                    file_data = [
                        (f"/test/file_{i}.jpg", f'{{"file_type": "image", "size": {i * 1000}}}')
                        for i in range(files_count)
                    ]

                    db_success = db_manager.execute_batch(
                        "INSERT INTO files (path, metadata) VALUES (?, ?)",
                        file_data
                    )

                    # Async icon loading
                    for i in range(files_count):
                        icon = icon_cache.get_icon('image', QSize(16, 16))

                    # Thread pool tasks
                    def process_file(file_path: str) -> str:
                        time.sleep(0.001)  # Simulate processing
                        return f"processed_{file_path}"

                    for i in range(files_count):
                        thread_pool.submit_task(
                            f"process_file_{i}",
                            process_file,
                            args=(f"/test/file_{i}.jpg",)
                        )

                    # Wait for completion
                    await asyncio.sleep(2.0)

                    # Get statistics
                    memory_stats = memory_manager.get_memory_stats()
                    icon_stats = icon_cache.get_stats()
                    db_stats = db_manager.get_query_stats()
                    thread_stats = thread_pool.get_stats()

                    # Cleanup
                    async_manager.shutdown()
                    thread_pool.shutdown()
                    memory_manager.shutdown()
                    icon_cache.shutdown()
                    db_manager.close()

                    return {
                        'processed_files': files_count,
                        'db_success': db_success,
                        'icon_hit_rate': icon_stats['hit_rate'],
                        'thread_completed': thread_stats.completed_tasks,
                        'memory_usage': memory_stats.used_memory_mb
                    }

                finally:
                    os.unlink(db_path)

            return asyncio.run(integration_test())

        # Run benchmarks
        baseline_result = self.runner.run_benchmark(
            "Integration_Baseline", baseline_integration, files_count
        )

        optimized_result = self.runner.run_benchmark(
            "Integration_Optimized", optimized_integration, files_count
        )

        return ComparisonResult("Integration_Performance", baseline_result, optimized_result)


class BenchmarkReporter:
    """Generates comprehensive benchmark reports."""

    def __init__(self):
        """Initialize benchmark reporter."""
        self.results = []

    def add_comparison(self, comparison: ComparisonResult):
        """Add a comparison result to the report."""
        self.results.append(comparison)

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive benchmark report."""
        report = {
            'timestamp': time.time(),
            'system_info': self._get_system_info(),
            'summary': self._generate_summary(),
            'detailed_results': self._generate_detailed_results(),
            'recommendations': self._generate_recommendations()
        }

        return report

    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information."""
        return {
            'cpu_count': psutil.cpu_count(),
            'memory_total_gb': psutil.virtual_memory().total / (1024**3),
            'python_version': os.sys.version,
            'platform': os.name
        }

    def _generate_summary(self) -> Dict[str, Any]:
        """Generate summary statistics."""
        if not self.results:
            return {}

        performance_improvements = [r.performance_improvement for r in self.results]
        memory_improvements = [r.memory_improvement for r in self.results]
        speed_improvements = [r.speed_improvement for r in self.results]

        return {
            'total_tests': len(self.results),
            'avg_performance_improvement': sum(performance_improvements) / len(performance_improvements),
            'avg_memory_improvement': sum(memory_improvements) / len(memory_improvements),
            'avg_speed_improvement': sum(speed_improvements) / len(speed_improvements),
            'best_performance_test': max(self.results, key=lambda r: r.performance_improvement).test_name,
            'best_memory_test': max(self.results, key=lambda r: r.memory_improvement).test_name,
            'best_speed_test': max(self.results, key=lambda r: r.speed_improvement).test_name
        }

    def _generate_detailed_results(self) -> List[Dict[str, Any]]:
        """Generate detailed results for each test."""
        detailed = []

        for result in self.results:
            detailed.append({
                'test_name': result.test_name,
                'baseline': result.baseline_result.to_dict(),
                'optimized': result.optimized_result.to_dict(),
                'improvements': {
                    'performance': result.performance_improvement,
                    'memory': result.memory_improvement,
                    'speed': result.speed_improvement
                }
            })

        return detailed

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on results."""
        recommendations = []

        # Analyze results and generate recommendations
        for result in self.results:
            if result.performance_improvement > 50:
                recommendations.append(
                    f"Excellent performance improvement in {result.test_name}: "
                    f"{result.performance_improvement:.1f}% - Consider prioritizing this optimization"
                )
            elif result.memory_improvement > 30:
                recommendations.append(
                    f"Significant memory improvement in {result.test_name}: "
                    f"{result.memory_improvement:.1f}% - Good for memory-constrained environments"
                )
            elif result.performance_improvement < 10:
                recommendations.append(
                    f"Low performance improvement in {result.test_name}: "
                    f"{result.performance_improvement:.1f}% - Consider further optimization"
                )

        return recommendations

    def save_report(self, filename: str):
        """Save report to JSON file."""
        report = self.generate_report()

        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"[BenchmarkReporter] Report saved to {filename}")

    def print_summary(self):
        """Print summary to console."""
        summary = self._generate_summary()

        print("\n" + "="*60)
        print("ONCUTF OPTIMIZATION BENCHMARK RESULTS")
        print("="*60)
        print(f"Total Tests: {summary.get('total_tests', 0)}")
        print(f"Average Performance Improvement: {summary.get('avg_performance_improvement', 0):.1f}%")
        print(f"Average Memory Improvement: {summary.get('avg_memory_improvement', 0):.1f}%")
        print(f"Average Speed Improvement: {summary.get('avg_speed_improvement', 0):.1f}%")
        print()
        print(f"Best Performance Test: {summary.get('best_performance_test', 'N/A')}")
        print(f"Best Memory Test: {summary.get('best_memory_test', 'N/A')}")
        print(f"Best Speed Test: {summary.get('best_speed_test', 'N/A')}")
        print("="*60)

        # Print detailed results
        for result in self.results:
            print(f"\n{result.test_name}:")
            print(f"  Performance: {result.performance_improvement:+.1f}%")
            print(f"  Memory: {result.memory_improvement:+.1f}%")
            print(f"  Speed: {result.speed_improvement:+.1f}%")


class PerformanceBenchmarkSuite(unittest.TestCase):
    """Main benchmark suite combining all tests."""

    def setUp(self):
        """Set up benchmark suite."""
        self.reporter = BenchmarkReporter()
        logger.info("[BenchmarkSuite] Starting performance benchmarks...")

    def test_memory_benchmarks(self):
        """Run memory optimization benchmarks."""
        memory_bench = MemoryBenchmarks()

        # LRU Cache performance
        lru_result = memory_bench.test_lru_cache_performance()
        self.reporter.add_comparison(lru_result)

        # Memory cleanup performance
        cleanup_result = memory_bench.test_memory_cleanup_performance()
        self.reporter.add_comparison(cleanup_result)

    def test_icon_cache_benchmarks(self):
        """Run icon cache benchmarks."""
        icon_bench = IconCacheBenchmarks()

        # Icon loading performance
        icon_result = icon_bench.test_icon_loading_performance()
        self.reporter.add_comparison(icon_result)

    def test_database_benchmarks(self):
        """Run database benchmarks."""
        db_bench = DatabaseBenchmarks()

        # Query performance
        query_result = db_bench.test_query_performance()
        self.reporter.add_comparison(query_result)

    def test_async_benchmarks(self):
        """Run async operations benchmarks."""
        async_bench = AsyncBenchmarks()

        # Async operations performance
        async_result = async_bench.test_async_operations_performance()
        self.reporter.add_comparison(async_result)

    def test_thread_pool_benchmarks(self):
        """Run thread pool benchmarks."""
        thread_bench = ThreadPoolBenchmarks()

        # Thread pool performance
        thread_result = thread_bench.test_thread_pool_performance()
        self.reporter.add_comparison(thread_result)

    def test_integration_benchmarks(self):
        """Run integration benchmarks."""
        integration_bench = IntegrationBenchmarks()

        # Complete integration scenario
        integration_result = integration_bench.test_complete_integration_scenario()
        self.reporter.add_comparison(integration_result)

    def tearDown(self):
        """Generate final report."""
        # Generate and save report
        timestamp = int(time.time())
        report_filename = f"benchmark_report_{timestamp}.json"
        self.reporter.save_report(report_filename)

        # Print summary
        self.reporter.print_summary()

        logger.info(f"[BenchmarkSuite] Benchmarks completed. Report saved to {report_filename}")


def run_benchmarks():
    """Run all performance benchmarks."""
    import sys

    # Run the benchmark suite
    suite = unittest.TestLoader().loadTestsFromTestCase(PerformanceBenchmarkSuite)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return success status
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_benchmarks()
    exit(0 if success else 1)
