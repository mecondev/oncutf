from PyQt5.QtWidgets import QCheckBox, QLabel, QHBoxLayout
from PyQt5.QtCore import Qt
from utils.icons_loader import get_menu_icon

class ToggleSwitch(QCheckBox):
    """
    A modern toggle switch widget (slide left/right) based on QCheckBox.
    Left = Off, Right = On, with icon.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTristate(False)
        self.setChecked(False)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumWidth(54)
        self.setMinimumHeight(22)
        self._icon_label = QLabel()
        self._icon_label.setFixedSize(22, 22)
        self._icon_label.setScaledContents(True)
        self._update_icon()
        self.toggled.connect(self._update_icon)
        # Layout: [icon][toggle]
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self._icon_label)
        # layout.addStretch()  # Αφαιρώ το stretch για να μην αφήνει χώρο
        self.setStyleSheet(self._toggle_qss())

    def _update_icon(self):
        if self.isChecked():
            self._icon_label.setPixmap(get_menu_icon("toggle-right").pixmap(22, 22))
        else:
            self._icon_label.setPixmap(get_menu_icon("toggle-left").pixmap(22, 22))

    def _toggle_qss(self) -> str:
        return """
        QCheckBox::indicator {
            width: 0;
            height: 0;
            background: none;
            border: none;
        }
        QCheckBox { padding-left: 0; }
        QCheckBox::indicator:unchecked {
            border-radius: 11px;
            background: #888;
            border: 1px solid #666;
        }
        QCheckBox::indicator:checked {
            border-radius: 11px;
            background: #4a6fa5;
            border: 1px solid #3e5c76;
        }
        QCheckBox::indicator:unchecked::before {
            content: '';
            position: absolute;
            left: 2px;
            top: 2px;
            width: 18px;
            height: 18px;
            border-radius: 9px;
            background: #fff;
            transition: left 0.2s;
        }
        QCheckBox::indicator:checked::before {
            content: '';
            position: absolute;
            left: 24px;
            top: 2px;
            width: 18px;
            height: 18px;
            border-radius: 9px;
            background: #fff;
            transition: left 0.2s;
        }
        """

    def mousePressEvent(self, event):
        self.toggle()
        super().mousePressEvent(event)
