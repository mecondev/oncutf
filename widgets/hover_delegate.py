"""
hover_delegate.py

Custom QStyledItemDelegate that enables full-row hover highlight.
The hover background color is provided via constructor and is applied
only when the row is not selected.

Author: Michael Economou
Date: 2025-05-21
"""

from PyQt5.QtWidgets import QStyledItemDelegate, QStyle, QStyleOptionViewItem, QTableView
from PyQt5.QtGui import QPainter, QColor, QPen, QPalette
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
        """
        Custom painting for full-row hover and custom selection, respecting QSS.

        - Uses self.hovered_row for hover feedback.
        - Uses table.selected_rows (custom selection) for full-row selection.
        - Applies QSS-defined highlight color from QPalette.
        - Avoids drawing full row manually — lets each cell draw its own background safely.
        """
        table = self.parent()
        if not isinstance(table, QTableView):
            super().paint(painter, option, index)
            return
        model = table.model()
        row = index.row()

        # Remove ugly focus border (dotted)
        if option.state & QStyle.State_HasFocus:
            option.state &= ~QStyle.State_HasFocus

        selection_model = table.selectionModel() if table else None
        is_selected = selection_model is not None and selection_model.isSelected(index)
        is_hovered = row == self.hovered_row

        # Hover πάνω από selection
        if is_selected and is_hovered:
            background_color = option.palette.color(QPalette.Highlight).lighter(120)
        elif is_selected:
            background_color = option.palette.color(QPalette.Highlight)
        elif is_hovered:
            background_color = self.hover_color
        else:
            background_color = None

        # Paint background if needed
        if background_color:
            painter.save()  # type: ignore
            painter.fillRect(option.rect, background_color)  # type: ignore
            painter.restore()  # type: ignore

        # Optional: draw border for selected row (only on column 0)
        if is_selected and index.column() == table.horizontalHeader().logicalIndex(model.columnCount() - 1):  # type: ignore
            painter.save()  # type: ignore
            border_color = option.palette.color(QPalette.Highlight).darker(120)
            pen = QPen(border_color)
            pen.setWidth(1)
            painter.setPen(pen)  # type: ignore

            # Draw full row rect border
            col_start = 0
            col_end = model.columnCount() - 1  # type: ignore
            rect_start = table.visualRect(model.index(row, col_start))  # type: ignore
            rect_end = table.visualRect(model.index(row, col_end))  # type: ignore
            full_rect = rect_start.united(rect_end)

            painter.drawRect(full_rect.adjusted(0, 0, -1, -1))  # type: ignore
            painter.restore()  # type: ignore

        # Καθαρίζουμε τα state flags για να μην ξαναγεμίσει το background
        option2 = QStyleOptionViewItem(option)
        option2.state &= ~QStyle.State_Selected
        option2.state &= ~QStyle.State_MouseOver
        super().paint(painter, option2, index)
