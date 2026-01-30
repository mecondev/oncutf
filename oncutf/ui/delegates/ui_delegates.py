"""Custom QStyledItemDelegate classes for enhanced UI components.

This module provides custom delegates for enhanced UI components:
- FileTableHoverDelegate: Full-row hover highlight for file tables
- ComboBoxItemDelegate: Themed styling for combobox dropdown items
- TreeViewItemDelegate: Hierarchical item painting with proper hover tracking

Author: Michael Economou
Date: 2025-05-22
"""

from typing import TYPE_CHECKING

from PyQt5.QtCore import QEvent, QModelIndex, Qt
from PyQt5.QtGui import QColor, QCursor, QIcon, QPainter, QPen
from PyQt5.QtWidgets import (
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableView,
    QTreeView,
    QWidget,
)

from oncutf.ui.theme_manager import get_theme_manager
from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.ui.theme_manager import ThemeManager

logger = get_cached_logger(__name__)


class ComboBoxItemDelegate(QStyledItemDelegate):
    """Custom delegate to render QComboBox dropdown items with theme and proper states.

    This delegate fully paints item backgrounds including alternating row colors,
    hover, and selection states. It ensures proper rendering on all platforms and
    DPI scaling scenarios.
    """

    def __init__(self, parent: QWidget | None = None, theme: "ThemeManager | None" = None) -> None:
        """Initialize the delegate with optional theme manager."""
        super().__init__(parent)
        self.theme = theme

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        """Paint combobox item with alternating backgrounds and state-aware colors.

        Paint order:
        1. Fill background (alternating, hover, or selected)
        2. Draw text with appropriate foreground color

        This ensures no gaps and proper alternating rows even with custom QSS.
        """
        if not self.theme:
            # Fallback to default painting if no theme available
            super().paint(painter, option, index)
            return

        painter.save()

        # --- Determine background and text colors based on state ---
        is_enabled = index.flags() & Qt.ItemFlag.ItemIsEnabled
        is_selected = option.state & QStyle.StateFlag.State_Selected
        is_hovered = option.state & QStyle.StateFlag.State_MouseOver
        is_odd_row = index.row() % 2 == 1

        # Background color logic with proper priority:
        # 1. Selected + Hover (highest priority)
        # 2. Selected (no hover)
        # 3. Hover (no selection)
        # 4. Alternating rows (normal state)
        # 5. Regular background (even rows, normal state)

        if not is_enabled:
            # Disabled items: use alternate_row background, dimmed text
            bg_color = QColor(self.theme.get_color("table_alternate"))
            text_color = QColor(self.theme.get_color("text_disabled"))
        elif is_selected and is_hovered:
            # Selected + Hover: light blue background, dark text
            bg_color = QColor(self.theme.get_color("selected_hover"))
            text_color = QColor(self.theme.get_color("selected_text"))
        elif is_selected:
            # Selected only: medium blue background, light text
            bg_color = QColor(self.theme.get_color("selected"))
            text_color = QColor(self.theme.get_color("text"))  # Light text on selected
        elif is_hovered:
            # Hover only (not selected): dark blue background, light text
            bg_color = QColor(self.theme.get_color("table_hover_bg"))
            text_color = QColor(self.theme.get_color("text"))
        elif is_odd_row:
            # Odd rows: alternating background for visual separation
            bg_color = QColor(self.theme.get_color("background_lighter"))
            text_color = QColor(self.theme.get_color("text"))
        else:
            # Even rows: regular menu background
            bg_color = QColor(self.theme.get_color("menu_background"))
            text_color = QColor(self.theme.get_color("text"))

        # --- Paint background (fill entire rect to avoid gaps) ---
        painter.fillRect(option.rect, bg_color)

        # --- Paint text ---
        painter.setPen(text_color)

        # Use theme font for consistency
        font = painter.font()
        font.setFamily(self.theme.fonts["base_family"])
        font.setPointSize(int(self.theme.fonts["interface_size"].replace("pt", "")))
        if not is_enabled:
            font.setItalic(True)
        painter.setFont(font)

        # Draw text with padding (matches QSS padding: 0px 8px)
        text_rect = option.rect.adjusted(8, 0, -8, 0)
        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        painter.drawText(
            text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text
        )

        painter.restore()

    def initStyleOption(self, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        """Initialize style option with theme fonts.

        Note: Background colors are now handled in paint(), so we don't set
        palette brushes here. This method only configures fonts.
        """
        super().initStyleOption(option, index)

        if not self.theme:
            return

        # Use font from theme for absolute consistency
        option.font.setFamily(self.theme.fonts["base_family"])
        option.font.setPointSize(int(self.theme.fonts["interface_size"].replace("pt", "")))

        # Italic for disabled items
        if not (index.flags() & Qt.ItemFlag.ItemIsEnabled):
            option.font.setItalic(True)

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex):
        """Return proper size hint for dropdown items to prevent overlap.

        This ensures each item has sufficient height in the dropdown menu.
        """
        # Get the default size hint
        size = super().sizeHint(option, index)

        # Set consistent height from theme (using combo_item_height for dropdown items)
        if self.theme:
            item_height = self.theme.get_constant("combo_item_height")
            size.setHeight(item_height)

        return size


