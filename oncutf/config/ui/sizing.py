"""Window and screen sizing configuration.

Author: Michael Economou
Date: 2026-01-13

Smart window sizing, breakpoints, and screen-aware defaults.
"""

SCREEN_SIZE_BREAKPOINTS = {
    "large_4k": 2560,
    "full_hd": 1920,
    "laptop": 1366,
}

SCREEN_SIZE_PERCENTAGES = {
    "large_4k": {"width": 0.80, "height": 0.80},
    "full_hd": {"width": 0.85, "height": 0.85},
    "laptop": {"width": 0.90, "height": 0.90},
    "small": {"width": 0.95, "height": 0.95},
}

WINDOW_MIN_SMART_WIDTH = 1000
WINDOW_MIN_SMART_HEIGHT = 700
LARGE_SCREEN_MIN_WIDTH = 1400
LARGE_SCREEN_MIN_HEIGHT = 900

WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 900
WINDOW_MIN_WIDTH = 800
WINDOW_MIN_HEIGHT = 500

WIDE_SCREEN_THRESHOLD = 1920
ULTRA_WIDE_SCREEN_THRESHOLD = 2560

SPLASH_SCREEN_DURATION = 2000
WAIT_CURSOR_SUPPRESS_AFTER_SPLASH_MS = 1000
