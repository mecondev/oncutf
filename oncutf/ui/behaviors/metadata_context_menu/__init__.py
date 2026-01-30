"""Metadata context menu behavior package.

Re-exports main classes for backward compatibility.

Author: Michael Economou
Date: 2026-01-05
"""

from oncutf.ui.behaviors.metadata_context_menu.context_menu_behavior import (
    MetadataContextMenuBehavior,
)
from oncutf.ui.behaviors.metadata_context_menu.protocols import ContextMenuWidget

__all__ = ["ContextMenuWidget", "MetadataContextMenuBehavior"]
