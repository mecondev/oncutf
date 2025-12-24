#!/usr/bin/env python3
"""Module: profile_memory.py

Memory profiling script for oncutf application.
Measures memory usage during startup and operation.

Author: Michael Economou
Date: 2025-12-19

Usage:
    python scripts/profile_memory.py [--detailed] [--save]

Options:
    --detailed  Show detailed memory breakdown by module
    --save      Save memory snapshot to reports/memory_snapshot.txt
"""

from __future__ import annotations

import argparse
import linecache
import sys
import tracemalloc
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def format_size(size: int) -> str:
    """Format size in bytes to human readable string.

    Args:
        size: Size in bytes.

    Returns:
        Human readable size string.

    """
    for unit in ("B", "KB", "MB", "GB"):
        if abs(size) < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024  # type: ignore[assignment]
    return f"{size:.1f} TB"


def display_top_allocations(snapshot: tracemalloc.Snapshot, limit: int = 20) -> list[str]:
    """Display top memory allocations.

    Args:
        snapshot: tracemalloc snapshot.
        limit: Number of top allocations to show.

    Returns:
        List of formatted allocation strings.

    """
    top_stats = snapshot.statistics("lineno")

    lines = []
    lines.append(f"\nTop {limit} memory allocations:")
    lines.append("-" * 70)

    for index, stat in enumerate(top_stats[:limit], 1):
        frame = stat.traceback[0]
        lines.append(f"#{index}: {frame.filename}:{frame.lineno}")
        lines.append(f"    Size: {format_size(stat.size)}, Count: {stat.count}")

        # Try to show the source line
        line = linecache.getline(frame.filename, frame.lineno).strip()
        if line:
            lines.append(f"    {line}")
        lines.append("")

    return lines


def display_top_by_file(snapshot: tracemalloc.Snapshot, limit: int = 15) -> list[str]:
    """Display memory usage grouped by file.

    Args:
        snapshot: tracemalloc snapshot.
        limit: Number of top files to show.

    Returns:
        List of formatted allocation strings.

    """
    top_stats = snapshot.statistics("filename")

    lines = []
    lines.append(f"\nTop {limit} files by memory usage:")
    lines.append("-" * 70)

    for index, stat in enumerate(top_stats[:limit], 1):
        lines.append(f"#{index}: {stat.traceback}")
        lines.append(f"    Total: {format_size(stat.size)}, Count: {stat.count}")
        lines.append("")

    return lines


def profile_startup_memory(detailed: bool = False) -> tuple[int, int, list[str]]:
    """Profile memory usage during application startup.

    Args:
        detailed: Whether to include detailed breakdown.

    Returns:
        Tuple of (current_memory, peak_memory, report_lines).

    """
    report_lines: list[str] = []

    print("Starting memory profiling...")
    print("-" * 50)

    tracemalloc.start()

    # Import core modules
    print("  Importing PyQt5...")
    from PyQt5.QtWidgets import QApplication  # noqa: F401

    current1, _ = tracemalloc.get_traced_memory()
    report_lines.append(f"After PyQt5 import: {format_size(current1)}")

    # Import oncutf
    print("  Importing oncutf...")
    from oncutf.ui.main_window import MainWindow  # noqa: F401

    current2, _ = tracemalloc.get_traced_memory()
    report_lines.append(f"After oncutf import: {format_size(current2)}")

    # Create application
    print("  Creating QApplication...")
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    current3, _ = tracemalloc.get_traced_memory()
    report_lines.append(f"After QApplication: {format_size(current3)}")

    # Create main window
    print("  Creating MainWindow...")
    window = MainWindow()
    window.show()
    app.processEvents()

    snapshot = tracemalloc.take_snapshot()
    current4, _ = tracemalloc.get_traced_memory()
    report_lines.append(f"After MainWindow: {format_size(current4)}")

    # Get final stats
    current, peak = tracemalloc.get_traced_memory()

    report_lines.append("")
    report_lines.append("=" * 50)
    report_lines.append("MEMORY SUMMARY")
    report_lines.append("=" * 50)
    report_lines.append(f"Current memory: {format_size(current)}")
    report_lines.append(f"Peak memory: {format_size(peak)}")

    # Detailed breakdown
    if detailed:
        report_lines.extend(display_top_allocations(snapshot, 20))
        report_lines.extend(display_top_by_file(snapshot, 15))

    # Cleanup
    window.close()
    tracemalloc.stop()

    return current, peak, report_lines


def save_report(lines: list[str], path: Path) -> None:
    """Save memory report to file.

    Args:
        lines: Report lines.
        path: Output file path.

    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nReport saved to: {path}")


def main() -> int:
    """Main entry point for memory profiling.

    Returns:
        Exit code (0 for success).

    """
    parser = argparse.ArgumentParser(description="Profile oncutf memory usage")
    parser.add_argument("--detailed", action="store_true", help="Show detailed memory breakdown")
    parser.add_argument(
        "--save", action="store_true", help="Save report to reports/memory_snapshot.txt"
    )
    args = parser.parse_args()

    print("=" * 50)
    print("OnCutF Memory Profiler")
    print("=" * 50)

    current, peak, report_lines = profile_startup_memory(args.detailed)

    # Print report
    for line in report_lines:
        print(line)

    # Save if requested
    if args.save:
        save_path = PROJECT_ROOT / "reports" / "memory_snapshot.txt"
        save_report(report_lines, save_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
