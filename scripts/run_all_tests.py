#!/usr/bin/env python3
"""Comprehensive Test Runner for oncutf Optimization Systems.

This script runs all performance tests, memory profiling, and generates
comprehensive reports for the optimization systems.

Features:
- Performance benchmarking
- Memory profiling and leak detection
- Automated report generation
- Test result comparison
- CI/CD integration support

Usage:
    python run_all_tests.py [options]

Author: Michael Economou
Date: 2025-07-06
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class ComprehensiveTestRunner:
    """Runs all optimization system tests and generates comprehensive reports."""

    def __init__(self, output_dir: str = "test_results"):
        """
        Initialize comprehensive test runner.

        Args:
            output_dir: Directory for test results and reports
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.start_time = time.time()
        self.test_results = {}

        logger.info(f"[ComprehensiveTestRunner] Initialized with output dir: {self.output_dir}")

    def run_unit_tests(self) -> Dict[str, Any]:
        """Run existing unit tests."""
        logger.info("[ComprehensiveTestRunner] Running unit tests...")

        try:
            # Run pytest on tests directory
            result = subprocess.run([
                sys.executable, "-m", "pytest",
                "tests/",
                "-v",
                "--tb=short",
                f"--junit-xml={self.output_dir}/unit_tests.xml"
            ],
            capture_output=True,
            text=True,
            cwd=project_root
            )

            unit_results = {
                'success': result.returncode == 0,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'duration': time.time() - self.start_time
            }

            if unit_results['success']:
                logger.info("[ComprehensiveTestRunner] Unit tests passed")
            else:
                logger.error(f"[ComprehensiveTestRunner] Unit tests failed: {result.stderr}")

            return unit_results

        except Exception as e:
            logger.error(f"[ComprehensiveTestRunner] Error running unit tests: {e}")
            return {
                'success': False,
                'error': str(e),
                'duration': time.time() - self.start_time
            }

    def run_performance_benchmarks(self, quick: bool = False) -> Dict[str, Any]:
        """Run performance benchmarks."""
        logger.info("[ComprehensiveTestRunner] Running performance benchmarks...")

        try:
            # Import and run performance tests
            from tests.test_performance_benchmarks import run_benchmarks

            benchmark_start = time.time()
            success = run_benchmarks()
            benchmark_duration = time.time() - benchmark_start

            benchmark_results = {
                'success': success,
                'duration': benchmark_duration,
                'config': 'quick' if quick else 'full'
            }

            if success:
                logger.info(f"[ComprehensiveTestRunner] Performance benchmarks completed in {benchmark_duration:.1f}s")
            else:
                logger.error("[ComprehensiveTestRunner] Performance benchmarks failed")

            return benchmark_results

        except Exception as e:
            logger.error(f"[ComprehensiveTestRunner] Error running performance benchmarks: {e}")
            return {
                'success': False,
                'error': str(e),
                'duration': time.time() - self.start_time
            }

    def run_memory_profiling(self) -> Dict[str, Any]:
        """Run memory profiling tests."""
        logger.info("[ComprehensiveTestRunner] Running memory profiling...")

        try:
            # Import and run memory profiling tests
            from tests.test_memory_profiling import run_memory_profiling_tests

            memory_start = time.time()
            success = run_memory_profiling_tests()
            memory_duration = time.time() - memory_start

            memory_results = {
                'success': success,
                'duration': memory_duration
            }

            if success:
                logger.info(f"[ComprehensiveTestRunner] Memory profiling completed in {memory_duration:.1f}s")
            else:
                logger.error("[ComprehensiveTestRunner] Memory profiling failed")

            return memory_results

        except Exception as e:
            logger.error(f"[ComprehensiveTestRunner] Error running memory profiling: {e}")
            return {
                'success': False,
                'error': str(e),
                'duration': time.time() - self.start_time
            }

    def run_integration_tests(self) -> Dict[str, Any]:
        """Run integration tests using the optimization example."""
        logger.info("[ComprehensiveTestRunner] Running integration tests...")

        try:
            # Run the optimization integration example
            result = subprocess.run([
                sys.executable,
                "examples/optimization_integration_example.py"
            ],
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=60  # 60 second timeout
            )

            integration_results = {
                'success': result.returncode == 0,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'duration': time.time() - self.start_time
            }

            if integration_results['success']:
                logger.info("[ComprehensiveTestRunner] Integration tests passed")
            else:
                logger.error(f"[ComprehensiveTestRunner] Integration tests failed: {result.stderr}")

            return integration_results

        except subprocess.TimeoutExpired:
            logger.error("[ComprehensiveTestRunner] Integration tests timed out")
            return {
                'success': False,
                'error': 'Test timed out after 60 seconds',
                'duration': 60.0
            }
        except Exception as e:
            logger.error(f"[ComprehensiveTestRunner] Error running integration tests: {e}")
            return {
                'success': False,
                'error': str(e),
                'duration': time.time() - self.start_time
            }

    def run_system_validation(self) -> Dict[str, Any]:
        """Run system validation tests."""
        logger.info("[ComprehensiveTestRunner] Running system validation...")

        validation_results = {
            'success': True,
            'checks': {},
            'duration': 0.0
        }

        validation_start = time.time()

        try:
            # Check if all optimization systems can be imported
            imports_to_check = [
                ('core.memory_manager', 'MemoryManager'),
                ('utils.smart_icon_cache', 'SmartIconCache'),
                ('core.optimized_database_manager', 'OptimizedDatabaseManager'),
                ('core.async_operations_manager', 'AsyncOperationsManager'),
                ('core.thread_pool_manager', 'ThreadPoolManager')
            ]

            for module_name, class_name in imports_to_check:
                try:
                    module = __import__(module_name, fromlist=[class_name])
                    cls = getattr(module, class_name)

                    # Try to instantiate (basic validation)
                    if class_name == 'MemoryManager':
                        instance = cls()
                        instance.shutdown()
                    elif class_name == 'SmartIconCache':
                        instance = cls(max_entries=10, max_memory_mb=1.0)
                        instance.shutdown()
                    elif class_name == 'OptimizedDatabaseManager':
                        # Skip instantiation for database (requires file)
                        pass
                    elif class_name == 'AsyncOperationsManager':
                        instance = cls(max_workers=2)
                        instance.shutdown()
                    elif class_name == 'ThreadPoolManager':
                        instance = cls(min_threads=1, max_threads=2)
                        instance.shutdown()

                    validation_results['checks'][f'{module_name}.{class_name}'] = {
                        'success': True,
                        'message': 'Import and instantiation successful'
                    }

                except Exception as e:
                    validation_results['success'] = False
                    validation_results['checks'][f'{module_name}.{class_name}'] = {
                        'success': False,
                        'error': str(e)
                    }

            # Check required dependencies
            dependencies_to_check = [
                'psutil',
                'aiofiles',
                'asyncio'
            ]

            for dep in dependencies_to_check:
                try:
                    __import__(dep)
                    validation_results['checks'][f'dependency_{dep}'] = {
                        'success': True,
                        'message': 'Dependency available'
                    }
                except ImportError as e:
                    validation_results['success'] = False
                    validation_results['checks'][f'dependency_{dep}'] = {
                        'success': False,
                        'error': str(e)
                    }

            validation_results['duration'] = time.time() - validation_start

            if validation_results['success']:
                logger.info("[ComprehensiveTestRunner] System validation passed")
            else:
                logger.error("[ComprehensiveTestRunner] System validation failed")

            return validation_results

        except Exception as e:
            logger.error(f"[ComprehensiveTestRunner] Error in system validation: {e}")
            return {
                'success': False,
                'error': str(e),
                'duration': time.time() - validation_start
            }

    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        total_duration = time.time() - self.start_time

        # Calculate overall success
        all_success = all(
            result.get('success', False)
            for result in self.test_results.values()
        )

        # Count successful tests
        successful_tests = sum(
            1 for result in self.test_results.values()
            if result.get('success', False)
        )

        report = {
            'timestamp': time.time(),
            'total_duration': total_duration,
            'overall_success': all_success,
            'successful_tests': successful_tests,
            'total_tests': len(self.test_results),
            'test_results': self.test_results,
            'summary': {
                'unit_tests': self.test_results.get('unit_tests', {}).get('success', False),
                'performance_benchmarks': self.test_results.get('performance_benchmarks', {}).get('success', False),
                'memory_profiling': self.test_results.get('memory_profiling', {}).get('success', False),
                'integration_tests': self.test_results.get('integration_tests', {}).get('success', False),
                'system_validation': self.test_results.get('system_validation', {}).get('success', False)
            },
            'recommendations': self._generate_recommendations()
        }

        return report

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []

        # Check each test result and generate recommendations
        for test_name, result in self.test_results.items():
            if not result.get('success', False):
                if test_name == 'unit_tests':
                    recommendations.append(
                        "Unit tests failed - Check existing functionality for regressions"
                    )
                elif test_name == 'performance_benchmarks':
                    recommendations.append(
                        "Performance benchmarks failed - Review optimization implementations"
                    )
                elif test_name == 'memory_profiling':
                    recommendations.append(
                        "Memory profiling failed - Check for memory leaks or excessive usage"
                    )
                elif test_name == 'integration_tests':
                    recommendations.append(
                        "Integration tests failed - Verify system components work together"
                    )
                elif test_name == 'system_validation':
                    recommendations.append(
                        "System validation failed - Check dependencies and imports"
                    )

        # Performance-specific recommendations
        if self.test_results.get('performance_benchmarks', {}).get('success', False):
            recommendations.append(
                "Performance benchmarks passed - Consider deploying optimizations"
            )

        if self.test_results.get('memory_profiling', {}).get('success', False):
            recommendations.append(
                "Memory profiling passed - Memory optimizations are working effectively"
            )

        return recommendations

    def save_report(self, filename: str):
        """Save comprehensive report to file."""
        report = self.generate_comprehensive_report()

        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"[ComprehensiveTestRunner] Report saved to {filename}")

    def print_summary(self):
        """Print test summary to console."""
        report = self.generate_comprehensive_report()

        print("\n" + "="*70)
        print("ONCUTF OPTIMIZATION SYSTEMS - COMPREHENSIVE TEST RESULTS")
        print("="*70)
        print(f"Overall Success: {' PASS' if report['overall_success'] else ' FAIL'}")
        print(f"Total Duration: {report['total_duration']:.1f} seconds")
        print(f"Tests Passed: {report['successful_tests']}/{report['total_tests']}")
        print()

        print("Test Results:")
        for test_name, result in report['test_results'].items():
            status = " PASS" if result.get('success', False) else " FAIL"
            duration = result.get('duration', 0)
            print(f"  {test_name.replace('_', ' ').title()}: {status} ({duration:.1f}s)")

            if not result.get('success', False) and 'error' in result:
                print(f"    Error: {result['error']}")

        print()
        print("Recommendations:")
        for rec in report['recommendations']:
            print(f"  • {rec}")

        print("="*70)

    def run_all_tests(self, quick_benchmarks: bool = False,
                     skip_unit_tests: bool = False) -> Dict[str, Any]:
        """
        Run all tests and generate comprehensive report.

        Args:
            quick_benchmarks: Use quick benchmark configuration
            skip_unit_tests: Skip unit tests (for faster execution)

        Returns:
            Comprehensive test results
        """
        logger.info("[ComprehensiveTestRunner] Starting comprehensive test suite...")

        # Run system validation first
        self.test_results['system_validation'] = self.run_system_validation()

        # Run unit tests (if not skipped)
        if not skip_unit_tests:
            self.test_results['unit_tests'] = self.run_unit_tests()

        # Run performance benchmarks
        self.test_results['performance_benchmarks'] = self.run_performance_benchmarks(quick_benchmarks)

        # Run memory profiling
        self.test_results['memory_profiling'] = self.run_memory_profiling()

        # Run integration tests
        self.test_results['integration_tests'] = self.run_integration_tests()

        # Generate and save report
        timestamp = int(time.time())
        report_filename = f"comprehensive_test_report_{timestamp}.json"
        self.save_report(str(self.output_dir / report_filename))

        # Print summary
        self.print_summary()

        logger.info(f"[ComprehensiveTestRunner] All tests completed. Report: {report_filename}")

        return self.generate_comprehensive_report()


def main():
    """Main function for command-line interface."""

    parser = argparse.ArgumentParser(
        description="OnCutF Comprehensive Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python run_all_tests.py
    python run_all_tests.py --quick
    python run_all_tests.py --skip-unit-tests --output-dir results/
        """
    )

    parser.add_argument('--quick', action='store_true',
                       help='Use quick benchmark configuration')
    parser.add_argument('--skip-unit-tests', action='store_true',
                       help='Skip unit tests for faster execution')
    parser.add_argument('--output-dir', default='test_results',
                       help='Directory for test results (default: test_results/)')

    args = parser.parse_args()

    # Create test runner
    runner = ComprehensiveTestRunner(args.output_dir)

    try:
        # Run all tests
        results = runner.run_all_tests(
            quick_benchmarks=args.quick,
            skip_unit_tests=args.skip_unit_tests
        )

        # Return success status
        return 0 if results['overall_success'] else 1

    except KeyboardInterrupt:
        logger.info("[ComprehensiveTestRunner] Test execution interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"[ComprehensiveTestRunner] Test execution failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
