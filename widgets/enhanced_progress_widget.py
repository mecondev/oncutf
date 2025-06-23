"""
enhanced_progress_widget.py

Author: Michael Economou
Date: 2025-06-23

Enhanced progress widget with file size tracking and time estimation.
Extends CompactWaitingWidget with additional progress information.

Features:
- File size tracking (35MB/20GB)
- Time estimation (3':20''/1:24':15'')
- Configurable layout (bottom row or side panel)
- Real-time progress rate calculation
- Cross-platform compatible formatting
"""

from typing import Optional

from core.qt_imports import Qt, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy
from utils.logger_factory import get_cached_logger
from utils.time_formatter import ProgressEstimator
from widgets.compact_waiting_widget import CompactWaitingWidget

logger = get_cached_logger(__name__)


class EnhancedProgressWidget(QWidget):
    """
    Enhanced progress widget with size and time tracking.

    Combines CompactWaitingWidget with additional progress information:
    - File size progress (processed/total)
    - Time estimation (elapsed/estimated)
    - Configurable layout options
    """

    def __init__(self, parent: Optional[QWidget] = None,
                 bar_color: str = "#64b5f6",
                 bar_bg_color: str = "#0a1a2a",
                 show_size_info: bool = True,
                 show_time_info: bool = True,
                 layout_style: str = "bottom"):
        """
        Initialize the enhanced progress widget.

        Args:
            parent: Parent widget
            bar_color: Progress bar color
            bar_bg_color: Progress bar background color
            show_size_info: Whether to show size tracking
            show_time_info: Whether to show time estimation
            layout_style: Layout style ("bottom" or "side")
        """
        super().__init__(parent)

        self.show_size_info = show_size_info
        self.show_time_info = show_time_info
        self.layout_style = layout_style

        # Progress estimator for advanced tracking
        self.progress_estimator = ProgressEstimator()

        # Setup the widget
        self._setup_ui(bar_color, bar_bg_color)

        logger.debug(f"[EnhancedProgressWidget] Initialized with layout: {layout_style}")

    def _setup_ui(self, bar_color: str, bar_bg_color: str):
        """Setup the UI components."""

        # Main layout
        if self.layout_style == "side":
            main_layout = QHBoxLayout(self)
        else:  # "bottom"
            main_layout = QVBoxLayout(self)

        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)

        # Core progress widget (CompactWaitingWidget)
        self.progress_widget = CompactWaitingWidget(
            parent=self,
            bar_color=bar_color,
            bar_bg_color=bar_bg_color
        )
        main_layout.addWidget(self.progress_widget)

        # Additional info panel
        if self.show_size_info or self.show_time_info:
            self._setup_info_panel(main_layout)

        self.setLayout(main_layout)

    def _setup_info_panel(self, main_layout):
        """Setup the additional information panel."""

        # Info container
        info_container = QWidget()
        info_layout = QHBoxLayout(info_container)
        info_layout.setContentsMargins(8, 4, 8, 4)
        info_layout.setSpacing(16)

        # Size info label
        if self.show_size_info:
            self.size_label = QLabel("Calculating size...")
            self.size_label.setObjectName("size_info_label")
            self.size_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.size_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            info_layout.addWidget(self.size_label)

        # Spacer
        if self.show_size_info and self.show_time_info:
            info_layout.addStretch()

        # Time info label
        if self.show_time_info:
            self.time_label = QLabel("Calculating time...")
            self.time_label.setObjectName("time_info_label")
            self.time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.time_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            info_layout.addWidget(self.time_label)

        info_container.setLayout(info_layout)
        main_layout.addWidget(info_container)

        # Apply styling
        self._apply_info_styling()

    def _apply_info_styling(self):
        """Apply styling to info labels."""

        info_style = """
        QLabel#size_info_label, QLabel#time_info_label {
            color: #b0bec5;
            font-size: 11px;
            font-family: 'Inter', sans-serif;
            background-color: transparent;
            border: none;
            padding: 2px 4px;
        }

        QLabel#size_info_label:hover, QLabel#time_info_label:hover {
            color: #cfd8dc;
        }
        """

        self.setStyleSheet(info_style)

    def start_progress(self, total_size: int = 0):
        """
        Start progress tracking.

        Args:
            total_size: Total size in bytes (optional)
        """
        self.progress_estimator.start(total_size)

        # Initialize displays
        if self.show_size_info:
            if total_size > 0:
                self.size_label.setText("0 B/calculating...")
            else:
                self.size_label.setText("Processing...")

        if self.show_time_info:
            self.time_label.setText("Starting...")

        logger.debug(f"[EnhancedProgressWidget] Started progress tracking (total_size: {total_size})")

    def update_progress(self, current: int, total: int, current_size: int = 0):
        """
        Update progress with comprehensive tracking.

        Args:
            current: Current item number
            total: Total number of items
            current_size: Current processed size in bytes
        """
        # Update core progress widget
        self.progress_widget.set_progress(current, total)

        # Update progress estimator
        self.progress_estimator.update(current, total, current_size)

        # Update additional info
        self._update_info_displays()

    def _update_info_displays(self):
        """Update the size and time info displays."""

        summary = self.progress_estimator.get_progress_summary()

        # Update size info
        if self.show_size_info:
            size_text = summary['size_range']
            if not size_text or size_text == "0 B":
                size_text = "Processing..."
            self.size_label.setText(size_text)

        # Update time info
        if self.show_time_info:
            time_text = summary['time_range']
            if not time_text or time_text == "0''":
                time_text = "Calculating..."
            self.time_label.setText(time_text)

    def set_status(self, status: str):
        """Set status message."""
        self.progress_widget.set_status(status)

    def set_filename(self, filename: str):
        """Set current filename."""
        self.progress_widget.set_filename(filename)

    def set_count(self, current: int, total: int):
        """Set current count display."""
        self.progress_widget.set_count(current, total)

    def set_size_info(self, processed_size: int, total_size: int = 0):
        """
        Manually set size information.

        Args:
            processed_size: Size processed so far in bytes
            total_size: Total size in bytes (optional)
        """
        if not self.show_size_info:
            return

        from utils.file_size_formatter import format_file_size_system_compatible

        processed_str = format_file_size_system_compatible(processed_size)

        if total_size > 0:
            total_str = format_file_size_system_compatible(total_size)
            size_text = f"{processed_str}/{total_str}"
        else:
            size_text = processed_str

        self.size_label.setText(size_text)

    def set_time_info(self, elapsed: float, estimated_total: Optional[float] = None):
        """
        Manually set time information.

        Args:
            elapsed: Elapsed time in seconds
            estimated_total: Estimated total time in seconds (optional)
        """
        if not self.show_time_info:
            return

        from utils.time_formatter import format_time_range

        time_text = format_time_range(elapsed, estimated_total)
        self.time_label.setText(time_text)

    def get_progress_summary(self) -> dict:
        """Get comprehensive progress summary."""
        return self.progress_estimator.get_progress_summary()

    def reset(self):
        """Reset all progress tracking."""
        self.progress_estimator = ProgressEstimator()
        self.progress_widget.set_progress(0, 100)

        if self.show_size_info:
            self.size_label.setText("Ready...")

        if self.show_time_info:
            self.time_label.setText("Ready...")


class CompactEnhancedProgressWidget(EnhancedProgressWidget):
    """
    Compact version of EnhancedProgressWidget optimized for dialogs.
    Uses smaller fonts and tighter spacing.
    """

    def __init__(self, *args, **kwargs):
        """Initialize compact version."""
        super().__init__(*args, **kwargs)

        # Apply compact styling
        self._apply_compact_styling()

    def _apply_compact_styling(self):
        """Apply compact styling optimized for dialogs."""

        compact_style = """
        QLabel#size_info_label, QLabel#time_info_label {
            color: #90a4ae;
            font-size: 10px;
            font-family: 'Inter', sans-serif;
            background-color: transparent;
            border: none;
            padding: 1px 2px;
            margin: 0px;
        }

        QLabel#size_info_label:hover, QLabel#time_info_label:hover {
            color: #b0bec5;
        }
        """

        self.setStyleSheet(compact_style)

        # Adjust layout spacing for compact mode
        layout = self.layout()
        if layout:
            layout.setSpacing(4)
            layout.setContentsMargins(0, 0, 0, 0)
