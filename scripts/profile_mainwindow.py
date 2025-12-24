#!/usr/bin/env python3
"""
Detailed cProfile analysis of MainWindow initialization.

Author: Michael Economou
Date: 2025-12-20
"""

from __future__ import annotations

import cProfile
import io
import pstats
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def profile_mainwindow_init() -> None:
    """Profile MainWindow initialization in detail."""
    print("=" * 80)
    print("cProfile: MainWindow Initialization")
    print("=" * 80)

    profiler = cProfile.Profile()

    # Setup
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # Profile the MainWindow creation
    profiler.enable()

    from oncutf.ui.main_window import MainWindow

    window = MainWindow()

    profiler.disable()

    # Print detailed stats
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s)
    ps.strip_dirs()
    ps.sort_stats(pstats.SortKey.CUMULATIVE)

    print("\n🔍 Top 50 Functions by Cumulative Time:")
    print("=" * 80)
    ps.print_stats(50)
    print(s.getvalue())

    # Also print callers for the slowest functions
    print("\n\n📞 Caller Analysis for Top Functions:")
    print("=" * 80)
    s2 = io.StringIO()
    ps2 = pstats.Stats(profiler, stream=s2)
    ps2.strip_dirs()
    ps2.sort_stats(pstats.SortKey.CUMULATIVE)
    ps2.print_callers(20)
    print(s2.getvalue())

    # Cleanup
    window.close()
    app.quit()


if __name__ == "__main__":
    profile_mainwindow_init()
