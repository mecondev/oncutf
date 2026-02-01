"""Thumbnail Delegate for rendering file thumbnails in grid view.

Author: Michael Economou
Date: 2026-01-16

Renders thumbnails with:
- Rectangle frame (photo slide style, 3px border)
- Thumbnail image centered with aspect ratio fit
- Filename word-wrapped below thumbnail
- Color flag indicator (top-left, 12px circle)
- Video duration badge (bottom-right, semi-transparent)
- Loading spinner for generating thumbnails
- Placeholder for failed/missing thumbnails
- Hover and selection visual feedback
"""

from typing import TYPE_CHECKING

from PyQt5.QtCore import QRect, QRectF, QSize, Qt
from PyQt5.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QPen,
    QPixmap,
)
from PyQt5.QtWidgets import QStyle, QStyledItemDelegate

from oncutf.config import METADATA_ICON_COLORS
from oncutf.models.file_item import FileItem
from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from PyQt5.QtCore import QModelIndex
    from PyQt5.QtWidgets import QStyleOptionViewItem, QWidget

logger = get_cached_logger(__name__)


class ThumbnailDelegate(QStyledItemDelegate):
    """Custom delegate for rendering file thumbnails in grid view.

    Displays:
    - Framed thumbnail with photo slide border
    - Color flag indicator (if set)
    - Video duration badge (for videos)
    - Filename below thumbnail
    - Loading/placeholder states

    Visual states:
    - Normal: Standard border
    - Hover: Highlighted border + tooltip
    - Selected: Distinct glow + semi-transparent background
    """

    # Layout constants (in pixels)
    FRAME_BORDER_WIDTH = 3
    FRAME_PADDING = 8  # Space between frame and thumbnail
    FILENAME_HEIGHT = 40  # Space below thumbnail for filename
    FILENAME_MARGIN = 8  # Vertical margin above filename

    # Metadata/Hash indicators (2 circles in top corners)
    INDICATOR_CIRCLE_SIZE = 12  # Diameter of each circle
    INDICATOR_MARGIN = 8  # Distance from corners of frame
    INDICATOR_BORDER_WIDTH = 2  # Border width for outline style

    COLOR_FLAG_SIZE = 12  # Diameter of color flag circle (deprecated, use indicators)
    COLOR_FLAG_MARGIN = 4  # Distance from top-left corner
    VIDEO_BADGE_MARGIN = 4  # Distance from bottom-right corner
    VIDEO_BADGE_PADDING = 4  # Padding inside badge

    # Colors
    FRAME_COLOR_NORMAL = QColor(200, 200, 200)
    FRAME_COLOR_HOVER = QColor(100, 150, 255)
    FRAME_COLOR_SELECTED = QColor(50, 120, 255)
    BACKGROUND_COLOR_SELECTED = QColor(50, 120, 255, 40)  # Semi-transparent
    VIDEO_BADGE_BACKGROUND = QColor(0, 0, 0, 180)  # Semi-transparent black
    VIDEO_BADGE_TEXT = QColor(255, 255, 255)
    PLACEHOLDER_BACKGROUND = QColor(240, 240, 240)
    PLACEHOLDER_TEXT = QColor(150, 150, 150)

    def __init__(self, parent: "QWidget | None" = None):
        """Initialize the thumbnail delegate.

        Args:
            parent: Parent widget

        """
        super().__init__(parent)
        self._thumbnail_size = 128  # Default size, will be set from viewport

    def set_thumbnail_size(self, size: int) -> None:
        """Set the thumbnail size for rendering.

        Args:
            size: Thumbnail size in pixels (applies to both width and height)

        """
        self._thumbnail_size = size
        logger.debug("[ThumbnailDelegate] Thumbnail size set to: %d", size)

    def sizeHint(self, option: "QStyleOptionViewItem", index: "QModelIndex") -> QSize:
        """Calculate the size hint for a thumbnail item.

        Returns the total size including frame, padding, thumbnail, and filename.

        Args:
            option: Style options
            index: Model index

        Returns:
            Size hint for the item

        """
        # Total width: border + padding + thumbnail + padding + border
        width = self.FRAME_BORDER_WIDTH * 2 + self.FRAME_PADDING * 2 + self._thumbnail_size

        # Total height: border + padding + thumbnail + padding + filename + border
        height = (
            self.FRAME_BORDER_WIDTH * 2
            + self.FRAME_PADDING * 2
            + self._thumbnail_size
            + self.FILENAME_MARGIN
            + self.FILENAME_HEIGHT
        )

        return QSize(width, height)

    def paint(
        self,
        painter: QPainter,
        option: "QStyleOptionViewItem",
        index: "QModelIndex",
    ) -> None:
        """Render a thumbnail item.

        Args:
            painter: QPainter for rendering
            option: Style options (includes hover/selection state)
            index: Model index

        """
        logger.debug("[ThumbnailDelegate] paint() called for index row=%d", index.row())
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        # Get file item from model
        file_item = index.data(Qt.UserRole)
        if not isinstance(file_item, FileItem):
            logger.warning("[ThumbnailDelegate] Invalid data at index %s", index)
            painter.restore()
            return

        # Determine visual state
        is_selected = option.state & QStyle.State_Selected
        is_hover = option.state & QStyle.State_MouseOver

        # Draw selection background (behind everything)
        if is_selected:
            painter.fillRect(option.rect, self.BACKGROUND_COLOR_SELECTED)

        # Calculate layout rects
        frame_rect = self._calculate_frame_rect(option.rect)
        thumbnail_rect = self._calculate_thumbnail_rect(frame_rect)
        filename_rect = self._calculate_filename_rect(option.rect, frame_rect)

        # Draw frame border with color tinting
        self._draw_frame(painter, frame_rect, file_item, is_selected, is_hover)

        # Draw thumbnail or placeholder
        # Use Qt.UserRole + 1 for thumbnail pixmaps (separate from status icons)
        thumbnail_pixmap = index.data(Qt.UserRole + 1)
        if isinstance(thumbnail_pixmap, QPixmap) and not thumbnail_pixmap.isNull():
            logger.debug("[ThumbnailDelegate] Drawing actual thumbnail for row=%d", index.row())
            self._draw_thumbnail(painter, thumbnail_rect, thumbnail_pixmap)
        else:
            logger.debug(
                "[ThumbnailDelegate] Drawing placeholder for row=%d (pixmap=%s)",
                index.row(),
                type(thumbnail_pixmap).__name__,
            )
            self._draw_placeholder(painter, thumbnail_rect, file_item)

        # Draw metadata/hash indicators (two circles, top-left)
        self._draw_metadata_indicators(painter, frame_rect, file_item)

        # Draw video duration badge (if video)
        duration = getattr(file_item, "duration", None)
        if duration:
            self._draw_video_badge(painter, frame_rect, duration)

        # Draw filename
        self._draw_filename(painter, filename_rect, file_item.filename, is_selected)

        painter.restore()

    def _calculate_frame_rect(self, item_rect: QRect) -> QRect:
        """Calculate the rectangle for the thumbnail frame.

        Args:
            item_rect: Full item rectangle

        Returns:
            Frame rectangle (excludes filename area)

        """
        frame_size = self.FRAME_BORDER_WIDTH * 2 + self.FRAME_PADDING * 2 + self._thumbnail_size

        # Center horizontally
        x = item_rect.left() + (item_rect.width() - frame_size) // 2
        y = item_rect.top()

        return QRect(x, y, frame_size, frame_size)

    def _calculate_thumbnail_rect(self, frame_rect: QRect) -> QRect:
        """Calculate the rectangle for the thumbnail image (inside frame).

        Args:
            frame_rect: Frame rectangle

        Returns:
            Thumbnail rectangle (centered in frame with padding)

        """
        x = frame_rect.left() + self.FRAME_BORDER_WIDTH + self.FRAME_PADDING
        y = frame_rect.top() + self.FRAME_BORDER_WIDTH + self.FRAME_PADDING

        return QRect(x, y, self._thumbnail_size, self._thumbnail_size)

    def _calculate_filename_rect(self, item_rect: QRect, frame_rect: QRect) -> QRect:
        """Calculate the rectangle for the filename text.

        Args:
            item_rect: Full item rectangle
            frame_rect: Frame rectangle

        Returns:
            Filename rectangle (below frame)

        """
        y = frame_rect.bottom() + self.FILENAME_MARGIN
        height = self.FILENAME_HEIGHT

        return QRect(item_rect.left(), y, item_rect.width(), height)

    def _draw_frame(
        self,
        painter: QPainter,
        frame_rect: QRect,
        file_item: FileItem,
        is_selected: bool,
        is_hover: bool,
    ) -> None:
        """Draw the thumbnail frame border with optional color tinting.

        If file has a color flag set, the frame border and background are tinted
        with that color. Otherwise, standard theme colors are used.

        Args:
            painter: QPainter
            frame_rect: Frame rectangle
            file_item: File item (for color flag)
            is_selected: Whether item is selected
            is_hover: Whether item is hovered

        """
        # Check if file has a color flag
        has_color = file_item.color and file_item.color.lower() != "none"

        if has_color:
            # Parse color flag
            color = QColor(file_item.color)
            if not color.isValid():
                color = self.FRAME_COLOR_NORMAL

            # Use color flag for border (slightly brighter on hover/selection)
            if is_selected:
                # Brighten color for selection
                border_color = color.lighter(120)
            elif is_hover:
                # Slightly brighten for hover
                border_color = color.lighter(110)
            else:
                border_color = color

            # Background tint (10% opacity of color flag)
            bg_color = QColor(color)
            bg_color.setAlpha(25)  # ~10% opacity
        else:
            # No color flag - use standard theme colors
            if is_selected:
                border_color = self.FRAME_COLOR_SELECTED
            elif is_hover:
                border_color = self.FRAME_COLOR_HOVER
            else:
                border_color = self.FRAME_COLOR_NORMAL

            bg_color = Qt.white

        # Draw background fill
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(bg_color))
        painter.drawRect(frame_rect)

        # Draw border
        pen = QPen(border_color, self.FRAME_BORDER_WIDTH)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(frame_rect)

    def _draw_thumbnail(
        self,
        painter: QPainter,
        thumbnail_rect: QRect,
        pixmap: QPixmap,
    ) -> None:
        """Draw the thumbnail image, scaled to fit with aspect ratio.

        Args:
            painter: QPainter
            thumbnail_rect: Target rectangle for thumbnail
            pixmap: Thumbnail pixmap

        """
        # Scale pixmap to fit rectangle while preserving aspect ratio
        scaled_pixmap = pixmap.scaled(
            thumbnail_rect.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

        # Center in thumbnail rect
        x = thumbnail_rect.left() + (thumbnail_rect.width() - scaled_pixmap.width()) // 2
        y = thumbnail_rect.top() + (thumbnail_rect.height() - scaled_pixmap.height()) // 2

        painter.drawPixmap(x, y, scaled_pixmap)

    def _draw_placeholder(
        self,
        painter: QPainter,
        thumbnail_rect: QRect,
        file_item: FileItem,
    ) -> None:
        """Draw a placeholder for missing/loading thumbnails.

        Args:
            painter: QPainter
            thumbnail_rect: Target rectangle
            file_item: File item (for extension/type info)

        """
        # Draw background
        painter.fillRect(thumbnail_rect, self.PLACEHOLDER_BACKGROUND)

        # Draw text (file extension or "Loading...")
        painter.setPen(self.PLACEHOLDER_TEXT)
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)

        # Use file extension as placeholder text
        ext = file_item.filename.rsplit(".", 1)[-1].upper() if "." in file_item.filename else "FILE"
        text = f".{ext}\nLoading..."

        painter.drawText(thumbnail_rect, Qt.AlignCenter, text)

    def _draw_color_flag(
        self,
        painter: QPainter,
        frame_rect: QRect,
        color_name: str,
    ) -> None:
        """Draw the color flag indicator circle.

        DEPRECATED: This method is kept for compatibility.
        Use _draw_metadata_indicators() instead which shows metadata/hash status.

        Args:
            painter: QPainter
            frame_rect: Frame rectangle (flag drawn at top-left)
            color_name: Color name (e.g., "red", "blue", "#FF0000")

        """
        # Calculate position (top-left corner with margin)
        center_x = frame_rect.left() + self.COLOR_FLAG_MARGIN + self.COLOR_FLAG_SIZE // 2
        center_y = frame_rect.top() + self.COLOR_FLAG_MARGIN + self.COLOR_FLAG_SIZE // 2

        # Parse color (handle both named colors and hex)
        color = QColor(color_name)
        if not color.isValid():
            # Fallback to gray if color parsing fails
            color = QColor(128, 128, 128)

        # Draw circle with border
        painter.setPen(QPen(Qt.white, 2))
        painter.setBrush(QBrush(color))
        painter.drawEllipse(
            center_x - self.COLOR_FLAG_SIZE // 2,
            center_y - self.COLOR_FLAG_SIZE // 2,
            self.COLOR_FLAG_SIZE,
            self.COLOR_FLAG_SIZE,
        )

    def _draw_metadata_indicators(
        self,
        painter: QPainter,
        frame_rect: QRect,
        file_item: FileItem,
    ) -> None:
        """Draw metadata and hash status indicators (2 circles in top corners).

        Top-left circle: Metadata status
        - No metadata: dark gray outline (#404040)
        - Fast metadata loaded: green filled (#51cf66)
        - Extended metadata loaded: yellowish-orange filled (#fabf65)

        Top-right circle: Hash status
        - No hash: dark gray outline (#404040)
        - Hash cached: pink-purple filled (#ce93d8)

        Args:
            painter: QPainter
            frame_rect: Frame rectangle
            file_item: File item with metadata/hash status

        """
        # Determine metadata status color and style
        metadata_status = getattr(file_item, "metadata_status", "none")
        if metadata_status == "extended":
            metadata_color_hex = METADATA_ICON_COLORS["extended"]
            metadata_filled = True
        elif metadata_status in ("loaded", "modified"):
            metadata_color_hex = METADATA_ICON_COLORS["loaded"]
            metadata_filled = True
        else:
            metadata_color_hex = METADATA_ICON_COLORS["none"]
            metadata_filled = False  # Outline for none

        # Determine hash status color and style
        hash_value = getattr(file_item, "hash_value", None)
        if hash_value:
            hash_color_hex = METADATA_ICON_COLORS["hash"]
            hash_filled = True
        else:
            hash_color_hex = METADATA_ICON_COLORS["none"]
            hash_filled = False  # Outline for none

        # Draw metadata circle (top-left corner)
        self._draw_status_circle(
            painter,
            frame_rect,
            "top-left",
            metadata_color_hex,
            metadata_filled,
        )

        # Draw hash circle (top-right corner)
        self._draw_status_circle(
            painter,
            frame_rect,
            "top-right",
            hash_color_hex,
            hash_filled,
        )

    def _draw_status_circle(
        self,
        painter: QPainter,
        frame_rect: QRect,
        corner: str,
        color_hex: str,
        filled: bool,
    ) -> None:
        """Draw a single status indicator circle.

        Args:
            painter: QPainter
            frame_rect: Frame rectangle
            corner: Corner position ("top-left" or "top-right")
            color_hex: Hex color for the circle
            filled: True for filled circle, False for outline only

        """
        # Calculate center position based on corner
        if corner == "top-left":
            center_x = frame_rect.left() + self.INDICATOR_MARGIN + self.INDICATOR_CIRCLE_SIZE // 2
        else:  # top-right
            center_x = frame_rect.right() - self.INDICATOR_MARGIN - self.INDICATOR_CIRCLE_SIZE // 2

        center_y = frame_rect.top() + self.INDICATOR_MARGIN + self.INDICATOR_CIRCLE_SIZE // 2

        # Parse color
        color = QColor(color_hex)
        if not color.isValid():
            color = QColor(METADATA_ICON_COLORS["none"])

        # Draw circle - filled or outline based on status
        if filled:
            # Filled circle with subtle border
            painter.setPen(QPen(color.darker(120), 1))
            painter.setBrush(QBrush(color))
        else:
            # Outline only for none status (like file table)
            painter.setPen(QPen(color, self.INDICATOR_BORDER_WIDTH))
            painter.setBrush(Qt.NoBrush)

        painter.drawEllipse(
            center_x - self.INDICATOR_CIRCLE_SIZE // 2,
            center_y - self.INDICATOR_CIRCLE_SIZE // 2,
            self.INDICATOR_CIRCLE_SIZE,
            self.INDICATOR_CIRCLE_SIZE,
        )

    def _draw_video_badge(
        self,
        painter: QPainter,
        frame_rect: QRect,
        duration: float,
    ) -> None:
        """Draw the video duration badge.

        Args:
            painter: QPainter
            frame_rect: Frame rectangle (badge drawn at bottom-right)
            duration: Video duration in seconds

        """
        # Format duration as HH:MM:SS or MM:SS
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = int(duration % 60)

        if hours > 0:
            duration_text = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            duration_text = f"{minutes:02d}:{seconds:02d}"

        # Calculate text size
        font = QFont()
        font.setPointSize(8)
        font.setBold(True)
        metrics = QFontMetrics(font)
        text_width = metrics.horizontalAdvance(duration_text)
        text_height = metrics.height()

        # Calculate badge rectangle (bottom-right corner with margin)
        badge_width = text_width + self.VIDEO_BADGE_PADDING * 2
        badge_height = text_height + self.VIDEO_BADGE_PADDING * 2
        badge_x = frame_rect.right() - self.VIDEO_BADGE_MARGIN - badge_width
        badge_y = frame_rect.bottom() - self.VIDEO_BADGE_MARGIN - badge_height

        badge_rect = QRectF(badge_x, badge_y, badge_width, badge_height)

        # Draw semi-transparent background with rounded corners
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self.VIDEO_BADGE_BACKGROUND))
        painter.drawRoundedRect(badge_rect, 3, 3)

        # Draw text
        painter.setPen(self.VIDEO_BADGE_TEXT)
        painter.setFont(font)
        painter.drawText(badge_rect, Qt.AlignCenter, duration_text)

    def _draw_filename(
        self,
        painter: QPainter,
        filename_rect: QRect,
        filename: str,
        is_selected: bool,
    ) -> None:
        """Draw the filename text, word-wrapped if needed.

        Args:
            painter: QPainter
            filename_rect: Target rectangle for filename
            filename: Filename to display
            is_selected: Whether item is selected

        """
        # Set text color (black normally, white if selected)
        text_color = Qt.white if is_selected else Qt.black
        painter.setPen(text_color)

        # Use smaller font for filename
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)

        # Draw text with word wrap and elision
        painter.drawText(
            filename_rect,
            Qt.AlignTop | Qt.AlignHCenter | Qt.TextWordWrap,
            filename,
        )

    def createEditor(
        self,
        parent: "QWidget",
        option: "QStyleOptionViewItem",
        index: "QModelIndex",
    ) -> "QWidget | None":
        """Disable inline editing (use rename dialog instead).

        Args:
            parent: Parent widget
            option: Style options
            index: Model index

        Returns:
            None (editing disabled)

        """
        # Inline editing disabled - use rename dialog or context menu
        return None

    def helpEvent(
        self,
        event,
        view: "QWidget",
        option: "QStyleOptionViewItem",
        index: "QModelIndex",
    ) -> bool:
        """Show tooltip with full filename on hover.

        Args:
            event: Help event
            view: View widget
            option: Style options
            index: Model index

        Returns:
            True if tooltip handled

        """
        from PyQt5.QtWidgets import QToolTip

        file_item = index.data(Qt.UserRole)
        if isinstance(file_item, FileItem):
            # Show full filename as tooltip
            QToolTip.showText(event.globalPos(), file_item.filename, view)
            return True

        return super().helpEvent(event, view, option, index)