class FileTableHoverDelegate(QStyledItemDelegate):
    """Custom delegate for file table items with full-row hover highlighting."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the hover delegate.

        Args:
            parent: The parent widget.

        """
        super().__init__(parent)
        self.hovered_row: int = -1

        # Get colors from theme system
        theme = get_theme_manager()
        self.hover_color: QColor = QColor(theme.get_color("table_hover_bg"))

    def update_hover_row(self, row: int) -> None:
        """Update the row that should be highlighted on hover."""
        self.hovered_row = row

    def leaveEvent(self, event) -> None:
        """Handle mouse leave events to hide tooltips."""
        # Hide any active tooltips when mouse leaves the delegate
        from oncutf.ui.helpers.tooltip_helper import TooltipHelper

        parent_widget = self.parent()
        if isinstance(parent_widget, QWidget):
            TooltipHelper.clear_tooltips_for_widget(parent_widget)

        # Note: QStyledItemDelegate doesn't have leaveEvent, this is for compatibility

    def enterEvent(self, event) -> None:
        """Handle mouse enter events to restore hover state."""
        # Update hover state when mouse enters the delegate
        table = self.parent()
        if isinstance(table, QTableView):
            viewport = table.viewport()
            if viewport:
                pos = viewport.mapFromGlobal(QCursor.pos())
                index = table.indexAt(pos)
                hovered_row = index.row() if index.isValid() else -1
                self.update_hover_row(hovered_row)

        # Note: QStyledItemDelegate doesn't have enterEvent, this is for compatibility

    def focusOutEvent(self, event) -> None:
        """Handle focus loss events to hide tooltips."""
        # Hide any active tooltips when focus is lost
        from oncutf.ui.helpers.tooltip_helper import TooltipHelper

        parent_widget = self.parent()
        if isinstance(parent_widget, QWidget):
            TooltipHelper.clear_tooltips_for_widget(parent_widget)

        # Note: QStyledItemDelegate doesn't have focusOutEvent, this is for compatibility

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        """Custom painting for full-row hover and selection with proper icon handling.

        Features:
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
        if option.state & QStyle.StateFlag.State_HasFocus:
            option.state &= ~QStyle.StateFlag.State_HasFocus

        selection_model = table.selectionModel() if table else None
        is_selected = selection_model is not None and selection_model.isSelected(index)
        is_hovered = row == self.hovered_row

        # Determine background color in priority order:
        # 1. Selection + Hover
        # 2. Selection
        # 3. Hover
        # 4. Alternate row color
        # 5. Default background

        theme = get_theme_manager()
        background_color = None
        if is_selected and is_hovered:
            # Selected + hovered: slightly lighter than normal selection
            background_color = QColor(theme.get_color("selected_hover"))
        elif is_selected:
            # Normal selection color
            background_color = QColor(theme.get_color("table_selection_bg"))
        elif is_hovered:
            # Hover color - paint over alternate background
            background_color = self.hover_color
        elif row % 2 == 1:
            # Alternate row color for odd rows (only if not selected/hovered)
            background_color = QColor(theme.get_color("table_alternate"))
        # For even rows, use default background (no painting needed)

        if background_color:
            painter.save()
            painter.fillRect(option.rect, background_color)
            painter.restore()

        # Draw border for selected rows (only on the last column to avoid overlaps)
        if is_selected and model and column == model.columnCount() - 1:
            painter.save()
            border_color = QColor(theme.get_color("table_selection_bg")).darker(130)
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
            icon_data = model.data(index, Qt.ItemDataRole.DecorationRole)
            if icon_data and isinstance(icon_data, QIcon):
                # Check if this is a combined icon (wider than tall) or single icon
                icon_size = icon_data.actualSize(option.rect.size())

                if icon_size.width() > icon_size.height():
                    # Combined icon - use wider rect with minimal padding
                    icon_rect = option.rect.adjusted(1, 3, -1, -3)
                else:
                    # Single icon - use square rect with normal padding
                    icon_rect = option.rect.adjusted(2, 3, -2, -3)

                icon_data.paint(painter, icon_rect, Qt.AlignmentFlag.AlignCenter)

            # Don't call super().paint() for column 0 since we handled the icon ourselves
            return

            # For all other columns, paint everything manually - no super().paint()
        display_text = model.data(index, Qt.ItemDataRole.DisplayRole) if model else ""
        if display_text:
            # Determine text color based on selection and hover state
            theme = get_theme_manager()
            if is_selected and is_hovered:
                # Selected + hovered: dark text for light blue background
                text_color = QColor(theme.get_color("table_selection_text"))
            else:
                # All other cases (normal, hover only, selected only): light text
                text_color = QColor(theme.get_color("text"))

            painter.save()
            painter.setPen(text_color)

            text_rect = option.rect.adjusted(
                4, 1, -4, -1
            )  # Horizontal and vertical padding for centering

            alignment = (
                model.data(index, Qt.ItemDataRole.TextAlignmentRole)
                if model
                else Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
            if not alignment:
                alignment = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

            # Ensure alignment is usable (convert from QVariant if needed)
            if hasattr(alignment, "value"):  # QVariant case
                alignment = alignment.value()
            # Qt.Alignment objects can be used directly with drawText
            # Only fallback to default if alignment is None or invalid
            if alignment is None:
                alignment = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

            fm = painter.fontMetrics()
            elided = fm.elidedText(
                str(display_text), Qt.TextElideMode.ElideRight, text_rect.width()
            )
            painter.drawText(text_rect, alignment, elided)
            painter.restore()


class TreeViewItemDelegate(QStyledItemDelegate):
    """Custom delegate for TreeView items that properly handles background painting."""

    def __init__(self, parent: QWidget | None = None, theme: "ThemeManager | None" = None) -> None:
        """Initialize the delegate with optional theme manager and hover tracking."""
        super().__init__(parent)
        self.theme = theme
        self.hovered_index: QModelIndex | None = None
        self._tree_view: QTreeView | None = None
        self._guard_warning_logged = False
        logger.debug("[TreeViewItemDelegate] Initialized")

    def install_event_filter(self, tree_view: QTreeView) -> None:
        """Install event filter for hover tracking (full-row).

        We listen on the viewport for mouse move/leave, and we force a repaint
        of the whole row by keeping track of the hovered index.
        """
        self._tree_view = tree_view
        viewport = tree_view.viewport()
        if viewport:
            viewport.setMouseTracking(True)
            viewport.installEventFilter(self)

    def eventFilter(self, obj: QWidget, event: QEvent) -> bool:
        """Handle mouse events for hover tracking."""
        if event.type() == QEvent.Type.Leave or event.type() == QEvent.Type.HoverLeave:
            self.hovered_index = None
            obj.update()
        elif event.type() == QEvent.Type.MouseMove and self._tree_view:
            pos = event.pos()
            index = self._tree_view.indexAt(pos)
            # Unify hover per row by tracking the first column sibling
            self.hovered_index = index.sibling(index.row(), 0) if index.isValid() else None
            obj.update()
        return False

    def update_hover_row(self, row: int) -> None:
        """Update hover row state (no-op, kept for compatibility)."""

    def _log_guard_warning(self, message: str) -> None:
        """Log guard-triggered warnings only once per delegate instance."""
        if not self._guard_warning_logged:
            logger.debug(
                "[TreeViewItemDelegate] Paint guard triggered: %s",
                message,
                extra={"dev_only": True},
            )
            self._guard_warning_logged = True

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        """Simplified paint - let QSS handle backgrounds, we handle text colors only."""
        # Just use the default painting - QSS handles hover/selection backgrounds
        super().paint(painter, option, index)

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex):
        """Return size hint for items - uses table_row_height from theme."""
        # Get the default size hint
        size = super().sizeHint(option, index)

        # Set a consistent height from theme (same as table rows)
        theme = get_theme_manager()
        row_height = theme.get_constant("table_row_height")

        # Keep the width but use theme height
        size.setHeight(row_height)

        return size


class MetadataTreeItemDelegate(TreeViewItemDelegate):
    """TreeView delegate for metadata tree with custom foreground colors.

    Features:
    - Full-row hover/selection backgrounds
    - Respects ForegroundRole for modified keys (yellow #ffe343 + bold)
    - Dimmed text for root group headers (from theme token)
    - Text visible in all states (normal, hover, selected)
    """

    def initStyleOption(self, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        """Initialize style option and force bold font for modified items."""
        super().initStyleOption(option, index)

        # Check if this is a modified key (has custom foreground)
        # If so, force bold font
        custom_fg = index.data(Qt.ItemDataRole.ForegroundRole)
        if custom_fg is not None:
            option.font.setBold(True)
        elif not index.parent().isValid():
            # Root-level group headers only: use dimmed color from theme
            from PyQt5.QtGui import QColor, QPalette

            from oncutf.ui.theme_manager import ThemeManager

            theme = ThemeManager()
            group_color = theme.get_color("metadata_group_text")
            option.palette.setColor(QPalette.ColorRole.Text, QColor(group_color))

        # Set vertical alignment to center for all items
        option.displayAlignment = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
