"""
Benchmark Files Cleanup Utility

This utility manages benchmark and test result files by:
- Moving them from root to logs directory
- Keeping only the latest 5 files of each type
- Automatic cleanup on application startup

Author: Michael Economou
Date: 2025-07-06
"""

import os
import sys
import time
import shutil
from pathlib import Path
from typing import List, Tuple, Optional

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class BenchmarkCleanupManager:
    """Manages benchmark and test result files cleanup."""

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize benchmark cleanup manager.

        Args:
            project_root: Project root directory (auto-detected if None)
        """
        self.project_root = project_root or Path(__file__).parent.parent
        self.logs_dir = self.project_root / "logs"
        self.reports_dir = self.project_root / "reports"
        self.test_results_dir = self.project_root / "test_results"

        # Ensure directories exist
        self.logs_dir.mkdir(exist_ok=True)
        self.reports_dir.mkdir(exist_ok=True)
        self.test_results_dir.mkdir(exist_ok=True)

        # File patterns to manage
        self.file_patterns = {
            'benchmark_reports': 'benchmark_report_*.json',
            'performance_reports': 'performance_report_*.json',
            'performance_html': 'performance_report_*.html',
            'test_reports': 'comprehensive_test_report_*.json',
            'unit_tests': 'unit_tests*.xml'
        }

        # Keep only this many files of each type
        self.max_files_per_type = 5

    def cleanup_all(self) -> dict:
        """
        Perform complete cleanup of all benchmark files.

        Returns:
            Dictionary with cleanup results
        """
        results = {
            'moved_files': 0,
            'deleted_files': 0,
            'errors': []
        }

        try:
            # Move files from root to appropriate directories
            moved = self._move_files_from_root()
            results['moved_files'] = moved

            # Clean up old files in each directory
            deleted = self._cleanup_old_files()
            results['deleted_files'] = deleted

            logger.info(f"[BenchmarkCleanup] Cleanup completed: "
                       f"{moved} files moved, {deleted} files deleted")

        except Exception as e:
            error_msg = f"Cleanup failed: {str(e)}"
            results['errors'].append(error_msg)
            logger.error(f"[BenchmarkCleanup] {error_msg}")

        return results

    def _move_files_from_root(self) -> int:
        """Move benchmark files from root to appropriate directories."""
        moved_count = 0

        # Files to move from root
        file_moves = [
            ('benchmark_report_*.json', self.logs_dir),
            ('performance_report_*.json', self.reports_dir),
            ('performance_report_*.html', self.reports_dir),
            ('comprehensive_test_report_*.json', self.test_results_dir),
            ('unit_tests*.xml', self.test_results_dir)
        ]

        for pattern, target_dir in file_moves:
            try:
                files = list(self.project_root.glob(pattern))
                for file_path in files:
                    if file_path.is_file():
                        target_path = target_dir / file_path.name

                        # Avoid overwriting existing files
                        if target_path.exists():
                            timestamp = int(time.time())
                            stem = target_path.stem
                            suffix = target_path.suffix
                            target_path = target_dir / f"{stem}_{timestamp}{suffix}"

                        shutil.move(str(file_path), str(target_path))
                        moved_count += 1
                        logger.debug(f"[BenchmarkCleanup] Moved {file_path.name} to {target_dir.name}/")

            except Exception as e:
                logger.error(f"[BenchmarkCleanup] Error moving {pattern}: {e}")

        return moved_count

    def _cleanup_old_files(self) -> int:
        """Clean up old files, keeping only the latest ones."""
        deleted_count = 0

        # Directories and patterns to clean
        cleanup_locations = [
            (self.logs_dir, 'benchmark_report_*.json'),
            (self.reports_dir, 'performance_report_*.json'),
            (self.reports_dir, 'performance_report_*.html'),
            (self.test_results_dir, 'comprehensive_test_report_*.json'),
            (self.test_results_dir, 'unit_tests*.xml')
        ]

        for directory, pattern in cleanup_locations:
            try:
                deleted = self._cleanup_directory_pattern(directory, pattern)
                deleted_count += deleted
            except Exception as e:
                logger.error(f"[BenchmarkCleanup] Error cleaning {directory}/{pattern}: {e}")

        return deleted_count

    def _cleanup_directory_pattern(self, directory: Path, pattern: str) -> int:
        """Clean up files in a directory matching a pattern."""
        if not directory.exists():
            return 0

        try:
            # Get all files matching pattern
            files = list(directory.glob(pattern))

            if len(files) <= self.max_files_per_type:
                return 0

            # Sort by modification time (newest first)
            files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

            # Keep only the latest files
            files_to_keep = files[:self.max_files_per_type]
            files_to_delete = files[self.max_files_per_type:]

            # Delete old files
            deleted_count = 0
            for file_path in files_to_delete:
                try:
                    file_path.unlink()
                    deleted_count += 1
                    logger.debug(f"[BenchmarkCleanup] Deleted old file: {file_path.name}")
                except Exception as e:
                    logger.error(f"[BenchmarkCleanup] Error deleting {file_path.name}: {e}")

            if deleted_count > 0:
                logger.info(f"[BenchmarkCleanup] Cleaned {directory.name}: "
                           f"kept {len(files_to_keep)}, deleted {deleted_count}")

            return deleted_count

        except Exception as e:
            logger.error(f"[BenchmarkCleanup] Error in cleanup_directory_pattern: {e}")
            return 0

    def get_file_counts(self) -> dict:
        """Get current file counts for each type."""
        counts = {}

        locations = [
            ('root_benchmark', self.project_root, 'benchmark_report_*.json'),
            ('root_performance', self.project_root, 'performance_report_*.json'),
            ('root_performance_html', self.project_root, 'performance_report_*.html'),
            ('root_test_reports', self.project_root, 'comprehensive_test_report_*.json'),
            ('root_unit_tests', self.project_root, 'unit_tests*.xml'),
            ('logs_benchmark', self.logs_dir, 'benchmark_report_*.json'),
            ('reports_performance', self.reports_dir, 'performance_report_*.json'),
            ('reports_performance_html', self.reports_dir, 'performance_report_*.html'),
            ('test_results_reports', self.test_results_dir, 'comprehensive_test_report_*.json'),
            ('test_results_unit', self.test_results_dir, 'unit_tests*.xml')
        ]

        for name, directory, pattern in locations:
            try:
                if directory.exists():
                    files = list(directory.glob(pattern))
                    counts[name] = len(files)
                else:
                    counts[name] = 0
            except Exception as e:
                logger.error(f"[BenchmarkCleanup] Error counting {name}: {e}")
                counts[name] = -1

        return counts

    def print_status(self):
        """Print current status of benchmark files."""
        counts = self.get_file_counts()

        print("\n" + "="*50)
        print("BENCHMARK FILES STATUS")
        print("="*50)

        print("Files in ROOT (should be 0):")
        for key, count in counts.items():
            if key.startswith('root_'):
                file_type = key.replace('root_', '').replace('_', ' ').title()
                print(f"  {file_type}: {count}")

        print("\nFiles in organized directories:")
        for key, count in counts.items():
            if not key.startswith('root_'):
                file_type = key.replace('logs_', '').replace('reports_', '').replace('test_results_', '').replace('_', ' ').title()
                directory = key.split('_')[0]
                print(f"  {directory.title()}/{file_type}: {count}")

        print("="*50)


def cleanup_benchmark_files(project_root: Optional[Path] = None) -> dict:
    """
    Convenience function to perform benchmark cleanup.

    Args:
        project_root: Project root directory (auto-detected if None)

    Returns:
        Cleanup results dictionary
    """
    manager = BenchmarkCleanupManager(project_root)
    return manager.cleanup_all()


def print_benchmark_status(project_root: Optional[Path] = None):
    """
    Convenience function to print benchmark files status.

    Args:
        project_root: Project root directory (auto-detected if None)
    """
    manager = BenchmarkCleanupManager(project_root)
    manager.print_status()


if __name__ == "__main__":
    # Run cleanup when executed directly
    print("Running benchmark files cleanup...")

    manager = BenchmarkCleanupManager()

    print("Before cleanup:")
    manager.print_status()

    results = manager.cleanup_all()

    print("\nAfter cleanup:")
    manager.print_status()

    print(f"\nCleanup Results:")
    print(f"  Files moved: {results['moved_files']}")
    print(f"  Files deleted: {results['deleted_files']}")
    if results['errors']:
        print(f"  Errors: {len(results['errors'])}")
        for error in results['errors']:
            print(f"    - {error}")
