# MetadataTreeView Refactoring Plan

**Author:** Michael Economou  
**Date:** 2026-01-02  
**Status:** Active

---

## Problem Statement

`metadata_tree/view.py` is 1272 lines with 101 methods, making it a maintenance hotspot.
Despite having 8+ handlers already extracted, the view still contains:
- 62 delegation methods (just forwarding to handlers)
- Embedded business logic that should be in handlers
- State management scattered across the class

---

## Current Architecture

```
metadata_tree/
├── view.py (1272 lines)          <- PROBLEM: Too large
├── controller.py (302 lines)     <- OK
├── service.py (593 lines)        <- OK
├── model.py (294 lines)          <- OK
├── view_config.py (309 lines)    <- OK
├── worker.py (358 lines)         <- OK
├── display_handler.py (502 lines) <- PROBLEM: Mini-god
├── search_handler.py (322 lines) <- OK
├── selection_handler.py (231 lines) <- OK
├── drag_handler.py (203 lines)   <- OK
├── event_handler.py (130 lines)  <- OK
├── modifications_handler.py (145 lines) <- OK
└── cache_handler.py (65 lines)   <- OK
```

---

## Phase 1: Split DisplayHandler (502 lines → 2 modules)

### Current DisplayHandler Responsibilities (mixed)

1. **Rendering** (~250 lines):
   - `rebuild_tree_from_metadata()` - Build tree model
   - `emit_rebuild_tree()` - Signal-based rebuild
   - `display_metadata()` - Display orchestration
   - `get_file_path_from_metadata()` - Path extraction
   - `rebuild_metadata_tree_with_stats()` - Stats-aware rebuild

2. **UI State** (~250 lines):
   - `display_placeholder()` - Placeholder display
   - `clear_tree()` - Clear tree content
   - `set_current_file_from_metadata()` - Current file tracking
   - `update_information_label()` - Info label updates
   - `display_file_metadata()` - File metadata display
   - `cleanup_on_folder_change()` - Cleanup
   - `sync_placeholder_state()` - Placeholder sync

### Target Structure

```
metadata_tree/
├── render_handler.py (~280 lines)     <- Tree model building
│   ├── rebuild_tree_from_metadata()
│   ├── emit_rebuild_tree()
│   ├── _build_tree_model()
│   ├── _add_tree_items()
│   ├── get_file_path_from_metadata()
│   └── rebuild_metadata_tree_with_stats()
│
├── ui_state_handler.py (~250 lines)   <- UI state management
│   ├── display_placeholder()
│   ├── clear_tree()
│   ├── display_metadata()
│   ├── update_information_label()
│   ├── set_current_file_from_metadata()
│   ├── display_file_metadata()
│   ├── cleanup_on_folder_change()
│   └── sync_placeholder_state()
│
└── display_handler.py (~50 lines)     <- Thin facade (backward compat)
    └── Re-exports from both handlers
```

---

## Phase 2: Thin MetadataTreeView (1272 → <600 lines)

### Current Problem: 62 Delegation Methods

Many methods are simple pass-through delegations:

```python
# Current (repetitive)
def clear_scroll_memory(self) -> None:
    self._scroll_behavior.clear_scroll_memory()

def restore_scroll_after_expand(self) -> None:
    self._scroll_behavior.restore_scroll_after_expand()
    
# ... 60 more like this
```

### Solution: Direct Handler Access via Properties

```python
# New approach - expose handlers as properties
@property
def scroll(self) -> MetadataScrollBehavior:
    """Access scroll behavior handler."""
    return self._scroll_behavior

@property
def cache(self) -> MetadataCacheBehavior:
    """Access cache behavior handler."""
    return self._cache_behavior

# Usage from outside:
# OLD: tree_view.clear_scroll_memory()
# NEW: tree_view.scroll.clear_scroll_memory()
```

### Methods to Keep in View (Core Qt Overrides + Public API)

1. **Qt Overrides (~10 methods):**
   - `__init__`
   - `setModel`
   - `keyPressEvent`
   - `wheelEvent`
   - `resizeEvent`
   - `dragEnterEvent`, `dragMoveEvent`, `dropEvent`
   - `focusOutEvent`, `mousePressEvent`
   - `scrollTo`

