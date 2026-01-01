"""Metadata editing behavior - Backward compatibility re-export.

This module re-exports MetadataEditBehavior from the new metadata_edit package
for backward compatibility. All code should import from this location.

Original Author: Michael Economou
Date: December 28, 2025
Refactored: January 1, 2026
"""

# Re-export for backward compatibility
from oncutf.ui.behaviors.metadata_edit import (
    EditableWidget,
    MetadataEditBehavior,
)

__all__ = ["MetadataEditBehavior", "EditableWidget"]
