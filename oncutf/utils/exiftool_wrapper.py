"""Compatibility re-export for ExifToolWrapper.

DEPRECATED: Import from oncutf.infra.external.exiftool_wrapper instead.

This module exists for backward compatibility only and may be removed in future versions.

Author: Michael Economou
Date: 2026-01-16
"""

import warnings

warnings.warn(
    "Importing from oncutf.utils.exiftool_wrapper is deprecated. "
    "Use 'from oncutf.infra.external.exiftool_wrapper import ExifToolWrapper' instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export for compatibility
from oncutf.infra.external.exiftool_wrapper import ExifToolWrapper

__all__ = ["ExifToolWrapper"]
