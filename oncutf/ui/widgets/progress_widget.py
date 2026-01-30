"""Module: progress_widget.py.

Author: Michael Economou
Date: 2025-06-01

Unified progress widget supporting both basic and enhanced progress tracking.
Simplified and cleaned up design with proper naming conventions.

Features:
- Basic progress display (percentage, count, filename)
- Optional size and time tracking
- Compact layout optimized for dialog usage
- Customizable appearance and behavior
- Progress bar modes: file count based or data volume based

Usage Examples:

1. Basic file count progress:
    widget = ProgressWidget()
    widget.set_progress(50, 100)  # 50%

2. Size-based progress for hash operations:
    widget = ProgressWidget(progress_mode="size", show_size_info=True, show_time_info=True)
    widget.start_progress_tracking(total_size=1000000000)  # 1GB total
    widget.update_progress(processed_bytes=500000000)     # 50% complete

3. Factory function for hash operations:
    widget = create_size_based_progress_widget()
    # Automatically configured with size-based progress and full tracking

4. Dynamic mode switching:
    widget = ProgressWidget()
    widget.set_progress_mode("size")  # Switch to size-based progress
    widget.set_progress_mode("count") # Switch back to count-based
"""

import math
import time

from PyQt5.QtCore import QSize, Qt, QTimer
from PyQt5.QtGui import QFontMetrics
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from typing_extensions import deprecated