2. **Public API (~15 methods):**
   - `display_metadata`
   - `display_file_metadata`
   - `show_empty_state`
   - `clear_view`
   - `handle_selection_change`
   - `handle_metadata_load_completion`
   - `get_modified_metadata`
   - `has_modifications_for_selected_files`
   - `initialize_with_parent`
   - `clear_for_folder_change`
   - Context menu methods
   - Edit value methods

3. **Handler Properties (~8 properties):**
   - `scroll` → `_scroll_behavior`
   - `cache` → `_cache_behavior`
   - `edit` → `_edit_behavior`
   - `context_menu` → `_context_menu_behavior`
   - `display` → `_display_handler`
   - `search` → `_search_handler`
   - `selection` → `_selection_handler`
   - `modifications` → `_modifications_handler`

### Delegation Methods to Remove (~50)

All simple pass-through methods like:
- `_path_in_dict`, `_get_from_path_dict`, `_set_in_path_dict`, `_remove_from_path_dict`
- `_update_metadata_in_cache`, `_update_file_icon_status`
- `clear_scroll_memory`, `restore_scroll_after_expand`
- `_get_original_value_from_cache`, `_get_original_metadata_value`
- Many more...

---

## Phase 3: Define Public API

### Subsystem Public API (metadata_tree/__init__.py)

```python
# Public API (exposed to MainWindow and other subsystems)
__all__ = [
    # Main classes
    "MetadataTreeView",
    "MetadataTreeController",
    
    # Types for type hints
    "MetadataTreeViewConfig",
    
    # Factory functions
    "create_metadata_tree",
]

# Everything else is internal implementation detail
```

### Usage Pattern

```python
# External code (MainWindow)
from oncutf.ui.widgets.metadata_tree import MetadataTreeView

tree = MetadataTreeView(parent)
tree.display_metadata(metadata)
tree.scroll.clear_memory()  # Direct handler access
tree.edit.edit_value(key, value)  # Direct handler access
```

---

## Implementation Plan

### Step 1: Split DisplayHandler
1. Create `render_handler.py` with tree building logic
2. Create `ui_state_handler.py` with UI state logic
3. Update `display_handler.py` as thin facade
4. Update view.py imports

### Step 2: Add Handler Properties to View
1. Add property accessors for all handlers
2. Update external callers to use new pattern
3. Mark old delegation methods as deprecated

### Step 3: Remove Delegation Methods
1. Remove delegation methods one section at a time
2. Update internal callers to use handler properties
3. Run tests after each section

### Step 4: Final Cleanup
1. Remove deprecated methods
2. Update `__init__.py` with clean public API
3. Update documentation

---

## Expected Results

| Metric | Before | After | Reduction |
|--------|--------|-------|-----------|
| view.py lines | 1272 | ~500 | 60% |
| view.py methods | 101 | ~40 | 60% |
| display_handler.py | 502 | ~50 | 90% |
| render_handler.py | 0 | ~280 | NEW |
| ui_state_handler.py | 0 | ~250 | NEW |

---

## Migration Notes

### Backward Compatibility

During migration, keep deprecated methods with warnings:

```python
def clear_scroll_memory(self) -> None:
    """DEPRECATED: Use tree_view.scroll.clear_scroll_memory() instead."""
    warnings.warn(
        "clear_scroll_memory() is deprecated. Use tree_view.scroll.clear_scroll_memory()",
        DeprecationWarning,
        stacklevel=2
    )
    self._scroll_behavior.clear_scroll_memory()
```

### Breaking Changes

After one release cycle, remove deprecated methods and update:
- MainWindow
- MetadataController
- Test files

---

## References

- [REFACTORING_ROADMAP.md](REFACTORING_ROADMAP.md)
- [MIGRATION_STANCE.md](MIGRATION_STANCE.md)
- [UI_ARCHITECTURE_PATTERNS.md](UI_ARCHITECTURE_PATTERNS.md)
