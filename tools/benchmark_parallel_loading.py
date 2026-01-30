#!/usr/bin/env python3
"""Benchmark script for parallel metadata loading.

Compares sequential vs parallel metadata loading performance.
"""

import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.parallel_metadata_loader import ParallelMetadataLoader
from models.file_item import FileItem

from oncutf.infra.external.exiftool_wrapper import ExifToolWrapper


def create_file_items(
    directory: str, extensions: list[str] | None = None, max_files: int = 50
) -> list[FileItem]:
    """Create FileItem objects from files in directory."""
    if extensions is None:
        extensions = [".jpg", ".jpeg", ".mp4", ".mov", ".png", ".tif", ".tiff"]

    dir_path = Path(directory)
    if not dir_path.exists():
        print(f" Directory not found: {directory}")
        return []

    files = []
    for ext in extensions:
        files.extend(list(dir_path.rglob(f"*{ext}"))[: max_files // len(extensions)])

    # Create FileItem objects
    items = []
    for file_path in files[:max_files]:
        item = FileItem(str(file_path))
        items.append(item)

    return items


def benchmark_sequential(items: list[FileItem], use_extended: bool = False) -> float:
    """Benchmark sequential metadata loading."""
    exiftool = ExifToolWrapper()

    print(f"\n Sequential Loading ({len(items)} files, extended={use_extended}):")
    start_time = time.perf_counter()

    for i, item in enumerate(items):
        metadata = exiftool.get_metadata(item.full_path, use_extended=use_extended)
        item.metadata = metadata

        if (i + 1) % 10 == 0:
            elapsed = time.perf_counter() - start_time
            rate = (i + 1) / elapsed
            print(f"   Progress: {i + 1}/{len(items)} files ({rate:.1f} files/sec)")

    elapsed = time.perf_counter() - start_time
    rate = len(items) / elapsed

    print(f"    Completed in {elapsed:.2f}s ({rate:.1f} files/sec)")

    return elapsed


def benchmark_parallel(items: list[FileItem], use_extended: bool = False) -> float:
    """Benchmark parallel metadata loading."""
    loader = ParallelMetadataLoader()

    completed = [0]  # Use list to modify in closure

    def on_progress(current: int, total: int, item: FileItem, metadata: dict):  # noqa: ARG001
        completed[0] = current
        if current % 10 == 0:
            elapsed = time.perf_counter() - start_time
            rate = current / elapsed
            print(f"   Progress: {current}/{total} files ({rate:.1f} files/sec)")

    print(
        f"\n Parallel Loading ({len(items)} files, extended={use_extended}, workers={loader.max_workers}):"
    )
    start_time = time.perf_counter()

    results = loader.load_metadata_parallel(
        items=items, use_extended=use_extended, progress_callback=on_progress
    )

    elapsed = time.perf_counter() - start_time
    rate = len(items) / elapsed

    print(f"    Completed in {elapsed:.2f}s ({rate:.1f} files/sec)")

    # Verify all files got metadata
    success_count = sum(1 for _, metadata in results if metadata)
    print(f"    Success: {success_count}/{len(items)} files")

    return elapsed


def main():
    """Main benchmark function."""
    if len(sys.argv) < 2:
        print(
            "Usage: python scripts/benchmark_parallel_loading.py <directory> [max_files] [extended]"
        )
        print("\nExamples:")
        print("  python scripts/benchmark_parallel_loading.py /mnt/data_1/C/ExifTest")
        print("  python scripts/benchmark_parallel_loading.py /mnt/data_1/C/ExifTest 30")
        print("  python scripts/benchmark_parallel_loading.py /mnt/data_1/C/ExifTest 30 extended")
        sys.exit(1)

    directory = sys.argv[1]
    max_files = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    use_extended = len(sys.argv) > 3 and sys.argv[3].lower() == "extended"

    print(f"\n{'=' * 80}")
    print(" Parallel Metadata Loading Benchmark")
    print(f"{'=' * 80}")
    print(f"Directory: {directory}")
    print(f"Max files: {max_files}")
    print(f"Extended mode: {use_extended}")
    print(f"{'=' * 80}")

    # Create file items
    print("\n Scanning directory...")
    items = create_file_items(directory, max_files=max_files)

    if not items:
        print(" No files found")
        return

    print(f" Found {len(items)} files")

    # Benchmark sequential loading
    sequential_time = benchmark_sequential(items[:], use_extended)

    # Reset metadata
    for item in items:
        item.metadata = None

    # Benchmark parallel loading
    parallel_time = benchmark_parallel(items[:], use_extended)

    # Summary
    speedup = sequential_time / parallel_time if parallel_time > 0 else 0
    improvement = (
        ((sequential_time - parallel_time) / sequential_time * 100) if sequential_time > 0 else 0
    )

    print(f"\n{'=' * 80}")
    print(" SUMMARY")
    print(f"{'=' * 80}")
    print(f"Sequential:  {sequential_time:.2f}s ({len(items) / sequential_time:.1f} files/sec)")
    print(f"Parallel:    {parallel_time:.2f}s ({len(items) / parallel_time:.1f} files/sec)")
    print("")
    print(f" Speedup:   {speedup:.2f}x faster")
    print(f" Improvement: {improvement:.1f}% time saved")
    print(f"⏱️  Time saved: {sequential_time - parallel_time:.2f}s")
    print(f"{'=' * 80}")

    # Performance category
    if speedup >= 3:
        print(" Excellent performance!")
    elif speedup >= 2:
        print(" Good performance!")
    elif speedup >= 1.5:
        print(" Moderate improvement")
    else:
        print("️  Limited improvement (consider file size/network factors)")


if __name__ == "__main__":
    main()
