"""Filesystem utilities package.

Helpers for path operations, file grouping, size formatting, etc.
"""

# Explicit re-exports for backward compatibility (avoid circular imports)
from oncutf.utils.filesystem.path_normalizer import normalize_path
from oncutf.utils.filesystem.path_utils import paths_equal

__all__ = [
    "normalize_path",
    "paths_equal",
]
