"""
Module: progress_widget.py

Author: Michael Economou
Date: 2025-06-20

Unified progress widget supporting both basic and enhanced progress tracking.
Simplified and cleaned up design with proper naming conventions.

Features:
- Basic progress display (percentage, count, filename)
- Optional size and time tracking
- Compact layout optimized for dialog usage
- Customizable appearance and behavior
"""

import os
from typing import Optional
import time

from PyQt5.QtCore import QTimer

from config import (
    QLABEL_BORDER_GRAY,
    QLABEL_PRIMARY_TEXT,
    QLABEL_SECONDARY_TEXT,
    QLABEL_TERTIARY_TEXT,
    QLABEL_WHITE_TEXT,
)
from core.qt_imports import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSize,
    QSizePolicy,
    Qt,
    QVBoxLayout,
    QWidget,
)
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class ProgressWidget(QWidget):
    """
    Unified progress widget with flexible configuration.

    Handles all progress display needs:
    - Basic progress (file counting, metadata loading)
    - Optional size and time tracking
    - Optimized layout for long paths and recursive imports
    """

    def __init__(self,
                 parent: Optional[QWidget] = None,
                 bar_color: str = "#64b5f6",
                 bar_bg_color: str = "#0a1a2a",
                 show_size_info: bool = False,
                 show_time_info: bool = False,
                 fixed_width: int = 400):
        """
        Initialize the progress widget.

        Args:
            parent: Parent widget
            bar_color: Progress bar color
            bar_bg_color: Progress bar background color
            show_size_info: Whether to show size information
            show_time_info: Whether to show time information
            fixed_width: Fixed width for the widget
        """
        super().__init__(parent)
        self.setFixedWidth(fixed_width)

        # Configuration
        self.show_size_info = show_size_info
        self.show_time_info = show_time_info
        self.bar_color = bar_color
        self.bar_bg_color = bar_bg_color

        # Simple progress tracking
        self.start_time = None
        self.total_size = 0
        self.processed_size = 0

        # Throttling to prevent flickering
        self._last_update_time = 0

        # Setup UI
        self._setup_ui()
        self._apply_styling()

        logger.debug(f"[ProgressWidget] Initialized (size_info: {show_size_info}, time_info: {show_time_info})")

    def _setup_ui(self):
        """Setup the UI components with compact layout."""
        # Main layout with compact settings
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(6, 6, 6, 6)
        self.main_layout.setSpacing(4)

        # First row: status label and count (horizontal layout)
        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 0, 0, 0)

        self.status_label = QLabel("Please wait...")
        self.status_label.setObjectName("status_label")
        self.status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.count_label = QLabel("")
        self.count_label.setObjectName("count_label")
        self.count_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.count_label.setFixedWidth(90)

        status_row.addWidget(self.status_label)
        status_row.addWidget(self.count_label)
        self.main_layout.addLayout(status_row)

        # Second row: progress bar (very thin)
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progress_bar")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        self.main_layout.addWidget(self.progress_bar)

        # Third row: percentage and filename (horizontal layout)
        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 0, 0, 0)
        bottom_row.setSpacing(5)

        self.percentage_label = QLabel("0%")
        self.percentage_label.setObjectName("percentage_label")
        self.percentage_label.setFixedWidth(40)
        self.percentage_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.filename_label = QLabel("")
        self.filename_label.setObjectName("filename_label")
        self.filename_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.filename_label.setWordWrap(True)
        self.filename_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        bottom_row.addWidget(self.percentage_label)
        bottom_row.addWidget(self.filename_label)
        self.main_layout.addLayout(bottom_row)

        # Enhanced info row (only if requested)
        if self.show_size_info or self.show_time_info:
            self._setup_enhanced_info_row()

        self.setLayout(self.main_layout)

    def _setup_enhanced_info_row(self):
        """Setup additional row for size and time information."""
        enhanced_row = QHBoxLayout()
        enhanced_row.setContentsMargins(0, 2, 0, 0)
        enhanced_row.setSpacing(10)

        if self.show_size_info:
            self.size_label = QLabel("Ready...")
            self.size_label.setObjectName("size_info_label")
            self.size_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.size_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            enhanced_row.addWidget(self.size_label)

        if self.show_size_info and self.show_time_info:
            enhanced_row.addStretch()

        if self.show_time_info:
            self.time_label = QLabel("Ready...")
            self.time_label.setObjectName("time_info_label")
            self.time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.time_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            enhanced_row.addWidget(self.time_label)

        self.main_layout.addLayout(enhanced_row)

    def _apply_styling(self):
        """Apply styling to all components."""
        style = f"""
        QLabel#status_label {{
            color: {QLABEL_PRIMARY_TEXT};
            font-size: 14px;
            font-weight: 500;
            margin: 2px 0px;
        }}

        QLabel#count_label {{
            color: {QLABEL_SECONDARY_TEXT};
            font-size: 12px;
            font-weight: 400;
            margin: 2px 0px;
        }}

        QLabel#percentage_label {{
            color: {QLABEL_SECONDARY_TEXT};
            font-size: 12px;
            font-weight: 400;
            margin: 2px 0px;
        }}

        QLabel#filename_label {{
            color: {QLABEL_TERTIARY_TEXT};
            font-size: 11px;
            font-weight: 400;
            margin: 2px 0px;
        }}

        QLabel#size_info_label {{
            color: {QLABEL_SECONDARY_TEXT};
            font-size: 11px;
            font-weight: 400;
            margin: 1px 0px;
        }}

        QLabel#time_info_label {{
            color: {QLABEL_SECONDARY_TEXT};
            font-size: 11px;
            font-weight: 400;
            margin: 1px 0px;
        }}

        QProgressBar#progress_bar {{
            border: 1px solid {QLABEL_BORDER_GRAY};
            border-radius: 4px;
            background-color: {self.bar_bg_color};
            text-align: center;
        }}

        QProgressBar#progress_bar::chunk {{
            background-color: {self.bar_color};
            border-radius: 3px;
            margin: 1px;
        }}
        """
        self.setStyleSheet(style)

    def sizeHint(self):
        """Return preferred size hint."""
        height = 80  # Base height for basic progress
        if self.show_size_info or self.show_time_info:
            height += 20  # Additional height for enhanced info
        return QSize(self.width(), height)

    def set_progress(self, value: int, total: int):
        """Set progress bar value and total."""
        if total <= 0:
            percentage = 0
        else:
            percentage = int((value / total) * 100)
            percentage = max(0, min(100, percentage))

        self.progress_bar.setValue(percentage)
        self.percentage_label.setText(f"{percentage}%")

    def set_status(self, text: str):
        """
        Set status text with intelligent truncation for long messages.

        Args:
            text: Status message to display
        """
        if not text:
            self.status_label.setText("Ready...")
            return

        # Intelligent truncation for very long status messages
        max_length = 80
        if len(text) > max_length:
            # Try to truncate at last space before limit
            truncate_pos = text.rfind(' ', 0, max_length - 3)
            if truncate_pos > max_length // 2:  # Only if we find a reasonable break point
                truncated_text = text[:truncate_pos] + "..."
            else:
                truncated_text = text[:max_length - 3] + "..."
            self.status_label.setText(truncated_text)
        else:
            self.status_label.setText(text)

    def set_filename(self, filename: str):
        """Set filename with intelligent truncation for long paths."""
        if not filename:
            self.filename_label.setText("")
            return

        # Intelligent truncation preserving extension
        max_length = 60
        if len(filename) > max_length:
            name_part, ext_part = os.path.splitext(filename)
            if ext_part and len(ext_part) < 10:
                available_length = max_length - len(ext_part) - 3
                if available_length > 10:
                    truncated_name = name_part[:available_length] + "..." + ext_part
                    self.filename_label.setText(truncated_name)
                    return

            # Fallback: simple truncation
            self.filename_label.setText(filename[:max_length] + "...")
        else:
            self.filename_label.setText(filename)

    def set_count(self, current: int, total: int):
        """Set count display."""
        self.count_label.setText(f"{current} of {total}")

    def set_indeterminate_mode(self):
        """Set progress bar to indeterminate/animated mode."""
        self.progress_bar.setRange(0, 0)
        self.percentage_label.setText("")
        self.count_label.setText("")
        self.progress_bar.show()
        self.percentage_label.hide()
        logger.debug("[ProgressWidget] Progress bar set to indeterminate mode")

    def set_determinate_mode(self):
        """Set progress bar back to normal determinate mode."""
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.percentage_label.setText("0%")
        self.percentage_label.show()
        self.count_label.setText("0 of 0")
        logger.debug("[ProgressWidget] Progress bar set to determinate mode")

    def start_progress_tracking(self, total_size: int = 0):
        """Start progress tracking with optional size tracking."""
        self.start_time = time.time()
        self.total_size = total_size
        self.processed_size = 0

        if self.show_size_info and hasattr(self, 'size_label'):
            if total_size > 0:
                self.size_label.setText("Starting...")
            else:
                self.size_label.setText("0 B")

        if self.show_time_info and hasattr(self, 'time_label'):
            self.time_label.setText("Starting...")

        logger.debug(f"[ProgressWidget] Started tracking (total_size: {total_size})")

    def update_progress_with_size(self, current: int, total: int, current_size: int = 0):
        """Update progress with size tracking."""
        # Update much less frequently to avoid flickering
        current_time = time.time()
        if current_time - self._last_update_time < 0.3:  # Update every 300ms only
            return
        self._last_update_time = current_time

        # Update basic progress
        self.set_progress(current, total)
        self.processed_size = current_size

        # Update size display
        if self.show_size_info and hasattr(self, 'size_label'):
            self._update_size_display()

        # Update time display
        if self.show_time_info and hasattr(self, 'time_label'):
            self._update_time_display()

    def _update_size_display(self):
        """Update size information display."""
        from utils.file_size_formatter import format_file_size_system_compatible

        processed_str = format_file_size_system_compatible(self.processed_size)
        if self.total_size > 0:
            total_str = format_file_size_system_compatible(self.total_size)
            size_text = f"{processed_str}/{total_str}"
        else:
            size_text = processed_str
        self.size_label.setText(size_text)

    def _update_time_display(self):
        """Update time information display."""
        if not self.start_time:
            return

        elapsed = time.time() - self.start_time
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)

        if minutes > 0:
            time_text = f"{minutes}m {seconds}s"
        else:
            time_text = f"{seconds}s"

        self.time_label.setText(time_text)

    def set_size_info(self, processed_size: int, total_size: int = 0):
        """Manually set size information."""
        if not self.show_size_info:
            return

        self.processed_size = processed_size
        if total_size > 0:
            self.total_size = total_size

        self._update_size_display()

    def set_time_info(self, elapsed: float):
        """Manually set time information."""
        if not self.show_time_info:
            return

        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)

        if minutes > 0:
            time_text = f"{minutes}m {seconds}s"
        else:
            time_text = f"{seconds}s"

        self.time_label.setText(time_text)

    def reset(self):
        """Reset all progress tracking."""
        self.set_progress(0, 100)
        self.set_status("Ready...")
        self.set_filename("")
        self.set_count(0, 0)

        self.start_time = None
        self.total_size = 0
        self.processed_size = 0

        if self.show_size_info and hasattr(self, 'size_label'):
            self.size_label.setText("Ready...")

        if self.show_time_info and hasattr(self, 'time_label'):
            self.time_label.setText("Ready...")


# Factory functions for easy creation with preset configurations
def create_basic_progress_widget(parent=None, **kwargs):
    """Create a basic progress widget (no enhanced tracking)."""
    return ProgressWidget(parent, show_size_info=False, show_time_info=False, **kwargs)

def create_size_tracking_widget(parent=None, **kwargs):
    """Create a progress widget with size tracking."""
    return ProgressWidget(parent, show_size_info=True, show_time_info=False, **kwargs)

def create_time_tracking_widget(parent=None, **kwargs):
    """Create a progress widget with time tracking."""
    return ProgressWidget(parent, show_size_info=False, show_time_info=True, **kwargs)

def create_full_tracking_widget(parent=None, **kwargs):
    """Create a progress widget with both size and time tracking."""
    return ProgressWidget(parent, show_size_info=True, show_time_info=True, **kwargs)
