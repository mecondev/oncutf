"""
Module: ui_delegates.py

Author: Michael Economou
Date: 2025-05-31

ui_delegates.py
Custom QStyledItemDelegate classes for enhanced UI components:
- FileTableHoverDelegate: Full-row hover highlight for file tables
- ComboBoxItemDelegate: Themed styling for combobox dropdown items
"""


from core.pyqt_imports import (
    QBrush,
    QColor,
    QCursor,
    QIcon,
    QPainter,
    QPalette,
    QPen,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    Qt,
    QTableView,
)
from utils.logger_factory import get_cached_logger
from utils.theme import get_qcolor, get_theme_color

logger = get_cached_logger(__name__)

class ComboBoxItemDelegate(QStyledItemDelegate):
    """Custom delegate to render QComboBox dropdown items with theme and proper states."""

    def __init__(self, parent=None, theme=None):
        super().__init__(parent)
        self.theme = theme

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)

        # Use font from theme for absolute consistency
        option.font.setFamily(self.theme.fonts["base_family"])
        option.font.setPointSize(int(self.theme.fonts["interface_size"].replace("pt", "")))
        # Height same as QComboBox fixedHeight (24px to match new height)
        option.rect.setHeight(24)

        # Handle disabled item (grayout)
        if not (index.flags() & Qt.ItemIsEnabled):
            option.palette.setBrush(
                QPalette.Text, QBrush(QColor(self.theme.get_color("disabled_text")))
            )
            option.font.setItalic(True)
            # Disabled items should not have hover/selected background
            option.palette.setBrush(QPalette.Highlight, QBrush(QColor("transparent")))
        else:
            # Handle selected/hover colors for enabled items
            if option.state & QStyle.State_Selected:
                option.palette.setBrush(
                    QPalette.Text, QBrush(QColor(self.theme.get_color("input_selection_text")))
                )
                option.palette.setBrush(
                    QPalette.Highlight,
                    QBrush(QColor(self.theme.get_color("combo_item_background_selected"))),
                )
            elif option.state & QStyle.State_MouseOver:
                option.palette.setBrush(
                    QPalette.Text, QBrush(QColor(self.theme.get_color("combo_text")))
                )
                option.palette.setBrush(
                    QPalette.Highlight,
                    QBrush(QColor(self.theme.get_color("combo_item_background_hover"))),
                )
            else:
                # Normal state
                option.palette.setBrush(
                    QPalette.Text, QBrush(QColor(self.theme.get_color("combo_text")))
                )
                option.palette.setBrush(QPalette.Highlight, QBrush(QColor("transparent")))


class FileTableHoverDelegate(QStyledItemDelegate):
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


class TreeViewItemDelegate(QStyledItemDelegate):
    """Custom delegate for TreeView items that properly handles background painting."""

    def __init__(self, parent=None, theme=None):
        super().__init__(parent)
        self.theme = theme
        logger.debug("[TreeViewItemDelegate] Initialized")

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        """Custom paint method that properly handles hierarchical items with precise background painting."""
        # Save original rect
        original_rect = option.rect

        # Get the item's indent level
        tree_view = self.parent()
        indent = tree_view.indentation() if tree_view else 20
        level = 0
        parent = index.parent()
        while parent.isValid():
            level += 1
            parent = parent.parent()

        branch_indicator_width = 16  # Usually 16px for the expand/collapse arrow

        # The left edge of the content (after indent and branch indicator)
        content_left = original_rect.left() + (level * indent) + branch_indicator_width

        # Get the text
        text = index.data(Qt.DisplayRole)
        if not text:
            super().paint(painter, option, index)
            return

        # Check if item is selectable (not a category)
        item_flags = index.flags()
        is_selectable = bool(item_flags & Qt.ItemIsSelectable)

        # Paint background only for selectable items (subcategories)
        if is_selectable:
            # Background rect: from content_left to the end of the row
            bg_rect = original_rect.adjusted(0, 1, 0, -1)
            bg_rect.setLeft(content_left)
            bg_rect.setRight(original_rect.right())

            # Paint background based on state
            if option.state & QStyle.State_Selected:
                bg_color = get_qcolor("combo_item_background_selected")
                painter.fillRect(bg_rect, bg_color)
            elif option.state & QStyle.State_MouseOver:
                bg_color = get_qcolor("combo_item_background_hover")
                painter.fillRect(bg_rect, bg_color)

        # Set text color based on state and item type
        if option.state & QStyle.State_Selected:
            text_color = get_qcolor("input_selection_text")
        elif not is_selectable:  # Categories
            text_color = get_qcolor("text_secondary")  # Dimmer color for categories
        else:
            text_color = get_qcolor("combo_text")

        # Draw the text
        painter.save()
        painter.setPen(text_color)

        # Text rect: from content_left + padding to the end of the row (with right padding)
        text_rect = original_rect.adjusted(0, 0, 0, 0)
        text_rect.setLeft(content_left + 4)
        text_rect.setRight(original_rect.right() - 4)

        painter.drawText(
            text_rect,
            Qt.AlignLeft | Qt.AlignVCenter,
            str(text),
        )
        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index):
        """Return size hint for items - make them same height as context menu items."""
        # Get the default size hint
        size = super().sizeHint(option, index)

        # Set a consistent, compact height similar to context menu items
        # Standard context menu items are usually around 22-24 pixels
        compact_height = 24

        # Keep the width but use compact height
        size.setHeight(compact_height)

        return size
