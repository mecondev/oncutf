# Technical Plan: MainWindow Modularization via Delegate Files + UI Specs

**Author:** Michael Economou  
**Date:** 2026-01-10  
**Status:** Phase 0 COMPLETED - Delegate extraction successful

**Achievement:** MainWindow reduced from 695 lines to 99 lines (85.7% reduction)

---

## 1. Overview

Plan to decompose MainWindow into:
1. **Delegate files** - Group ~50 delegate methods by concern into separate files
2. **UI spec files** - Extract specifications (shortcuts, menus) following `viewport_specs.py` pattern

This reduces MainWindow from 695 lines to ~150 lines (initialization only).

### Goals

1. **Reduce MainWindow size** from 695 lines to ~150 lines (core initialization only)
2. **Extract delegates** into logical groups in `oncutf/ui/main_window_delegates/`
3. **Extract UI specifications** into dedicated `oncutf/ui/*_specs.py` modules
4. **Improve testability** - delegates and specs can be tested independently
5. **Enable reusability** - specs can be imported independently
6. **Follow architecture guidelines** from `migration_stance.md`

### Current State Analysis

**MainWindow (695 lines) contains:**
- 50+ delegate methods to handlers/managers (KEEP - this is correct pattern)
- 0 UI specifications currently in MainWindow (already extracted via handlers)
- Initialization delegated to `InitializationOrchestrator` (GOOD)

**Already Extracted (ui/handlers/):**
- `window_event_handler.py` - Window events, geometry
- `shortcut_command_handler.py` - Keyboard shortcuts
- `metadata_signal_handler.py` - Metadata signals
- `config_column_handler.py` - Column configuration
- `shutdown_lifecycle_handler.py` - Shutdown logic

**Candidates for Extraction:**
1. Keyboard shortcuts specifications
2. Menu/context menu specifications
3. Status bar specifications
4. Column specifications (already in column_service.py)
5. Toolbar specifications (if added in future)

---

## 2. Architecture Decision

### 2.1 What Should Be Specs Modules?

**YES - Extract to specs modules:**
- Static data definitions (NamedTuples, dataclasses)
- Configuration constants
- UI element specifications (buttons, menus, shortcuts)
- Layout constants

**NO - Keep in handlers/controllers:**
- Logic and behavior
- Signal connections
- Event handling
- State management

### 2.2 Module Naming Convention

```
oncutf/ui/
  viewport_specs.py      # DONE - Viewport button specs
  shortcut_specs.py      # NEW - Keyboard shortcut definitions
  menu_specs.py          # NEW - Menu/context menu definitions
  column_specs.py        # NEW - Table column definitions
  status_specs.py        # FUTURE - Status bar messages/colors
  toolbar_specs.py       # FUTURE - Toolbar button definitions
```

---

## 3. Phase 1: Keyboard Shortcuts Extraction

### 3.1 Current State

Shortcuts are defined in `ShortcutManager._setup_shortcuts()`:

```python
# oncutf/core/ui_managers/shortcut_manager.py (lines ~50-150)
shortcuts = [
    ("Ctrl+A", self.parent_window.select_all_rows),
    ("Ctrl+D", self.parent_window.clear_all_selection),
    ...
]
```

### 3.2 Target State

**New file: `oncutf/ui/shortcut_specs.py`**

