# UI Manager Migration Plan

**Author:** Michael Economou  
**Date:** 2026-01-02  
**Status:** In Progress

---

## Executive Summary

Migrate UIManager (982 lines, 20 methods) from legacy manager pattern to modern controller architecture.

**Current:** Monolithic UI setup manager with tight coupling to MainWindow  
**Target:** Specialized, testable controllers with clear separation of concerns

---

## Current Analysis

### UIManager Structure (982 lines, 20 methods)

**Initialization & Orchestration:**
1. `__init__(parent_window)` — Store reference
2. `setup_all_ui()` — Master orchestration method
3. `setup_main_window()` — Window properties (size, title, icon)
4. `_calculate_optimal_window_size()` — Adaptive sizing logic
5. `_calculate_optimal_splitter_sizes()` — Splitter sizing
6. `_legacy_calculate_optimal_splitter_sizes()` — Legacy fallback

**Layout Setup (6 methods):**
7. `setup_main_layout()` — Main QHBoxLayout
8. `setup_splitters()` — Create splitters
9. `setup_left_panel()` — File tree + controls
10. `setup_center_panel()` — File table + rename modules
11. `setup_right_panel()` — Metadata tree + preview
12. `setup_bottom_layout()` — Status + progress

**Footer & UI Elements:**
13. `setup_footer()` — Footer labels and links
14. `setup_signals()` — Signal connections
15. `setup_shortcuts()` — Keyboard shortcuts

**Helpers (5 methods):**
16. `_refresh_file_table()` — Table refresh helper
17. `_show_search_context_menu()` — Context menu for search
18. `_on_metadata_search_text_changed()` — Search handler
19. `_clear_metadata_search()` — Clear search
20. `restore_metadata_search_text()` — Restore search

### Dependencies

**Used By:**
- `initialization_orchestrator.py` (2 locations)
- `ui_managers/__init__.py` (re-export)

**Uses:**
- Heavy widget imports (lazy loaded)
- Multiple config imports
- Qt classes
- Various UI helpers

---

## Migration Strategy

### Target Architecture

```
MainWindow
    ↓
InitializationOrchestrator
    ↓
    ├── WindowSetupController (window properties, sizing)
    ├── LayoutController (panels, splitters, layout)
    ├── SignalController (signal connections)
    └── ShortcutController (keyboard shortcuts)
```

### Phase 1: Extract WindowSetupController

**Responsibilities:**
- Window sizing and positioning
- Window title and icon
- Window state management

**Methods to move:**
- `setup_main_window()`
- `_calculate_optimal_window_size()`

**Target:** ~150 lines

---

### Phase 2: Extract LayoutController

**Responsibilities:**
- Panel creation and layout
- Splitter configuration
- Widget hierarchy setup

**Methods to move:**
- `setup_main_layout()`
- `setup_splitters()`
- `setup_left_panel()`
- `setup_center_panel()`
- `setup_right_panel()`
- `setup_bottom_layout()`
- `setup_footer()`
- `_calculate_optimal_splitter_sizes()`
- `_legacy_calculate_optimal_splitter_sizes()`

**Target:** ~600 lines

---

### Phase 3: Extract SignalController

**Responsibilities:**
- Connect all UI signals
- Event handler setup
- Signal routing

**Methods to move:**
- `setup_signals()`
- `_refresh_file_table()`
- `_show_search_context_menu()`
- `_on_metadata_search_text_changed()`
- `_clear_metadata_search()`
- `restore_metadata_search_text()`

**Target:** ~200 lines

---

### Phase 4: Extract ShortcutController

**Responsibilities:**
- Keyboard shortcut registration
- Shortcut conflict resolution
- Shortcut documentation

**Methods to move:**
- `setup_shortcuts()`

**Target:** ~100 lines

---

## Implementation Plan

### Step 1: Create Controller Package Structure

```
oncutf/controllers/ui/
├── __init__.py (20 lines)
├── window_setup_controller.py (150 lines)
├── layout_controller.py (600 lines)
├── signal_controller.py (200 lines)
└── shortcut_controller.py (100 lines)
```

**Total:** ~1070 lines (vs 982 original)
- Slight increase acceptable for better organization
- Controllers are independently testable
- Clear separation of concerns

---

### Step 2: Update InitializationOrchestrator

Replace:
```python
from oncutf.core.ui_managers.ui_manager import UIManager

self.window.ui_manager = UIManager(self.window)
self.window.ui_manager.setup_all_ui()
```

With:
```python
from oncutf.controllers.ui import (
    WindowSetupController,
    LayoutController,
    SignalController,
    ShortcutController,
)

# Setup in phases
window_controller = WindowSetupController(self.window)
window_controller.setup()

layout_controller = LayoutController(self.window)
layout_controller.setup()

signal_controller = SignalController(self.window)
signal_controller.setup()

shortcut_controller = ShortcutController(self.window)
shortcut_controller.setup()
```

---

### Step 3: Maintain Backward Compatibility

Keep UIManager as thin delegator for any external usage:

```python
class UIManager:
    """LEGACY: Thin delegator to new controllers."""
    
    def __init__(self, parent_window):
        self.parent_window = parent_window
        self._window_controller = WindowSetupController(parent_window)
        self._layout_controller = LayoutController(parent_window)
        self._signal_controller = SignalController(parent_window)
        self._shortcut_controller = ShortcutController(parent_window)
    
    def setup_all_ui(self):
        """Delegate to new controllers."""
        self._window_controller.setup()
        self._layout_controller.setup()
        self._signal_controller.setup()
        self._shortcut_controller.setup()
```

---

## Success Metrics

| Metric | Before | Target |
|--------|--------|--------|
| **UIManager** | 982 lines | ~150 lines (delegator) |
| **Controller Package** | 0 lines | ~1070 lines (4 controllers) |
| **Tests Passing** | 949/949 | 949+/949+ |
| **Testability** | Hard (Qt-coupled) | Easy (injected dependencies) |

---

## Risks & Mitigations

### Risk 1: Breaking UI Initialization

**Mitigation:**
- Maintain exact initialization order
- Thorough testing of UI setup
- Keep delegator for backward compatibility

### Risk 2: Import Cycles

**Mitigation:**
- Controllers use TYPE_CHECKING for MainWindow
- Lazy imports where needed
- Clear dependency hierarchy

### Risk 3: Increased Complexity

**Mitigation:**
- Each controller has single responsibility
- Better testability outweighs line count increase
- Clear documentation

---

## Timeline

**Estimated:** 2-3 hours

1. Create controller package (30 min)
2. Extract WindowSetupController (20 min)
3. Extract LayoutController (40 min)
4. Extract SignalController (30 min)
5. Extract ShortcutController (15 min)
6. Update InitializationOrchestrator (15 min)
7. Testing & fixes (30 min)

---

## Next Steps

1. [x] Create migration plan
2. ⏭️ Create controller package structure
3. ⏭️ Extract WindowSetupController
4. ⏭️ Extract LayoutController
5. ⏭️ Extract SignalController
6. ⏭️ Extract ShortcutController
7. ⏭️ Update InitializationOrchestrator
8. ⏭️ Run quality gates

