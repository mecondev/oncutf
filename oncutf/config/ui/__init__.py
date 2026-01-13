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

from oncutf.config.ui.components import *
from oncutf.config.ui.fonts import *
from oncutf.config.ui.layout import *
from oncutf.config.ui.sizing import *
from oncutf.config.ui.theme import *
