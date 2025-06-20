"""
Module: compact_waiting_widget.py

Author: Michael Economou
Date: 2025-05-24

This module defines the CompactWaitingWidget class, a minimal visual component
used to display a lightweight waiting UI with a label and a horizontal progress bar.
It is designed to be embedded within modal dialogs such as metadata loading popups.

Features:
- Static or dynamic message display.
- Progress bar with optional chunk color override.
- Compact vertical layout suitable for tight dialog space.

Typical Usage:
    widget = CompactWaitingWidget(parent=some_dialog, bar_color="#f5a623")
    widget.setMessage("Reading extended metadata...")
    widget.updateProgress(current=3, total=10)

This widget is used in the Batch File Renamer GUI application within the
MetadataWaitingDialog to indicate progress during metadata loading (basic or extended).
"""

import os
from typing import Optional

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# Setup Logger
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)

class CompactWaitingWidget(QWidget):
    """
    A compact widget-based progress display to be embedded in dialogs or floating containers.

    Features:
    - Fixed width (400 px)
    - No window title, no close button
    - First row: status label (align left)
    - Second row: progress bar (minimal height, no percentage text)
    - Third row: right-aligned percentage, left-aligned file name (with word wrap)
    """

    def __init__(self, parent=None, bar_color: Optional[str] = None, bar_bg_color: Optional[str] = None):
        super().__init__(parent)

        self.setFixedWidth(400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)  # Slightly reduced margins for better space utilization
        layout.setSpacing(4)  # Reduced spacing between elements

        # First row: status label
        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 0, 0, 0)

        self.status_label = QLabel("Reading metadata...", self)
        self.status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.count_label = QLabel("", self)
        self.count_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.count_label.setFixedWidth(90)  # Increased from 60px to handle larger numbers like "2034600"

        status_row.addWidget(self.status_label)
        status_row.addWidget(self.count_label)

        layout.addLayout(status_row)

        # Second row: progress bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setTextVisible(False)  # Hide percentage inside bar
        self.progress_bar.setFixedHeight(8)  # Even thinner progress bar

        # Apply optional color override for extended metadata scans
        if bar_color and bar_bg_color:
            self.progress_bar.setStyleSheet(
                f"QProgressBar {{ background-color: {bar_bg_color}; border-radius: 3px; }} "
                f"QProgressBar::chunk {{ background-color: {bar_color}; border-radius: 3px; }}"
            )
        elif bar_color:
            self.progress_bar.setStyleSheet(
                f"QProgressBar::chunk {{ background-color: {bar_color}; border-radius: 3px; }}"
            )

        layout.addWidget(self.progress_bar)

        # Third row: horizontal layout
        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 0, 0, 0)
        bottom_row.setSpacing(5)

        self.percentage_label = QLabel("0%", self)
        self.percentage_label.setFixedWidth(40)
        self.percentage_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.filename_label = QLabel("", self)
        self.filename_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.filename_label.setWordWrap(True)
        self.filename_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        bottom_row.addWidget(self.percentage_label)
        bottom_row.addWidget(self.filename_label)

        layout.addLayout(bottom_row)

    def sizeHint(self):
        """Return the preferred size for this widget."""
        # Return the fixed width we set, and let the height be calculated by the layout
        height = super().sizeHint().height()
        return QSize(400, height)  # Use our fixed width of 400px

    def set_progress(self, value: int, total: int) -> None:
        self.set_count(value, total)
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(value)
        percent = int(100 * value / total) if total else 0
        self.percentage_label.setText(f"{percent}%")

    def set_filename(self, filename: str) -> None:
        """Set the filename with intelligent truncation for long paths."""
        if not filename:
            self.filename_label.setText("")
            return

        # For very long filenames, show beginning + "..." + extension
        max_length = 60  # Adjust based on dialog width
        if len(filename) > max_length:
            # Try to preserve extension
            name_part, ext_part = os.path.splitext(filename)
            if ext_part and len(ext_part) < 10:  # Reasonable extension length
                # Calculate how much of the name we can show
                available_length = max_length - len(ext_part) - 3  # 3 for "..."
                if available_length > 10:  # Minimum meaningful name length
                    truncated_name = name_part[:available_length] + "..." + ext_part
                    self.filename_label.setText(truncated_name)
                else:
                    # Extension too long or name too short, just truncate normally
                    self.filename_label.setText(filename[:max_length] + "...")
            else:
                # No extension or extension too long, just truncate
                self.filename_label.setText(filename[:max_length] + "...")
        else:
            self.filename_label.setText(filename)

    def set_status(self, text: str) -> None:
        """Set the status with intelligent truncation for long messages."""
        if text.strip():
            logger.debug(f"[Waiting Dialog] Status: {text.strip()}", extra={"dev_only": True})

        if not text:
            self.status_label.setText("")
            return

        # For very long status messages, apply intelligent truncation
        max_length = 50  # Adjust based on dialog width and count label space
        if len(text) > max_length:
            # For paths in status messages, try to preserve meaningful parts
            if "/" in text or "\\" in text:  # Looks like a path
                # Try to show beginning and end of path
                parts = text.replace("\\", "/").split("/")
                if len(parts) > 2:
                    # Show first part + "..." + last part
                    truncated_text = f"{parts[0]}/.../{parts[-1]}"
                    if len(truncated_text) <= max_length:
                        self.status_label.setText(truncated_text)
                        return

            # Fallback: simple truncation with ellipsis
            self.status_label.setText(text[:max_length] + "...")
        else:
            self.status_label.setText(text)

    def set_count(self, current: int, total: int) -> None:
        self.count_label.setText(f"{current} of {total}")
