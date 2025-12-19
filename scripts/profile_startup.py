#!/usr/bin/env python3
"""
Module: profile_startup.py

Startup profiling script for oncutf application.
Measures import time, initialization time, and identifies bottlenecks.

Author: Michael Economou
Date: 2025-12-19

Usage:
    python scripts/profile_startup.py [--full] [--save]

Options:
    --full  Run full profiling with cProfile (slower but more detail)
    --save  Save profile data to reports/startup_profile.prof
"""

from __future__ import annotations

import argparse
import cProfile
import importlib
import pstats
import sys
import time
from io import StringIO
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def measure_import_times() -> dict[str, float]:
    """Measure import times for key modules.

    Returns:
        Dictionary mapping module name to import time in seconds.
    """
    import_times: dict[str, float] = {}

    modules_to_measure = [
        "PyQt5",
        "PyQt5.QtWidgets",
        "PyQt5.QtCore",
        "PyQt5.QtGui",
        "oncutf",
        "oncutf.config",
        "oncutf.core",
        "oncutf.core.application_context",
        "oncutf.core.application_service",
        "oncutf.core.unified_rename_engine",
        "oncutf.core.unified_metadata_manager",
        "oncutf.ui",
        "oncutf.ui.main_window",
        "oncutf.services",
        "oncutf.controllers",
        "oncutf.modules",
    ]

    print("Measuring import times...")
    print("-" * 50)

    for module_name in modules_to_measure:
        # Skip if already imported
        if module_name in sys.modules:
            import_times[module_name] = 0.0
            continue

        start = time.perf_counter()
        try:
            importlib.import_module(module_name)
            elapsed = time.perf_counter() - start
            import_times[module_name] = elapsed
            status = "OK"
        except ImportError as e:
            elapsed = time.perf_counter() - start
            import_times[module_name] = -1.0
            status = f"FAILED: {e}"

        if import_times[module_name] >= 0:
            print(f"  {module_name}: {import_times[module_name]*1000:.1f}ms")
        else:
            print(f"  {module_name}: {status}")

    return import_times


def measure_window_creation() -> tuple[float, float]:
    """Measure MainWindow creation time.

    Returns:
        Tuple of (creation_time, show_time) in seconds.
    """
    from PyQt5.QtWidgets import QApplication

    # Create app if needed
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    print("\nMeasuring window creation...")
    print("-" * 50)

    # Import and create MainWindow
    start_import = time.perf_counter()
    from oncutf.ui.main_window import MainWindow
    import_time = time.perf_counter() - start_import
    print(f"  MainWindow import: {import_time*1000:.1f}ms")

    start_create = time.perf_counter()
    window = MainWindow()
    creation_time = time.perf_counter() - start_create
    print(f"  MainWindow.__init__: {creation_time*1000:.1f}ms")

    start_show = time.perf_counter()
    window.show()
    app.processEvents()  # Process pending events
    show_time = time.perf_counter() - start_show
    print(f"  MainWindow.show(): {show_time*1000:.1f}ms")

    # Cleanup
    window.close()

    return creation_time, show_time


def run_full_profile(save_path: Path | None = None) -> None:
    """Run full cProfile analysis.

    Args:
        save_path: Optional path to save profile data.
    """
    print("\nRunning full profile (this may take a moment)...")
    print("-" * 50)

    profiler = cProfile.Profile()
    profiler.enable()

    # Profile the full startup
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    from oncutf.ui.main_window import MainWindow
    window = MainWindow()
    window.show()
    app.processEvents()
    window.close()

    profiler.disable()

    # Print stats
    print("\nTop 30 functions by cumulative time:")
    s = StringIO()
    stats = pstats.Stats(profiler, stream=s)
    stats.sort_stats("cumulative")
    stats.print_stats(30)
    print(s.getvalue())

    # Save if requested
    if save_path:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        stats.dump_stats(str(save_path))
        print(f"\nProfile data saved to: {save_path}")


def print_summary(import_times: dict[str, float],
                  creation_time: float,
                  show_time: float) -> None:
    """Print a summary of profiling results."""
    print("\n" + "=" * 50)
    print("STARTUP PROFILING SUMMARY")
    print("=" * 50)

    # Calculate totals
    total_import = sum(t for t in import_times.values() if t >= 0)
    total_startup = total_import + creation_time + show_time

    print(f"\nTotal import time:     {total_import*1000:.1f}ms")
    print(f"Window creation time:  {creation_time*1000:.1f}ms")
    print(f"Window show time:      {show_time*1000:.1f}ms")
    print(f"{'='*30}")
    print(f"TOTAL STARTUP TIME:    {total_startup*1000:.1f}ms ({total_startup:.2f}s)")

    # Identify slowest imports
    print("\nSlowest imports:")
    sorted_imports = sorted(
        [(k, v) for k, v in import_times.items() if v > 0],
        key=lambda x: x[1],
        reverse=True
    )
    for name, t in sorted_imports[:5]:
        print(f"  {name}: {t*1000:.1f}ms")


def main() -> int:
    """Main entry point for startup profiling.

    Returns:
        Exit code (0 for success).
    """
    parser = argparse.ArgumentParser(
        description="Profile oncutf startup performance"
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full cProfile analysis"
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save profile data to reports/startup_profile.prof"
    )
    args = parser.parse_args()

    print("=" * 50)
    print("OnCutF Startup Profiler")
    print("=" * 50)

    # Measure imports
    import_times = measure_import_times()

    # Measure window creation
    creation_time, show_time = measure_window_creation()

    # Print summary
    print_summary(import_times, creation_time, show_time)

    # Full profile if requested
    if args.full:
        save_path = None
        if args.save:
            save_path = PROJECT_ROOT / "reports" / "startup_profile.prof"
        run_full_profile(save_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
