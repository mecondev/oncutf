"""Module: oncutf.config.ui.thumbnail.

Author: Michael Economou
Date: 2026-02-24

Visual / layout constants for the thumbnail delegate and grid view.

Extracted from ``oncutf.ui.delegates.thumbnail_delegate`` so that the
delegate file stays focused on rendering logic while all tunable
numbers live here in the config layer.
"""

# =====================================================================
# Layout constants (pixels)
# =====================================================================

FRAME_BORDER_WIDTH = 3
FRAME_PADDING = 8  # Space between frame border and thumbnail
FILENAME_HEIGHT = 30  # Space below thumbnail for filename text
FILENAME_MARGIN = 6  # Vertical margin above filename

# Metadata / hash indicator icons
INDICATOR_ICON_SIZE = 16  # Metadata status icon (top-left)
HASH_ICON_SIZE = 20  # Hash/tag status icon (top-right, larger for visibility)
INDICATOR_MARGIN = 8  # Distance from corners of frame

# Video duration badge
VIDEO_BADGE_MARGIN = 4  # Distance from bottom-right corner
VIDEO_BADGE_PADDING = 4  # Padding inside badge

# File-type / status badges (overlays on thumbnail area)
BADGE_ICON_SIZE = 16  # Bottom-left filetype, bottom-right LOG badge (px)
BADGE_MARGIN = 3  # Distance from thumbnail rect edges (px)
TYPE_ICON_SIZE = 36  # Centered file-type icon during loading (px)
BADGE_OPACITY = 0.9  # Overlay badge opacity (0.0 - 1.0)
BADGE_ICON_COLOR = "#ffffff"  # White overlay for badges

# =====================================================================
# Colors -- frame & selection
# =====================================================================

FRAME_COLOR_NORMAL = (100, 100, 100)  # RGB
FRAME_COLOR_HOVER = (100, 150, 255)  # RGB
FRAME_COLOR_SELECTED = (50, 120, 255)  # RGB
FRAME_BG_COLOR_DEFAULT = (100, 100, 100)  # RGB -- default frame fill (no color tag)
FRAME_BG_OPACITY_NORMAL = 0.4  # Frame fill opacity when unselected
FRAME_BG_OPACITY_SELECTED = 0.7  # Frame fill opacity when selected
BACKGROUND_COLOR_SELECTED = (50, 120, 255, 40)  # RGBA

# =====================================================================
# Colors -- video badge
# =====================================================================

VIDEO_BADGE_BACKGROUND = (0, 0, 0, 180)  # RGBA
VIDEO_BADGE_TEXT = (255, 255, 255)  # RGB

# =====================================================================
# Colors -- skeleton placeholder (loading state)
# =====================================================================

SKELETON_BG_COLOR = (42, 44, 50)  # Dark fill -- "still building"
SKELETON_SHAPE_COLOR = (55, 58, 66)  # Inner shape, slightly lighter
SKELETON_SHIMMER_ALPHA = 28  # Shimmer highlight alpha (0-255)

# =====================================================================
# Colors -- no-preview placeholder (permanent state)
# =====================================================================

NO_PREVIEW_BG_COLOR = (48, 50, 56)  # Dark background for non-previewable files
NO_PREVIEW_ICON_SIZE = 48  # Filetype silhouette size (px)
NO_PREVIEW_ICON_OPACITY = 0.88  # 88% opacity for better visibility
NO_PREVIEW_ICON_COLOR = "#6b7280"  # Muted gray for dark background

# =====================================================================
# Colors -- error placeholder (failed thumbnail generation)
# =====================================================================

ERROR_BG_COLOR = (42, 44, 50)  # Dark fill matching skeleton
ERROR_ICON_SIZE = 48  # Warning triangle size (px)
ERROR_ICON_COLOR = "#e06060"  # Muted red warning
ERROR_ICON_OPACITY = 0.7  # Error icon draw opacity

# =====================================================================
# Loading type icon (centered during shimmer)
# =====================================================================

LOADING_TYPE_ICON_SIZE = 48  # Same as no-preview
LOADING_TYPE_ICON_OPACITY = 0.35  # Subtle hint during loading
LOADING_TYPE_ICON_COLOR = "#6b7280"  # Muted gray

# =====================================================================
# Badge opacity (active vs inactive)
# =====================================================================

BADGE_ACTIVE_OPACITY = 0.85
BADGE_INACTIVE_OPACITY = 0.25

# =====================================================================
# LOG profile badge (bottom-right, video files only)
# =====================================================================

LOG_BADGE_COLOR_ACTIVE = "#4ade80"  # Green for detected LOG profile
LOG_BADGE_COLOR_INACTIVE = "#6b7280"  # Gray for no LOG
LOG_BADGE_FONT_SIZE = 7  # Tiny label font size
LOG_BADGE_BG = (0, 0, 0, 140)  # RGBA -- semi-transparent pill behind "L"
LOG_BADGE_TEXT = (255, 255, 255)  # RGB -- "L" text color

# =====================================================================
# Font sizes (pt)
# =====================================================================

THUMBNAIL_FONT_SIZE = 8  # Badge text + filename font size (pt)

# =====================================================================
# Animation timing
# =====================================================================

CROSSFADE_DURATION_MS = 500.0  # Skeleton -> thumbnail fade (ms)

SHIMMER_TICK_MS = 33  # Timer interval (~30 fps)
SHIMMER_PHASE_STEP = 0.025  # Phase advance per tick
# Phase range: 0.0 -> 1.0 = diagonal sweep, 1.0 -> SHIMMER_PHASE_MAX = pause.
# At 33ms tick and 0.025 step: sweep ~1.3s, pause ~0.66s, total cycle ~2s.
SHIMMER_PHASE_MAX = 1.5  # Phase wraps at this value (values > 1.0 = pause)