from oncutf.config import (
    QLABEL_BORDER_GRAY,
    QLABEL_PRIMARY_TEXT,
    QLABEL_SECONDARY_TEXT,
    QLABEL_TERTIARY_TEXT,
)
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class ProgressWidget(QWidget):
    """Unified progress widget with flexible configuration.

    Handles all progress display needs:
    - Basic progress (file counting, metadata loading)
    - Optional size and time tracking
    - Optimized layout for long paths and recursive imports
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        bar_color: str | None = None,
        bar_bg_color: str | None = None,
        show_size_info: bool = False,
        show_time_info: bool = False,
        fixed_width: int = 400,
        progress_mode: str = "count",
    ):
        """Initialize the progress widget.

        Args:
            parent: Parent widget
            bar_color: Progress bar color (defaults to theme accent)
            bar_bg_color: Progress bar background color (defaults to theme background_lighter)
            show_size_info: Whether to show size information
            show_time_info: Whether to show time information
            fixed_width: Fixed width for the widget
            progress_mode: Progress bar mode - "count" for file count, "size" for data volume

        """
        super().__init__(parent)
        self.setFixedWidth(fixed_width)

        self._size_label_width_total: int | None = None

        # Get default colors from theme if not provided
        if bar_color is None or bar_bg_color is None:
            from oncutf.ui.theme_manager import get_theme_manager

            theme = get_theme_manager()
            bar_color = bar_color or theme.colors.get("accent_color", "#748cab")
            bar_bg_color = bar_bg_color or theme.colors.get("disabled_background", "#181818")

        # Configuration
        self.show_size_info = show_size_info
        self.show_time_info = show_time_info
        self.bar_color = bar_color
        self.bar_bg_color = bar_bg_color
        self.progress_mode = progress_mode  # "count" or "size"

        # Simple progress tracking
        self.start_time = None
        self.total_size = 0
        self.processed_size = 0
        self.current_count = 0  # Track current file count
        self.total_count = 0  # Track total file count

        # Optimized throttling for better responsiveness
        self._last_update_time = 0
        self._min_update_interval = 0.05  # 50ms for better responsiveness (was 100ms)

        # Timer for time updates
        self._time_timer = None

        # Setup UI
        self._setup_ui()
        self._apply_styling()

        logger.debug(
            "[ProgressWidget] Initialized (size_info: %s, time_info: %s, progress_mode: %s)",
            show_size_info,
            show_time_info,
            progress_mode,
            extra={"dev_only": True},
        )

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
        self.count_label.setMinimumWidth(70)

        status_row.addWidget(self.status_label)
        status_row.addWidget(self.count_label)
        self.main_layout.addLayout(status_row)

        # Second row: progress bar (very thin)
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progress_bar")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        # DPI-aware progress bar height (8px at 96 DPI)
        from PyQt5.QtWidgets import QApplication

        dpi_scale = QApplication.instance().devicePixelRatio() if QApplication.instance() else 1.0
        progress_height = max(6, int(8 * dpi_scale))  # Minimum 6px, scaled for DPI
        self.progress_bar.setFixedHeight(progress_height)
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
            # Split size into 3 labels to prevent jumping
            size_container = QHBoxLayout()
            size_container.setContentsMargins(0, 0, 0, 0)
            size_container.setSpacing(3)

            self.size_current_label = QLabel("")
            self.size_current_label.setObjectName("size_current_label")
            self.size_current_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            # Fixed width + AlignRight for stability (text flows towards 'of')
            # Width will be adjusted via QFontMetrics when total size is known.
            self.size_current_label.setFixedWidth(70)
            self.size_current_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

            self.size_of_label = QLabel("of")
            self.size_of_label.setObjectName("size_of_label")
            self.size_of_label.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            # Fixed small width to act as stable anchor
            self.size_of_label.setFixedWidth(18)
            self.size_of_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

            self.size_total_label = QLabel("")
            self.size_total_label.setObjectName("size_total_label")
            self.size_total_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            # Minimum width + AlignLeft (text sticks to 'of', grows as needed)
            # Width will be adjusted via QFontMetrics when total size is known.
            self.size_total_label.setMinimumWidth(70)
            self.size_total_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

            size_container.addWidget(self.size_current_label)
            size_container.addWidget(self.size_of_label)
            size_container.addWidget(self.size_total_label)
            # No addStretch() here - let labels stay on the left side

            enhanced_row.addLayout(size_container)

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
        # Store for display
        self.current_count = value
        self.total_count = total

        if total <= 0:
            percentage = 0
        else:
            percentage = int((value / total) * 100)
            percentage = max(0, min(100, percentage))

        self.progress_bar.setValue(percentage)
        # Display percentage (below bar, left)
        self.percentage_label.setText(f"{percentage}%")
        # Update count label (top-right)
        self.count_label.setText(f"{value} of {total}")

    def set_progress_by_size(self, processed_bytes: int, total_bytes: int):
        """Set progress based on data volume (bytes processed).

        Args:
            processed_bytes: Number of bytes processed so far
            total_bytes: Total number of bytes to process

        """
        # Throttling to prevent excessive updates (max 20 updates per second)
        current_time = time.time()
        if current_time - self._last_update_time < 0.05:  # 50ms = 20 FPS
            return
        self._last_update_time = current_time

        if total_bytes <= 0:
            percentage = 0
        else:
            # Convert to integers to prevent overflow issues
            processed_bytes = int(processed_bytes)
            total_bytes = int(total_bytes)

            # Calculate percentage with overflow protection
            if processed_bytes >= total_bytes:
                percentage = 100
            else:
                percentage = int((processed_bytes * 100) // total_bytes)
                percentage = max(0, min(100, percentage))

        self.progress_bar.setValue(percentage)
        # Always display percentage (below bar, left)
        self.percentage_label.setText(f"{percentage}%")
        # Update count label if available (top-right)
        if self.current_count > 0 and self.total_count > 0:
            self.count_label.setText(f"{self.current_count} of {self.total_count}")

        # Log milestone progress (every 10%)
        if percentage % 10 == 0 and percentage != getattr(self, "_last_milestone", -1):
            self._last_milestone = percentage
            logger.debug(
                "[ProgressWidget] Progress milestone: %d%% (%d/%d bytes)",
                percentage,
                processed_bytes,
                total_bytes,
                extra={"dev_only": True},
            )

    def set_status(self, text: str):
        """Set status text with intelligent truncation for long messages.

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
            truncate_pos = text.rfind(" ", 0, max_length - 3)
            if truncate_pos > max_length // 2:  # Only if we find a reasonable break point
                truncated_text = text[:truncate_pos] + "..."
            else:
                truncated_text = text[: max_length - 3] + "..."
            self.status_label.setText(truncated_text)
        else:
            self.status_label.setText(text)

    def set_filename(self, filename: str):
        """Set filename with intelligent truncation for long paths."""
        from oncutf.utils.naming.text_helpers import truncate_filename_middle

        truncated_filename = truncate_filename_middle(filename)
        self.filename_label.setText(truncated_filename)

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
        logger.debug(
            "[ProgressWidget] Progress bar set to indeterminate mode",
            extra={"dev_only": True},
        )

    def set_determinate_mode(self):
        """Set progress bar back to normal determinate mode."""
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.current_count = 0
        self.total_count = 0
        self.percentage_label.setText("0%")
        self.percentage_label.show()
        self.count_label.setText("0 of 0")
        logger.debug(
            "[ProgressWidget] Progress bar set to determinate mode",
            extra={"dev_only": True},
        )

    def set_progress_mode(self, mode: str):
        """Set progress calculation mode.

        Args:
            mode: Either "count" (file count based) or "size" (byte size based)

        """
        if mode not in ["count", "size"]:
            logger.warning("[ProgressWidget] Invalid progress mode: %s, using 'count'", mode)
            mode = "count"

        old_mode = self.progress_mode
        self.progress_mode = mode

        if old_mode != mode:
            logger.debug(
                "[ProgressWidget] Progress mode changed: %s -> %s",
                old_mode,
                mode,
                extra={"dev_only": True},
            )

            # Only warn if switching to size mode and no total size will be set
            # (This warning is mainly for debugging, not a real problem)
            if mode == "size" and self.total_size <= 0:
                logger.debug(
                    "[ProgressWidget] Switched to size mode without total size. Size will be set via start_progress_tracking().",
                    extra={"dev_only": True},
                )

    def start_progress_tracking(self, total_size: int = 0):
        """Start progress tracking with optional size tracking."""
        self.start_time = time.time()
        self.total_size = total_size
        self.processed_size = 0

        if self.show_size_info and hasattr(self, "size_current_label"):
            from oncutf.utils.filesystem.file_size_formatter import (
                format_file_size_system_compatible,
            )

            self.size_current_label.setText("0 B")
            if total_size > 0:
                total_str = format_file_size_system_compatible(total_size)
                self.size_total_label.setText(total_str)
                self._update_size_label_widths(total_size)
            else:
                self.size_total_label.setText("0 B")
                self._update_size_label_widths(0)

        if self.show_time_info and hasattr(self, "time_label"):
            self.time_label.setText("0s")
            # Start timer to update time display every 500ms for smoother updates
            self._time_timer = QTimer(self)
            self._time_timer.timeout.connect(self._update_time_display)
            self._time_timer.start(500)  # Update every 500ms for smoother time display
            logger.debug(
                "[ProgressWidget] Timer started for time updates (500ms interval)",
                extra={"dev_only": True},
            )

        logger.debug(
            "[ProgressWidget] Started tracking (total_size: %d)",
            total_size,
            extra={"dev_only": True},
        )

    def update_progress(
        self,
        file_count: int = 0,
        total_files: int = 0,
        processed_bytes: int = 0,
        total_bytes: int = 0,
    ):
        """Unified method to update progress regardless of mode.

        This method automatically selects the appropriate progress calculation
        based on the current progress_mode setting.

        Args:
            file_count: Current number of files processed
            total_files: Total number of files to process
            processed_bytes: Current bytes processed (cumulative)
            total_bytes: Total bytes to process (optional, uses stored value if 0)

        """
        # Update internal size tracking
        if processed_bytes > 0:
            self.processed_size = processed_bytes
        if total_bytes > 0:
            self.total_size = total_bytes

        # Update progress based on mode
        if self.progress_mode == "size" and self.total_size > 0:
            # Size-based progress
            self.set_progress_by_size(self.processed_size, self.total_size)
        # Count-based progress (default)
        elif total_files > 0:
            self.set_progress(file_count, total_files)
        # If no file count provided, try to calculate from size
        elif self.total_size > 0:
            self.set_progress_by_size(self.processed_size, self.total_size)

        # Update displays
        if self.show_size_info and hasattr(self, "size_current_label"):
            self._update_size_display()

        if self.show_time_info and hasattr(self, "time_label"):
            self._update_time_display()

    def _update_size_display(self):
        """Update size information display with improved formatting (split labels)."""
        # For split labels, avoid padded/monospace strings.
        # Alignment + fixed/min widths handle stability; padding would add visible gaps.
        from oncutf.utils.filesystem.file_size_formatter import (
            format_file_size_system_compatible,
        )

        processed_str = format_file_size_system_compatible(self.processed_size)
        self.size_current_label.setText(processed_str)

        if self.total_size > 0:
            total_str = format_file_size_system_compatible(self.total_size)
            self.size_total_label.setText(total_str)
        else:
            self.size_total_label.setText("")

    def _update_size_label_widths(self, total_size: int) -> None:
        """Adjust size label widths using font metrics for compact, stable alignment.

        Goal:
        - Keep current label stable (fixed width) and right-aligned, so it hugs 'of'.
        - Keep total label left-aligned so it starts immediately after 'of'.
        - Reduce wasted space vs. a large hard-coded fixed width.

        Widths are derived from the formatted total size plus a couple of
        worst-case candidates near unit boundaries to avoid truncation.
        """
        if not (
            self.show_size_info
            and hasattr(self, "size_current_label")
            and hasattr(self, "size_total_label")
        ):
            return

        if self._size_label_width_total == total_size:
            return

        from oncutf.utils.filesystem.file_size_formatter import (
            format_file_size_system_compatible,
        )

        font_metrics = QFontMetrics(self.size_current_label.font())
        padding_px = 6

        candidates: list[str] = ["0 B"]
        if total_size > 0:
            candidates.append(format_file_size_system_compatible(total_size))
            candidates.append(format_file_size_system_compatible(max(0, total_size - 1)))

            unit_index = int(math.log(total_size, 1024)) if total_size > 0 else 0
            unit_index = max(0, min(unit_index, 5))

            # Add a couple of near-boundary candidates to cover cases like
            # total "1.0 GB" but current shown as "1023 MB".
            try:
                bytes_this_unit = int(999.9 * (1024**unit_index))
                candidates.append(format_file_size_system_compatible(bytes_this_unit))
            except OverflowError:
                pass

            if unit_index > 0:
                try:
                    bytes_lower_unit = int(1023.0 * (1024 ** (unit_index - 1)))
                    candidates.append(format_file_size_system_compatible(bytes_lower_unit))
                except OverflowError:
                    pass

        max_text_width = 0
        for text in candidates:
            max_text_width = max(max_text_width, font_metrics.horizontalAdvance(text))

        target_width = max(10, max_text_width + padding_px)

        # Current: fixed + AlignRight for stability.
        self.size_current_label.setFixedWidth(target_width)

        # Total: minimum + AlignLeft so it sticks to 'of'.
        self.size_total_label.setMinimumWidth(target_width)

        self._size_label_width_total = total_size

    def _update_time_display(self):
        """Update time display with elapsed and estimated time in HH:MM:SS format.

        Improved estimation (2025): More stable time calculation that doesn't reset
        between files - better than old approach that lost estimation accuracy.
        """
        if not self.show_time_info or not hasattr(self, "time_label"):
            return

        if self.start_time is None:
            self.time_label.setText("Ready...")
            return

        # Calculate elapsed time
        elapsed = time.time() - self.start_time

        # Debug logging to see if this method is being called
        logger.debug(
            "[ProgressWidget] _update_time_display called: elapsed=%.1fs, processed=%d, total=%d",
            elapsed,
            self.processed_size,
            self.total_size,
            extra={"dev_only": True},
        )

        # Stable estimation based on cumulative progress - no more resets between files
        if self.processed_size > 0 and self.total_size > 0:
            progress_ratio = self.processed_size / self.total_size

            # Store previous estimation for stability check
            if not hasattr(self, "_last_progress_ratio"):
                self._last_progress_ratio = 0.0
            if not hasattr(self, "_last_estimation"):
                self._last_estimation = None

            # Only update estimation if progress has changed significantly (>0.5%)
            progress_change = abs(progress_ratio - self._last_progress_ratio)

            # Only show estimation if we have meaningful progress (>1%)
            if progress_ratio > 0.01:
                # Calculate new estimation
                estimated_total = elapsed / progress_ratio

                # Use previous estimation if change is too small (prevents jumping)
                if self._last_estimation is not None and progress_change < 0.005:
                    estimated_total = self._last_estimation
                else:
                    self._last_estimation = estimated_total
                    self._last_progress_ratio = progress_ratio

                # Format times in HH:MM:SS format with improved formatting
                elapsed_str = self._format_time_hms(elapsed)
                estimated_total_str = self._format_time_hms(estimated_total)

                time_text = f"{elapsed_str} of {estimated_total_str} Est."
                self.time_label.setText(time_text)
                logger.debug(
                    "[ProgressWidget] Time updated: %s",
                    time_text,
                    extra={"dev_only": True},
                )
            else:
                # Early stage - just show elapsed time until we have stable estimation
                elapsed_str = self._format_time_hms(elapsed)
                time_text = f"{elapsed_str} of calculating... Est."
                self.time_label.setText(time_text)
                logger.debug(
                    "[ProgressWidget] Time updated (early): %s",
                    time_text,
                    extra={"dev_only": True},
                )
        else:
            elapsed_str = self._format_time_hms(elapsed)
            self.time_label.setText(elapsed_str)
            logger.debug(
                "[ProgressWidget] Time updated (no progress): %s",
                elapsed_str,
                extra={"dev_only": True},
            )

    def _format_time_hms(self, seconds: float) -> str:
        """Format time in HH:MM:SS format for consistent display.

        Args:
            seconds: Time in seconds

        Returns:
            Formatted time string (e.g., "00:01:30", "01:23:45")

        """
        if seconds < 0:
            return "00:00:00"

        # Convert to integers
        total_seconds = int(seconds)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60

        # Format as HH:MM:SS
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    @deprecated("Use _format_time_hms() instead. Will be removed in v2.0.")
    def _format_time(self, seconds: float) -> str:
        """Format time in a human-readable format (legacy method).

        Note: This method is kept for compatibility but _format_time_hms
        should be used for new implementations.
        """
        if seconds < 1:
            return "0s"
        elif seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            remaining_seconds = int(seconds % 60)
            if remaining_seconds == 0:
                return f"{minutes}m"
            else:
                return f"{minutes}m {remaining_seconds}s"
        else:
            hours = int(seconds // 3600)
            remaining_minutes = int((seconds % 3600) // 60)
            if remaining_minutes == 0:
                return f"{hours}h"
            else:
                return f"{hours}h {remaining_minutes}m"

    def set_size_info(self, processed_size: int, total_size: int = 0):
        """Update size information display with cumulative tracking.

        Improved handling (2025): Accepts cumulative processed_size that continuously
        increases - no more reset issues between files like the old approach.

        Added 64-bit integer support and overflow protection for large files (>24GB).

        Args:
            processed_size: Cumulative bytes processed (always increasing, 64-bit)
            total_size: Total bytes to process (optional, uses stored value if 0, 64-bit)

        """
        # Enhanced layout uses split labels (size_current_label / size_total_label).
        # Keep compatibility with older layouts by checking the actual fields.
        if not self.show_size_info or not hasattr(self, "size_current_label"):
            return

        # Convert to Python integers to handle 64-bit values properly
        processed_size = int(processed_size)
        total_size = int(total_size) if total_size > 0 else 0

        # Always update internal values first
        old_processed = self.processed_size
        old_total = self.total_size

        self.processed_size = processed_size
        if total_size > 0:
            self.total_size = total_size

        # Update the visible split labels.
        self._update_size_display()

        # Debug logging to track what's happening - improved logic
        # Only log significant changes to avoid spam
        log_message = ""

        # Check for backwards progress (potential problem) - with overflow protection
        if processed_size < old_processed:
            # Check if this might be an overflow (large negative number)
            if processed_size < 0 and old_processed > 0:
                log_message = f"[ProgressWidget] INTEGER OVERFLOW detected! processed_size={processed_size}, old_processed={old_processed}"
                logger.error(log_message)
                # Reset to prevent further issues
                self.processed_size = old_processed
                return
            else:
                # Regular backwards movement
                log_message = f"[ProgressWidget] WARNING: Processed size went backwards! {processed_size} < {old_processed} (diff: {old_processed - processed_size})"
                logger.warning(log_message)

        # Check for total size changes
        elif total_size > 0 and total_size != old_total:
            log_message = f"[ProgressWidget] Total size updated: {old_total:,} -> {total_size:,}"
            logger.debug(log_message)

        # Check for large progress jumps (>50MB)
        elif processed_size > old_processed + 50_000_000:
            log_message = f"[ProgressWidget] Large progress jump: {old_processed:,} -> {processed_size:,} (+{processed_size - old_processed:,} bytes)"
            logger.debug(log_message)

        # Check if we need to force an update (significant change or new total_size)
        force_update = False
        if total_size > 0 and total_size != old_total:
            force_update = True  # New total size - always update UI
        elif processed_size > old_processed:
            # For small files: lower threshold to ensure updates are visible
            # For large operations: higher threshold to avoid UI flooding
            if self.total_size > 0:
                progress_change_ratio = (processed_size - old_processed) / self.total_size
                # Force update if progress changed by more than 1% OR more than 1MB
                if progress_change_ratio > 0.01 or (processed_size - old_processed) > 1_000_000:
                    force_update = True
            # No total size known - update for any significant change (>1MB)
            elif (processed_size - old_processed) > 1_000_000:
                force_update = True

        # Apply optimized throttling for better responsiveness
        current_time = time.time()
        time_since_last_update = current_time - self._last_update_time

        # Force update if enough time has passed OR if it's a significant change
        if force_update or time_since_last_update >= self._min_update_interval:
            self._last_update_time = current_time
            self._update_size_display()

            # Also update time display if enabled
            if self.show_time_info:
                self._update_time_display()

    def set_time_info(self, elapsed: float, estimated_total: float | None = None):
        """Manually set time information in HH:MM:SS format.

        Args:
            elapsed: Elapsed time in seconds
            estimated_total: Estimated total time in seconds (optional)

        """
        if not self.show_time_info:
            return

        # Format elapsed time
        elapsed_text = self._format_time_hms(elapsed)

        # If we have estimated total, show both elapsed and estimated
        if estimated_total is not None and estimated_total > elapsed:
            estimated_text = self._format_time_hms(estimated_total)
            time_text = f"{elapsed_text} of {estimated_text} Est."
        else:
            time_text = elapsed_text

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

        # Reset time estimation tracking variables
        if hasattr(self, "_last_progress_ratio"):
            self._last_progress_ratio = 0.0
        if hasattr(self, "_last_estimation"):
            self._last_estimation = None

        # Stop timer if running
        if self._time_timer and self._time_timer.isActive():
            self._time_timer.stop()
            self._time_timer = None

        if self.show_size_info and hasattr(self, "size_current_label"):
            self.size_current_label.setText("0 B")
            self.size_total_label.setText("0 B")

        if self.show_time_info and hasattr(self, "time_label"):
            self.time_label.setText("Ready...")


# Simplified factory functions - only keep the essential ones
def create_basic_progress_widget(parent=None, **kwargs):
    """Create a basic progress widget (no enhanced tracking)."""
    return ProgressWidget(parent, show_size_info=False, show_time_info=False, **kwargs)


def create_size_based_progress_widget(parent=None, **kwargs):
    """Create a progress widget with size-based progress bar and full tracking."""
    return ProgressWidget(
        parent, show_size_info=True, show_time_info=True, progress_mode="size", **kwargs
    )
