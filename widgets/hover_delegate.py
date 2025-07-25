"""
Module: hover_delegate.py

Author: Michael Economou
Date: 2025-05-31

hover_delegate.py
Custom QStyledItemDelegate that enables full-row hover highlight.
The hover background color is provided via constructor and is applied
only when the row is not selected.
"""

from core.pyqt_imports import (
    QColor,
    QCursor,
    QIcon,
    QPen,
    QStyle,
    QStyledItemDelegate,
    Qt,
    QTableView,
)
from utils.theme import get_qcolor, get_theme_color


class HoverItemDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        """
        Initializes the hover delegate.

        Args:
            parent: The parent widget.
            hover_color: The background color to use for hovered rows (if None, uses theme)
        """
        super().__init__(parent)
        self.hovered_row: int = -1

        # Get colors from theme system
        self.hover_color: QColor = get_qcolor("table_hover_background")

    def update_hover_row(self, row: int) -> None:
        """
        Updates the row that should be highlighted on hover.
        """
        self.hovered_row = row

    def leaveEvent(self, event) -> None:
        """Handle mouse leave events to hide tooltips."""
        # Hide any active tooltips when mouse leaves the delegate
        from utils.tooltip_helper import TooltipHelper

        TooltipHelper.clear_tooltips_for_widget(self.parent())

        super().leaveEvent(event)

    def enterEvent(self, event) -> None:
        """Handle mouse enter events to restore hover state."""
        # Update hover state when mouse enters the delegate
        table = self.parent()
        if isinstance(table, QTableView):
            pos = table.viewport().mapFromGlobal(QCursor.pos())
            index = table.indexAt(pos)
            hovered_row = index.row() if index.isValid() else -1
            self.update_hover_row(hovered_row)

        super().enterEvent(event)

    def focusOutEvent(self, event) -> None:
        """Handle focus loss events to hide tooltips."""
        # Hide any active tooltips when focus is lost
        from utils.tooltip_helper import TooltipHelper

        TooltipHelper.clear_tooltips_for_widget(self.parent())

        super().focusOutEvent(event)

    def paint(self, painter, option, index):
        """
        Custom painting for full-row hover and selection with proper icon handling.

        - Always paints background for hover/selection to override alternate colors
        - Icons in column 0 paint over the background
        - Adds borders for selected rows
        - Proper text colors for selection state
        - Handles alternate row colors internally
        """
        table = self.parent()
        if not isinstance(table, QTableView):
            super().paint(painter, option, index)
            return

        model = table.model()
        row = index.row()
        column = index.column()

        # Remove ugly focus border (dotted)
        if option.state & QStyle.State_HasFocus:
            option.state &= ~QStyle.State_HasFocus

        selection_model = table.selectionModel() if table else None
        is_selected = selection_model is not None and selection_model.isSelected(index)
        is_hovered = row == self.hovered_row

        # Determine background color in priority order:
        # 1. Selection + Hover
        # 2. Selection
        # 3. Hover
        # 4. Alternate row color
        # 5. Default background

        background_color = None
        if is_selected and is_hovered:
            # Selected + hovered: slightly lighter than normal selection
            background_color = QColor(get_theme_color("highlight_light_blue"))
        elif is_selected:
            # Normal selection color
            background_color = QColor(get_theme_color("table_selection_background"))
        elif is_hovered:
            # Hover color - paint over alternate background
            background_color = self.hover_color
        elif row % 2 == 1:
            # Alternate row color for odd rows (only if not selected/hovered)
            background_color = QColor(get_theme_color("table_alternate_background"))
        # For even rows, use default background (no painting needed)

        if background_color:
            painter.save()
            painter.fillRect(option.rect, background_color)
            painter.restore()

        # Draw border for selected rows (only on the last column to avoid overlaps)
        if is_selected and model and column == model.columnCount() - 1:
            painter.save()
            border_color = QColor(get_theme_color("table_selection_background")).darker(130)
            painter.setPen(QPen(border_color, 1))

            # Calculate full row rect
            col_start = 0
            col_end = model.columnCount() - 1
            rect_start = table.visualRect(model.index(row, col_start))
            rect_end = table.visualRect(model.index(row, col_end))
            full_rect = rect_start.united(rect_end)

            painter.drawRect(full_rect.adjusted(0, 0, -1, -1))
            painter.restore()

        # For column 0 (icons), use custom painting to ensure icons appear over background
        if column == 0:
            # Get the icon from the model's DecorationRole
            icon_data = model.data(index, Qt.DecorationRole)
            if icon_data and isinstance(icon_data, QIcon):
                # Check if this is a combined icon (wider than tall) or single icon
                icon_size = icon_data.actualSize(option.rect.size())

                if icon_size.width() > icon_size.height():
                    # Combined icon - use wider rect with minimal padding
                    icon_rect = option.rect.adjusted(1, 2, -1, -2)
                else:
                    # Single icon - use square rect with normal padding
                    icon_rect = option.rect.adjusted(2, 2, -2, -2)

                icon_data.paint(painter, icon_rect, Qt.AlignCenter)

            # Don't call super().paint() for column 0 since we handled the icon ourselves
            return

            # For all other columns, paint everything manually - no super().paint()
        display_text = model.data(index, Qt.DisplayRole) if model else ""
        if display_text:
            # Determine text color based on selection and hover state
            if is_selected and is_hovered:
                # Selected + hovered: dark text for light blue background
                text_color = QColor(get_theme_color("table_selection_text"))
            else:
                # All other cases (normal, hover only, selected only): light text
                text_color = QColor(get_theme_color("table_text"))

            painter.save()
            painter.setPen(text_color)

            text_rect = option.rect.adjusted(4, 0, -4, 0)  # Small horizontal padding

            alignment = (
                model.data(index, Qt.TextAlignmentRole) if model else Qt.AlignLeft | Qt.AlignVCenter
            )  # type: ignore
            if not alignment:
                alignment = Qt.AlignLeft | Qt.AlignVCenter  # type: ignore

            # Ensure alignment is an integer (convert from QVariant if needed)
            if hasattr(alignment, "value"):  # QVariant case
                alignment = alignment.value()
            # Handle Qt.Alignment objects (they're not int but can be used directly)
            if not isinstance(alignment, int | Qt.Alignment):  # type: ignore
                alignment = Qt.AlignLeft | Qt.AlignVCenter  # type: ignore

            fm = painter.fontMetrics()
            elided = fm.elidedText(str(display_text), Qt.ElideRight, text_rect.width())  # type: ignore
            painter.drawText(text_rect, alignment, elided)
            painter.restore()
