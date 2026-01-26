"""Delegator module for backward compatibility.

DEPRECATED: ApplicationContext has moved to ui.adapters.application_context.
This module will be removed in v2.0.

Author: Michael Economou
Date: 2026-01-27

Migration path:
- UI code: Use QtAppContext from oncutf.ui.adapters.qt_app_context
- Non-UI code: Use AppContext from oncutf.app.state.context
- Legacy code: Temporarily use oncutf.ui.adapters.application_context
"""

import warnings

warnings.warn(
    "oncutf.core.application_context is deprecated. "
    "Use QtAppContext from ui.adapters or AppContext from app.state instead. "
    "Will be removed in v2.0.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export for backward compatibility
from oncutf.ui.adapters.application_context import (  # noqa: F401, E402
    ApplicationContext,
    get_app_context,
)

__all__ = ["ApplicationContext", "get_app_context"]
