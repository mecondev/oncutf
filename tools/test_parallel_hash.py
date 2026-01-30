#!/usr/bin/env python3
"""Test script for parallel hash worker performance comparison.

Compares performance between serial and parallel hash workers.
"""

import os
import sys
import tempfile
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def create_test_files(count: int = 100, size_mb: float = 1.0) -> list[str]:
    """Create temporary test files for hash calculation.

    Args:
        count: Number of files to create
        size_mb: Size of each file in MB

    Returns:
        list: Paths to created files

    """
    temp_dir = tempfile.mkdtemp(prefix="hash_test_")
    file_paths = []

    print(f"Creating {count} test files ({size_mb}MB each) in {temp_dir}...")

    size_bytes = int(size_mb * 1024 * 1024)
    chunk_size = 8192

    for i in range(count):
        file_path = os.path.join(temp_dir, f"test_file_{i:04d}.dat")

        with open(file_path, "wb") as f:
            remaining = size_bytes
            while remaining > 0:
                write_size = min(chunk_size, remaining)
                # Write random-ish data (faster than os.urandom)
                f.write(bytes([i % 256] * write_size))
                remaining -= write_size

        file_paths.append(file_path)

        if (i + 1) % 10 == 0:
            print(f"  Created {i + 1}/{count} files...")

    print(f"Created {len(file_paths)} test files")
    return file_paths, temp_dir


def cleanup_test_files(temp_dir: str) -> None:
    """Remove test files and directory."""
    import shutil

    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
        print(f"Cleaned up test files in {temp_dir}")


def test_serial_worker(file_paths: list[str]) -> tuple[float, dict]:
    """Test serial hash worker."""
    from core.hash_worker import HashWorker
    from core.pyqt_imports import QApplication

    print("\n=== Testing Serial Hash Worker ===")

    app = QApplication.instance() or QApplication(sys.argv)

    worker = HashWorker()
    worker.setup_checksum_calculation(file_paths)

    results = {}
    completed = [False]

    def on_results(hash_results):
        results.update(hash_results)

    def on_finished(_success):
        completed[0] = True

    worker.checksums_calculated.connect(on_results)
    worker.finished_processing.connect(on_finished)

    start_time = time.time()
    worker.start()

    # Wait for completion
    while not completed[0]:
        app.processEvents()
        time.sleep(0.01)

    elapsed = time.time() - start_time

    worker.quit()
    worker.wait()

    print(f"Serial worker: {len(results)} files in {elapsed:.2f}s")
    print(f"  Speed: {len(file_paths) / elapsed:.1f} files/sec")

    return elapsed, results


def test_parallel_worker(
    file_paths: list[str], max_workers: int | None = None
) -> tuple[float, dict]:
    """Test parallel hash worker."""
    from core.parallel_hash_worker import ParallelHashWorker
    from core.pyqt_imports import QApplication

    worker_str = f"{max_workers} workers" if max_workers else "auto workers"
    print(f"\n=== Testing Parallel Hash Worker ({worker_str}) ===")

    app = QApplication.instance() or QApplication(sys.argv)

    worker = ParallelHashWorker(max_workers=max_workers)
    worker.setup_checksum_calculation(file_paths)

    results = {}
    completed = [False]

    def on_results(hash_results):
        results.update(hash_results)

    def on_finished(_success):
        completed[0] = True

    worker.checksums_calculated.connect(on_results)
    worker.finished_processing.connect(on_finished)

    start_time = time.time()
    worker.start()

    # Wait for completion
    while not completed[0]:
        app.processEvents()
        time.sleep(0.01)

    elapsed = time.time() - start_time

    worker.quit()
    worker.wait()

    print(f"Parallel worker ({worker_str}): {len(results)} files in {elapsed:.2f}s")
    print(f"  Speed: {len(file_paths) / elapsed:.1f} files/sec")

    return elapsed, results


def main():
    """Run performance comparison tests."""
    import argparse

    parser = argparse.ArgumentParser(description="Test parallel hash worker performance")
    parser.add_argument("--count", type=int, default=50, help="Number of test files (default: 50)")
    parser.add_argument(
        "--size", type=float, default=2.0, help="Size of each file in MB (default: 2.0)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of parallel workers (default: auto-detect)",
    )
    parser.add_argument("--skip-serial", action="store_true", help="Skip serial worker test")

    args = parser.parse_args()

    print("=" * 60)
    print("Parallel Hash Worker Performance Test")
    print("=" * 60)
    print(f"Files: {args.count}")
    print(f"Size per file: {args.size}MB")
    print(f"Total data: {args.count * args.size:.1f}MB")
    print()

    # Create test files
    file_paths, temp_dir = create_test_files(args.count, args.size)

    try:
        # Test serial worker
        if not args.skip_serial:
            serial_time, serial_results = test_serial_worker(file_paths)
        else:
            serial_time = None
            serial_results = None
            print("\n=== Skipping Serial Worker ===")

        # Test parallel worker
        parallel_time, parallel_results = test_parallel_worker(file_paths, args.workers)

        # Compare results
        print("\n" + "=" * 60)
        print("Performance Comparison")
        print("=" * 60)

        if serial_time:
            speedup = serial_time / parallel_time
            print(f"Serial time:   {serial_time:.2f}s")
            print(f"Parallel time: {parallel_time:.2f}s")
            print(f"Speedup:       {speedup:.2f}x")
            print(
                f"Time saved:    {serial_time - parallel_time:.2f}s ({(1 - parallel_time / serial_time) * 100:.1f}%)"
            )

            # Verify results match
            if serial_results and parallel_results:
                mismatches = 0
                for path in file_paths:
                    if serial_results.get(path) != parallel_results.get(path):
                        mismatches += 1

                if mismatches == 0:
                    print("\n All hash values match between serial and parallel!")
                else:
                    print(f"\n WARNING: {mismatches} hash mismatches detected!")
        else:
            print(f"Parallel time: {parallel_time:.2f}s")
            print(f"Speed: {args.count / parallel_time:.1f} files/sec")

    finally:
        # Cleanup
        cleanup_test_files(temp_dir)

    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
