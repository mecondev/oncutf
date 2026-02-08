"""Drag Overlay Widget - Floating info label for external drag operations.

Author: Michael Economou
Date: 2026-02-08

Provides visual feedback for external drag & drop operations when cursor
control is not available (dragging from file explorer).
"""

from PyQt5.QtCore import QPoint, QSize, Qt, QTimer
from PyQt5.QtGui import QColor, QCursor, QFont, QFontMetrics, QIcon, QPainter, QPainterPath, QPixmap
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QLabel, QSizePolicy, QWidget

from oncutf.config import ICON_SIZES
from oncutf.ui.services.icon_service import get_menu_icon
from oncutf.ui.theme_manager import get_theme_manager
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class IconComposite(QWidget):
    """Container widget for main icon with action icon overlays.

    Displays a base icon (file/folder) with action icons positioned below,
    compactly overlapping for visual hierarchy.
    """

    def __init__(self, parent: QWidget | None = None):
        """Initialize icon composite container."""
        super().__init__(parent)

        # Container size: expanded width for action icons, fixed height to avoid vertical shift
        # Two icons: 18 (base) + 12 (spacing) + 18 (icon width) = 48
        # One icon: 18 (base) + 18 (icon width) + 2 (padding) = 38
        # Height: 32 (main icon) + 14 (partial action icon) = 46
        self._expanded_size = QSize(48, 46)
        self._single_icon_size = QSize(38, 46)
        self._compact_size = QSize(ICON_SIZES["LARGE"], 46)
        self.setFixedSize(self._expanded_size)

        # Main icon label (base layer)
        self._main_icon_label = QLabel(self)
        self._main_icon_label.setFixedSize(ICON_SIZES["LARGE"], ICON_SIZES["LARGE"])
        self._main_icon_label.move(0, 0)

        # Action icon labels (overlay layer) - positioned below and to the right
        # Using 18px size for compact overlay that fits 2 icons with overlap
        self._action_icon_size = 18

        # First action icon (e.g., "add" for merge)
        self._action_label_1 = QLabel(self)
        self._action_label_1.setFixedSize(self._action_icon_size, self._action_icon_size)
        self._action_label_1.hide()

        # Second action icon (e.g., "stacks" for recursive)
        self._action_label_2 = QLabel(self)
        self._action_label_2.setFixedSize(self._action_icon_size, self._action_icon_size)
        self._action_label_2.hide()

    def set_main_icon(self, pixmap: QPixmap) -> None:
        """Set the main icon pixmap."""
        self._main_icon_label.setPixmap(pixmap)

    def set_action_icons(self, action_pixmaps: list[QPixmap]) -> None:
        """Set action icon overlays positioned below main icon.

        Icons are positioned compactly with large overlap when 2 icons present.
        Single icon appears at same position as leftmost icon in 2-icon layout.

        Args:
            action_pixmaps: List of pixmaps for action icons (max 2)

        """
        # Hide both action icons first
        self._action_label_1.hide()
        self._action_label_2.hide()

        if len(action_pixmaps) == 0:
            self.setFixedSize(self._compact_size)
            return

        if len(action_pixmaps) == 1:
            self.setFixedSize(self._single_icon_size)
        else:
            self.setFixedSize(self._expanded_size)

        # Position icons below and to the right of main icon
        # Main icon is 32x32, action icons are 18x18
        # Place at y=28 (32 - 4px overlap) to sit below main icon with small overlap
        y_pos = 28
        # Base x position for icons - shifted more to the right
        x_base = 18
        overlap = 4  # Less overlap for more spacing between icons

        if len(action_pixmaps) == 1:
            # Single icon at base position (where leftmost icon would be with 2)
            self._action_label_1.move(x_base, y_pos)
            self._action_label_1.setPixmap(action_pixmaps[0])
            self._action_label_1.show()
            self._action_label_1.raise_()  # Ensure overlay is on top
        else:
            # Two icons with spacing between them
            # First icon (leftmost) at base position
            x1 = x_base
            self._action_label_1.move(x1, y_pos)
            self._action_label_1.setPixmap(action_pixmaps[0])
            self._action_label_1.show()
            self._action_label_1.raise_()  # Ensure overlay is on top

            # Second icon (rightmost) with more spacing
            x2 = x1 + (self._action_icon_size - overlap)
            self._action_label_2.move(x2, y_pos)
            self._action_label_2.setPixmap(action_pixmaps[1])
            self._action_label_2.show()
            self._action_label_2.raise_()  # Ensure overlay is on top


