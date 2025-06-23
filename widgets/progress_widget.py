"""
progress_widget.py

Author: Michael Economou
Date: 2025-06-23

Unified progress widget system for the oncutf application.
Single flexible class that handles all progress display needs.

Features:
- Compact layout optimized for long paths (400px fixed width)
- Optional enhanced tracking with size and time estimation
- Intelligent path truncation for recursive imports
- Configurable colors for different operation types
- Single class with flexible parameters instead of multiple inheritance
"""

import os
from typing import Optional

from core.qt_imports import (
    Qt, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QSizePolicy, QSize
)
from PyQt5.QtCore import QPropertyAnimation, QEasingCurve, QTimer
from config import (
    QLABEL_PRIMARY_TEXT, QLABEL_SECONDARY_TEXT, QLABEL_TERTIARY_TEXT,
    QLABEL_WHITE_TEXT, QLABEL_BORDER_GRAY
)
from utils.logger_factory import get_cached_logger
from utils.time_formatter import ProgressEstimator

logger = get_cached_logger(__name__)


class ProgressWidget(QWidget):
    """
    Unified progress widget with flexible configuration.

    Handles all progress display needs:
    - Basic progress (file counting, metadata loading)
    - Enhanced progress (with size and time tracking)
    - Optimized layout for long paths and recursive imports

    Parameters control behavior rather than separate classes.
    """

    def __init__(self,
                 parent: Optional[QWidget] = None,
                 bar_color: str = "#64b5f6",
                 bar_bg_color: str = "#0a1a2a",
                 show_size_info: bool = False,
                 show_time_info: bool = False,
                 fixed_width: int = 400):
        """
        Initialize the unified progress widget.

        Args:
            parent: Parent widget
            bar_color: Progress bar color
            bar_bg_color: Progress bar background color
            show_size_info: Whether to show file size tracking
            show_time_info: Whether to show time estimation
            fixed_width: Fixed width in pixels (400 for compact layout)
        """
        super().__init__(parent)

        self.bar_color = bar_color
        self.bar_bg_color = bar_bg_color
        self.show_size_info = show_size_info
        self.show_time_info = show_time_info

        # Enhanced tracking components
        self.progress_estimator = None
        if self.show_size_info or self.show_time_info:
            self.progress_estimator = ProgressEstimator()

        # Animation components for smooth bounce effect
        self._bounce_animation = None
        self._bounce_timer = QTimer()
        self._bounce_timer.setSingleShot(False)
        self._bounce_direction = 1  # 1 for forward, -1 for backward
        self._bounce_position = 0

        # Set fixed width for consistent layout
        self.setFixedWidth(fixed_width)

        self._setup_ui()
        self._apply_styling()

        logger.debug(f"[ProgressWidget] Initialized (size_info: {show_size_info}, time_info: {show_time_info})")

    def _setup_ui(self):
        """Setup the UI components with compact layout."""
        # Main layout with compact settings
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(6, 6, 6, 6)  # Original compact margins
        self.main_layout.setSpacing(4)  # Original compact spacing

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
        self.count_label.setFixedWidth(90)  # Original width for large numbers

        status_row.addWidget(self.status_label)
        status_row.addWidget(self.count_label)
        self.main_layout.addLayout(status_row)

        # Second row: progress bar (very thin)
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progress_bar")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)  # Original thin height
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
        enhanced_row.setContentsMargins(0, 2, 0, 0)  # Small top margin
        enhanced_row.setSpacing(10)

        if self.show_size_info:
            self.size_label = QLabel("Calculating size...")
            self.size_label.setObjectName("size_info_label")
            self.size_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.size_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            enhanced_row.addWidget(self.size_label)

        if self.show_size_info and self.show_time_info:
            enhanced_row.addStretch()

        if self.show_time_info:
            self.time_label = QLabel("Calculating time...")
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
            font-family: 'Inter', sans-serif;
            font-weight: 500;
            background-color: transparent;
            border: none;
        }}

        QLabel#count_label {{
            color: {QLABEL_SECONDARY_TEXT};
            font-size: 13px;
            font-family: 'Inter', sans-serif;
            background-color: transparent;
            border: none;
        }}

        QLabel#percentage_label {{
            color: {QLABEL_SECONDARY_TEXT};
            font-size: 12px;
            font-family: 'Inter', sans-serif;
            background-color: transparent;
            border: none;
        }}

        QLabel#filename_label {{
            color: {QLABEL_TERTIARY_TEXT};
            font-size: 12px;
            font-family: 'Inter', sans-serif;
            background-color: transparent;
            border: none;
        }}

        QLabel#size_info_label {{
            color: {QLABEL_TERTIARY_TEXT};
            font-size: 11px;
            font-family: 'Inter', sans-serif;
            background-color: transparent;
            border: none;
        }}

        QLabel#time_info_label {{
            color: {QLABEL_TERTIARY_TEXT};
            font-size: 11px;
            font-family: 'Inter', sans-serif;
            background-color: transparent;
            border: none;
        }}

        QProgressBar#progress_bar {{
            background-color: {self.bar_bg_color};
            border: 1px solid {QLABEL_BORDER_GRAY};
            border-radius: 3px;
            text-align: center;
            color: {QLABEL_WHITE_TEXT};
            font-size: 9px;
        }}

        QProgressBar#progress_bar::chunk {{
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                      stop: 0 {self.bar_color},
                                      stop: 1 {self.bar_color});
            border-radius: 2px;
            margin: 1px;
        }}
        """

        # Add enhanced info styling if needed
        if self.show_size_info or self.show_time_info:
            enhanced_style = f"""
            QLabel#size_info_label, QLabel#time_info_label {{
                color: {QLABEL_SECONDARY_TEXT};
                font-size: 10px;
                font-family: 'Inter', sans-serif;
                background-color: transparent;
                border: none;
            }}
            """
            style += enhanced_style

        self.setStyleSheet(style)

    def sizeHint(self):
        """Return the preferred size for this widget."""
        height = super().sizeHint().height()
        return QSize(self.width(), height)

    # Core progress methods
    def set_progress(self, value: int, total: int):
        """Set progress bar value and total."""
        logger.debug(f"[ProgressWidget] Set progress: {value}/{total}", extra={"dev_only": True})

        # Update progress bar
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(value)

        # Calculate percentage based on size if enhanced tracking enabled, otherwise use count
        if self.progress_estimator and hasattr(self.progress_estimator, 'current_size') and hasattr(self.progress_estimator, 'total_size'):
            # Calculate percentage based on file size
            current_size = getattr(self.progress_estimator, 'current_size', 0)
            total_size = getattr(self.progress_estimator, 'total_size', 0)

            if total_size > 0:
                percent = int(100 * current_size / total_size)
            else:
                percent = int(100 * value / total) if total else 0
        else:
            # Fallback to count-based percentage
            percent = int(100 * value / total) if total else 0

        self.percentage_label.setText(f"{percent}%")

        # Update count display
        self.set_count(value, total)

        # Update enhanced tracking if enabled
        if self.progress_estimator:
            self.progress_estimator.update(value, total)
            self._update_enhanced_displays()

    def set_status(self, text: str):
        """Set status with intelligent truncation for long messages."""
        logger.debug(f"[ProgressWidget] Set status: {text.strip()}")

        if not text:
            self.status_label.setText("")
            return

        # Intelligent truncation for paths and long messages
        max_length = 50
        if len(text) > max_length:
            if "/" in text or "\\" in text:  # Path-like text
                parts = text.replace("\\", "/").split("/")
                if len(parts) > 2:
                    truncated_text = f"{parts[0]}/.../{parts[-1]}"
                    if len(truncated_text) <= max_length:
                        self.status_label.setText(truncated_text)
                        return

            # Fallback: simple truncation
            self.status_label.setText(text[:max_length] + "...")
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
        self.progress_bar.setRange(0, 0)  # Qt built-in indeterminate mode
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

    def start_enhanced_tracking(self, total_size: int = 0):
        """Start enhanced progress tracking with size information."""
        if not self.progress_estimator:
            logger.warning("[ProgressWidget] Enhanced tracking not enabled")
            return

        self.progress_estimator.start(total_size)

        # Store total size for percentage calculation
        self.progress_estimator.total_size = total_size
        self.progress_estimator.current_size = 0

        if self.show_size_info:
            if total_size > 0:
                self.size_label.setText("0 B/calculating...")
            else:
                self.size_label.setText("Processing...")

        if self.show_time_info:
            self.time_label.setText("Starting...")

        logger.debug(f"[ProgressWidget] Started enhanced tracking (total_size: {total_size})")

    def update_enhanced_progress(self, current: int, total: int, current_size: int = 0):
        """Update progress with enhanced size/time tracking."""
        # Update enhanced tracking first (before progress bar)
        if self.progress_estimator:
            self.progress_estimator.update(current, total, current_size)
            # Store current size in estimator for percentage calculation
            self.progress_estimator.current_size = current_size

        # Update basic progress (which will now use size-based percentage if available)
        self.set_progress(current, total)

        # Update enhanced displays
        if self.progress_estimator:
            self._update_enhanced_displays()

    def _update_enhanced_displays(self):
        """Update enhanced size and time displays."""
        if not self.progress_estimator:
            return

        summary = self.progress_estimator.get_progress_summary()

        if self.show_size_info:
            size_text = summary.get('size_range', 'Processing...')
            if not size_text or size_text == "0 B":
                size_text = "Processing..."
            self.size_label.setText(size_text)

        if self.show_time_info:
            time_text = summary.get('time_range', 'Calculating...')
            if not time_text or time_text == "0''":
                time_text = "Calculating..."
            self.time_label.setText(time_text)

    def set_size_info(self, processed_size: int, total_size: int = 0):
        """Manually set size information."""
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
        """Manually set time information."""
        if not self.show_time_info:
            return

        from utils.time_formatter import format_time_range

        time_text = format_time_range(elapsed, estimated_total)
        self.time_label.setText(time_text)

    def get_progress_summary(self) -> dict:
        """Get comprehensive progress summary (if enhanced tracking enabled)."""
        if self.progress_estimator:
            return self.progress_estimator.get_progress_summary()
        return {}

    def _stop_bounce_animation(self):
        """Placeholder for bounce animation cleanup (not used in simple mode)."""
        pass

    def reset(self):
        """Reset all progress tracking."""
        # Stop any animations first
        self._stop_bounce_animation()

        self.set_progress(0, 100)
        self.set_status("Ready...")
        self.set_filename("")
        self.set_count(0, 0)

        if self.progress_estimator:
            self.progress_estimator = ProgressEstimator()

        if self.show_size_info:
            self.size_label.setText("Ready...")

        if self.show_time_info:
            self.time_label.setText("Ready...")


# Factory functions for easy creation with preset configurations
def create_basic_progress_widget(parent=None, **kwargs):
    """Create a basic progress widget (no enhanced tracking)."""
    return ProgressWidget(parent, show_size_info=False, show_time_info=False, **kwargs)

def create_enhanced_progress_widget(parent=None, **kwargs):
    """Create an enhanced progress widget (with size and time tracking)."""
    return ProgressWidget(parent, show_size_info=True, show_time_info=True, **kwargs)

def create_size_only_progress_widget(parent=None, **kwargs):
    """Create a progress widget with only size tracking."""
    return ProgressWidget(parent, show_size_info=True, show_time_info=False, **kwargs)

def create_time_only_progress_widget(parent=None, **kwargs):
    """Create a progress widget with only time tracking."""
    return ProgressWidget(parent, show_size_info=False, show_time_info=True, **kwargs)


# Legacy compatibility aliases
CompactWaitingWidget = ProgressWidget  # For backward compatibility
CompactProgressWidget = ProgressWidget
CompactEnhancedProgressWidget = lambda *args, **kwargs: ProgressWidget(*args, show_size_info=True, show_time_info=True, **kwargs)
