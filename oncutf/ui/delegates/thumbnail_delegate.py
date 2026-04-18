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
    QPainterPath,
    QPen,
    QPixmap,
)
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import QStyle, QStyledItemDelegate

from oncutf.config.file_types import (
    FILETYPE_ICON_MAP,
    PREVIEWABLE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    get_filetype_icon,
)
from oncutf.config.ui import MISSED_TEXT_COLOR, MODIFIED_TEXT_COLOR, QLABEL_PRIMARY_TEXT
from oncutf.config.ui.thumbnail import (
    BACKGROUND_COLOR_HOVER as _BG_HOVER,
    BACKGROUND_COLOR_SELECTED as _BG_SELECTED,
    BADGE_ICON_COLOR,
    BADGE_ICON_SIZE,
    BADGE_MARGIN,
    BADGE_OPACITY,
    CROSSFADE_DURATION_MS,
    ERROR_BG_COLOR as _ERR_BG,
    ERROR_ICON_COLOR,
    ERROR_ICON_OPACITY,
    ERROR_ICON_SIZE,
    FILENAME_HEIGHT,
    FILENAME_MARGIN,
    FRAME_BG_COLOR_DEFAULT as _FRAME_BG_DEFAULT,
    FRAME_BG_OPACITY_NORMAL,
    FRAME_BG_OPACITY_SELECTED,
    FRAME_BORDER_WIDTH,
    FRAME_COLOR_HOVER as _FC_HOVER,
    FRAME_COLOR_NORMAL as _FC_NORMAL,
    FRAME_COLOR_SELECTED as _FC_SELECTED,
    FRAME_PADDING,
    HASH_ICON_SIZE,
    INDICATOR_ICON_SIZE,
    INDICATOR_MARGIN,
    LOADING_TYPE_ICON_COLOR,
    LOADING_TYPE_ICON_OPACITY,
    LOG_BADGE_BG as _LOG_BG,
    LOG_BADGE_COLOR_ACTIVE,
    LOG_BADGE_COLOR_INACTIVE,
    LOG_BADGE_OPACITY_ACTIVE,
    LOG_BADGE_OPACITY_INACTIVE,
    LOG_BADGE_TEXT as _LOG_TEXT,
    NO_PREVIEW_BG_COLOR as _NP_BG,
    NO_PREVIEW_ICON_COLOR,
    NO_PREVIEW_ICON_OPACITY,
    NO_PREVIEW_ICON_SIZE,
    SHIMMER_PHASE_MAX,
    SHIMMER_PHASE_STEP,
    SHIMMER_TICK_MS,
    SKELETON_BG_COLOR as _SK_BG,
    SKELETON_SHAPE_COLOR as _SK_SHAPE,
    SKELETON_SHIMMER_ALPHA,
    TEXT_COLOR_SELECTED,
    THUMBNAIL_FONT_SIZE,
    TYPE_ICON_SIZE,
    VIDEO_BADGE_BACKGROUND as _VB_BG,
    VIDEO_BADGE_MARGIN,
    VIDEO_BADGE_PADDING,
    VIDEO_BADGE_TEXT as _VB_TEXT,
)
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

    # -- Layout (from config.ui.thumbnail) -----------------------------------
    FRAME_BORDER_WIDTH = FRAME_BORDER_WIDTH
    FRAME_PADDING = FRAME_PADDING
    FILENAME_HEIGHT = FILENAME_HEIGHT
    FILENAME_MARGIN = FILENAME_MARGIN
    INDICATOR_ICON_SIZE = INDICATOR_ICON_SIZE
    HASH_ICON_SIZE = HASH_ICON_SIZE
    INDICATOR_MARGIN = INDICATOR_MARGIN
    VIDEO_BADGE_MARGIN = VIDEO_BADGE_MARGIN
    VIDEO_BADGE_PADDING = VIDEO_BADGE_PADDING

    # -- Colors (QColor instances built from config tuples) ------------------
    FRAME_COLOR_NORMAL = QColor(*_FC_NORMAL)
    FRAME_COLOR_HOVER = QColor(*_FC_HOVER)
    FRAME_COLOR_SELECTED = QColor(*_FC_SELECTED)
    FRAME_BG_COLOR_DEFAULT = QColor(*_FRAME_BG_DEFAULT)
    FRAME_BG_OPACITY_NORMAL = FRAME_BG_OPACITY_NORMAL
    FRAME_BG_OPACITY_SELECTED = FRAME_BG_OPACITY_SELECTED
    BACKGROUND_COLOR_SELECTED = QColor(*_BG_SELECTED)
    BACKGROUND_COLOR_HOVER = QColor(*_BG_HOVER)
    TEXT_COLOR_SELECTED = TEXT_COLOR_SELECTED
    VIDEO_BADGE_BACKGROUND = QColor(*_VB_BG)
    VIDEO_BADGE_TEXT = QColor(*_VB_TEXT)

    # Skeleton placeholder
    SKELETON_BG_COLOR = QColor(*_SK_BG)
    SKELETON_SHAPE_COLOR = QColor(*_SK_SHAPE)
    SKELETON_SHIMMER_ALPHA = SKELETON_SHIMMER_ALPHA

    # No-preview placeholder
    NO_PREVIEW_BG_COLOR = QColor(*_NP_BG)
    NO_PREVIEW_ICON_SIZE = NO_PREVIEW_ICON_SIZE
    NO_PREVIEW_ICON_OPACITY = NO_PREVIEW_ICON_OPACITY
    NO_PREVIEW_ICON_COLOR = NO_PREVIEW_ICON_COLOR

    # Error placeholder
    ERROR_BG_COLOR = QColor(*_ERR_BG)
    ERROR_ICON_SIZE = ERROR_ICON_SIZE
    ERROR_ICON_COLOR = ERROR_ICON_COLOR
    ERROR_ICON_OPACITY = ERROR_ICON_OPACITY

    # LOG badge
    LOG_BADGE_BG = QColor(*_LOG_BG)
    LOG_BADGE_TEXT = QColor(*_LOG_TEXT)
    LOG_BADGE_COLOR_ACTIVE = LOG_BADGE_COLOR_ACTIVE
    LOG_BADGE_COLOR_INACTIVE = LOG_BADGE_COLOR_INACTIVE
    LOG_BADGE_OPACITY_ACTIVE = LOG_BADGE_OPACITY_ACTIVE
    LOG_BADGE_OPACITY_INACTIVE = LOG_BADGE_OPACITY_INACTIVE

    # Loading type icon
    LOADING_TYPE_ICON_OPACITY = LOADING_TYPE_ICON_OPACITY
    LOADING_TYPE_ICON_COLOR = LOADING_TYPE_ICON_COLOR

    # Font
    THUMBNAIL_FONT_SIZE = THUMBNAIL_FONT_SIZE

    # -- Badge overlay (bottom-left filetype, bottom-right LOG) ---------------
    BADGE_ICON_SIZE = BADGE_ICON_SIZE
    BADGE_MARGIN = BADGE_MARGIN
    TYPE_ICON_SIZE = TYPE_ICON_SIZE
    BADGE_OPACITY = BADGE_OPACITY
    BADGE_ICON_COLOR = BADGE_ICON_COLOR

    # -- Animation timing (from config.ui.thumbnail) -------------------------
    CROSSFADE_DURATION_MS = CROSSFADE_DURATION_MS
    SHIMMER_TICK_MS = SHIMMER_TICK_MS
    SHIMMER_PHASE_STEP = SHIMMER_PHASE_STEP
    SHIMMER_PHASE_MAX = SHIMMER_PHASE_MAX

    # -- File type data (from config.file_types) -----------------------------
    PREVIEWABLE_EXTENSIONS: ClassVar[frozenset[str]] = PREVIEWABLE_EXTENSIONS
    VIDEO_EXTENSIONS: ClassVar[frozenset[str]] = VIDEO_EXTENSIONS

    # Filetype icon cache: (extension, size, color) -> QPixmap
    _filetype_icon_cache: ClassVar[dict[tuple[str, int, str], QPixmap]] = {}

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
        # rows whose crossfade has completed -- never re-register these
        self._completed_fades: set[int] = set()

        # Rows needing animation repaint (shimmer or crossfade) -- for targeted updates
        self._animated_rows: set[int] = set()

        # Paths that failed thumbnail generation (error state)
        self._failed_paths: set[str] = set()

        # Scaled pixmap cache: (pixmap.cacheKey(), target_size) -> scaled_pixmap
        self._scaled_cache: dict[tuple[int, tuple[int, int]], QPixmap] = {}
        self._SCALED_CACHE_MAX = 200

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

    def reset_for_new_files(self) -> None:
        """Full animation reset for a new file-loading session.

        Called when new files are loaded into the model (not on view switch).
        Clears all crossfade and completion tracking so incoming thumbnails
        fade in cleanly. The shimmer timer is NOT started here -- it starts
        automatically when start_shimmer() is called once queuing begins.

        """
        self._fade_states.clear()
        self._completed_fades.clear()
        self._animated_rows.clear()
        self._scaled_cache.clear()
        self._failed_paths.clear()
        self._loading_active = False
        # Stop timer if running -- it will be restarted by start_shimmer()
        if self._shimmer_timer.isActive():
            self._shimmer_timer.stop()

    def register_error(self, file_path: str) -> None:
        """Mark *file_path* as failed so the delegate shows an error state."""
        self._failed_paths.add(file_path)

    def start_shimmer(self) -> None:
        """Start shimmer animation for loading state (called from viewport).

        Safe to call multiple times; the timer will not double-start.
        Does NOT clear _completed_fades -- use reset_for_new_files() for that.

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

    def mark_row_completed(self, row: int) -> None:
        """Mark a row as having a completed (cached) thumbnail.

        Call this for rows that already have a real pixmap in the model
        so the paint() state machine skips the shimmer and draws the
        thumbnail directly -- no crossfade needed.

        Args:
            row: Model row index to mark as completed

        """
        self._completed_fades.add(row)

    def register_fade(self, row: int, pixmap: QPixmap) -> None:
        """Register a crossfade transition for a specific row.

        Called from ThumbnailViewportWidget._on_thumbnail_ready() when a real
        thumbnail has arrived and should fade in over the skeleton placeholder.

        Skips registration if the row has already completed a fade -- this
        prevents the crossfade loop bug where a re-emitted thumbnail_ready
        signal restarts the animation indefinitely.

        Args:
            row: Model row index of the item to transition
            pixmap: The newly ready real thumbnail pixmap

        """
        # Guard: never re-fade a row that already finished its crossfade
        if row in self._completed_fades:
            return

        self._fade_states[row] = (time.monotonic() * 1000.0, pixmap)
        # Ensure timer is running for the crossfade repaints
        if not self._shimmer_timer.isActive():
            self._shimmer_timer.start()

    def _tick(self) -> None:
        """Advance shimmer phase and trigger targeted viewport repaint.

        Only repaints items that need animation (shimmer or crossfade),
        not the entire viewport. Modeled after the C++ oncut-lut-engine
        approach of tracking animated rects.
        """
        self._shimmer_phase = (
            self._shimmer_phase + self.SHIMMER_PHASE_STEP
        ) % self.SHIMMER_PHASE_MAX

        # Move completed fades into _completed_fades so paint() never re-registers them
        now_ms = time.monotonic() * 1000.0
        still_active: dict[int, tuple[float, QPixmap]] = {}
        for row, state in self._fade_states.items():
            if (now_ms - state[0]) < self.CROSSFADE_DURATION_MS:
                still_active[row] = state
            else:
                self._completed_fades.add(row)
        self._fade_states = still_active

        # Targeted repaint: only update rects that were marked as animated
        parent = self.parent()
        if parent is not None and self._animated_rows:
            vp = parent.viewport()
            rows_to_update = self._animated_rows.copy()
            self._animated_rows.clear()
            model = parent.model()
            if model is not None:
                for row in rows_to_update:
                    index = model.index(row, 0)
                    if index.isValid():
                        rect = parent.visualRect(index)
                        if rect.isValid():
                            vp.update(rect)

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

        # Calculate layout rects
        frame_rect = self._calculate_frame_rect(option.rect)
        thumbnail_rect = self._calculate_thumbnail_rect(frame_rect)
        filename_rect = self._calculate_filename_rect(option.rect, frame_rect)

        # Cell-level background: a single rounded rect that spans from the
        # top of the frame to the bottom of the filename area.  This
        # eliminates any visible divider between the image area and the
        # filename row and gives a subtle rounded-corner appearance.
        if is_selected or is_hover:
            bg_color = (
                self.BACKGROUND_COLOR_SELECTED if is_selected else self.BACKGROUND_COLOR_HOVER
            )
            cell_bg_rect = QRectF(
                frame_rect.left(),
                frame_rect.top(),
                frame_rect.width(),
                filename_rect.bottom() - frame_rect.top(),
            )
            path = QPainterPath()
            path.addRoundedRect(cell_bg_rect, 4.0, 4.0)
            painter.fillPath(path, bg_color)

        # Draw frame border
        self._draw_frame(painter, frame_rect, file_item, is_selected, is_hover)

        # --- Thumbnail area: state machine ---
        row = index.row()
        pixmap = index.data(Qt.UserRole + 1)
        has_real_pixmap = isinstance(pixmap, QPixmap) and not pixmap.isNull()
        extension = file_item.extension.lower()
        is_previewable = extension in self.PREVIEWABLE_EXTENSIONS
        is_failed = file_item.full_path in self._failed_paths

        # Skeleton fills the full frame interior (border inset only, includes padding).
        # This ensures the dark bg covers the frame padding area so no light-colored
        # frame background leaks around the skeleton.
        skeleton_fill_rect = frame_rect.adjusted(
            self.FRAME_BORDER_WIDTH,
            self.FRAME_BORDER_WIDTH,
            -self.FRAME_BORDER_WIDTH,
            -self.FRAME_BORDER_WIDTH,
        )

        if is_failed and not has_real_pixmap:
            # Error: thumbnail generation failed -- show error placeholder
            self._draw_error_placeholder(painter, skeleton_fill_rect, thumbnail_rect, extension)
            show_icons = True

        elif row in self._fade_states:
            # Crossfade: skeleton fades out, thumbnail fades in
            start_ms, real_pixmap = self._fade_states[row]
            t = min(1.0, (time.monotonic() * 1000.0 - start_ms) / self.CROSSFADE_DURATION_MS)

            painter.setOpacity(1.0 - t)
            self._draw_skeleton_placeholder(painter, skeleton_fill_rect, thumbnail_rect, extension)
            painter.setOpacity(t)
            self._draw_thumbnail(painter, thumbnail_rect, real_pixmap)
            painter.setOpacity(1.0)

            # Status icons only after fade is mostly done (avoids icon pop-in)
            show_icons = t > 0.7
            self._animated_rows.add(row)  # needs repaint next tick

        elif has_real_pixmap:
            # During an active loading session: only show real pixmap for rows
            # that completed a fade. This prevents the race-condition flash where
            # the cache has the pixmap before register_fade() was called.
            if (self._loading_active or self._fade_states) and row not in self._completed_fades:
                self._draw_skeleton_placeholder(
                    painter, skeleton_fill_rect, thumbnail_rect, extension
                )
                show_icons = False
                self._animated_rows.add(row)  # needs repaint next tick
            else:
                self._draw_thumbnail(painter, thumbnail_rect, pixmap)
                show_icons = True

        elif is_previewable:
            # Loading: shimmer skeleton only
            self._draw_skeleton_placeholder(painter, skeleton_fill_rect, thumbnail_rect, extension)
            show_icons = False
            self._animated_rows.add(row)  # needs repaint next tick

        else:
            # No preview possible: permanent file-type silhouette
            self._draw_no_preview_placeholder(
                painter, skeleton_fill_rect, thumbnail_rect, file_item
            )
            show_icons = True

        # Status icons and video badge only when thumbnail is (or nearly) final
        if show_icons:
            self._draw_status_icons(painter, frame_rect, file_item, index)
            # Bottom-left: filetype badge (Ready + Failed, matching C++ lut-engine)
            self._draw_filetype_badge(painter, thumbnail_rect, extension)
            # Bottom-right: LOG badge -- only for video files (LOG profile is
            # a per-clip property of footage; not relevant for stills/audio).
            if extension in self.VIDEO_EXTENSIONS:
                has_log = bool(getattr(file_item, "has_log", False))
                self._draw_log_badge(painter, thumbnail_rect, has_log)

        duration = getattr(file_item, "duration", None)
        if show_icons and duration:
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
        """Draw the thumbnail frame border.

        Border color is constant in all states (idle/hover/selected/loading/
        ready/failed) -- matches oncut-lut-engine behavior. The interior is
        NOT filled here so the cell-level hover/selection background (painted
        in paint() across the whole option.rect) stays visible through the
        frame padding area. Only color-tagged files get an interior fill.

        Args:
            painter: QPainter
            frame_rect: Frame rectangle
            file_item: File item (used for color tag)
            is_selected: Unused (kept for signature stability)
            is_hover: Unused (kept for signature stability)

        """
        del is_selected, is_hover  # background handled at cell level

        has_color_tag = getattr(file_item, "color", "none") != "none"
        if has_color_tag:
            color_value = QColor(file_item.color)
            if color_value.isValid():
                painter.setBrush(QBrush(color_value))
            else:
                painter.setBrush(Qt.NoBrush)
        else:
            painter.setBrush(Qt.NoBrush)

        painter.setPen(QPen(self.FRAME_COLOR_NORMAL, self.FRAME_BORDER_WIDTH))
        painter.drawRect(frame_rect)

    def _draw_thumbnail(
        self,
        painter: QPainter,
        thumbnail_rect: QRect,
        thumbnail_pixmap: QPixmap,
    ) -> None:
        """Draw the thumbnail image centered within the thumbnail rect.

        A dark letterbox fill is drawn first so that aspect-ratio gaps
        around non-square images show a consistent background instead of
        the cell-level hover/selection color bleeding through.

        Uses a scaled pixmap cache to avoid expensive QPixmap.scaled()
        on every paint() call.
        """
        # Letterbox fill (matches lut-engine #1a1a1a)
        painter.fillRect(thumbnail_rect, self.FRAME_BG_COLOR_DEFAULT)

        target_size = (thumbnail_rect.width(), thumbnail_rect.height())
        cache_key = (thumbnail_pixmap.cacheKey(), target_size)

        scaled = self._scaled_cache.get(cache_key)
        if scaled is None:
            scaled = thumbnail_pixmap.scaled(
                thumbnail_rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            if len(self._scaled_cache) >= self._SCALED_CACHE_MAX:
                self._scaled_cache.clear()
            self._scaled_cache[cache_key] = scaled

        x = thumbnail_rect.left() + (thumbnail_rect.width() - scaled.width()) // 2
        y = thumbnail_rect.top() + (thumbnail_rect.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)

    def _draw_skeleton_placeholder(
        self,
        painter: QPainter,
        fill_rect: QRect,
        shimmer_rect: QRect,
        extension: str,
    ) -> None:
        """Draw animated shimmer skeleton for loading state.

        Matches C++ oncut-lut-engine layout:
        1. Dark fill on fill_rect (frame interior, covers padding area)
        2. Shimmer gradient on shimmer_rect (thumbnail area only)
        3. Centered filetype icon on shimmer_rect

        Args:
            painter: QPainter
            fill_rect: Full interior rect (frame minus border, includes padding)
            shimmer_rect: Thumbnail rect (where shimmer + icon are drawn)
            extension: Lowercase file extension for icon lookup

        """
        painter.setPen(Qt.NoPen)

        # Base fill covers full interior (including padding area)
        painter.setBrush(QBrush(self.SKELETON_BG_COLOR))
        painter.drawRect(fill_rect)

        # Shimmer gradient: diagonal sweep confined to shimmer_rect.
        # Only draw during active sweep phase (phase < 1.0).
        # When phase >= 1.0: pause (no shimmer band visible).
        phase = self._shimmer_phase
        if phase < 1.0:
            # Diagonal gradient: bottom-left to top-right with shallow angle (~-25deg)
            # Matches C++ lut-engine: start(left, bottom) -> end(right, top + 0.35*h)
            start_x = float(shimmer_rect.left())
            start_y = float(shimmer_rect.bottom())
            end_x = float(shimmer_rect.right())
            end_y = float(shimmer_rect.top() + shimmer_rect.height() * 0.35)

            shimmer = QLinearGradient(start_x, start_y, end_x, end_y)

            band_half = 0.14  # band half-width
            transparent = QColor(255, 255, 255, 0)
            highlight = QColor(255, 255, 255, self.SKELETON_SHIMMER_ALPHA)

            shimmer.setColorAt(0.0, transparent)
            shimmer.setColorAt(max(0.001, phase - band_half), transparent)
            shimmer.setColorAt(min(max(0.002, phase), 0.998), highlight)
            shimmer.setColorAt(min(0.999, phase + band_half), transparent)
            shimmer.setColorAt(1.0, transparent)

            painter.setBrush(QBrush(shimmer))
            painter.drawRect(shimmer_rect)

        # Centered filetype icon (dimmed, like C++ lut-engine loading state)
        icon_px = self._get_filetype_icon(
            extension, self.TYPE_ICON_SIZE, self.LOADING_TYPE_ICON_COLOR
        )
        if not icon_px.isNull():
            ix = shimmer_rect.left() + (shimmer_rect.width() - icon_px.width()) // 2
            iy = shimmer_rect.top() + (shimmer_rect.height() - icon_px.height()) // 2
            painter.setOpacity(self.LOADING_TYPE_ICON_OPACITY)
            painter.drawPixmap(ix, iy, icon_px)
            painter.setOpacity(1.0)

    def _draw_no_preview_placeholder(
        self,
        painter: QPainter,
        fill_rect: QRect,
        thumbnail_rect: QRect,
        file_item: "FileItem",
    ) -> None:
        """Draw permanent no-preview placeholder with filetype silhouette.

        Applies to files whose extension is not in PREVIEWABLE_EXTENSIONS.
        Background is slightly brighter than the loading skeleton to indicate
        that this state is permanent, not transient.

        Args:
            painter: QPainter
            fill_rect: Full interior rect (frame minus border, includes padding)
            thumbnail_rect: Target rectangle inside the frame
            file_item: FileItem for extension lookup

        """
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self.NO_PREVIEW_BG_COLOR))
        painter.drawRect(fill_rect)

        icon_px = self._get_filetype_icon(file_item.extension.lower(), self.NO_PREVIEW_ICON_SIZE)
        if not icon_px.isNull():
            ix = thumbnail_rect.left() + (thumbnail_rect.width() - icon_px.width()) // 2
            iy = thumbnail_rect.top() + (thumbnail_rect.height() - icon_px.height()) // 2
            painter.setOpacity(self.NO_PREVIEW_ICON_OPACITY)
            painter.drawPixmap(ix, iy, icon_px)
            painter.setOpacity(1.0)

    def _draw_error_placeholder(
        self,
        painter: QPainter,
        fill_rect: QRect,
        thumbnail_rect: QRect,
        extension: str,
    ) -> None:
        """Draw error state: dark bg with a muted-red warning triangle.

        Uses ``metadata/warning.svg`` (Material Design warning glyph) tinted
        with ``ERROR_ICON_COLOR`` -- matches oncut-lut-engine failed state.

        Args:
            painter: QPainter
            fill_rect: Full interior rect (including padding)
            thumbnail_rect: Inner thumbnail rect
            extension: Lowercase file extension (kept for signature stability)

        """
        del extension  # not used: a generic warning glyph is shown for all types

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self.ERROR_BG_COLOR))
        painter.drawRect(fill_rect)

        icon_px = self._get_named_svg_icon(
            "metadata", "warning", self.ERROR_ICON_SIZE, self.ERROR_ICON_COLOR
        )
        if not icon_px.isNull():
            ix = thumbnail_rect.left() + (thumbnail_rect.width() - icon_px.width()) // 2
            iy = thumbnail_rect.top() + (thumbnail_rect.height() - icon_px.height()) // 2
            painter.setOpacity(self.ERROR_ICON_OPACITY)
            painter.drawPixmap(ix, iy, icon_px)
            painter.setOpacity(1.0)

    def _draw_filetype_badge(
        self,
        painter: QPainter,
        thumbnail_rect: QRect,
        extension: str,
    ) -> None:
        """Draw file-type icon badge at bottom-left of thumbnail area.

        Shown on Ready and Failed thumbnails, matching the C++ lut-engine
        media-type badge layout.

        Args:
            painter: QPainter
            thumbnail_rect: Thumbnail rect (badge anchored to its bottom-left)
            extension: Lowercase file extension for icon lookup

        """
        icon_px = self._get_filetype_icon(extension, self.BADGE_ICON_SIZE, self.BADGE_ICON_COLOR)
        if icon_px.isNull():
            return

        bx = thumbnail_rect.left() + self.BADGE_MARGIN
        by = thumbnail_rect.bottom() - self.BADGE_ICON_SIZE - self.BADGE_MARGIN

        painter.setOpacity(self.BADGE_OPACITY)
        painter.drawPixmap(bx, by, icon_px)
        painter.setOpacity(1.0)

    def _draw_log_badge(
        self,
        painter: QPainter,
        thumbnail_rect: QRect,
        has_log: bool,
    ) -> None:
        """Draw LOG badge at bottom-right of thumbnail area.

        Always rendered for video files using ``preview/LOG.svg``:
        - LOG detected (``has_log=True``):  green ``LOG_BADGE_COLOR_ACTIVE``
        - Not detected (``has_log=False``): white, dimmed via opacity

        Matches oncut-lut-engine LOG badge (no pill background).

        Args:
            painter: QPainter
            thumbnail_rect: Thumbnail rect (badge anchored to its bottom-right)
            has_log: Whether LOG profile is detected for this file

        """
        if has_log:
            color = self.LOG_BADGE_COLOR_ACTIVE
            opacity = self.LOG_BADGE_OPACITY_ACTIVE
        else:
            color = self.LOG_BADGE_COLOR_INACTIVE
            opacity = self.LOG_BADGE_OPACITY_INACTIVE

        icon_px = self._get_named_svg_icon("preview", "LOG", self.BADGE_ICON_SIZE, color)
        if icon_px.isNull():
            return

        bx = thumbnail_rect.right() - self.BADGE_ICON_SIZE - self.BADGE_MARGIN
        by = thumbnail_rect.bottom() - self.BADGE_ICON_SIZE - self.BADGE_MARGIN

        painter.setOpacity(opacity)
        painter.drawPixmap(bx, by, icon_px)
        painter.setOpacity(1.0)

    @classmethod
    def _get_filetype_icon(cls, extension: str, size: int, color: str = "") -> QPixmap:
        """Load and return a filetype SVG icon at the requested size, with caching.

        Args:
            extension: Lowercase file extension without leading dot
            size: Icon size in pixels (square)
            color: CSS hex color string for tinting (default: NO_PREVIEW_ICON_COLOR)

        Returns:
            QPixmap of the icon, or null QPixmap on failure

        """
        tint = color or cls.NO_PREVIEW_ICON_COLOR
        cache_key = (extension, size, tint)
        if cache_key in cls._filetype_icon_cache:
            return cls._filetype_icon_cache[cache_key]

        icon_name = get_filetype_icon(extension)
        icons_dir = Path(__file__).parent.parent / "resources" / "icons" / "filetypes"
        svg_path = icons_dir / f"{icon_name}.svg"
        if not svg_path.exists():
            svg_path = icons_dir / "description.svg"

        pixmap = cls._render_svg_icon(svg_path, size, tint)
        cls._filetype_icon_cache[cache_key] = pixmap
        return pixmap

    @classmethod
    def _get_named_svg_icon(cls, subdir: str, name: str, size: int, color: str) -> QPixmap:
        """Load any SVG icon under ``oncutf/resources/icons/<subdir>/<name>.svg``.

        Used for non-filetype overlays (warning glyph, LOG badge, etc.).
        Cached on (subdir, name, size, color).
        """
        cache_key = (f"{subdir}/{name}", size, color)
        if cache_key in cls._filetype_icon_cache:
            return cls._filetype_icon_cache[cache_key]

        icons_dir = Path(__file__).parent.parent / "resources" / "icons" / subdir
        svg_path = icons_dir / f"{name}.svg"
        pixmap = cls._render_svg_icon(svg_path, size, color) if svg_path.exists() else QPixmap()
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
            x = frame_rect.right() - self.INDICATOR_MARGIN - self.HASH_ICON_SIZE
            y = frame_rect.top() + self.INDICATOR_MARGIN
            painter.drawPixmap(x, y, self.HASH_ICON_SIZE, self.HASH_ICON_SIZE, hash_icon)

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
        font.setPointSize(self.THUMBNAIL_FONT_SIZE)
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
        # Red for missing, yellow for renamed-dirty; otherwise:
        # - selected: dark navy for legibility on the light selection bg
        # - normal:   default table text color
        if file_missing:
            text_color = QColor(MISSED_TEXT_COLOR)
        elif rename_dirty:
            text_color = QColor(MODIFIED_TEXT_COLOR)
        elif is_selected:
            text_color = QColor(self.TEXT_COLOR_SELECTED)
        else:
            text_color = QColor(QLABEL_PRIMARY_TEXT)
        painter.setPen(text_color)

        # Use smaller font for filename
        font = painter.font()
        font.setPointSize(self.THUMBNAIL_FONT_SIZE)
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
