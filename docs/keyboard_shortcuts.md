# Keyboard Shortcuts Reference

Complete keyboard shortcuts guide for oncutf application.

## Global Shortcuts

These shortcuts work throughout the application, regardless of which widget has focus.

### File Operations
| Shortcut | Action | Description |
|----------|--------|-------------|
| `Ctrl+O` | Browse Files | Open file browser to select files/folders |
| `Escape` | Cancel Drag | Cancel current drag & drop operation |
| `Shift+Escape` | Clear Table | Clear all files from file table |

### Selection Management (File Table focus)
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

### Hash Operations (File Table focus)
| Shortcut | Action | Description |
|----------|--------|-------------|
| `Ctrl+H` | Calculate Hash (Selected) | Calculate CRC32 checksums for selected files (file table) |
| `Ctrl+Shift+H` | Calculate Hash (All) | Calculate CRC32 checksums for all files (file table) |
| `Ctrl+L` | Show Results List | Display hash calculation results dialog |

### History & Undo/Redo
| Shortcut | Action | Description |
|----------|--------|-------------|
| `Ctrl+Z` | Undo | Undo last operation (metadata edits, renames, etc.) |
| `Ctrl+Shift+Z` | Redo | Redo last undone operation |
| `Ctrl+Y` | Show History | Display command history dialog with all operations |

**Note:** Undo/Redo are global shortcuts that work across all operations. Currently supports metadata edits; rename undo is planned.

---

## Widget-Specific Shortcuts

These shortcuts work only when the respective widget has focus.

### F5 - Refresh (Widget-Dependent)

The `F5` key performs context-aware refresh based on which widget has focus:

| Widget Focus | Action | Description |
|--------------|--------|-------------|
| **File Table** | Reload Files | Reload files from current folder |
| **File Tree** | Refresh Tree | Refresh file tree view |
| **Metadata Tree** | Refresh Metadata | Reload metadata from current selection |
| **Preview Tables** | Refresh Preview | Recalculate preview from current selection |
| **Rename Modules** | (none) | No action (planned) |

### File Table Shortcuts
| Shortcut | Action |
|----------|--------|
| `Ctrl+T` | Auto-fit columns to content |
| `Ctrl+Shift+T` | Reset columns to default widths |

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

- **F5**: Widget-dependent refresh (see table above)
- **Ctrl+Z / Ctrl+Shift+Z / Ctrl+Y**: 
  - Global shortcuts that work throughout the application
  - Currently handle metadata edits through command manager
  - Future: Will handle rename operations and batch operations in unified history
  - Show History (Ctrl+Y) opens MetadataHistoryDialog (temporary until unified system)

### Conflict Resolution

The shortcut system uses this priority order:
1. **Widget-specific shortcuts** (local to focused widget, highest priority)
2. **Global shortcuts** (application-wide, attached to MainWindow)
3. **Qt default shortcuts** (built-in Qt behavior)

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

**Last Updated**: December 2025
**Version**: oncutf v2.0+
