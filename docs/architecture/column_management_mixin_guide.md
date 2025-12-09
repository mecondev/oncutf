# ColumnManagementMixin Guide

**Last Updated:** 2025-12-09  
**File:** `widgets/mixins/column_management_mixin.py` (1179 LOC)

---

## Overview

`ColumnManagementMixin` encapsulates all column-related functionality for `FileTableView`. It handles:

- **Column configuration** — Define columns, set defaults
- **Width management** — Save/load widths, auto-fit, resizing
- **Visibility management** — Show/hide columns, toggle
- **Event handling** — React to column moves, resizes
- **Persistence** — Remember user preferences (SQLite)

This mixin reduces `FileTableView` by 1093 LOC and improves testability by isolating column logic from core table behavior.

---

## Public API Reference

### Configuration Methods

| Method | Parameters | Returns | Purpose |
|--------|-----------|---------|---------|
| `_configure_columns()` | - | - | Set up columns at initialization |
| `_ensure_column_proper_width()` | `index: int`, `width: int` | - | Apply minimum/maximum width constraints |
| `_update_header_visibility()` | - | - | Show/hide header based on column count |

### Width Management

| Method | Parameters | Returns | Purpose |
|--------|-----------|---------|---------|
| `_load_column_width()` | `section: int` | `int` | Load width from config for column |
| `_save_column_width()` | `section: int`, `width: int` | - | Persist width to config |
| `_on_column_resized()` | `section: int`, `width: int` | - | Handle user resize (debounced) |
| `auto_fit_columns_to_content()` | - | - | Calculate optimal widths for content |
| `_check_and_fix_column_widths()` | - | - | Validate and correct invalid widths |

### Visibility Management

| Method | Parameters | Returns | Purpose |
|--------|-----------|---------|---------|
| `_load_column_visibility_config()` | - | - | Load hidden columns from config |
| `_apply_column_visibility()` | - | - | Apply visibility state to table |
| `_toggle_column_visibility()` | `index: int` | - | Show/hide column by index |
| `toggle_column_visibility()` | `column_name: str` | - | Show/hide column by name |
| `add_column()` | `name: str`, `config: dict` | - | Add new column dynamically |
| `remove_column()` | `index: int` | - | Remove column by index |
| `get_visible_columns_list()` | - | `list[str]` | Get list of visible column names |
| `_get_column_key_from_index()` | `index: int` | `str` | Map column index to config key |

### Shortcuts & Utilities

| Method | Parameters | Returns | Purpose |
|--------|-----------|---------|---------|
| `_reset_columns_to_default()` | - | - | Restore original column layout |
| `_auto_fit_columns_to_content()` | - | - | (alias for auto_fit) |
| `refresh_columns_after_model_change()` | - | - | Update columns when model changes |
| `_on_column_moved()` | `from: int`, `to: int` | - | Handle drag-reorder |

---

## Usage Examples

### Example 1: Basic Column Configuration

```python
# Automatically happens in __init__
table = FileTableView()
# Columns are auto-configured from config.json
```

### Example 2: Toggling Column Visibility

```python
# Hide a column by name
table.toggle_column_visibility("date_modified")

# Show it again
table.toggle_column_visibility("date_modified")

# Check what's visible
visible = table.get_visible_columns_list()
print(visible)  # ['path', 'size', 'type', ...]
```

### Example 3: Auto-Fitting Columns

```python
# After loading new files, adjust column widths to content
table.auto_fit_columns_to_content()
```

### Example 4: Adding/Removing Columns Dynamically

```python
# Add a new column
table.add_column("custom_field", {
    "display_name": "Custom",
    "width": 100,
    "visible": True,
    "sortable": True
})

# Remove a column by index
table.remove_column(5)

# Refresh to apply changes
table.refresh_columns_after_model_change()
```

### Example 5: Resetting to Defaults

```python
# User clicks "Reset Columns"
table._reset_columns_to_default()
table.refresh_columns_after_model_change()
```

---

## Configuration Schema

Columns are stored in `config/config.json`:

```json
{
  "columns": {
    "path": {
      "display_name": "Path",
      "width": 300,
      "visible": true,
      "sortable": true,
      "editable": false,
      "min_width": 50,
      "max_width": 2000
    },
    "size": {
      "display_name": "Size",
      "width": 100,
      "visible": true,
      "sortable": true,
      "editable": false,
      "min_width": 50,
      "max_width": 500
    },
    "date_modified": {
      "display_name": "Modified",
      "width": 150,
      "visible": true,
      "sortable": true,
      "editable": false,
      "min_width": 100,
      "max_width": 300
    }
  },
  "column_order": ["path", "size", "type", "date_modified"],
  "column_visibility": {
    "path": true,
    "size": true,
    "type": true,
    "date_modified": true,
    "permissions": false
  }
}
```

### Configuration Fields

| Field | Type | Purpose |
|-------|------|---------|
| `display_name` | str | Label shown in header |
| `width` | int | Current width in pixels |
| `visible` | bool | Is column shown? |
| `sortable` | bool | Can user sort by this column? |
| `editable` | bool | Can user edit cells? |
| `min_width` | int | Minimum allowed width |
| `max_width` | int | Maximum allowed width |

