#!/usr/bin/env python3
"""
Profile metadata loading performance for sample files.

Author: Michael Economou
Date: 2025-12-20

This script tests:
1. ExifTool overhead
2. Per-file metadata load time
3. Batch vs sequential loading
4. Cache hit performance
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def find_test_images() -> list[Path]:
    """Find test images in various locations."""
    test_paths = [
        PROJECT_ROOT / "tests" / "test_data",
        PROJECT_ROOT / "examples",
        Path.home() / "Pictures",
        Path("/usr/share/pixmaps"),
    ]

    images = []
    for test_path in test_paths:
        if test_path.exists():
            # Find JPG, PNG, TIFF files
            for pattern in ["*.jpg", "*.jpeg", "*.png", "*.tiff", "*.tif"]:
                images.extend(test_path.glob(pattern))
                if len(images) >= 20:
                    break
        if len(images) >= 20:
            break

    return images[:20]  # Limit to 20 files


def profile_exiftool_overhead() -> dict[str, float]:
    """Profile ExifTool startup/initialization overhead."""
    print("\n" + "=" * 80)
    print("PROFILING: ExifTool Overhead")
    print("=" * 80)

    # Import time
    import_start = time.perf_counter()
    from oncutf.utils.exiftool_wrapper import ExifToolWrapper

    import_time = time.perf_counter() - import_start

    # Initialization time
    init_start = time.perf_counter()
    exiftool = ExifToolWrapper()
    init_time = time.perf_counter() - init_start

    # First command (warm-up)
    test_images = find_test_images()
    if test_images:
        warmup_start = time.perf_counter()
        _ = exiftool.get_metadata(str(test_images[0]))
        warmup_time = time.perf_counter() - warmup_start
    else:
        warmup_time = 0.0
        print("⚠️  No test images found for warmup")

    # Cleanup
    exiftool.close()

    results = {
        "import_time": import_time * 1000,
        "init_time": init_time * 1000,
        "warmup_time": warmup_time * 1000,
    }

    print("\n📊 ExifTool Overhead:")
    print(f"  Import:     {results['import_time']:>8.1f} ms")
    print(f"  Init:       {results['init_time']:>8.1f} ms")
    print(f"  First cmd:  {results['warmup_time']:>8.1f} ms")
    print(f"  Total:      {sum(results.values()):>8.1f} ms")

    return results


def profile_sequential_loading() -> dict[str, float]:
    """Profile sequential metadata loading (one file at a time)."""
    print("\n" + "=" * 80)
    print("PROFILING: Sequential Metadata Loading")
    print("=" * 80)

    test_images = find_test_images()
    if not test_images:
        print("⚠️  No test images found - skipping")
        return {}

    print(f"Testing with {len(test_images)} files")

    from oncutf.utils.exiftool_wrapper import ExifToolWrapper

    exiftool = ExifToolWrapper()

    # Measure individual file load times
    load_times = []
    total_start = time.perf_counter()

    for img in test_images:
        start = time.perf_counter()
        _ = exiftool.get_metadata(str(img))
        elapsed = time.perf_counter() - start
        load_times.append(elapsed * 1000)

    total_time = time.perf_counter() - total_start

    exiftool.close()

    results = {
        "total_time": total_time * 1000,
        "avg_per_file": sum(load_times) / len(load_times),
        "min_per_file": min(load_times),
        "max_per_file": max(load_times),
        "num_files": len(test_images),
    }

    print(f"\n📊 Sequential Loading ({len(test_images)} files):")
    print(f"  Total:      {results['total_time']:>8.1f} ms")
    print(f"  Avg/file:   {results['avg_per_file']:>8.1f} ms")
    print(f"  Min/file:   {results['min_per_file']:>8.1f} ms")
    print(f"  Max/file:   {results['max_per_file']:>8.1f} ms")
    print(f"  Throughput: {len(test_images) / (results['total_time']/1000):>8.1f} files/sec")

    return results


def profile_batch_loading() -> dict[str, float]:
    """Profile batch metadata loading (all files at once)."""
    print("\n" + "=" * 80)
    print("PROFILING: Batch Metadata Loading")
    print("=" * 80)

    test_images = find_test_images()
    if not test_images:
        print("⚠️  No test images found - skipping")
        return {}

    print(f"Testing with {len(test_images)} files")

    from oncutf.utils.exiftool_wrapper import ExifToolWrapper

    exiftool = ExifToolWrapper()

    # Batch load
    start = time.perf_counter()
    _ = exiftool.get_metadata_batch([str(img) for img in test_images])
    total_time = time.perf_counter() - start

    exiftool.close()

    results = {
        "total_time": total_time * 1000,
        "avg_per_file": (total_time * 1000) / len(test_images),
        "num_files": len(test_images),
    }

    print(f"\n📊 Batch Loading ({len(test_images)} files):")
    print(f"  Total:      {results['total_time']:>8.1f} ms")
    print(f"  Avg/file:   {results['avg_per_file']:>8.1f} ms")
    print(f"  Throughput: {len(test_images) / (results['total_time']/1000):>8.1f} files/sec")

    return results


def profile_cache_performance() -> dict[str, float]:
    """Profile metadata cache hit performance."""
    print("\n" + "=" * 80)
    print("PROFILING: Cache Performance")
    print("=" * 80)

    test_images = find_test_images()
    if not test_images:
        print("⚠️  No test images found - skipping")
        return {}

    print(f"Testing with {len(test_images)} files")

    from oncutf.utils.metadata_cache_helper import MetadataCacheHelper

    cache = MetadataCacheHelper()

    # First pass: populate cache (cold)
    cold_times = []
    for img in test_images:
        start = time.perf_counter()
        _ = cache.get_cached_metadata(str(img))
        elapsed = time.perf_counter() - start
        cold_times.append(elapsed * 1000)

    # Second pass: read from cache (hot)
    hot_times = []
    for img in test_images:
        start = time.perf_counter()
        _ = cache.get_cached_metadata(str(img))
        elapsed = time.perf_counter() - start
        hot_times.append(elapsed * 1000)

    results = {
        "cold_avg": sum(cold_times) / len(cold_times),
        "hot_avg": sum(hot_times) / len(hot_times),
        "speedup": (sum(cold_times) / len(cold_times)) / (sum(hot_times) / len(hot_times)),
    }

    print("\n📊 Cache Performance:")
    print(f"  Cold (miss): {results['cold_avg']:>8.3f} ms/file")
    print(f"  Hot (hit):   {results['hot_avg']:>8.3f} ms/file")
    print(f"  Speedup:     {results['speedup']:>8.1f}x")

    return results


def main() -> int:
    """Run all metadata profiling tests."""
    print("\n" + "=" * 80)
    print("🔬 Metadata Loading Performance Profiling")
    print("=" * 80)

    test_images = find_test_images()
    if not test_images:
        print("\n❌ No test images found!")
        print("Searched in:")
        print("  - tests/test_data/")
        print("  - examples/")
        print("  - ~/Pictures/")
        print("  - /usr/share/pixmaps/")
        return 1

    print(f"\n✅ Found {len(test_images)} test images")
    for img in test_images[:5]:
        print(f"  - {img.name}")
    if len(test_images) > 5:
        print(f"  ... and {len(test_images) - 5} more")

    results = {}

    try:
        results["exiftool"] = profile_exiftool_overhead()
        results["sequential"] = profile_sequential_loading()
        results["batch"] = profile_batch_loading()
        # Skip cache profiling - requires FileItem objects
        # results["cache"] = profile_cache_performance()
    except Exception as e:
        print(f"\n❌ Error during profiling: {e}")
        import traceback

        traceback.print_exc()
        return 1

    # Summary
    print("\n" + "=" * 80)
    print("📈 PROFILING SUMMARY")
    print("=" * 80)

    if "exiftool" in results and results["exiftool"]:
        print(f"\n✅ ExifTool overhead: {sum(results['exiftool'].values()):.1f} ms")

    if "sequential" in results and results["sequential"]:
        seq = results["sequential"]
        print(
            f"\n✅ Sequential: {seq['avg_per_file']:.1f} ms/file ({seq['total_time']:.1f} ms for {int(seq['num_files'])} files)"
        )

    if "batch" in results and results["batch"]:
        batch = results["batch"]
        print(
            f"\n✅ Batch: {batch['avg_per_file']:.1f} ms/file ({batch['total_time']:.1f} ms for {int(batch['num_files'])} files)"
        )

    if "sequential" in results and "batch" in results:
        seq_total = results["sequential"]["total_time"]
        batch_total = results["batch"]["total_time"]
        speedup = seq_total / batch_total
        print(f"\n🚀 Batch speedup: {speedup:.1f}x faster than sequential")

    print("\n" + "=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
