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

FRAME_COLOR_NORMAL = (200, 200, 200)  # RGB
FRAME_COLOR_HOVER = (100, 150, 255)  # RGB
FRAME_COLOR_SELECTED = (50, 120, 255)  # RGB
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

NO_PREVIEW_BG_COLOR = (210, 210, 210)  # Light grey background for non-image files
NO_PREVIEW_ICON_SIZE = 48  # Filetype silhouette size (px)
NO_PREVIEW_ICON_OPACITY = 0.88  # 88% opacity for better visibility
NO_PREVIEW_ICON_COLOR = "#4a5568"  # Dark gray-blue for contrast with light bg

# =====================================================================
# Animation timing
# =====================================================================

CROSSFADE_DURATION_MS = 500.0  # Skeleton -> thumbnail fade (ms)

SHIMMER_TICK_MS = 33  # Timer interval (~30 fps)
SHIMMER_PHASE_STEP = 0.025  # Phase advance per tick
# Phase range: 0.0 -> 1.0 = diagonal sweep, 1.0 -> SHIMMER_PHASE_MAX = pause.
# At 33ms tick and 0.025 step: sweep ~1.3s, pause ~0.66s, total cycle ~2s.
SHIMMER_PHASE_MAX = 1.5  # Phase wraps at this value (values > 1.0 = pause)