```python
"""
Keyboard shortcut specifications for oncutf.

Author: Michael Economou
Date: 2026-01-10
"""

from typing import NamedTuple


class ShortcutSpec(NamedTuple):
    """Specification for a keyboard shortcut."""

    key_sequence: str        # Qt key sequence (e.g., "Ctrl+A")
    action_name: str         # Method name to call (e.g., "select_all_rows")
    description: str         # Human-readable description
    category: str = "General"  # Grouping for help dialog


# Keyboard shortcut specifications - single source of truth
SHORTCUT_SPECS: list[ShortcutSpec] = [
    # Selection
    ShortcutSpec("Ctrl+A", "select_all_rows", "Select all files", "Selection"),
    ShortcutSpec("Ctrl+D", "clear_all_selection", "Clear selection", "Selection"),
    ShortcutSpec("Ctrl+I", "invert_selection", "Invert selection", "Selection"),
    
    # Metadata
    ShortcutSpec("F5", "shortcut_load_metadata", "Load fast metadata", "Metadata"),
    ShortcutSpec("Shift+F5", "shortcut_load_extended_metadata", "Load extended metadata", "Metadata"),
    ShortcutSpec("Ctrl+S", "shortcut_save_selected_metadata", "Save selected metadata", "Metadata"),
    ShortcutSpec("Ctrl+Shift+S", "shortcut_save_all_metadata", "Save all metadata", "Metadata"),
    
    # Operations
    ShortcutSpec("F2", "rename_files", "Execute rename", "Operations"),
    ShortcutSpec("Ctrl+H", "shortcut_calculate_hash_selected", "Calculate hash", "Operations"),
    ShortcutSpec("Delete", "clear_file_table_shortcut", "Clear file table", "Operations"),
    
    # Undo/Redo
    ShortcutSpec("Ctrl+Z", "global_undo", "Undo", "Edit"),
    ShortcutSpec("Ctrl+Shift+Z", "global_redo", "Redo", "Edit"),
    ShortcutSpec("Ctrl+Y", "show_command_history", "Command history", "Edit"),
    
    # View
    ShortcutSpec("Ctrl+Shift+C", "auto_color_by_folder", "Auto-color by folder", "View"),
    ShortcutSpec("Escape", "force_drag_cleanup", "Cancel drag operation", "View"),
]
```

### 3.3 Changes to ShortcutManager

```python
# oncutf/core/ui_managers/shortcut_manager.py

from oncutf.ui.shortcut_specs import SHORTCUT_SPECS

class ShortcutManager:
    def _setup_shortcuts(self) -> None:
        """Setup keyboard shortcuts from specifications."""
        for spec in SHORTCUT_SPECS:
            handler = getattr(self.parent_window, spec.action_name, None)
            if handler:
                shortcut = QShortcut(QKeySequence(spec.key_sequence), self.parent_window)
                shortcut.activated.connect(handler)
                self._shortcuts.append(shortcut)
            else:
                logger.warning("Shortcut handler not found: %s", spec.action_name)
```

### 3.4 Benefits

1. **Help dialog generation** - Can iterate SHORTCUT_SPECS to show all shortcuts
2. **Conflict detection** - Can check for duplicate key sequences
3. **Testing** - Can test shortcut definitions without Qt
4. **Documentation** - Self-documenting with descriptions and categories

---

## 4. Phase 2: Context Menu Extraction

### 4.1 Target State

**New file: `oncutf/ui/menu_specs.py`**

```python
"""
Menu and context menu specifications for oncutf.

Author: Michael Economou
Date: 2026-01-10
"""

from typing import NamedTuple


class MenuItemSpec(NamedTuple):
    """Specification for a menu item."""

    id: str                  # Unique identifier
    label: str               # Display text
    action_name: str         # Method name to call
    icon_name: str = ""      # Icon name (optional)
    shortcut: str = ""       # Keyboard shortcut hint
    separator_after: bool = False  # Add separator after this item


class MenuGroupSpec(NamedTuple):
    """Specification for a menu group."""

    id: str                  # Unique identifier
    label: str               # Group label (for submenus)
    items: list[MenuItemSpec]


# File table context menu specifications
FILE_TABLE_CONTEXT_MENU: list[MenuItemSpec | MenuGroupSpec] = [
    MenuItemSpec("open", "Open", "handle_open_file", "folder-open"),
    MenuItemSpec("open_folder", "Open containing folder", "handle_open_folder", "folder"),
    MenuItemSpec("separator1", "", "", separator_after=True),
    
    MenuGroupSpec("metadata", "Metadata", [
        MenuItemSpec("load_meta", "Load metadata", "shortcut_load_metadata", "database", "F5"),
        MenuItemSpec("load_ext_meta", "Load extended metadata", "shortcut_load_extended_metadata", "database", "Shift+F5"),
    ]),
    
    MenuItemSpec("separator2", "", "", separator_after=True),
    MenuItemSpec("select_all", "Select all", "select_all_rows", "check-square", "Ctrl+A"),
    MenuItemSpec("clear_sel", "Clear selection", "clear_all_selection", "square", "Ctrl+D"),
]
```

