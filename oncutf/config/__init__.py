"""Module: oncutf.config

Author: Michael Economou
Date: 2026-01-01

Configuration package for oncutf application.

This package organizes configuration into logical modules:
- app: Application info, debug flags, logging
- paths: File paths, extensions, validation patterns
- ui: UI settings, themes, colors, fonts
- columns: Column configurations for tables and trees
- features: Feature flags, external tools, limits
- shortcuts: Keyboard shortcuts

All settings are re-exported from this module for backward compatibility:
    from oncutf.config import APP_NAME, THEME_COLORS  # Works as before
"""

# Re-export everything for backward compatibility
from oncutf.config.app import *  # noqa: F401, F403
from oncutf.config.columns import *  # noqa: F401, F403
from oncutf.config.features import *  # noqa: F401, F403
from oncutf.config.paths import *  # noqa: F401, F403
from oncutf.config.shortcuts import *  # noqa: F401, F403
from oncutf.config.ui import *  # noqa: F401, F403
