# UI Architecture Patterns — Mixins vs Behaviors vs Handlers [COMPLETED]

**Author:** Michael Economou  
**Date:** 2025-12-28  
**Completed:** 2026-01-05  
**Archived:** 2026-01-09  
**Status:** [x] COMPLETED - All behaviors extracted, pattern established

**Archive Reason:** Mixin-to-behavior migration complete. All large behaviors split to packages. Pattern guidelines finalized.

---

## Overview

The oncutf UI layer uses **three abstraction patterns** for different purposes:

1. **Mixins** (`ui/mixins/`) — **LEGACY** pattern for existing widgets
2. **Behaviors** (`ui/behaviors/`) — **PREFERRED** composition pattern for NEW features
3. **Handlers** (`ui/widgets/*/handlers/`) — Widget-internal event routing

This document defines **clear boundaries** to avoid overlap and confusion.

---

## 1. Mixins (Legacy Pattern)

### Location
`oncutf/ui/mixins/*.py`

### Purpose
**Legacy abstraction for existing widgets.** Used when multiple widgets need to share identical UI logic through inheritance.

### When to use
- **NEVER for new features** — mixins exist only for backward compatibility
- Refactoring existing mixin-based code requires careful testing
- Do not extend existing mixins with new functionality

### Current usage
| Mixin | Used in | Purpose |
|-------|---------|---------|
| `SelectionMixin` | `FileTableView` | Row selection, anchor row, Ctrl/Shift modifiers |
| `DragDropMixin` | `FileTableView` | Drag enter/leave, drop event handling |
| `ColumnManagementMixin` | `FileTableView` | Column visibility, reordering, persistence |
| `MetadataCacheMixin` | `MetadataTreeView` | Metadata caching logic |
| `MetadataEditMixin` | `MetadataTreeView` | Inline metadata editing |
| `MetadataContextMenuMixin` | `MetadataTreeView` | Right-click menu actions |
| `MetadataScrollMixin` | `MetadataTreeView` | Scroll synchronization |

### Characteristics
- **Inheritance-based** — tightly couples widget to mixin behavior
- **Hard to test** — requires full Qt widget instantiation
- **State shared via `self`** — no clear boundaries between mixin and widget state
- **Multiple inheritance** — fragile MRO (Method Resolution Order) issues

### Migration path
When refactoring mixin-based widgets:
1. Create equivalent behavior class in `ui/behaviors/`
2. Use composition instead of inheritance
3. Test thoroughly — mixins often have subtle Qt lifecycle dependencies
4. **Do not remove mixins until widget is fully migrated**

---

## 2. Behaviors (Preferred Pattern)

### Location
`oncutf/ui/behaviors/*.py`

### Purpose
**Composition-based reusable UI logic.** Encapsulates complex widget behaviors in testable, independent classes.

### When to use
- **ALL new UI features** requiring shared logic across widgets
- Widget needs complex state management (selection, drag-drop, filtering)
- Logic can be tested independently of Qt widgets
- Multiple widgets need the same behavior but different base classes

### Example: SelectionBehavior
```python
from oncutf.ui.behaviors import SelectionBehavior

class MyTableView(QTableView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._selection_behavior = SelectionBehavior(self)
    
    def mousePressEvent(self, event: QMouseEvent):
        self._selection_behavior.handle_mouse_press(event)
        super().mousePressEvent(event)
```

### Characteristics
- **Composition-based** — widget owns behavior instance
- **Protocol-driven** — uses `SelectableWidget`, `DraggableWidget` protocols
- **Testable** — behavior can be tested with mock widgets
- **Clear boundaries** — behavior state is isolated from widget state
- **No MRO issues** — no multiple inheritance

### Current behaviors
| Behavior | Protocol | Purpose | Status |
|----------|----------|---------|--------|
| `SelectionBehavior` | `SelectableWidget` | Row selection with Qt sync, anchor row, keyboard modifiers | [x] Complete (package) |
| `DragDropBehavior` | `DraggableWidget` | Drag-and-drop with visual feedback, metadata tree drops | [x] Complete (cohesive) |
| `ColumnManagementBehavior` | `ColumnManageableWidget` | Column width/visibility management, delayed save, config persistence | [x] Complete (package) |
| `MetadataContextMenuBehavior` | `ContextMenuWidget` | Right-click menu actions for metadata | [x] Complete (package) |
| `MetadataCacheBehavior` | `CacheableWidget` | Metadata caching logic | [x] Complete (cohesive) |
| `MetadataEditBehavior` | `EditableWidget` | Inline metadata editing | [x] Complete (package) |
| `MetadataScrollBehavior` | `ScrollableWidget` | Scroll synchronization | [x] Complete (cohesive) |

