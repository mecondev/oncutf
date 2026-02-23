"""Thumbnail Delegate for rendering file thumbnails in grid view.

Author: Michael Economou
Date: 2026-01-16

Renders thumbnails with:
- Rectangle frame (photo slide style, 3px border)
- Thumbnail image centered with aspect ratio fit
- Filename word-wrapped below thumbnail
- Metadata/hash status icons (top corners)
- Video duration badge (bottom-right, semi-transparent)
- Loading spinner for generating thumbnails
- Placeholder for failed/missing thumbnails
- Hover and selection visual feedback
"""

import time
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from PyQt5.QtCore import QRect, QRectF, QSize, Qt, QTimer
from PyQt5.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QPen,
    QPixmap,
)
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import QStyle, QStyledItemDelegate

from oncutf.config.ui import MISSED_TEXT_COLOR, MODIFIED_TEXT_COLOR, QLABEL_PRIMARY_TEXT
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
    - Metadata/hash status icons (top corners)
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
    FILENAME_HEIGHT = 30  # Space below thumbnail for filename
    FILENAME_MARGIN = 4  # Vertical margin above filename

    # Metadata/Hash indicators (icons from file table column 0)
    INDICATOR_ICON_SIZE = 16  # Size of each status icon
    INDICATOR_MARGIN = 8  # Distance from corners of frame

    VIDEO_BADGE_MARGIN = 4  # Distance from bottom-right corner
    VIDEO_BADGE_PADDING = 4  # Padding inside badge

    # Colors
    FRAME_COLOR_NORMAL = QColor(200, 200, 200)
    FRAME_COLOR_HOVER = QColor(100, 150, 255)
    FRAME_COLOR_SELECTED = QColor(50, 120, 255)
    BACKGROUND_COLOR_SELECTED = QColor(50, 120, 255, 40)  # Semi-transparent
    VIDEO_BADGE_BACKGROUND = QColor(0, 0, 0, 180)  # Semi-transparent black
    VIDEO_BADGE_TEXT = QColor(255, 255, 255)

    # Skeleton placeholder colors (loading state)
    SKELETON_BG_COLOR = QColor(42, 44, 50)  # dark fill, "still building"
    SKELETON_SHAPE_COLOR = QColor(55, 58, 66)  # inner shape, slightly lighter
    SKELETON_SHIMMER_ALPHA = 28  # shimmer highlight alpha (0-255)
    PROGRESS_BAR_TRACK_COLOR = QColor(55, 58, 66)  # indeterminate bar track
    PROGRESS_BAR_FILL_COLOR = QColor(75, 105, 155)  # indeterminate bar fill
    PROGRESS_BAR_HEIGHT = 3  # px

    # No-preview placeholder colors (permanent state, slightly brighter than skeleton)
    NO_PREVIEW_BG_COLOR = QColor(58, 62, 72)  # brighter than skeleton
    NO_PREVIEW_ICON_SIZE = 48  # filetype silhouette px
    NO_PREVIEW_ICON_OPACITY = 0.65  # 65% opacity
    NO_PREVIEW_ICON_COLOR = "#7a7f8c"  # muted gray-blue tint

    # Crossfade duration (ms)
    CROSSFADE_DURATION_MS = 500.0

    # Shimmer timer interval (ms) -- 25 fps
    SHIMMER_TICK_MS = 40
    SHIMMER_PHASE_STEP = 0.04  # phase advance per tick (1.0 = full sweep)

    # Extensions that have thumbnail support (matches ThumbnailManager.PREVIEWABLE_EXTENSIONS)
    PREVIEWABLE_EXTENSIONS: ClassVar[frozenset[str]] = frozenset(
        {
            "jpg",
            "jpeg",
            "png",
            "gif",
            "bmp",
            "tiff",
            "tif",
            "webp",
            "heic",
            "heif",
            "raw",
            "cr2",
            "cr3",
            "nef",
            "arw",
            "dng",
            "orf",
            "raf",
            "rw2",
            "pef",
            "nrw",
            "srw",
            "dcr",
            "fff",
            "mp4",
            "mov",
            "avi",
            "mkv",
            "wmv",
            "m4v",
            "flv",
            "webm",
            "m2ts",
            "ts",
            "mts",
            "3gp",
            "ogv",
        }
    )

    # Mapping from file extension to filetype icon name (in resources/icons/filetypes/)
    _FILETYPE_ICON_MAP: ClassVar[dict[str, str]] = {
        # Raster images
        "jpg": "photo",
        "jpeg": "photo",
        "png": "photo",
        "gif": "photo",
        "bmp": "photo",
        "tiff": "photo",
        "tif": "photo",
        "webp": "photo",
        "heic": "photo",
        "heif": "photo",
        # RAW camera
        "raw": "image",
        "cr2": "image",
        "cr3": "image",
        "nef": "image",
        "arw": "image",
        "dng": "image",
        "orf": "image",
        "raf": "image",
        "rw2": "image",
        "pef": "image",
        "nrw": "image",
        "srw": "image",
        "dcr": "image",
        "fff": "image",
        # Video
        "mp4": "film",
        "mov": "film",
        "avi": "film",
        "mkv": "film",
        "wmv": "film",
        "m4v": "film",
        "flv": "film",
        "webm": "film",
        "m2ts": "film",
        "ts": "film",
        "mts": "film",
        "3gp": "film",
        "ogv": "film",
        # Audio
        "mp3": "audio_file",
        "flac": "audio_file",
        "wav": "audio_file",
        "aac": "audio_file",
        "ogg": "audio_file",
        "wma": "audio_file",
        "m4a": "audio_file",
        "opus": "audio_file",
        "aiff": "audio_file",
        # Archives
        "zip": "folder_zip",
        "rar": "folder_zip",
        "7z": "folder_zip",
        "tar": "folder_zip",
        "gz": "folder_zip",
        "bz2": "folder_zip",
        # Code / text ("ts" used for video above, not duplicated here)
        "py": "code",
        "js": "code",
        "html": "code",
        "css": "code",
        "json": "code",
        "xml": "code",
        "yaml": "code",
        "yml": "code",
        "sh": "code",
        "bat": "code",
    }

    # Filetype icon cache: (extension, size) -> QPixmap
    _filetype_icon_cache: ClassVar[dict[tuple[str, int], QPixmap]] = {}

    def __init__(self, parent: "QWidget | None" = None):
        """Initialize the thumbnail delegate.

        Args:
            parent: Parent widget

        """
        super().__init__(parent)
        self._thumbnail_size = 128  # Default size, will be set from viewport
        self._status_icons = self._load_status_icons()

        # Shimmer / crossfade animation state
        self._shimmer_phase: float = 0.0
        self._loading_active: bool = False
        # row -> (start_time_ms, real_pixmap) for active crossfades
        self._fade_states: dict[int, tuple[float, QPixmap]] = {}

        # Single shared timer drives both shimmer and crossfade repaints
        self._shimmer_timer = QTimer(self)
        self._shimmer_timer.setInterval(self.SHIMMER_TICK_MS)
        self._shimmer_timer.timeout.connect(self._tick)

    def _load_status_icons(self) -> dict[str, QPixmap]:
        """Load metadata/hash status icons used by the file table."""
        from oncutf.ui.services.icon_service import load_metadata_icons

        return load_metadata_icons()

    # ------------------------------------------------------------------
    # Animation control (called from ThumbnailViewportWidget)
    # ------------------------------------------------------------------

    def start_shimmer(self) -> None:
        """Start shimmer animation for loading state (called from viewport).

        Safe to call multiple times; the timer will not double-start.

        """
        self._loading_active = True
        if not self._shimmer_timer.isActive():
            self._shimmer_timer.start()

    def stop_shimmer(self) -> None:
        """Signal that bulk loading is complete.

        The timer continues running until all crossfades finish, then stops
        itself automatically inside _tick().

        """
        self._loading_active = False

    def register_fade(self, row: int, pixmap: QPixmap) -> None:
        """Register a crossfade transition for a specific row.

        Called from ThumbnailViewportWidget._on_thumbnail_ready() when a real
        thumbnail has arrived and should fade in over the skeleton placeholder.

        Args:
            row: Model row index of the item to transition
            pixmap: The newly ready real thumbnail pixmap

        """
        self._fade_states[row] = (time.monotonic() * 1000.0, pixmap)
        # Ensure timer is running for the crossfade repaints
        if not self._shimmer_timer.isActive():
            self._shimmer_timer.start()

    def _tick(self) -> None:
        """Advance shimmer phase and trigger viewport repaint.

        Called by _shimmer_timer every SHIMMER_TICK_MS ms. Also handles
        cleanup of completed crossfade transitions.

        """
        self._shimmer_phase = (self._shimmer_phase + self.SHIMMER_PHASE_STEP) % 1.0

        # Clean up completed fades (elapsed >= CROSSFADE_DURATION_MS)
        now_ms = time.monotonic() * 1000.0
        self._fade_states = {
            row: state
            for row, state in self._fade_states.items()
            if (now_ms - state[0]) < self.CROSSFADE_DURATION_MS
        }

        # Trigger viewport repaint for visible items
        parent = self.parent()
        if parent is not None:
            parent.viewport().update()

        # Self-stop when no animation is needed
        if not self._loading_active and not self._fade_states:
            self._shimmer_timer.stop()

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

        State machine:
          1. row in _fade_states  -> crossfade skeleton -> real thumbnail (500 ms)
          2. has real pixmap      -> draw real thumbnail directly
          3. previewable ext      -> shimmer skeleton + indeterminate progress bar
          4. non-previewable ext  -> permanent file-type silhouette

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

        # --- Thumbnail area: state machine ---
        row = index.row()
        pixmap = index.data(Qt.UserRole + 1)
        has_real_pixmap = isinstance(pixmap, QPixmap) and not pixmap.isNull()
        extension = file_item.extension.lower()
        is_previewable = extension in self.PREVIEWABLE_EXTENSIONS

        if row in self._fade_states:
            # Crossfade: skeleton fades out, thumbnail fades in
            start_ms, real_pixmap = self._fade_states[row]
            t = min(1.0, (time.monotonic() * 1000.0 - start_ms) / self.CROSSFADE_DURATION_MS)
            orientation = self._get_orientation_from_metadata(file_item, index)

            painter.setOpacity(1.0 - t)
            self._draw_skeleton_placeholder(painter, thumbnail_rect, orientation)
            painter.setOpacity(t)
            self._draw_thumbnail(painter, thumbnail_rect, real_pixmap)
            painter.setOpacity(1.0)

        elif has_real_pixmap:
            # Normal: real thumbnail fully loaded
            self._draw_thumbnail(painter, thumbnail_rect, pixmap)

        elif is_previewable:
            # Loading: shimmer skeleton + indeterminate progress bar
            orientation = self._get_orientation_from_metadata(file_item, index)
            self._draw_skeleton_placeholder(painter, thumbnail_rect, orientation)
            self._draw_skeleton_progress_bar(painter, thumbnail_rect)

        else:
            # No preview possible: permanent file-type silhouette
            self._draw_no_preview_placeholder(painter, thumbnail_rect, file_item)

        # Status icons and video badge always drawn on top
        self._draw_status_icons(painter, frame_rect, file_item, index)

        duration = getattr(file_item, "duration", None)
        if duration:
            self._draw_video_badge(painter, frame_rect, duration)

        # Draw filename
        self._draw_filename(
            painter,
            filename_rect,
            file_item.filename,
            is_selected,
            getattr(file_item, "rename_dirty", False),
            getattr(file_item, "file_missing", False),
        )

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
        """Draw the thumbnail frame border with file color background.

        Border: Normal/hover/selected color
        Background: File color if set, otherwise white
        - Unselected: 40% opacity
        - Selected:   70% opacity

        Args:
            painter: QPainter
            frame_rect: Frame rectangle
            file_item: File item with color tag
            is_selected: Whether item is selected
            is_hover: Whether item is hovered

        """
        border_color = self.FRAME_COLOR_SELECTED if is_selected else self.FRAME_COLOR_NORMAL
        if is_hover and not is_selected:
            border_color = self.FRAME_COLOR_HOVER

        background_color = QColor(255, 255, 255)
        if getattr(file_item, "color", "none") != "none":
            color_value = QColor(file_item.color)
            if color_value.isValid():
                background_color = color_value

        background_color.setAlphaF(0.7 if is_selected else 0.4)

        painter.setPen(QPen(border_color, self.FRAME_BORDER_WIDTH))
        painter.setBrush(QBrush(background_color))
        painter.drawRect(frame_rect)

    def _draw_thumbnail(
        self,
        painter: QPainter,
        thumbnail_rect: QRect,
        thumbnail_pixmap: QPixmap,
    ) -> None:
        """Draw the thumbnail image centered within the thumbnail rect."""
        scaled = thumbnail_pixmap.scaled(
            thumbnail_rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        x = thumbnail_rect.left() + (thumbnail_rect.width() - scaled.width()) // 2
        y = thumbnail_rect.top() + (thumbnail_rect.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)

    def _draw_skeleton_placeholder(
        self,
        painter: QPainter,
        thumbnail_rect: QRect,
        orientation: str,
    ) -> None:
        """Draw animated shimmer skeleton for loading state.

        Shows a dark base fill with a sweeping highlight gradient and an
        orientation-aware inner shape (portrait vs landscape).

        Args:
            painter: QPainter
            thumbnail_rect: Target rectangle inside the frame
            orientation: "portrait", "landscape", or "unknown" (defaults landscape)

        """
        painter.setPen(Qt.NoPen)

        # Base fill
        painter.setBrush(QBrush(self.SKELETON_BG_COLOR))
        painter.drawRect(thumbnail_rect)

        # Shimmer gradient: sweeps left to right based on shared phase
        phase = self._shimmer_phase
        tw = thumbnail_rect.width()
        band_cx = thumbnail_rect.left() + phase * (tw + 80) - 40
        shimmer = QLinearGradient(band_cx - 50, 0.0, band_cx + 50, 0.0)
        shimmer.setColorAt(0.0, QColor(255, 255, 255, 0))
        shimmer.setColorAt(0.5, QColor(255, 255, 255, self.SKELETON_SHIMMER_ALPHA))
        shimmer.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(QBrush(shimmer))
        painter.drawRect(thumbnail_rect)

        # Orientation-aware inner shape (suggests image proportions)
        if orientation == "portrait":
            iw = int(tw * 0.52)
            ih = int(thumbnail_rect.height() * 0.72)
        else:
            iw = int(tw * 0.72)
            ih = int(thumbnail_rect.height() * 0.52)
        ix = thumbnail_rect.left() + (thumbnail_rect.width() - iw) // 2
        iy = thumbnail_rect.top() + (thumbnail_rect.height() - ih) // 2
        painter.setBrush(QBrush(self.SKELETON_SHAPE_COLOR))
        painter.drawRoundedRect(QRect(ix, iy, iw, ih), 3, 3)

    def _draw_skeleton_progress_bar(
        self,
        painter: QPainter,
        thumbnail_rect: QRect,
    ) -> None:
        """Draw an indeterminate animated progress bar at the bottom of thumbnail.

        A thin bar (PROGRESS_BAR_HEIGHT px) sweeps left to right using the
        shared shimmer phase, giving visual feedback during loading.

        Args:
            painter: QPainter
            thumbnail_rect: The thumbnail area rectangle

        """
        bar_h = self.PROGRESS_BAR_HEIGHT
        bar_y = thumbnail_rect.bottom() - bar_h
        painter.setPen(Qt.NoPen)

        # Track
        painter.setBrush(QBrush(self.PROGRESS_BAR_TRACK_COLOR))
        painter.drawRect(QRect(thumbnail_rect.left(), bar_y, thumbnail_rect.width(), bar_h))

        # Animated fill (~35% width bar sweeping left to right)
        fill_w = int(thumbnail_rect.width() * 0.35)
        travel = thumbnail_rect.width() + fill_w
        bar_x = thumbnail_rect.left() + int(self._shimmer_phase * travel) - fill_w
        painter.setBrush(QBrush(self.PROGRESS_BAR_FILL_COLOR))
        painter.drawRect(QRect(bar_x, bar_y, fill_w, bar_h))

    def _draw_no_preview_placeholder(
        self,
        painter: QPainter,
        thumbnail_rect: QRect,
        file_item: "FileItem",
    ) -> None:
        """Draw permanent no-preview placeholder with filetype silhouette.

        Applies to files whose extension is not in PREVIEWABLE_EXTENSIONS.
        Background is slightly brighter than the loading skeleton to indicate
        that this state is permanent, not transient.

        Args:
            painter: QPainter
            thumbnail_rect: Target rectangle inside the frame
            file_item: FileItem for extension lookup

        """
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self.NO_PREVIEW_BG_COLOR))
        painter.drawRect(thumbnail_rect)

        icon_px = self._get_filetype_icon(file_item.extension.lower(), self.NO_PREVIEW_ICON_SIZE)
        if not icon_px.isNull():
            ix = thumbnail_rect.left() + (thumbnail_rect.width() - icon_px.width()) // 2
            iy = thumbnail_rect.top() + (thumbnail_rect.height() - icon_px.height()) // 2
            painter.setOpacity(self.NO_PREVIEW_ICON_OPACITY)
            painter.drawPixmap(ix, iy, icon_px)
            painter.setOpacity(1.0)

    def _get_orientation_from_metadata(self, file_item: "FileItem", index: "QModelIndex") -> str:
        """Return orientation hint from cached metadata if available.

        Args:
            file_item: FileItem to inspect
            index: Model index used to reach the metadata cache

        Returns:
            "portrait" if height > width, "landscape" otherwise

        """
        try:
            model = index.model() if index is not None else None
            if model is None or not hasattr(model, "parent_window"):
                return "landscape"
            parent_window = model.parent_window
            if parent_window is None or not hasattr(parent_window, "metadata_cache"):
                return "landscape"
            entry = parent_window.metadata_cache.get_entry(file_item.full_path)
            if entry is None or not entry.data:
                return "landscape"

            width_keys = [
                "EXIF:ImageWidth",
                "File:ImageWidth",
                "PNG:ImageWidth",
                "ExifImageWidth",
                "PixelXDimension",
            ]
            height_keys = [
                "EXIF:ImageHeight",
                "File:ImageHeight",
                "PNG:ImageHeight",
                "ExifImageHeight",
                "PixelYDimension",
            ]
            width: int | None = None
            height: int | None = None
            for key in width_keys:
                if key in entry.data:
                    try:
                        width = int(entry.data[key])
                        break
                    except (ValueError, TypeError):
                        pass
            for key in height_keys:
                if key in entry.data:
                    try:
                        height = int(entry.data[key])
                        break
                    except (ValueError, TypeError):
                        pass

            if width and height:
                return "portrait" if height > width else "landscape"
        except Exception:
            pass
        return "landscape"

    @classmethod
    def _get_filetype_icon(cls, extension: str, size: int) -> QPixmap:
        """Load and return a filetype SVG icon at the requested size, with caching.

        Icons are colorized with NO_PREVIEW_ICON_COLOR for a muted appearance.

        Args:
            extension: Lowercase file extension without leading dot
            size: Icon size in pixels (square)

        Returns:
            QPixmap of the icon, or null QPixmap on failure

        """
        cache_key = (extension, size)
        if cache_key in cls._filetype_icon_cache:
            return cls._filetype_icon_cache[cache_key]

        icon_name = cls._FILETYPE_ICON_MAP.get(extension, "description")
        icons_dir = Path(__file__).parent.parent / "resources" / "icons" / "filetypes"
        svg_path = icons_dir / f"{icon_name}.svg"
        if not svg_path.exists():
            svg_path = icons_dir / "description.svg"

        pixmap = cls._render_svg_icon(svg_path, size, cls.NO_PREVIEW_ICON_COLOR)
        cls._filetype_icon_cache[cache_key] = pixmap
        return pixmap

    @staticmethod
    def _render_svg_icon(svg_path: Path, size: int, color: str) -> QPixmap:
        """Render an SVG file to a QPixmap with color substitution.

        Args:
            svg_path: Path to the SVG file
            size: Output size in pixels (square)
            color: CSS hex color string to tint all fill/stroke values

        Returns:
            QPixmap of the rendered icon, or null QPixmap on failure

        """
        import re

        try:
            content = svg_path.read_text(encoding="utf-8")
            # Replace non-transparent fills/strokes with the tint color
            content = re.sub(r'fill="(?!none)[^"]*"', f'fill="{color}"', content)
            content = re.sub(r'stroke="(?!none)[^"]*"', f'stroke="{color}"', content)
            content = content.replace("currentColor", color)

            from PyQt5.QtCore import QByteArray

            renderer = QSvgRenderer()
            renderer.load(QByteArray(content.encode("utf-8")))
            if not renderer.isValid():
                return QPixmap()

            pixmap = QPixmap(size, size)
            pixmap.fill(QColor(0, 0, 0, 0))
            p = QPainter(pixmap)
            p.setRenderHint(QPainter.Antialiasing)
            renderer.render(p)
            p.end()
        except Exception:
            return QPixmap()
        else:
            return pixmap

    def _draw_status_icons(
        self,
        painter: QPainter,
        frame_rect: QRect,
        file_item: FileItem,
        index: "QModelIndex",
    ) -> None:
        """Draw metadata/hash status icons in the top corners.

        Args:
            painter: QPainter
            frame_rect: Frame rectangle
            file_item: FileItem for status checks
            index: QModelIndex for model access

        """
        metadata_status, hash_status = self._get_status_values(file_item, index)

        metadata_icon = self._status_icons.get(metadata_status)
        hash_icon = self._status_icons.get(hash_status)

        if metadata_icon:
            x = frame_rect.left() + self.INDICATOR_MARGIN
            y = frame_rect.top() + self.INDICATOR_MARGIN
            painter.drawPixmap(x, y, metadata_icon)

        if hash_icon:
            x = frame_rect.right() - self.INDICATOR_MARGIN - self.INDICATOR_ICON_SIZE
            y = frame_rect.top() + self.INDICATOR_MARGIN
            painter.drawPixmap(x, y, hash_icon)

    def _get_status_values(self, file_item: FileItem, index: "QModelIndex") -> tuple[str, str]:
        """Return metadata and hash status values matching file table logic."""
        metadata_status = "metadata_unavailable"

        is_modified = False
        try:
            from oncutf.core.metadata import get_metadata_staging_manager

            staging_manager = get_metadata_staging_manager()
            if staging_manager and staging_manager.has_staged_changes(file_item.full_path):
                is_modified = True
        except Exception:
            pass

        parent_window = None
        model = index.model() if index is not None else None
        if model is not None and hasattr(model, "parent_window"):
            parent_window = model.parent_window

        if parent_window and hasattr(parent_window, "metadata_cache"):
            entry = parent_window.metadata_cache.get_entry(file_item.full_path)
            if entry and hasattr(entry, "data") and entry.data:
                if is_modified or (hasattr(entry, "modified") and entry.modified):
                    metadata_status = "modified"
                elif hasattr(entry, "is_extended") and entry.is_extended:
                    metadata_status = "extended"
                else:
                    metadata_status = "loaded"

        from oncutf.utils.filesystem.file_status_helpers import has_hash

        hash_status = "tag" if has_hash(file_item.full_path) else "hash_unavailable"
        return metadata_status, hash_status

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
        rename_dirty: bool = False,
        file_missing: bool = False,
    ) -> None:
        """Draw the filename text, word-wrapped if needed.

        Args:
            painter: QPainter
            filename_rect: Target rectangle for filename
            filename: Filename to display
            is_selected: Whether item is selected
            rename_dirty: Whether the file was renamed but not yet reloaded
            file_missing: Whether the file is no longer found on disk

        """
        # Red for missing, yellow for renamed-dirty, default table text color otherwise
        if file_missing:
            text_color = QColor(MISSED_TEXT_COLOR)
        elif rename_dirty:
            text_color = QColor(MODIFIED_TEXT_COLOR)
        else:
            text_color = QColor(QLABEL_PRIMARY_TEXT)
        painter.setPen(text_color)

        # Use smaller font for filename
        font = painter.font()
        font.setPointSize(8)
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
        _event,
        _view: "QWidget",
        option: "QStyleOptionViewItem",
        index: "QModelIndex",
    ) -> bool:
        """Show tooltip with full filename on hover.

        Args:
            _event: Help event (unused, required by Qt API)
            _view: View widget (unused, required by Qt API)
            option: Style options
            index: Model index

        Returns:
            True if tooltip handled

        """
        return True
