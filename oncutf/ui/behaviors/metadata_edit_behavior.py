"""Metadata editing behavior - Backward compatibility re-export.

DEPRECATED: This module re-exports MetadataEditBehavior from the new
metadata_edit package for backward compatibility.
Use `oncutf.ui.behaviors.metadata_edit` instead.
Scheduled for removal in v2.0.

Original Author: Michael Economou
Date: December 28, 2025
Refactored: January 1, 2026
"""
import warnings

warnings.warn(
    "oncutf.ui.behaviors.metadata_edit_behavior is deprecated. "
    "Use oncutf.ui.behaviors.metadata_edit instead. "
    "This module will be removed in v2.0.",
    DeprecationWarning,
    stacklevel=2,
)

from oncutf.ui.behaviors.metadata_edit import (
    EditableWidget,
    MetadataEditBehavior,
)

__all__ = ["MetadataEditBehavior", "EditableWidget"]
