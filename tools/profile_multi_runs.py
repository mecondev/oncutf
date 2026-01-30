#!/usr/bin/env python3
"""Run multiple startup performance tests and report statistics.

Author: Michael Economou
Date: 2025-12-20
"""

from __future__ import annotations

import statistics
import sys
import time
import tracemalloc
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def measure_startup() -> tuple[float, float, float, float]:
    """Single startup measurement."""
    start_time = time.perf_counter()
    tracemalloc.start()

    # Import timing
    import_start = time.perf_counter()
    from PyQt5.QtWidgets import QApplication

    from oncutf.ui.main_window import MainWindow

    import_time = time.perf_counter() - import_start

    # Application creation
    app_start = time.perf_counter()
    app = QApplication(sys.argv)
    app_time = time.perf_counter() - app_start

    # Window creation
    window_start = time.perf_counter()
    window = MainWindow()
    window_time = time.perf_counter() - window_start

    total_time = time.perf_counter() - start_time

    # Cleanup
    window.close()
    app.quit()
    tracemalloc.stop()

    return total_time, import_time, app_time, window_time


def main() -> int:
    """Run multiple tests and report statistics."""
    print("=" * 80)
    print("Performance Test - Multiple Runs")
    print("=" * 80)
    print("Note: First run may be slower due to disk caching\n")

    num_runs = 5
    results = []

    for i in range(num_runs):
        print(f"Run {i + 1}/{num_runs}...", end=" ", flush=True)
        try:
            total, import_t, app_t, window_t = measure_startup()
            results.append(
                {
                    "total": total * 1000,
                    "import": import_t * 1000,
                    "app": app_t * 1000,
                    "window": window_t * 1000,
                }
            )
            print(f"{total * 1000:.1f}ms")
        except Exception as e:
            print(f"FAILED: {e}")
            continue

    if not results:
        print("\n❌ All runs failed!")
        return 1

    # Calculate statistics
    print("\n" + "=" * 80)
    print("STATISTICS")
    print("=" * 80)

    for metric in ["total", "import", "app", "window"]:
        values = [r[metric] for r in results]
        print(f"\n{metric.upper()}:")
        print(f"  Min:    {min(values):>8.1f} ms")
        print(f"  Median: {statistics.median(values):>8.1f} ms")
        print(f"  Mean:   {statistics.mean(values):>8.1f} ms")
        print(f"  Max:    {max(values):>8.1f} ms")
        if len(values) > 1:
            print(f"  StdDev: {statistics.stdev(values):>8.1f} ms")

    return 0


if __name__ == "__main__":
    sys.exit(main())
