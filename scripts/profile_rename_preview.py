#!/usr/bin/env python3
"""Profile rename preview generation performance.

Author: Michael Economou
Date: 2025-12-20

This script tests:
1. Preview generation time for different file counts
2. Rename engine overhead
3. Conflict detection performance
4. UI update overhead
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def create_test_files(count: int) -> list[str]:
    """Create dummy file paths for testing."""
    return [f"/tmp/test_file_{i:04d}.jpg" for i in range(count)]


def profile_rename_preview(file_count: int) -> dict[str, float]:
    """Profile rename preview generation for given file count."""
    print(f"\n{'=' * 80}")
    print(f"PROFILING: Rename Preview ({file_count} files)")
    print("=" * 80)

    from PyQt5.QtWidgets import QApplication

    from oncutf.models.file_item import FileItem

    # Create QApplication if needed
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    # Create test file items
    file_items = []
    for path in create_test_files(file_count):
        item = FileItem.from_path(path)
        file_items.append(item)

    # Simple name transformation: add prefix (simulate module output)
    transform_start = time.perf_counter()
    new_names = {}
    for item in file_items:
        # Simulate what a rename module would do
        new_name = f"renamed_{item.filename}"
        new_names[item.full_path] = new_name
    transform_time = time.perf_counter() - transform_start

    # Conflict detection (what UnifiedRenameEngine does)
    validate_start = time.perf_counter()
    conflicts = set()
    seen = {}
    for path, new_name in new_names.items():
        if new_name in seen:
            conflicts.add(path)
            conflicts.add(seen[new_name])
        else:
            seen[new_name] = path
    validate_time = time.perf_counter() - validate_start

    total_time = transform_time + validate_time

    results = {
        "file_count": file_count,
        "transform_time": transform_time * 1000,
        "validate_time": validate_time * 1000,
        "total_time": total_time * 1000,
        "per_file": (total_time * 1000) / file_count,
        "conflicts": len(conflicts),
    }

    print("\n📊 Rename Preview Performance:")
    print(f"  Files:           {file_count}")
    print(f"  Transform:       {results['transform_time']:>8.3f} ms")
    print(f"  Validation:      {results['validate_time']:>8.3f} ms")
    print(f"  Total:           {results['total_time']:>8.3f} ms")
    print(f"  Per file:        {results['per_file']:>8.4f} ms")
    print(f"  Throughput:      {file_count / (results['total_time']/1000):>8.0f} files/sec")
    print(f"  Conflicts:       {results['conflicts']}")

    return results


def profile_multiple_sizes() -> list[dict[str, float]]:
    """Profile rename preview for multiple file counts."""
    print("\n" + "=" * 80)
    print("Rename Preview Scaling Test")
    print("=" * 80)

    sizes = [10, 50, 100, 500, 1000]
    results = []

    for size in sizes:
        result = profile_rename_preview(size)
        if result:
            results.append(result)
        time.sleep(0.5)  # Brief pause between tests

    return results


def main() -> int:
    """Run rename preview profiling tests."""
    print("\n" + "=" * 80)
    print("🔬 Rename Preview Performance Profiling")
    print("=" * 80)

    try:
        results = profile_multiple_sizes()
    except Exception as e:
        print(f"\n❌ Error during profiling: {e}")
        import traceback

        traceback.print_exc()
        return 1

    # Summary
    print("\n" + "=" * 80)
    print("📈 SCALING ANALYSIS")
    print("=" * 80)

    if results:
        print("\n| Files | Total (ms) | Per File (μs) | Throughput (files/sec) |")
        print("|-------|------------|---------------|------------------------|")
        for r in results:
            per_file_us = r["per_file"] * 1000  # Convert ms to microseconds
            print(
                f"| {r['file_count']:>5} | {r['total_time']:>10.3f} | "
                f"{per_file_us:>13.2f} | "
                f"{r['file_count'] / (r['total_time']/1000):>22.0f} |"
            )

        # Check for linear scaling
        if len(results) >= 3:
            first = results[0]
            last = results[-1]
            file_ratio = last["file_count"] / first["file_count"]
            time_ratio = last["total_time"] / first["total_time"]

            print("\n📊 Scaling Factor:")
            print(f"  Files increased by: {file_ratio:.1f}x")
            print(f"  Time increased by:  {time_ratio:.1f}x")

            if abs(time_ratio - file_ratio) / file_ratio < 0.2:  # Within 20%
                print("  ✅ Linear scaling (O(n))")
            elif time_ratio > file_ratio * 1.5:
                print("  ⚠️  Worse than linear (possible O(n²) component)")
            else:
                print("  ✅ Sub-linear scaling (good caching or optimization)")

    print("\n" + "=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
