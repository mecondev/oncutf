# Keyboard Shortcuts Reference

Complete keyboard shortcuts guide for oncutf application.

## Global Shortcuts

These shortcuts work throughout the application, regardless of which widget has focus.

### File Operations
| Shortcut | Action | Description |
|----------|--------|-------------|
| `Ctrl+O` | Browse Files | Open file browser to select files/folders |
| `F5` | Force Reload | Reload current folder and refresh file list |
| `Escape` | Cancel Drag | Cancel current drag & drop operation |
| `Shift+Escape` | Clear Table | Clear all files from file table |

### Selection Management
| Shortcut | Action | Description |
|----------|--------|-------------|
| `Ctrl+A` | Select All | Select all files in file table |
| `Ctrl+Shift+A` | Clear Selection | Deselect all files |
| `Ctrl+I` | Invert Selection | Invert current selection |

### Metadata Operations
| Shortcut | Action | Description |
|----------|--------|-------------|
| `Ctrl+M` | Load Basic Metadata | Load basic metadata for selected files (file table) |
| `Ctrl+E` | Load Extended Metadata | Load extended metadata for selected files (file table) |
| `Ctrl+Shift+M` | Load All Basic Metadata | Load basic metadata for all files (file table) |
| `Ctrl+Shift+E` | Load All Extended Metadata | Load extended metadata for all files (file table) |
| `Ctrl+S` | Save Selected Metadata | Save metadata changes for selected files (file table) |
| `Ctrl+Shift+S` | Save All Metadata | Save metadata changes for all files (file table) |

### Hash Operations
| Shortcut | Action | Description |
|----------|--------|-------------|
| `Ctrl+H` | Calculate Hash (Selected) | Calculate CRC32 checksums for selected files (file table) |
| `Ctrl+Shift+H` | Calculate Hash (All) | Calculate CRC32 checksums for all files (file table) |
| `Ctrl+L` | Show Results List | Display hash calculation results dialog |

### History & Dialogs
| Shortcut | Action | Description |
|----------|--------|-------------|
| `Ctrl+Shift+Z` | Command History | Show complete command history dialog |

**Note:** All File Table shortcuts (prefixed above) only work when the file table widget has focus.

---

## Widget-Specific Shortcuts

These shortcuts only work when specific widgets have keyboard focus.

### Metadata Tree Shortcuts

Active only when the metadata tree widget has focus.

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Ctrl+Z` | Undo | Undo last metadata field edit |
| `Ctrl+R` | Redo | Redo last undone metadata field edit |

**Note:** These shortcuts are also shown in the metadata tree context menu.

---

## Drag & Drop Modifiers

Special keyboard modifiers that change drag & drop behavior.

### From File Tree to File Table

| Modifier | Behavior |
|----------|----------|
| None | Skip metadata loading (folders only imported) |
| `Ctrl` | Load basic metadata after import |
| `Ctrl+Shift` | Load extended metadata after import |

### From File Table to Metadata Tree

| Modifier | Behavior |
|----------|----------|
| None | Load fast metadata for dragged file |
| `Shift` | Load extended metadata for dragged file |

---

## Future Shortcuts

Planned shortcuts for upcoming features:

### Rename Module Undo/Redo (Planned)
- Local `Ctrl+Z` / `Ctrl+R` shortcuts in rename module editor
- Will work similarly to metadata tree undo/redo
- Awaiting implementation of rename module undo system

---

## Notes

### Context-Aware Shortcuts

Some shortcuts behave differently based on context:

- **Ctrl+Z / Ctrl+R**: 
  - In metadata tree → undo/redo metadata edits
  - In rename module (future) → undo/redo rename configuration changes
  - Global fallback → show history dialog

### Conflict Resolution

The shortcut system uses this priority order:
1. **Local shortcuts** (widget-specific)
2. **Global shortcuts** (application-wide)
3. **Qt default shortcuts** (built-in Qt behavior)

When a widget has focus, its local shortcuts take precedence over global shortcuts with the same key combination.

### Accessibility

All shortcuts are also accessible through:
- Context menus (right-click)
- Main menu bar
- Toolbar buttons (where applicable)

This ensures the application is usable even without keyboard shortcuts.

---

## Customization

Currently, keyboard shortcuts are **not customizable** and are hardcoded in the application configuration (`config.py`).

Future versions may include:
- User-customizable shortcut mappings
- Shortcut conflict detection
- Shortcut scheme presets (e.g., "Photoshop-like", "VS Code-like")

---

**Last Updated**: November 2025
**Version**: oncutf v2.0+
