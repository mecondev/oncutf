#!/usr/bin/env python3
"""Test: Multiple Files Scroll Simulation

Author: Michael Economou
Date: 2026-01-16

Purpose:
    Simulate realistic scrolling through a thumbnail grid with multiple files.
    Verify deduplication works correctly when scrolling back and forth.

Usage:
    python tests/manual/test_scroll_multiple_files.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from PyQt5.QtWidgets import QApplication

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from oncutf.core.database.database_manager import DatabaseManager
from oncutf.core.thumbnail.thumbnail_manager import ThumbnailManager
from oncutf.utils.paths import AppPaths


def simulate_viewport_scroll(
    manager: ThumbnailManager,
    all_files: list[str],
    viewport_size: int = 10,
    num_scrolls: int = 20
) -> dict[str, int]:
    """Simulate scrolling through thumbnail grid.

    Args:
        manager: ThumbnailManager instance
        all_files: List of file paths
        viewport_size: Number of visible items in viewport
        num_scrolls: Number of scroll steps

    Returns:
        Statistics about queue behavior
    """
    print("\nSimulating viewport scroll:")
    print(f"  Total files:    {len(all_files)}")
    print(f"  Viewport size:  {viewport_size}")
    print(f"  Scroll steps:   {num_scrolls}")
    print("-" * 80)

    start_time = time.perf_counter()
    total_requests = 0

    # Simulate scrolling forward and backward
    for scroll_idx in range(num_scrolls):
        # Calculate visible range
        start_idx = (scroll_idx * 2) % max(1, len(all_files) - viewport_size)
        end_idx = min(start_idx + viewport_size, len(all_files))

        visible_files = all_files[start_idx:end_idx]

        # Request thumbnails for visible items (simulates data() calls)
        for file_path in visible_files:
            manager.get_thumbnail(file_path, size_px=128)
            total_requests += 1

        if scroll_idx % 5 == 0:
            queue_size = manager._request_queue.qsize()
            pending_size = len(manager._pending_requests)
            print(f"  Scroll {scroll_idx:2d}: visible=[{start_idx}:{end_idx}], "
                  f"queue={queue_size}, pending={pending_size}")

    end_time = time.perf_counter()

    final_queue = manager._request_queue.qsize()
    final_pending = len(manager._pending_requests)
    unique_files = len(set(all_files[:viewport_size * 3]))  # Files we've actually seen

    print("\nResults:")
    print(f"  Total get_thumbnail() calls: {total_requests}")
    print(f"  Unique files requested:      {unique_files}")
    print(f"  Queue entries created:       {final_queue}")
    print(f"  Pending requests:            {final_pending}")
    print(f"  Deduplication savings:       {total_requests - final_pending} avoided duplicates")
    print(f"  Time elapsed:                {end_time - start_time:.3f}s")

    return {
        "total_calls": total_requests,
        "unique_files": unique_files,
        "queue_size": final_queue,
        "pending": final_pending,
        "duplicates_avoided": total_requests - final_pending,
    }


def main() -> None:
    """Run multiple file scroll test."""
    print("=" * 80)
    print("Multiple Files Scroll Simulation")
    print("=" * 80)

    # Initialize Qt application
    _app = QApplication(sys.argv)

    # Initialize database
    db_path = AppPaths.get_database_path()
    print(f"\nDatabase: {db_path}")

    db_manager = DatabaseManager(str(db_path))

    # Initialize thumbnail manager
    thumbnail_store = db_manager.thumbnail_store
    manager = ThumbnailManager(thumbnail_store, max_workers=2)

    # Find test files
    test_dir = Path.home() / "Videos"
    if not test_dir.exists():
        test_dir = Path.home() / "Pictures"

    # Try multiple file types
    test_files = []
    for pattern in ["**/*.mp4", "**/*.jpg", "**/*.png", "**/*.jpeg"]:
        test_files.extend([str(f) for f in test_dir.glob(pattern)])
        if len(test_files) >= 30:
            break

    test_files = test_files[:30]  # Limit to 30

    if len(test_files) < 5:
        print(f"\nERROR: Need at least 5 test files, found {len(test_files)}")
        sys.exit(1)

    print(f"Test files: {len(test_files)} files")

    # Run test
    stats = simulate_viewport_scroll(
        manager,
        test_files,
        viewport_size=10,
        num_scrolls=20
    )

    # Validate results
    print("\n" + "=" * 80)
    efficiency = 100 * (1 - stats["pending"] / stats["total_calls"])
    print(f"Deduplication efficiency: {efficiency:.1f}%")
    print(f"  ({stats['duplicates_avoided']} duplicate requests avoided)")

    if efficiency >= 80:
        print("[SUCCESS] Excellent deduplication!")
    elif efficiency >= 50:
        print("[WARNING] Moderate deduplication")
    else:
        print("[FAIL] Poor deduplication")

    # Cleanup
    manager.shutdown()
    db_manager.close()

    print("\nTest completed.")


if __name__ == "__main__":
    main()