class OverlayText(QWidget):
    """Lightweight text widget rendered with paintEvent for precise positioning."""

    def __init__(self, parent: QWidget | None = None):
        """Initialize overlay text widget."""
        super().__init__(parent)
        self._text = ""
        self._color = Qt.white
        self._font = QFont("Inter", 10, QFont.DemiBold)
        self._padding_left = 0
        self._padding_top = 0
        self._padding_right = 0
        self._padding_bottom = 0
        self._baseline_offset = 0
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

    def set_text(self, text: str) -> None:
        if self._text != text:
            self._text = text
            self.updateGeometry()
            self.update()

    def set_color(self, color: str | QColor) -> None:
        next_color = QColor(color) if isinstance(color, str) else color
        if self._color != next_color:
            self._color = next_color
            self.update()

    def set_font(self, font: QFont) -> None:
        self._font = font
        self.updateGeometry()
        self.update()

    def set_baseline_offset(self, offset: int) -> None:
        if self._baseline_offset != offset:
            self._baseline_offset = offset
            self.update()

    def sizeHint(self) -> QSize:
        metrics = QFontMetrics(self._font)
        width = metrics.horizontalAdvance(self._text)
        height = metrics.height()
        width += self._padding_left + self._padding_right
        height += self._padding_top + self._padding_bottom
        return QSize(width, height)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        painter.setPen(self._color)
        painter.setFont(self._font)

        metrics = QFontMetrics(self._font)
        x = self._padding_left
        y = self._padding_top + metrics.ascent() + self._baseline_offset
        painter.drawText(x, y, self._text)


