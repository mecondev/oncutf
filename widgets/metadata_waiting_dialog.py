from PyQt5.QtWidgets import QDialog, QVBoxLayout
from widgets.compact_waiting_widget import CompactWaitingWidget
from PyQt5.QtCore import Qt
from config import EXTENDED_METADATA_COLOR, EXTENDED_METADATA_BG_COLOR, FAST_METADATA_COLOR, FAST_METADATA_BG_COLOR


class MetadataWaitingDialog(QDialog):
    """
    QDialog wrapper that contains a CompactWaitingWidget.

    This dialog:
    - Has no title bar (frameless)
    - Is styled via QSS using standard QWidget rules
    - Hosts a compact waiting UI to display metadata reading progress
    """
    def __init__(self, parent=None, is_extended=False):
        super().__init__(parent)

        # Frameless and styled externally
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # CompactWaitingWidget
        is_extended = getattr(parent, "force_extended_metadata", False)
        if is_extended:
            bar_color = EXTENDED_METADATA_COLOR
            bar_bg_color = EXTENDED_METADATA_BG_COLOR
        else:
            bar_color = FAST_METADATA_COLOR
            bar_bg_color = FAST_METADATA_BG_COLOR
        self.waiting_widget = CompactWaitingWidget(self, bar_color=bar_color, bar_bg_color=bar_bg_color)

        layout.addWidget(self.waiting_widget)

        self.setLayout(layout)

    def set_progress(self, value: int, total: int):
        self.waiting_widget.set_progress(value, total)

    def set_filename(self, filename: str):
        self.waiting_widget.set_filename(filename)

    def set_status(self, text: str):
        self.waiting_widget.set_status(text)
