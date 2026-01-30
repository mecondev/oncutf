"""UI configuration subsystem.

Author: Michael Economou
Date: 2026-01-13

Centralized UI configuration split by responsibility:
- fonts: Font system (families, sizes, widget overrides)
- theme: Color system (themes, tokens, semantic colors)
- layout: Layout structure (margins, splitters, constraints)
- sizing: Window sizing (breakpoints, smart sizing)
- components: Component-specific settings (icons, dialogs, etc.)

All constants are re-exported for backward compatibility.

For better clarity and IDE support, prefer importing from specific modules:
    from oncutf.config.ui.fonts import DEFAULT_UI_FONT
    from oncutf.config.ui.theme import THEME_COLORS
    from oncutf.config.ui.sizing import WINDOW_WIDTH
    from oncutf.config.ui.layout import LEFT_PANEL_MIN_WIDTH
    from oncutf.config.ui.components import ICON_SIZES
"""

# oncutf.config.ui.components
from oncutf.config.ui.components import (
    COLOR_GRID_COLS,
    COLOR_GRID_ROWS,
    COLOR_PICKER_IMAGE,
    COLOR_SWATCH_SIZE,
    CONTENT_MARGINS,
    DEFAULT_PREVIEW_ICON_SIZE,
    FILE_TAG_COLOR_ARRAY,
    HASH_LIST_CONTENT_MARGINS,
    HASH_LIST_FONT_SIZE,
    HASH_LIST_HEADER_ALIGNMENT,
    HASH_LIST_LABEL_BACKGROUND,
    HASH_LIST_ROW_HEIGHT,
    HASH_LIST_WINDOW_DEFAULT_HEIGHT,
    HASH_LIST_WINDOW_DEFAULT_WIDTH,
    HASH_LIST_WINDOW_MAX_HEIGHT,
    HASH_LIST_WINDOW_MIN_HEIGHT,
    ICON_SIZES,
    MAX_LABEL_LENGTH,
    METADATA_TREE_COLUMN_WIDTHS,
    METADATA_TREE_USE_CUSTOM_DELEGATE,
    METADATA_TREE_USE_PROXY,
    PREVIEW_INDICATOR_BORDER,
    PREVIEW_INDICATOR_SHAPE,
    PREVIEW_INDICATOR_SIZE,
    RESULTS_TABLE_DEFAULT_HEIGHT,
    RESULTS_TABLE_DEFAULT_WIDTH,
    RESULTS_TABLE_LEFT_COLUMN_WIDTH,
    RESULTS_TABLE_MAX_HEIGHT,
    RESULTS_TABLE_MIN_HEIGHT,
    RESULTS_TABLE_MIN_WIDTH,
    RESULTS_TABLE_RIGHT_COLUMN_WIDTH,
    STATUS_AUTO_RESET_DELAY,
    TOOLTIP_DURATION,
    TOOLTIP_POSITION_OFFSET,
)

# oncutf.config.ui.fonts
from oncutf.config.ui.fonts import (
    DEFAULT_DATA_FONT,
    DEFAULT_UI_FONT,
    FONT_FAMILIES,
    FONT_SIZE_ADJUSTMENTS,
    USE_EMBEDDED_FONTS,
    WIDGET_FONTS,
    get_ui_font_family,
)

# oncutf.config.ui.layout
from oncutf.config.ui.layout import (
    LEFT_PANEL_MAX_WIDTH,
    LEFT_PANEL_MIN_WIDTH,
    LOWER_SECTION_LEFT_MIN_SIZE,
    LOWER_SECTION_RIGHT_MIN_SIZE,
    LOWER_SECTION_SPLIT_RATIO,
    PREVIEW_COLUMN_WIDTH,
    PREVIEW_MIN_WIDTH,
    RIGHT_PANEL_MAX_WIDTH,
    RIGHT_PANEL_MIN_WIDTH,
    TOP_BOTTOM_SPLIT_RATIO,
)

# oncutf.config.ui.sizing
from oncutf.config.ui.sizing import (
    LARGE_SCREEN_MIN_HEIGHT,
    LARGE_SCREEN_MIN_WIDTH,
    SCREEN_SIZE_BREAKPOINTS,
    SCREEN_SIZE_PERCENTAGES,
    SPLASH_SCREEN_DURATION,
    ULTRA_WIDE_SCREEN_THRESHOLD,
    WAIT_CURSOR_SUPPRESS_AFTER_SPLASH_MS,
    WIDE_SCREEN_THRESHOLD,
    WINDOW_HEIGHT,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_SMART_HEIGHT,
    WINDOW_MIN_SMART_WIDTH,
    WINDOW_MIN_WIDTH,
    WINDOW_WIDTH,
)

# oncutf.config.ui.theme
from oncutf.config.ui.theme import (
    CONTEXT_MENU_COLORS,
    EXTENDED_METADATA_BG_COLOR,
    EXTENDED_METADATA_COLOR,
    FAST_METADATA_BG_COLOR,
    FAST_METADATA_COLOR,
    FILE_LOADING_BG_COLOR,
    FILE_LOADING_COLOR,
    HASH_CALCULATION_BG_COLOR,
    HASH_CALCULATION_COLOR,
    METADATA_ICON_COLORS,
    PREVIEW_COLORS,
    QLABEL_BORDER_GRAY,
    QLABEL_DARK_BG,
    QLABEL_DARK_BORDER,
    QLABEL_ERROR_BG,
    QLABEL_ERROR_TEXT,
    QLABEL_INFO_TEXT,
    QLABEL_MUTED_TEXT,
    QLABEL_PRIMARY_TEXT,
    QLABEL_SECONDARY_TEXT,
    QLABEL_TERTIARY_TEXT,
    QLABEL_WHITE_TEXT,
    SAVE_BG_COLOR,
    SAVE_COLOR,
    STATUS_COLORS,
    THEME_COLORS,
    THEME_NAME,
    THEME_TOKENS,
)