class DragOverlay(QWidget):
    """Floating widget that follows cursor during external drag operations.

    Displays file/folder counts and modifier state information with icons.
    """

    def __init__(self, parent: QWidget | None = None):
        """Initialize drag overlay.

        Args:
            parent: Parent widget (usually main window)

        """
        # Create as top-level window (no parent) to avoid rendering issues
        super().__init__(None)

        # Setup widget properties
        self.setWindowFlags(
            Qt.Window  # Top-level window
            | Qt.FramelessWindowHint  # No frame
            | Qt.WindowStaysOnTopHint  # Always on top
            | Qt.Tool  # Tool window (no taskbar)
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)  # Don't steal focus
        self.setAttribute(Qt.WA_TransparentForMouseEvents)  # Pass mouse events through

        # Create layout with icon composite and text
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(8, 6, 8, 6)
        self._layout.setSpacing(6)  # Default spacing (will be adjusted dynamically)

        # Icon composite (main icon + action overlays)
        self._icon_composite = IconComposite()
        self._layout.addWidget(self._icon_composite, 0, Qt.AlignVCenter)

        # Text widget rendered via paintEvent (no margins)
        self._text_widget = OverlayText()
        self._layout.addWidget(self._text_widget, 0, Qt.AlignVCenter)

        # Theme manager for dynamic colors
        self._theme_manager = get_theme_manager()
        self._theme_manager.theme_changed.connect(self._update_theme_colors)

        # Apply initial theme colors
        self._update_theme_colors()

        # State
        self._info_text = ""
        self._modifier_text = ""
        self._drag_type = None  # Will be set when showing
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._update_position)
        self._update_timer.setInterval(16)  # ~60 FPS

        # Initially hidden
        self.hide()

    def show_for_drag(self, info_text: str, drag_type: str = "multiple") -> None:
        """Show overlay with drag information.

        Args:
            info_text: Text to display (e.g., "5 files")
            drag_type: Type of drag ("file", "folder", "multiple")

        """
        self._info_text = info_text
        self._drag_type = drag_type
        self._update_display()
        self._update_position()
        self.raise_()  # Bring to front
        self.show()
        self._update_timer.start()
        logger.info("[DragOverlay] Showing with text: %s, type: %s", info_text, drag_type)

    def update_modifier(self, modifier_text: str) -> None:
        """Update modifier state display.

        Args:
            modifier_text: Modifier description (e.g., "Merge + Recursive")

        """
        if self._modifier_text != modifier_text:
            self._modifier_text = modifier_text
            self._update_display()

    def hide_overlay(self) -> None:
        """Hide the overlay."""
        self._update_timer.stop()
        self.hide()
        logger.info("[DragOverlay] Hidden")

    def _update_theme_colors(self) -> None:
        """Update colors based on current theme."""
        text_color = self._theme_manager.get_color("text")

        # Update text label style with theme color
        font = QFont("Inter", 10)
        font.setWeight(QFont.DemiBold)
        self._text_widget.set_font(font)
        self._text_widget.set_color(text_color)

        # Update widget style - transparent background
        self.setStyleSheet(
            """
            QWidget {
                background-color: transparent;
                border: none;
            }
            """
        )

        logger.debug(
            "[DragOverlay] Updated theme colors: text=%s", text_color, extra={"dev_only": True}
        )

    def _update_display(self) -> None:
        """Update the displayed text and icons."""
        # Update main icon based on drag type (LARGE size like file tree)
        if self._drag_type == "folder":
            icon_name = "folder"
        elif self._drag_type == "file":
            icon_name = "draft"
        else:
            icon_name = "content_copy"

        icon = get_menu_icon(icon_name)
        if not icon.isNull():
            main_pixmap = icon.pixmap(ICON_SIZES["LARGE"], ICON_SIZES["LARGE"])
            self._icon_composite.set_main_icon(main_pixmap)

        # Update text (show only info text, no modifier text)
        self._text_widget.set_text(self._info_text)

        # Update action icons based on modifier (18px size for compact overlay)
        action_icons = []
        if "Ctrl+Shift" in self._modifier_text:
            action_icons = ["add", "stacks"]  # Merge + Recursive
        elif "Shift" in self._modifier_text:
            action_icons = ["add"]  # Merge
        elif "Ctrl" in self._modifier_text:
            action_icons = ["stacks"]  # Recursive

        # Create action pixmaps with 18px size
        action_pixmaps = []
        for icon_name in action_icons:
            icon = get_menu_icon(icon_name)
            if not icon.isNull():
                pixmap = icon.pixmap(18, 18)
                action_pixmaps.append(pixmap)

        # Set action overlays
        self._icon_composite.set_action_icons(action_pixmaps)

        # Dynamic spacing based on mod icons presence
        if len(action_pixmaps) > 0:
            # With mod icons: more spacing and less horizontal offset
            self._layout.setSpacing(6)
        else:
            # Without mod icons: minimal spacing and more horizontal offset
            self._layout.setSpacing(-15)

        self._text_widget.set_baseline_offset(-4)

        self.adjustSize()

    def _update_position(self) -> None:
        """Update position to follow cursor at same height."""
        cursor_pos = QCursor.pos()

        # Position at cursor height, offset to the right
        offset_x = 25
        offset_y = -self.height() // 2  # Center vertically with cursor

        # Calculate position
        x = cursor_pos.x() + offset_x
        y = cursor_pos.y() + offset_y

        # Keep within screen bounds
        screen = QApplication.desktop().screenGeometry()
        if x + self.width() > screen.right():
            x = cursor_pos.x() - self.width() - 10
        if y < screen.top():
            y = screen.top() + 5
        if y + self.height() > screen.bottom():
            y = screen.bottom() - self.height() - 5

        self.move(x, y)
        self.raise_()  # Keep on top


class DragOverlayManager:
    """Singleton manager for drag overlay widget."""

    _instance: "DragOverlayManager | None" = None
    _overlay: DragOverlay | None = None

    @classmethod
    def get_instance(cls) -> "DragOverlayManager":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def initialize(self, parent: QWidget) -> None:
        """Initialize overlay widget with parent.

        Args:
            parent: Parent widget (main window)

        """
        if self._overlay is None:
            self._overlay = DragOverlay(parent)
            logger.debug("[DragOverlayManager] Initialized", extra={"dev_only": True})

    def show_drag_info(self, info_text: str, drag_type: str = "multiple") -> None:
        """Show drag information overlay.

        Args:
            info_text: Information to display
            drag_type: Type of drag ("file", "folder", "multiple")

        """
        if self._overlay is not None:
            self._overlay.show_for_drag(info_text, drag_type)

    def update_modifier_info(self, modifier_text: str) -> None:
        """Update modifier information.

        Args:
            modifier_text: Modifier state description

        """
        if self._overlay is not None:
            self._overlay.update_modifier(modifier_text)

    def hide_overlay(self) -> None:
        """Hide the overlay."""
        if self._overlay is not None:
            self._overlay.hide_overlay()

    def is_visible(self) -> bool:
        """Check if overlay is visible."""
        return self._overlay is not None and self._overlay.isVisible()
