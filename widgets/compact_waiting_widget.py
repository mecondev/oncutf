from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QSizePolicy, QHBoxLayout
from PyQt5.QtCore import Qt

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

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFixedWidth(250)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # First row: status label
        self.status_label = QLabel("Reading metadata", self)
        self.status_label.setAlignment(Qt.AlignLeft)
        layout.addWidget(self.status_label)

        # Second row: progress bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setTextVisible(False)  # Hide percentage inside bar
        self.progress_bar.setFixedHeight(10)
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

    def set_progress(self, value: int, total: int):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(value)
        percent = int(100 * value / total) if total else 0
        self.percentage_label.setText(f"{percent}%")

    def set_filename(self, filename: str):
        self.filename_label.setText(filename)

    def set_status(self, text: str):
        self.status_label.setText(text)
