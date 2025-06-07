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

from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# Setup Logger
from utils.logger_helper import get_logger

logger = get_logger(__name__)

class CompactWaitingWidget(QWidget):
    """
    A compact widget-based progress display to be embedded in dialogs or floating containers.

    Features:
    - Fixed width (250 px)
    - No window title, no close button
    - First row: status label (align left)
    - Second row: progress bar (minimal height, no percentage text)
    - Third row: right-aligned percentage, left-aligned file name (with word wrap)
    """

    def __init__(self, parent=None, bar_color: Optional[str] = None, bar_bg_color: Optional[str] = None):
        super().__init__(parent)

        self.setFixedWidth(250)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # First row: status label
        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 0, 0, 0)

        self.status_label = QLabel("Reading metadata...", self)
        self.status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.count_label = QLabel("", self)
        self.count_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.count_label.setFixedWidth(60)  # enough for "1234/1234"

        status_row.addWidget(self.status_label)
        status_row.addWidget(self.count_label)

        layout.addLayout(status_row)

        # Second row: progress bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setTextVisible(False)  # Hide percentage inside bar
        self.progress_bar.setFixedHeight(10)

        # Apply optional color override for extended metadata scans
        if bar_color and bar_bg_color:
            self.progress_bar.setStyleSheet(
                f"QProgressBar {{ background-color: {bar_bg_color}; border-radius: 4px; }} "
                f"QProgressBar::chunk {{ background-color: {bar_color}; border-radius: 4px; }}"
            )
        elif bar_color:
            self.progress_bar.setStyleSheet(
                f"QProgressBar::chunk {{ background-color: {bar_color}; }}"
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

    def set_progress(self, value: int, total: int) -> None:
        logger.debug(f"[Waiting Dialog] Set progress. Called from: {value} of {total}")
        self.set_count(value, total)
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(value)
        percent = int(100 * value / total) if total else 0
        self.percentage_label.setText(f"{percent}%")

    def set_filename(self, filename: str) -> None:
        self.filename_label.setText(filename)

    def set_status(self, text: str) -> None:
        logger.debug(f"[Waiting Dialog] Set status. Called from: {text.strip()}")
        self.status_label.setText(text)

    def set_count(self, current: int, total: int) -> None:
        self.count_label.setText(f"{current} of {total}")
