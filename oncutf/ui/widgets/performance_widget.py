"""
Module: performance_widget.py

Author: Michael Economou
Date: 2025-05-01

Performance Widget for displaying UnifiedRenameEngine performance metrics.
"""

from oncutf.core.pyqt_imports import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    Qt,
    QTimer,
    QVBoxLayout,
    QWidget,
)
from oncutf.utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class PerformanceWidget(QWidget):
    """Widget for displaying performance metrics."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("PerformanceWidget")
        self.setProperty("class", "PerformanceWidget")

        # Performance update timer
        self.update_timer = QTimer()
        self.update_timer.setInterval(2000)  # Update every 2 seconds
        self.update_timer.timeout.connect(self.update_display)

        self.setup_ui()
        self.update_display()

        # Start auto-update
        self.update_timer.start()

    def setup_ui(self):
        """Setup the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Title
        title = QLabel("Performance Metrics")
        title.setProperty("class", "PerformanceTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)

        # Stats container
        self.stats_container = QWidget()
        stats_layout = QVBoxLayout(self.stats_container)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setSpacing(2)
        layout.addWidget(self.stats_container)

        # Create stat labels
        self.total_ops_label = self._create_stat_label("Total Operations: 0")
        self.avg_duration_label = self._create_stat_label("Avg Duration: 0ms")
        self.success_rate_label = self._create_stat_label("Success Rate: 100%")
        self.avg_files_label = self._create_stat_label("Avg Files/Op: 0")

        stats_layout.addWidget(self.total_ops_label)
        stats_layout.addWidget(self.avg_duration_label)
        stats_layout.addWidget(self.success_rate_label)
        stats_layout.addWidget(self.avg_files_label)

        # Operations breakdown
        self.operations_label = QLabel("Operations:")
        self.operations_label.setProperty("class", "PerformanceSubtitle")
        stats_layout.addWidget(self.operations_label)

        self.operations_container = QWidget()
        self.operations_layout = QVBoxLayout(self.operations_container)
        self.operations_layout.setContentsMargins(8, 0, 0, 0)
        self.operations_layout.setSpacing(1)
        stats_layout.addWidget(self.operations_container)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(4)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.update_display)
        self.refresh_button.setProperty("class", "PerformanceButton")

        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_metrics)
        self.clear_button.setProperty("class", "PerformanceButton")

        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.clear_button)
        layout.addLayout(button_layout)

    def _create_stat_label(self, text: str) -> QLabel:
        """Create a stat label."""
        label = QLabel(text)
        label.setProperty("class", "PerformanceStat")
        return label

    def _create_operation_label(self, operation: str, stats: dict) -> QLabel:
        """Create an operation stat label."""
        text = f"  {operation}: {stats['total']} ops, {stats['average_duration']:.1f}ms avg"
        label = QLabel(text)
        label.setProperty("class", "PerformanceOperation")
        return label

    def update_display(self):
        """Update the performance display."""
        try:
            # Get performance stats from main window
            from oncutf.core.application_context import get_app_context

            context = get_app_context()
            if not context or not hasattr(context, "main_window"):
                return

            main_window = context.main_window
            if not hasattr(main_window, "unified_rename_engine"):
                return

            stats = main_window.unified_rename_engine.get_performance_stats()

            # Update overall stats
            self.total_ops_label.setText(f"Total Operations: {stats['total_operations']}")
            self.avg_duration_label.setText(
                f"Avg Duration: {stats['average_duration'] * 1000:.1f}ms"
            )
            self.success_rate_label.setText(f"Success Rate: {stats['success_rate'] * 100:.1f}%")
            self.avg_files_label.setText(
                f"Avg Files/Op: {stats['average_files_per_operation']:.1f}"
            )

            # Clear existing operation labels
            for i in reversed(range(self.operations_layout.count())):
                widget = self.operations_layout.itemAt(i).widget()
                if widget:
                    widget.deleteLater()

            # Add operation stats
            for operation, op_stats in stats["operations"].items():
                label = self._create_operation_label(operation, op_stats)
                self.operations_layout.addWidget(label)

        except Exception as e:
            logger.error("[PerformanceWidget] Error updating display: %s", e)

    def clear_metrics(self):
        """Clear performance metrics."""
        try:
            from oncutf.core.application_context import get_app_context

            context = get_app_context()
            if context and hasattr(context, "main_window"):
                main_window = context.main_window
                if hasattr(main_window, "unified_rename_engine"):
                    main_window.unified_rename_engine.clear_performance_metrics()
                    self.update_display()
        except Exception as e:
            logger.error("[PerformanceWidget] Error clearing metrics: %s", e)

    def showEvent(self, event):
        """Show event - start timer."""
        super().showEvent(event)
        self.update_timer.start()

    def hideEvent(self, event):
        """Hide event - stop timer."""
        super().hideEvent(event)
        self.update_timer.stop()
