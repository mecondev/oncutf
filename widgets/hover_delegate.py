"""
hover_delegate.py

Custom QStyledItemDelegate that enables full-row hover highlight.
The hover background color is provided via constructor and is applied
only when the row is not selected.

Author: Michael Economou
Date: 2025-05-21
"""

from PyQt5.QtWidgets import QStyledItemDelegate, QStyle, QStyleOptionViewItem
from PyQt5.QtGui import QPainter, QColor, QPen
from PyQt5.QtCore import QModelIndex


class HoverItemDelegate(QStyledItemDelegate):
    def __init__(self, parent=None, hover_color: str = "#2e3b4e"):
        """
        Initializes the hover delegate.

        Args:
            parent: The parent widget.
            hover_color: The background color to use for hovered rows.
        """
        super().__init__(parent)
        self.hovered_row: int = -1
        self.hover_color: QColor = QColor(hover_color)

    def update_hover_row(self, row: int) -> None:
        """
        Updates the row that should be highlighted on hover.
        """
        self.hovered_row = row

    def paint(self, painter, option, index):
        # καταστολή visual focus
        if option.state & QStyle.State_HasFocus:
            option.state &= ~QStyle.State_HasFocus

        # hover (μόνο αν όχι selected)
        if index.row() == self.hovered_row and not (option.state & QStyle.State_Selected):
            painter.save()
            painter.fillRect(option.rect, self.hover_color)
            painter.restore()

        # draw selection border (από κάθε κελί — harmless redundancy)
        if option.state & QStyle.State_Selected:
            painter.save()
            pen = QPen(QColor("#304d6a"))  # soft blue-gray
            pen.setWidth(1)
            painter.setPen(pen)

            # full row rect from this cell
            table = self.parent()
            model = table.model()
            row = index.row()
            col_start = 0
            col_end = model.columnCount() - 1
            rect_start = table.visualRect(model.index(row, col_start))
            rect_end = table.visualRect(model.index(row, col_end))
            full_rect = rect_start.united(rect_end)

            painter.drawRect(full_rect.adjusted(0, 0, -1, -1))
            painter.restore()

        super().paint(painter, option, index)