---

## Internal Methods (Advanced)

If you need to extend the mixin:

### Batch 1: Configuration (10 methods)
```python
_configure_columns()              # Main setup
_ensure_column_proper_width()     # Constraint checking
_update_header_visibility()       # Hide header if no columns
_get_header_section_from_key()    # Lookup column index
_register_width_change_listener() # Connect resize signals
_check_column_bounds()            # Validate indices
_create_column_from_config()      # Build column settings
_apply_default_column_widths()    # Set initial sizes
_configure_header_behavior()      # Setup column drag/resize
_load_system_column_widths()      # Read from storage
```

### Batch 2: Width Management (7 methods)
```python
_load_column_width()              # Get stored width
_save_column_width()              # Persist width
_on_column_resized()              # Event handler (debounced)
_calculate_optimal_width()        # Auto-fit logic
_get_content_width_hint()         # Estimate content size
_apply_calculated_widths()        # Apply auto-fit
_queue_width_persistence()        # Debounce saves
```

### Batch 3: Visibility (12 methods)
```python
_load_column_visibility_config()  # Load hidden state
_apply_column_visibility()        # Show/hide columns
toggle_column_visibility()        # API: toggle by name
_toggle_column_visibility()       # Internal: toggle by index
add_column()                      # API: add new
remove_column()                   # API: remove
get_visible_columns_list()        # API: get list
_get_column_key_from_index()      # Index ↔ Name mapping
_update_visibility_config()       # Persist visibility
_apply_visibility_to_header()     # Show/hide in UI
_build_column_order_list()        # Get column order
_reorder_columns()                # Change column order
```

### Batch 4: Event Handlers (2 methods)
```python
_on_column_moved()                # Handle drag reorder
_on_column_visibility_toggled()   # Handle visibility change
```

### Batch 5: Utilities (4 methods)
```python
_reset_columns_to_default()       # Restore defaults
_auto_fit_columns_to_content()    # (alias)
refresh_columns_after_model_change() # API: full refresh
_check_and_fix_column_widths()    # Validation
```

---

## Testing

### Test File: `tests/test_column_management_mixin.py`

Recommended test cases:

```python
def test_add_column():
    """Test adding a new column"""
    
def test_remove_column():
    """Test removing a column preserves others"""
    
def test_toggle_visibility():
    """Test showing/hiding columns"""
    
def test_get_visible_columns():
    """Test getting list of visible columns"""
    
def test_reset_to_default():
    """Test restoring original layout"""
    
def test_auto_fit():
    """Test calculating optimal widths"""
    
def test_width_persistence():
    """Test saving/loading widths"""
    
def test_on_column_resized():
    """Test handling user resize"""
    
def test_on_column_moved():
    """Test handling drag-reorder"""
    
def test_refresh_after_model_change():
    """Test full refresh works correctly"""
```

---

## Common Patterns

### Pattern 1: Programmatically Hide Columns

```python
def hide_columns_except(table, visible_names):
    """Hide all columns except those listed."""
    for col_name in table.get_visible_columns_list():
        if col_name not in visible_names:
            table.toggle_column_visibility(col_name)
```

### Pattern 2: Save Current Layout

```python
def save_layout_preset(table, preset_name):
    """Save current column layout as preset."""
    visible = table.get_visible_columns_list()
    widths = {
        i: table.horizontalHeader().sectionSize(i)
        for i in range(table.model().columnCount())
    }
    # Store preset in config...
```

### Pattern 3: Restore Layout Preset

```python
def restore_layout_preset(table, preset_name):
    """Restore column layout from preset."""
    # Load preset from config...
    for col_name in preset["hidden"]:
        table.toggle_column_visibility(col_name)
    # Apply widths...
```

---

## Performance Notes

### Width Persistence
- Resize events are **debounced** (300ms) to avoid excessive saves
- Uses SQLite for persistence (fast lookups)
- Python dict (L1 cache) for immediate access

### Column Visibility
- Visibility changes are immediately persisted
- Hidden columns are stored in config, not removed from model
- Improves responsiveness vs. recreating columns

### Auto-Fit Logic
- Scans visible cells only
- Respects min/max width constraints
- O(columns × visible_rows) complexity

---

## Troubleshooting

### Issue: Columns not showing after visibility toggle

**Solution:** Call `refresh_columns_after_model_change()` after visibility changes.

```python
table.toggle_column_visibility("path")
table.refresh_columns_after_model_change()  # Force refresh
```

### Issue: Column widths not persisting

**Solution:** Ensure `_on_column_resized()` is connected to resize signal.

```python
# Should be automatic in _register_width_change_listener()
# Check logs if signal not connected
```

### Issue: Auto-fit makes columns too wide

**Solution:** Check `max_width` constraints in config.

```json
"path": {
  "max_width": 500  // Limit even if content is wider
}
```

---

## Future Improvements

- [ ] Column drag-drop reordering (partial, needs testing)
- [ ] Column pinning (freeze first N columns)
- [ ] Column groups/hierarchy
- [ ] Per-file-type column layouts
- [ ] Column search/filter in header

---

*Generated: 2025-12-09*