---

## 5. Phase 3: Column Specifications (Optional)

Column specs already exist in `column_service.py`. Could be extracted to `column_specs.py`
if the file grows too large, but currently not necessary.

---

## 6. Phase 0: Delegate File Extraction (CHOSEN APPROACH)

### 6.1 Strategy: Option C - Delegate Composition Files

Extract MainWindow's ~50 delegate methods into logical groups:

```
oncutf/ui/
├── main_window.py                    # Core (150 lines) - init only
├── main_window_delegates/            # NEW folder
│   ├── __init__.py
│   ├── selection_delegates.py        # select_all, clear_selection, invert
│   ├── metadata_delegates.py         # load_metadata, save_metadata, shortcuts
│   ├── file_operation_delegates.py   # load_files, clear_table, browse
│   ├── preview_delegates.py          # update_preview, generate_names
│   ├── table_delegates.py            # sort_by_column, prepare_table
│   ├── event_delegates.py            # context_menu, double_click, splitter
│   ├── utility_delegates.py          # get_selected, find_item, update_label
│   ├── validation_delegates.py       # confirm_large_folder, check_large_files
│   └── window_delegates.py           # resize, close, center, config
```

### 6.2 MainWindow Structure After Refactoring

```python
# oncutf/ui/main_window.py
from oncutf.ui.main_window_delegates import (
    SelectionDelegates,
    MetadataDelegates,
    FileOperationDelegates,
    PreviewDelegates,
    TableDelegates,
    EventDelegates,
    UtilityDelegates,
    ValidationDelegates,
    WindowDelegates,
)

class MainWindow(
    SelectionDelegates,
    MetadataDelegates,
    FileOperationDelegates,
    PreviewDelegates,
    TableDelegates,
    EventDelegates,
    UtilityDelegates,
    ValidationDelegates,
    WindowDelegates,
    QMainWindow
):
    """Main application window.
    
    This class only contains initialization.
    All operations are delegated to handlers via delegate classes.
    """
    
    def __init__(self, theme_callback=None):
        super().__init__()
        # ... initialization only (use InitializationOrchestrator)
```

### 6.3 Benefits of Option C

1. **No API changes** - Existing code continues to work: `main_window.select_all_rows()`
2. **Not mixins** - Just logical grouping of delegates (no business logic)
3. **Better navigation** - Know exactly which file contains which delegate
4. **Easier testing** - Can test delegate groups independently
5. **Smaller files** - Each delegate file ~50-100 lines max
6. **Clear separation** - MainWindow = initialization, Delegates = forwarding

---

## 7. Implementation Order

| Phase | Module | Priority | Effort | Impact |
|-------|--------|----------|--------|--------|
| **0** | **Delegate extraction** | **HIGH** | **4h** | **MainWindow 695→150 lines** |
| 1 | `shortcut_specs.py` | HIGH | 2h | Help dialog, conflict detection |
| 2 | `menu_specs.py` | MEDIUM | 3h | Context menu consistency |
| 3 | `column_specs.py` | LOW | 1h | Already in column_service.py |
| 4 | `status_specs.py` | LOW | 1h | Status message standardization |
| 5 | `toolbar_specs.py` | FUTURE | 2h | When toolbar is added |

---

## 8. Files to Create/Modify

### Phase 0 (Delegate Extraction)

