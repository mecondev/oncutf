#!/usr/bin/env python3
"""
test_enhanced_progress.py

Author: Michael Economou
Date: 2025-06-23

Test script for the enhanced progress dialog system.
Demonstrates size tracking and time estimation features.
"""

import sys
import time
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from core.qt_imports import QApplication, QTimer
    from utils.progress_dialog import ProgressDialog
    from utils.time_formatter import ProgressEstimator, format_duration

    def demo_enhanced_progress():
        """Demonstrate enhanced progress features."""

        app = QApplication(sys.argv)

        print("Enhanced Progress Dialog Demo")
        print("=" * 40)

        # Create enhanced dialog for file loading
        dialog = ProgressDialog.create_file_loading_dialog(
            parent=None,
            show_enhanced_info=True
        )

        dialog.show()

        # Demo data
        total_files = 100
        total_size = 2 * 1024 * 1024 * 1024  # 2GB

        # Start enhanced tracking
        dialog.start_progress_tracking(total_size)
        dialog.set_status("Loading files...")

        print(f"Simulating loading {total_files} files ({total_size / (1024*1024*1024):.1f}GB)")

        # Simulate file loading with size progression
        current_size = 0

        def update_progress():
            nonlocal current_size

            for i in range(total_files):
                # Simulate variable file sizes
                file_size = (i + 1) * 1024 * 200  # Progressive file sizes
                current_size += file_size

                # Update progress with size tracking
                dialog.update_enhanced_progress(i + 1, total_files, current_size)
                dialog.set_filename(f"file_{i+1:03d}.mp4")

                # Process events to update UI
                app.processEvents()

                # Small delay to see the progression
                time.sleep(0.05)

                # Print progress summary every 10 files
                if (i + 1) % 10 == 0:
                    summary = dialog.get_progress_summary()
                    if summary:
                        print(f"Progress: {i+1}/{total_files} files, "
                              f"Size: {summary.get('size_range', 'N/A')}, "
                              f"Time: {summary.get('time_range', 'N/A')}")

        # Use timer to prevent blocking
        timer = QTimer()
        timer.timeout.connect(update_progress)
        timer.setSingleShot(True)
        timer.start(100)

        # Show dialog
        result = dialog.exec_()

        print(f"Dialog result: {result}")

        return app.exec_()

    def demo_time_formatter():
        """Demonstrate time formatting functionality."""

        print("\nTime Formatter Demo")
        print("=" * 30)

        # Test time formatting
        test_times = [5, 65, 125, 3665, 7325]  # Various durations

        for seconds in test_times:
            formatted = format_duration(seconds)
            print(f"{seconds:5d} seconds -> {formatted}")

        print()

        # Test progress estimator
        estimator = ProgressEstimator()
        estimator.start(total_size=1000000)  # 1MB total

        print("Progress Estimation Demo:")
        for i in range(0, 101, 10):
            current_size = i * 10000  # 10KB per step
            estimator.update(i, 100, current_size)

            summary = estimator.get_progress_summary()
            print(f"Progress {i:3d}%: {summary['size_range']:>10} | {summary['time_range']:>12}")

            time.sleep(0.1)  # Simulate work

    def test_enhanced_widget_standalone():
        """Test enhanced widget in standalone mode."""

        from widgets.progress_widget import CompactEnhancedProgressWidget

        app = QApplication(sys.argv)

        # Create standalone enhanced widget
        widget = CompactEnhancedProgressWidget(
            show_size_info=True,
            show_time_info=True,
            layout_style="bottom"
        )

        widget.setWindowTitle("Enhanced Progress Widget Test")
        widget.show()

        # Demo progression
        widget.start_progress(500 * 1024 * 1024)  # 500MB

        for i in range(101):
            current_size = i * 5 * 1024 * 1024  # 5MB per step
            widget.update_progress(i, 100, current_size)
            widget.set_filename(f"processing_file_{i:03d}.dat")

            app.processEvents()
            time.sleep(0.02)

        widget.set_status("Complete!")

        return app.exec_()

    if __name__ == "__main__":
        if len(sys.argv) > 1:
            command = sys.argv[1]

            if command == "dialog":
                demo_enhanced_progress()
            elif command == "widget":
                test_enhanced_widget_standalone()
            elif command == "time":
                demo_time_formatter()
            else:
                print("Usage: python test_enhanced_progress.py [dialog|widget|time]")
        else:
            print("Enhanced Progress System Demo")
            print("Available commands:")
            print("  dialog - Demo enhanced progress dialog")
            print("  widget - Demo enhanced progress widget")
            print("  time   - Demo time formatting")
            print()
            print("Example: python test_enhanced_progress.py dialog")

except ImportError as e:
    print(f"Import error: {e}")
    print("This test requires PyQt5. Please make sure it's installed.")
    sys.exit(1)
