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

FRAME_BORDER_WIDTH = 1
FRAME_PADDING = 4  # Space between frame border and thumbnail
FILENAME_HEIGHT = 25  # Space below thumbnail for filename text
FILENAME_MARGIN = 2  # Vertical gap between frame bottom and filename top

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

# Single stable border color used in ALL states (idle, hover, selected,
# loading, ready, failed). Visual feedback comes from the cell background
# fill, not from changing the border color.
FRAME_COLOR_NORMAL = (58, 59, 64)  # RGB -- #3a3b40
FRAME_COLOR_HOVER = (58, 59, 64)  # RGB -- same as normal (no state change)
FRAME_COLOR_SELECTED = (58, 59, 64)  # RGB -- same as normal (no state change)

# Default frame interior fill when no color tag is set. Letterbox-dark
# so the frame looks identical before and after the thumbnail loads.
FRAME_BG_COLOR_DEFAULT = (26, 26, 26)  # RGB -- #1a1a1a (letterbox)
FRAME_BG_OPACITY_NORMAL = 1.0  # Solid fill
FRAME_BG_OPACITY_SELECTED = 1.0  # Solid fill (selection shows on cell bg, not frame)

# Cell-level backgrounds (fill the whole option.rect including the
# filename row, so hover/selection visually wrap around the filename).
BACKGROUND_COLOR_HOVER = (10, 26, 42)  # RGBA -- #0a1a2a
BACKGROUND_COLOR_SELECTED = (116, 140, 171)  # RGB -- #748cab
TEXT_COLOR_SELECTED = "#0d1321"  # Dark navy for legibility on selected bg

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
# SVG icon recolored, no pill background.
# =====================================================================

LOG_BADGE_COLOR_ACTIVE = "#00fe00"  # Pure green
LOG_BADGE_COLOR_INACTIVE = "#ffffff"  # White when LOG not detected
LOG_BADGE_OPACITY_INACTIVE = 0.35  # Dimmed when no LOG profile present
LOG_BADGE_OPACITY_ACTIVE = 0.90  # Prominent when LOG detected

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