| File | Change Type | Description |
|------|-------------|-------------|
| `oncutf/ui/main_window_delegates/__init__.py` | **Create** | Export all delegate classes |
| `oncutf/ui/main_window_delegates/selection_delegates.py` | **Create** | Selection operations |
| `oncutf/ui/main_window_delegates/metadata_delegates.py` | **Create** | Metadata operations |
| `oncutf/ui/main_window_delegates/file_operation_delegates.py` | **Create** | File load/browse operations |
| `oncutf/ui/main_window_delegates/preview_delegates.py` | **Create** | Preview operations |
| `oncutf/ui/main_window_delegates/table_delegates.py` | **Create** | Table operations |
| `oncutf/ui/main_window_delegates/event_delegates.py` | **Create** | Event handling |
| `oncutf/ui/main_window_delegates/utility_delegates.py` | **Create** | Utility operations |
| `oncutf/ui/main_window_delegates/validation_delegates.py` | **Create** | Validation operations |
| `oncutf/ui/main_window_delegates/window_delegates.py` | **Create** | Window lifecycle |
| `oncutf/ui/main_window.py` | **Modify** | Remove delegates, inherit from delegate classes |

### Phase 1 (Shortcuts)

| File | Change Type | Description |
|------|-------------|-------------|
| `oncutf/ui/shortcut_specs.py` | **Create** | ShortcutSpec + SHORTCUT_SPECS |
| `oncutf/core/ui_managers/shortcut_manager.py` | **Modify** | Use SHORTCUT_SPECS |

### Phase 2 (Menus)

| File | Change Type | Description |
|------|-------------|-------------|
| `oncutf/ui/menu_specs.py` | **Create** | MenuItemSpec + menu definitions |
| `oncutf/core/ui_managers/event_handler_manager.py` | **Modify** | Use menu specs |

---

## 9. Validation Checklist

### Phase 0 (Delegates) - COMPLETED ✓

- [x] All 9 delegate files created in `main_window_delegates/`
- [x] `__init__.py` exports all delegate classes
- [x] MainWindow inherits from all delegates
- [x] MainWindow reduced to 99 lines (from 695 - 85.7% reduction!)
- [x] Application runs without errors
- [x] All existing functionality works
- [x] `ruff check .` passes
- [x] `mypy .` passes
- [x] `pytest` passes (1000 passed, 6 skipped)
- [x] eventFilter recursion issue resolved (removed from EventDelegates)

### Phase 1 (Shortcuts)

- [ ] `shortcut_specs.py` created with ShortcutSpec NamedTuple
- [ ] All shortcuts from ShortcutManager moved to SHORTCUT_SPECS
- [ ] ShortcutManager reads from SHORTCUT_SPECS
- [ ] All shortcuts work as before
- [ ] `ruff check .` passes
- [10] `mypy .` passes
- [ ] `pytest` passes

### Phase 2 (Menus)

- [ ] `menu_specs.py` created with MenuItemSpec NamedTuple
- [ ] Context menu reads from specs
- [ ] All menu items work as before
- [ ] Quality gates pass

---

## 9. Future Considerations

### Keyboard Shortcut Help Dialog

With SHORTCUT_SPECS, a help dialog can be auto-generated:

```python
def show_shortcuts_help(self):
    """Show dialog with all available keyboard shortcuts."""
    from oncutf.ui.shortcut_specs import SHORTCUT_SPECS
    
    # Group by category
    by_category = {}
    for spec in SHORTCUT_SPECS:
        by_category.setdefault(spec.category, []).append(spec)
    
    # Build help text
    help_text = []
    for category, shortcuts in sorted(by_category.items()):
        help_text.append(f"\n{category}:")
        for s in shortcuts:
            help_text.append(f"  {s.key_sequence:20} {s.description}")
    
    # Show dialog...
```

### Shortcut Customization
1
Specs pattern enables future shortcut customization:

```python
# User can override default shortcuts
USER_SHORTCUT_OVERRIDES = {
    "select_all_rows": "Ctrl+Shift+A",  # Override default
}
```

---

## 10. References

- Pattern source: `oncutf/ui/viewport_specs.py`
- Architecture guidelines: `docs/migration_stance.md`
- Current shortcuts: `oncutf/core/ui_managers/shortcut_manager.py`
- Context menus: `oncutf/core/ui_managers/event_handler_manager.py`
