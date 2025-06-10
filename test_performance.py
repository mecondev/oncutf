#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Performance Testing Suite for oncutf Application

Author: Michael Economou
Date: 2025-06-10

Comprehensive performance testing to measure the impact of
ApplicationContext and SelectionStore optimizations.

Tests:
- Selection operations (before/after optimization)
- Parent traversal elimination
- Signal propagation efficiency
- Memory usage patterns
- UI responsiveness metrics
"""

import gc
import time
import tracemalloc
from typing import Dict, List, Tuple, Any
from contextlib import contextmanager
from dataclasses import dataclass

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QElapsedTimer, QTimer
from PyQt5.QtTest import QTest

# Initialize QApplication if needed
if not QApplication.instance():
    app = QApplication([])

from main_window import MainWindow
from core.application_context import get_app_context


@dataclass
class PerformanceMetric:
    """Container for performance measurement results."""
    name: str
    duration_ms: float
    memory_peak_mb: float
    iterations: int
    success_rate: float = 1.0
    details: Dict[str, Any] = None


class PerformanceTester:
    """
    Comprehensive performance testing framework for oncutf.

    Measures the impact of ApplicationContext optimizations across
    various operations and UI interactions.
    """

    def __init__(self):
        self.results: List[PerformanceMetric] = []
        self.main_window: MainWindow = None
        self.test_files: List[str] = []

    def setup_test_environment(self) -> bool:
        """Setup test environment with sample files."""
        print("🔧 Setting up test environment...")

        try:
            # Create main window
            self.main_window = MainWindow()
            self.main_window.show()

            # Wait for initialization
            QTest.qWait(500)

            # Load a test folder with files
            test_folder = "/mnt/data_1/241130 Petros - Vasiliki/audio"
            if not hasattr(self.main_window, 'load_files_from_folder'):
                print("❌ MainWindow doesn't have load_files_from_folder method")
                return False

            self.main_window.load_files_from_folder(test_folder, skip_metadata=True)
            QTest.qWait(200)

            # Verify files loaded
            if hasattr(self.main_window, 'file_model') and self.main_window.file_model:
                file_count = len(self.main_window.file_model.files)
                print(f"✅ Loaded {file_count} test files")
                self.test_files = [f.full_path for f in self.main_window.file_model.files[:10]]  # Limit to 10 for testing
                return file_count > 0
            else:
                print("❌ No files loaded")
                return False

        except Exception as e:
            print(f"❌ Setup failed: {e}")
            traceback.print_exc()
            return False

    @contextmanager
    def measure_performance(self, test_name: str, iterations: int = 1):
        """Context manager for measuring performance metrics."""
        print(f"📊 Running test: {test_name} ({iterations} iterations)")

        # Start memory tracking
        tracemalloc.start()
        gc.collect()  # Clean start

        # Start timing
        timer = QElapsedTimer()
        timer.start()

        successful_iterations = 0
        details = {}

        try:
            yield details
            successful_iterations = iterations
        except Exception as e:
            print(f"❌ Test {test_name} failed: {e}")
            successful_iterations = 0
        finally:
            # Stop timing
            duration_ms = timer.elapsed()

            # Get memory peak
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            memory_peak_mb = peak / 1024 / 1024

            # Calculate success rate
            success_rate = successful_iterations / iterations if iterations > 0 else 0.0

            # Store result
            metric = PerformanceMetric(
                name=test_name,
                duration_ms=duration_ms,
                memory_peak_mb=memory_peak_mb,
                iterations=iterations,
                success_rate=success_rate,
                details=details
            )
            self.results.append(metric)

            print(f"✅ {test_name}: {duration_ms:.1f}ms, {memory_peak_mb:.1f}MB peak, {success_rate*100:.1f}% success")

    def test_selection_operations(self):
        """Test selection operation performance."""
        if not self.main_window or not self.test_files:
            print("❌ Cannot test selection operations - no test environment")
            return

        file_table = self.main_window.file_table_view
        file_count = len(self.main_window.file_model.files)

        # Test 1: Single selection operations
        with self.measure_performance("Selection: Single Item", iterations=50) as details:
            for i in range(50):
                row = i % file_count
                file_table.clearSelection()
                file_table.selectRow(row)
                QTest.qWait(1)  # Small delay to let signals propagate
            details['rows_selected'] = 50

        # Test 2: Multiple selection operations
        with self.measure_performance("Selection: Multiple Items", iterations=20) as details:
            for i in range(20):
                start_row = (i * 2) % file_count
                end_row = min(start_row + 3, file_count - 1)
                file_table.clearSelection()
                file_table.select_rows_range(start_row, end_row)
                QTest.qWait(5)
            details['range_selections'] = 20

        # Test 3: Select all operation
        with self.measure_performance("Selection: Select All", iterations=10) as details:
            for i in range(10):
                self.main_window.clear_all_selection()
                QTest.qWait(10)
                self.main_window.select_all_rows()
                QTest.qWait(10)
            details['select_all_operations'] = 10

        # Test 4: Invert selection
        with self.measure_performance("Selection: Invert Selection", iterations=10) as details:
            for i in range(10):
                file_table.clearSelection()
                file_table.selectRow(i % file_count)
                self.main_window.invert_selection()
                QTest.qWait(10)
            details['invert_operations'] = 10

    def test_application_context_access(self):
        """Test ApplicationContext access performance."""

        # Test 1: Context retrieval speed
        with self.measure_performance("Context: Retrieval Speed", iterations=1000) as details:
            successful_retrievals = 0
            for i in range(1000):
                try:
                    context = get_app_context()
                    if context:
                        successful_retrievals += 1
                except:
                    pass
            details['successful_retrievals'] = successful_retrievals

        # Test 2: Selection store access
        with self.measure_performance("Context: SelectionStore Access", iterations=500) as details:
            context = get_app_context()
            successful_accesses = 0
            for i in range(500):
                try:
                    selection_store = context.selection_store
                    if selection_store:
                        selected_rows = selection_store.get_selected_rows()
                        successful_accesses += 1
                except:
                    pass
            details['successful_accesses'] = successful_accesses

        # Test 3: File access via context
        with self.measure_performance("Context: File Access", iterations=300) as details:
            context = get_app_context()
            successful_accesses = 0
            for i in range(300):
                try:
                    files = context.get_files()
                    if files:
                        successful_accesses += 1
                except:
                    pass
            details['successful_file_accesses'] = successful_accesses

    def test_signal_propagation(self):
        """Test signal propagation performance."""

        if not self.main_window:
            print("❌ Cannot test signals - no main window")
            return

        # Test 1: Selection changed signal propagation
        with self.measure_performance("Signals: Selection Changed", iterations=100) as details:
            file_table = self.main_window.file_table_view
            file_count = len(self.main_window.file_model.files)

            for i in range(100):
                row = i % file_count
                file_table.clearSelection()
                file_table.selectRow(row)
                QApplication.processEvents()  # Ensure signals are processed
            details['signal_emissions'] = 100

        # Test 2: Preview update performance
        with self.measure_performance("Signals: Preview Updates", iterations=50) as details:
            for i in range(50):
                row = i % len(self.main_window.file_model.files)
                self.main_window.file_table_view.clearSelection()
                self.main_window.file_table_view.selectRow(row)
                self.main_window.request_preview_update()
                QTest.qWait(10)  # Wait for timer
            details['preview_updates'] = 50

    def test_legacy_vs_optimized(self):
        """Compare legacy parent traversal vs ApplicationContext approach."""

        # Simulate legacy parent traversal
        with self.measure_performance("Legacy: Parent Traversal", iterations=200) as details:
            widget = self.main_window.metadata_tree_view
            successful_traversals = 0

            for i in range(200):
                try:
                    # Simulate the old _get_parent_window_with_file_table approach
                    parent_window = widget.parent()
                    while parent_window and not hasattr(parent_window, 'file_table_view'):
                        parent_window = parent_window.parent()

                    if parent_window and hasattr(parent_window, 'file_table_view'):
                        successful_traversals += 1
                except:
                    pass
            details['successful_traversals'] = successful_traversals

        # Compare with optimized ApplicationContext approach
        with self.measure_performance("Optimized: ApplicationContext", iterations=200) as details:
            widget = self.main_window.metadata_tree_view
            successful_accesses = 0

            for i in range(200):
                try:
                    context = widget._get_app_context()
                    if context and hasattr(context, 'selection_store'):
                        successful_accesses += 1
                except:
                    pass
            details['successful_context_accesses'] = successful_accesses

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all performance tests and return comprehensive results."""
        print("🚀 Starting Performance Testing Suite")
        print("=" * 50)

        # Setup
        if not self.setup_test_environment():
            print("❌ Failed to setup test environment")
            return {"success": False, "error": "Setup failed"}

        try:
            # Run test suites
            self.test_selection_operations()
            self.test_application_context_access()
            self.test_signal_propagation()
            self.test_legacy_vs_optimized()

            # Generate summary
            return self.generate_summary()

        except Exception as e:
            print(f"❌ Testing failed: {e}")
            traceback.print_exc()
            return {"success": False, "error": str(e)}
        finally:
            # Cleanup
            if self.main_window:
                self.main_window.close()

    def generate_summary(self) -> Dict[str, Any]:
        """Generate comprehensive performance summary."""
        print("\n" + "=" * 50)
        print("📈 PERFORMANCE TEST SUMMARY")
        print("=" * 50)

        # Overall metrics
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r.success_rate > 0.8)
        total_duration = sum(r.duration_ms for r in self.results)
        avg_memory = sum(r.memory_peak_mb for r in self.results) / total_tests if total_tests > 0 else 0

        print(f"📊 Total Tests: {total_tests}")
        print(f"✅ Successful: {successful_tests} ({successful_tests/total_tests*100:.1f}%)")
        print(f"⏱️  Total Duration: {total_duration:.1f}ms")
        print(f"💾 Average Memory Peak: {avg_memory:.1f}MB")
        print()

        # Detailed results
        print("📋 DETAILED RESULTS:")
        print("-" * 50)

        for result in self.results:
            status = "✅" if result.success_rate > 0.8 else "⚠️" if result.success_rate > 0.5 else "❌"
            print(f"{status} {result.name}")
            print(f"   Duration: {result.duration_ms:.1f}ms | Memory: {result.memory_peak_mb:.1f}MB")
            print(f"   Iterations: {result.iterations} | Success: {result.success_rate*100:.1f}%")
            if result.details:
                for key, value in result.details.items():
                    print(f"   {key}: {value}")
            print()

        # Performance insights
        self._analyze_performance_insights()

        return {
            "success": True,
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "total_duration_ms": total_duration,
            "average_memory_mb": avg_memory,
            "results": self.results
        }

    def _analyze_performance_insights(self):
        """Analyze results and provide performance insights."""
        print("🔍 PERFORMANCE INSIGHTS:")
        print("-" * 50)

        # Find fastest/slowest operations
        if self.results:
            fastest = min(self.results, key=lambda r: r.duration_ms / r.iterations)
            slowest = max(self.results, key=lambda r: r.duration_ms / r.iterations)

            print(f"🏃 Fastest Operation: {fastest.name}")
            print(f"   {fastest.duration_ms / fastest.iterations:.2f}ms per operation")
            print()
            print(f"🐌 Slowest Operation: {slowest.name}")
            print(f"   {slowest.duration_ms / slowest.iterations:.2f}ms per operation")
            print()

        # ApplicationContext vs Legacy comparison
        legacy_results = [r for r in self.results if "Legacy" in r.name]
        optimized_results = [r for r in self.results if "Optimized" in r.name]

        if legacy_results and optimized_results:
            legacy_avg = sum(r.duration_ms / r.iterations for r in legacy_results) / len(legacy_results)
            optimized_avg = sum(r.duration_ms / r.iterations for r in optimized_results) / len(optimized_results)

            if legacy_avg > 0:
                improvement = ((legacy_avg - optimized_avg) / legacy_avg) * 100
                print(f"🚀 ApplicationContext Improvement: {improvement:.1f}%")
                print(f"   Legacy: {legacy_avg:.2f}ms avg | Optimized: {optimized_avg:.2f}ms avg")
                print()

        # Memory efficiency
        memory_results = [(r.name, r.memory_peak_mb) for r in self.results]
        memory_results.sort(key=lambda x: x[1])

        print(f"💾 Most Memory Efficient: {memory_results[0][0]} ({memory_results[0][1]:.1f}MB)")
        print(f"💾 Most Memory Intensive: {memory_results[-1][0]} ({memory_results[-1][1]:.1f}MB)")


def main():
    """Run the performance testing suite."""
    tester = PerformanceTester()
    results = tester.run_all_tests()

    if results.get("success"):
        print("\n🎉 Performance testing completed successfully!")
        print(f"📊 Results: {results['successful_tests']}/{results['total_tests']} tests passed")
    else:
        print(f"\n❌ Performance testing failed: {results.get('error', 'Unknown error')}")

    return results


if __name__ == "__main__":
    main()