### Creating new behaviors
1. Define protocol in `ui/behaviors/<feature>_behavior.py`:
   ```python
   from typing import Protocol
   
   class SelectableWidget(Protocol):
       def get_current_row(self) -> int: ...
       def get_row_count(self) -> int: ...
   ```

2. Implement behavior class with protocol dependency:
   ```python
   class SelectionBehavior:
       def __init__(self, widget: SelectableWidget):
           self._widget = widget
   ```

3. Widget implements protocol methods:
   ```python
   class MyWidget(QTableView):
       def get_current_row(self) -> int:
           return self.currentIndex().row()
   ```

---

## 3. Handlers (Widget-Internal Pattern)

### Location
`oncutf/ui/widgets/<widget_name>/handlers/*.py`

### Purpose
**Widget-specific event routing.** Breaks down complex widget logic into focused, single-responsibility handlers.

### When to use
- Widget has complex event handling (mouse, keyboard, drag-drop)
- Logic is **specific to this widget only** (not reusable)
- Want to split monolithic widget file into smaller modules

### Example: MetadataTreeView handlers
```
ui/widgets/metadata_tree_view/
├── __init__.py
├── handlers/
│   ├── selection_handler.py    # Selection-specific events
│   ├── edit_handler.py          # Inline editing logic
│   ├── context_menu_handler.py  # Right-click menus
│   └── scroll_handler.py        # Scroll synchronization
```

### Characteristics
- **Widget-scoped** — not shared across widgets
- **Event-focused** — each handler manages one category of events
- **No protocol requirements** — direct widget method calls are fine
- **Internal detail** — handlers are implementation details of the widget

### Handler structure
```python
# ui/widgets/metadata_tree_view/handlers/selection_handler.py
class SelectionHandler:
    def __init__(self, tree_view: 'MetadataTreeView'):
        self._tree = tree_view
    
    def handle_selection_changed(self):
        # Widget-specific selection logic
        selected_items = self._tree.selectedItems()
        # ...
```

---

## Decision Tree

```
Need UI functionality?
│
├─ Reusable across multiple widgets?
│  │
│  ├─ YES → Use **Behavior** (composition)
│  │        Create protocol + behavior class
│  │
│  └─ NO → Use **Handler** (widget-internal)
│           Create handler in widget's handlers/ folder
│
└─ Already exists as Mixin?
   │
   ├─ Modifying existing widget → Keep **Mixin** (legacy)
   │
   └─ Creating new widget → Use **Behavior** (composition)
```

---

## Anti-Patterns

### [FAIL] Don't: Create new mixins
```python
# WRONG — new features should use behaviors
class NewFeatureMixin:
    def new_feature_logic(self):
        pass
```

### [x] Do: Create new behaviors
```python
# CORRECT — composition-based
class NewFeatureBehavior:
    def __init__(self, widget: NewFeatureWidget):
        self._widget = widget
```

### [FAIL] Don't: Put reusable logic in handlers
```python
# WRONG — if FileTableView and MetadataTreeView both need this,
# it should be a behavior, not a handler
class SelectionHandler:  # in file_table_view/handlers/
    def handle_selection(self):  # Logic copied in metadata_tree_view too
        pass
```

### [x] Do: Use behaviors for shared logic
```python
# CORRECT — one behavior, many widgets
class SelectionBehavior:
    def __init__(self, widget: SelectableWidget):
        self._widget = widget

class FileTableView(QTableView):
    def __init__(self):
        self._selection = SelectionBehavior(self)

class MetadataTreeView(QTreeWidget):
    def __init__(self):
        self._selection = SelectionBehavior(self)
```

---

## Migration Strategy

### Phase 1: Freeze mixins ([x] Complete)
- [x] Do not add functionality to existing mixins
- [x] Document mixin usage in this file
- [x] All new features use behaviors

