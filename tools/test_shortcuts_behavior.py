#!/usr/bin/env python3
"""Test script for keyboard shortcuts behavior in file_table and results_table.

Tests:
1. Ctrl+T: Auto-fit columns to content (filename stretches, others fit content)
2. Ctrl+Shift+T: Reset to default widths from config
3. Context menu styling (should use global theme, not local styles)
4. Metadata tree vertical alignment (should use MetadataTreeItemDelegate)
"""

import sys
from pathlib import Path

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 60)
print("KEYBOARD SHORTCUTS BEHAVIOR TEST")
print("=" * 60)
print()
print("Expected behavior:")
print()
print("1. FILE TABLE & RESULTS TABLE:")
print("   - Ctrl+T: Auto-fit columns to content")
print("     * filename: stretches to fill available space")
print("     * other columns: resize to fit their content")
print()
print("   - Ctrl+Shift+T: Reset to default widths")
print("     * All columns return to config defaults")
print("     * All columns use Interactive resize mode")
print()
print("2. CONTEXT MENUS (all widgets):")
print("   - Use global theme styling")
print("   - NO local setStyleSheet() calls")
print("   - Consistent hover/pressed colors across app")
print()
print("3. METADATA TREE:")
print("   - Uses MetadataTreeItemDelegate")
print("   - Proper vertical center alignment")
print("   - Text aligned like file_tree (not too high in cells)")
print()
print("=" * 60)
print()
print("To test manually:")
print("1. Run the main app: python main.py")
print("2. Load some files")
print("3. Try Ctrl+T and Ctrl+Shift+T in file table")
print("4. Open hash verification and try same shortcuts")
print("5. Right-click context menus (file table, metadata tree)")
print("   - Check hover color consistency")
print("6. Check metadata tree - text should be vertically centered")
print()
