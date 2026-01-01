"""file_table_model.py - Backward compatibility re-export.

This module re-exports FileTableModel from the new file_table package
for backward compatibility. All code should import from this location.

Original Author: Michael Economou
Date: 2025-05-01
Refactored: 2026-01-01
"""

# Re-export FileTableModel for backward compatibility
from oncutf.models.file_table import FileTableModel

__all__ = ["FileTableModel"]