### Phase 2: Extract behaviors ([x] Complete - 2026-01-05)
**Completed (split to packages):**
- [x] `column_management/` — 6 modules (column_behavior, visibility_manager, width_manager, header_configurator, protocols, __init__)
- [x] `metadata_context_menu/` — 6 modules (context_menu_behavior, menu_builder, column_integration, key_mapping, protocols, __init__)
- [x] `selection/` — 3 modules (selection_behavior, protocols, __init__)

**Completed (already cohesive):**
- [x] `DragDropBehavior` — 501 lines (cohesive)
- [x] `MetadataCacheBehavior` — 466 lines (cohesive)
- [x] `MetadataScrollBehavior` — 325 lines (cohesive)
- [x] `metadata_edit/` — Already package (8 modules)

**Migration process per mixin:**
1. Create behavior equivalent in `ui/behaviors/`
2. Define protocol for widget contract
3. Add behavior instance to widget (composition)
4. Route mixin methods to behavior methods
5. Test thoroughly — mixins often have Qt lifecycle dependencies
6. **Do not remove mixin until widget is fully migrated**

### Phase 3: Standardize handlers (Future)
For widgets with complex logic:
1. Create `handlers/` subfolder
2. Extract event handling to focused handlers
3. Keep widget class as thin coordinator

---

## Summary

| Pattern | Use case | Testability | Reusability | Status |
|---------|----------|-------------|-------------|--------|
| **Mixin** | Legacy widgets | Low (needs Qt) | High (inheritance) | [FREEZE] Frozen |
| **Behavior** | NEW shared logic | High (protocols) | High (composition) | [OK] Preferred |
| **Handler** | Widget-internal routing | Medium | None (widget-specific) | [OK] Recommended |

**Golden rule:** Mixins are **frozen legacy**. Behaviors are the **future**. Handlers are **internal organization**.

---

## Widget Architecture Inventory

This section tracks which widgets use which patterns, to prevent "dual system forever" syndrome.

### Mixin-Based Widgets (Legacy - Frozen)

| Widget | Mixins Used | Migration Status |
|--------|-------------|------------------|
| `FileTableView` | `SelectionMixin`, `DragDropMixin`, `ColumnManagementMixin` | [FROZEN] Mixins frozen, behaviors available |
| `MetadataTreeView` | `MetadataCacheMixin`, `MetadataEditMixin`, `MetadataContextMenuMixin`, `MetadataScrollMixin` | [FROZEN] Mixins frozen, behaviors available |

### Behavior-Based Widgets (Modern - Recommended)

| Widget | Behaviors Used | Status |
|--------|----------------|--------|
| `FileTableView` | `ColumnManagementBehavior`, `SelectionBehavior`, `DragDropBehavior` (available) | [OK] Composition pattern established |
| `MetadataTreeView` | `MetadataCacheBehavior`, `MetadataEditBehavior`, `MetadataContextMenuBehavior`, `MetadataScrollBehavior` (available) | [OK] Composition pattern established |

### Handler-Based Widgets (Internal Organization)

| Widget | Handlers | Purpose |
|--------|----------|---------|
| `metadata_tree/` | `event_handler.py`, `drag_handler.py`, `search_handler.py`, `selection_handler.py`, `display_handler.py` | Event routing, specialized logic |

### Migration Triggers

Migrate a mixin to behavior when:
- Bug requires touching mixin code extensively
- New feature needs similar functionality
- Widget is being refactored for other reasons
- Testing becomes painful due to Qt dependencies

**Do NOT migrate just for the sake of migration** - focus on value delivered.

---

## Final Summary (2026-01-09)

**All objectives achieved:**
- [x] Mixins frozen (no new mixins created)
- [x] Behaviors extracted (7 total behaviors)
- [x] Large behaviors split to packages (3 packages: column_management/, metadata_context_menu/, selection/)
- [x] Cohesive behaviors remain as single files (4 behaviors)
- [x] Backward compatibility maintained (delegators)
- [x] Pattern guidelines established
- [x] All quality gates passing (986 tests, ruff clean, mypy clean, 99.9%+ docstring coverage)

**Pattern is now stable and documented.** Future UI work should follow behavior pattern over mixins.

