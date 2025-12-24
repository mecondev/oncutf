"""
Module: .cache/test_qss.py

Author: Michael Economou
Date: 2025-06-14

This module provides functionality for the OnCutF batch file renaming application.
"""

from PyQt5.QtCore import QModelIndex
from PyQt5.QtGui import QColor, QPainter, QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QMainWindow,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableView,
)


class HoverDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.hovered_row = -1

    def update_hover_row(self, row):
        self.hovered_row = row

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        if (
            index.row() == self.hovered_row
            and not option.state & QStyleOptionViewItem.State_Selected
        ):
            painter.fillRect(option.rect, QColor("#2e3b4e"))  # custom hover color
        super().paint(painter, option, index)


class HoverTableView(QTableView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.hover_delegate = HoverDelegate(self)
        self.setItemDelegate(self.hover_delegate)

    def mouseMoveEvent(self, event):
        index = self.indexAt(event.pos())
        row = index.row() if index.isValid() else -1
        if row != self.hover_delegate.hovered_row:
            self.hover_delegate.update_hover_row(row)
            self.viewport().update()
        super().mouseMoveEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Full Row Hover QTableView")

        self.table = HoverTableView()
        self.setCentralWidget(self.table)

        self.model = QStandardItemModel(20, 3)
        for row in range(20):
            for col in range(3):
                item = QStandardItem(f"Item {row},{col}")
                self.model.setItem(row, col, item)

        self.table.setModel(self.model)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.resize(400, 300)


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
