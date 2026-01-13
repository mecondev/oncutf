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
Import from specific modules for better IDE support and clarity.
"""

from oncutf.config.ui.components import *  # noqa: F401, F403
from oncutf.config.ui.fonts import *  # noqa: F401, F403
from oncutf.config.ui.layout import *  # noqa: F401, F403
from oncutf.config.ui.sizing import *  # noqa: F401, F403
from oncutf.config.ui.theme import *  # noqa: F401, F403
