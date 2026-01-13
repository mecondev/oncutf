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

import warnings as _warnings

_warnings.filterwarnings("once", category=DeprecationWarning, module=__name__)

_DEPRECATION_SHOWN = False


def _show_deprecation_hint() -> None:
    """Show deprecation hint once on first wildcard import."""
    global _DEPRECATION_SHOWN
    if not _DEPRECATION_SHOWN:
        _warnings.warn(
            "Importing all UI config via 'from oncutf.config.ui import *' works but is not recommended. "
            "For better clarity, import from specific modules: "
            "oncutf.config.ui.fonts, oncutf.config.ui.theme, oncutf.config.ui.sizing, "
            "oncutf.config.ui.layout, oncutf.config.ui.components",
            DeprecationWarning,
            stacklevel=3,
        )
        _DEPRECATION_SHOWN = True


_show_deprecation_hint()

from oncutf.config.ui.components import *  # noqa: F401, F403, E402
from oncutf.config.ui.fonts import *  # noqa: F401, F403, E402
from oncutf.config.ui.layout import *  # noqa: F401, F403, E402
from oncutf.config.ui.sizing import *  # noqa: F401, F403, E402
from oncutf.config.ui.theme import *  # noqa: F401, F403, E402
