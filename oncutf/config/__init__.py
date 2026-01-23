"""Module: oncutf.config.

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
from oncutf.config.app import *
from oncutf.config.columns import *
from oncutf.config.features import *
from oncutf.config.paths import *
from oncutf.config.shortcuts import *
from oncutf.config.ui import *
