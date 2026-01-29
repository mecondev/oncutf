#!/usr/bin/env python3
"""Test: Scroll Duplicate Prevention

Author: Michael Economou
Date: 2026-01-16

Purpose:
    Verify that ThumbnailManager prevents duplicate requests during rapid
    viewport scrolling.

Expected Behavior:
    - WITHOUT deduplication: 100 scroll events = 100+ queue entries for same file
    - WITH deduplication: 100 scroll events = 1 queue entry per unique file

Usage:
    python tests/manual/test_scroll_duplicate_prevention.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from PyQt5.QtWidgets import QApplication

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from oncutf.core.thumbnail.thumbnail_manager import ThumbnailManager
from oncutf.infra.db.database_manager import DatabaseManager
from oncutf.utils.paths import AppPaths


def simulate_scroll_events(manager: ThumbnailManager, test_file: str, num_scrolls: int = 100) -> dict[str, int]:
    """Simulate rapid scrolling that triggers multiple get_thumbnail() calls.

    Args:
        manager: ThumbnailManager instance
        test_file: Path to test file
        num_scrolls: Number of simulated scroll events

    Returns:
        Statistics about queue behavior
    """
    print(f"\nSimulating {num_scrolls} scroll events for: {test_file}")
    print("-" * 80)

    start_time = time.perf_counter()
    initial_queue_size = manager._request_queue.qsize()

    # Simulate rapid scrolling - each scroll triggers data() → get_thumbnail()
    for i in range(num_scrolls):
        manager.get_thumbnail(test_file, size_px=128)

        if i % 20 == 0:
            queue_size = manager._request_queue.qsize()
            pending_size = len(manager._pending_requests)
            print(f"  Scroll {i:3d}: queue_size={queue_size}, pending={pending_size}")

    end_time = time.perf_counter()
    final_queue_size = manager._request_queue.qsize()
    final_pending = len(manager._pending_requests)

    queue_delta = final_queue_size - initial_queue_size

    print("\nResults:")
    print(f"  Total scroll events:     {num_scrolls}")
    print(f"  Queue entries added:     {queue_delta}")
    print(f"  Deduplication rate:      {100 * (1 - queue_delta / num_scrolls):.1f}%")
    print(f"  Final queue size:        {final_queue_size}")
    print(f"  Final pending requests:  {final_pending}")
    print(f"  Time elapsed:            {end_time - start_time:.3f}s")

    return {
        "scroll_events": num_scrolls,
        "queue_added": queue_delta,
        "dedup_rate": 100 * (1 - queue_delta / num_scrolls),
        "final_queue": final_queue_size,
        "final_pending": final_pending,
    }


def main() -> None:
    """Run scroll duplication test."""
    print("=" * 80)
    print("Scroll Duplicate Prevention Test")
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

    # Find a test file
    test_dir = Path.home() / "Videos"  # Adjust to your test directory
    if not test_dir.exists():
        test_dir = Path.home() / "Pictures"

    test_files = list(test_dir.glob("**/*.mp4"))[:1]  # First video
    if not test_files:
        test_files = list(test_dir.glob("**/*.jpg"))[:1]  # Fallback to images

    if not test_files:
        print("\nERROR: No test files found!")
        print(f"Searched in: {test_dir}")
        sys.exit(1)

    test_file = str(test_files[0])
    print(f"Test file: {test_file}")

    # Run test
    stats = simulate_scroll_events(manager, test_file, num_scrolls=100)

    # Validate results
    print("\n" + "=" * 80)
    if stats["queue_added"] <= 1:
        print("[SUCCESS] Deduplication working correctly!")
        print(f"   Expected: 1 queue entry for {stats['scroll_events']} scroll events")
        print(f"   Actual:   {stats['queue_added']} queue entries")
    else:
        print("[WARNING] Deduplication may not be optimal")
        print("   Expected: 1 queue entry")
        print(f"   Actual:   {stats['queue_added']} queue entries")
        print(f"   Deduplication rate: {stats['dedup_rate']:.1f}%")

    # Cleanup
    manager.shutdown()
    db_manager.close()

    print("\nTest completed.")


if __name__ == "__main__":
    main()
