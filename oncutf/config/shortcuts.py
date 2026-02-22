"""Module: oncutf.config.shortcuts.

Author: Michael Economou
Date: 2026-01-01

Keyboard shortcuts configuration.
"""

# =====================================
# KEYBOARD SHORTCUTS CONFIGURATION
# =====================================

# Common refresh key used by multiple widgets
REFRESH_KEY = "F5"

# File Table shortcuts (work when FileListView has focus)
FILE_TABLE_SHORTCUTS = {
    "SELECT_ALL": "Ctrl+A",
    "CLEAR_SELECTION": "Ctrl+Shift+A",
    "INVERT_SELECTION": "Ctrl+I",
    "LOAD_METADATA": "Ctrl+M",
    "LOAD_EXTENDED_METADATA": "Ctrl+Shift+M",
    "CALCULATE_HASH": "Ctrl+H",
    "REFRESH": REFRESH_KEY,
}

# File Tree shortcuts (work when FileTreeView has focus)
FILE_TREE_SHORTCUTS = {
    "REFRESH": REFRESH_KEY,
}

# Metadata Tree shortcuts (work when MetadataTreeView has focus)
METADATA_TREE_SHORTCUTS = {
    "REFRESH": REFRESH_KEY,
}

# Preview shortcuts (work when PreviewTablesView has focus)
PREVIEW_SHORTCUTS = {
    "REFRESH": REFRESH_KEY,
}

# Global shortcuts (work regardless of which widget has focus)
GLOBAL_SHORTCUTS = {
    "BROWSE_FOLDER": "Ctrl+O",
    "SAVE_METADATA": "Ctrl+S",
    "CANCEL_DRAG": "Escape",
    "CLEAR_FILE_TABLE": "Shift+Escape",
    "UNDO": "Ctrl+Z",
    "REDO": "Ctrl+Shift+Z",
    "SHOW_HISTORY": "Ctrl+Y",
}

# Column operation shortcuts
COLUMN_SHORTCUTS = {
    "AUTO_FIT_CONTENT": "Ctrl+T",
    "RESET_TO_DEFAULT": "Ctrl+Shift+T",
}
