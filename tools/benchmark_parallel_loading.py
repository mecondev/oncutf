#!/usr/bin/env python3
"""Benchmark script for parallel metadata loading.

Compares sequential vs parallel metadata loading performance.
"""

import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from oncutf.core.metadata.parallel_loader import ParallelMetadataLoader
from oncutf.domain.models.file_item import FileItem
from oncutf.infra.external.exopsis_wrapper import ExopsisWrapper


def create_file_items(
    directory: str, extensions: list[str] | None = None, max_files: int = 50
) -> list[FileItem]:
    """Create FileItem objects from files in directory."""
    supported_exts = {
        ".jpg", ".jpeg", ".JPG", ".JPEG",
        ".tif", ".tiff", ".TIF", ".TIFF",
        ".png", ".PNG",
        ".cr2", ".CR2", ".cr3", ".CR3",
        ".nef", ".NEF", ".arw", ".ARW",
        ".mp4", ".MP4", ".mov", ".MOV",
        ".mxf", ".MXF",
        ".ari", ".arx",
        ".r3d", ".R3D",
        ".wav", ".WAV",
    }
    if extensions is None:
        extensions = list(supported_exts)

    dir_path = Path(directory)
    if not dir_path.exists():
        print(f" Directory not found: {directory}")
        return []

    files = [p for p in dir_path.rglob("*") if p.is_file() and p.suffix in supported_exts]

    # Create FileItem objects
    items = []
    for file_path in files[:max_files]:
        stat = file_path.stat()
        item = FileItem(
            str(file_path),
            extension=file_path.suffix.lstrip("."),
            modified=datetime.fromtimestamp(stat.st_mtime),
        )
        items.append(item)

    return items


def benchmark_sequential(items: list[FileItem]) -> float:
    """Benchmark sequential metadata loading."""
    exopsis = ExopsisWrapper()

    print(f"\n Sequential Loading ({len(items)} files):")
    start_time = time.perf_counter()

    for i, item in enumerate(items):
        metadata = exopsis.get_metadata(item.full_path)
        item.metadata = metadata

        if (i + 1) % 10 == 0:
            elapsed = time.perf_counter() - start_time
            rate = (i + 1) / elapsed
            print(f"   Progress: {i + 1}/{len(items)} files ({rate:.1f} files/sec)")

    elapsed = time.perf_counter() - start_time
    rate = len(items) / elapsed

    print(f"    Completed in {elapsed:.2f}s ({rate:.1f} files/sec)")

    return elapsed


def benchmark_parallel(items: list[FileItem]) -> float:
    """Benchmark parallel metadata loading."""
    loader = ParallelMetadataLoader()

    completed = [0]  # Use list to modify in closure

    def on_progress(current: int, total: int, item: FileItem, metadata: dict) -> None:  # noqa: ARG001
        completed[0] = current
        if current % 10 == 0:
            elapsed = time.perf_counter() - start_time
            rate = current / elapsed
            print(f"   Progress: {current}/{total} files ({rate:.1f} files/sec)")

    print(f"\n Parallel Loading ({len(items)} files, workers={loader.max_workers}):")
    start_time = time.perf_counter()

    results = loader.load_metadata_parallel(items=items, progress_callback=on_progress)

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
        print("Usage: python scripts/benchmark_parallel_loading.py <directory> [max_files]")
        print("\nExamples:")
        print("  python scripts/benchmark_parallel_loading.py /mnt/data_1/C/ExifTest")
        print("  python scripts/benchmark_parallel_loading.py /mnt/data_1/C/ExifTest 30")
        sys.exit(1)

    directory = sys.argv[1]
    max_files = int(sys.argv[2]) if len(sys.argv) > 2 else 50

    print(f"\n{'=' * 80}")
    print(" Parallel Metadata Loading Benchmark")
    print(f"{'=' * 80}")
    print(f"Directory: {directory}")
    print(f"Max files: {max_files}")
    print(f"{'=' * 80}")

    # Create file items
    print("\n Scanning directory...")
    items = create_file_items(directory, max_files=max_files)

    if not items:
        print(" No files found")
        return

    print(f" Found {len(items)} files")

    # Benchmark sequential loading
    sequential_time = benchmark_sequential(items[:])

    # Reset metadata
    for item in items:
        item.metadata = None

    # Benchmark parallel loading
    parallel_time = benchmark_parallel(items[:])

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
