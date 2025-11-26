# Metadata Tree Visual Feedback - Implementation Guide

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    User Edits Metadata Field                         │
│                    (MetadataEditDialog)                              │
└───────────────────┬─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│              Create EditMetadataFieldCommand                         │
│         (tracks change: key, old_value, new_value)                  │
└───────────────────┬─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│          MetadataStagingManager.stage_change()                      │
│      (stores modified field in staged_changes dict)                 │
└───────────────────┬─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│        MetadataTreeView.display_metadata(context="mod")             │
│    (requests rebuild of tree with modification context)             │
└───────────────────┬─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│         MetadataTreeView._render_metadata_view()                    │
│  (gets modified_keys from staging_manager.get_staged_changes())     │
└───────────────────┬─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│      build_metadata_tree_model(metadata,                            │
│            modified_keys, extended_keys)                           │
│      (processes metadata and applies styling)                       │
└───────────────────┬─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│     For each key in modified_keys:                                  │
│     - Apply Yellow Color (255, 255, 0)                             │
│     - Apply Bold Font                                              │
│     - Skip [Mod] prefix (just style the text)                      │
└───────────────────┬─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│              Metadata Tree View Updated                              │
│     Modified keys display in Yellow + Bold                          │
│     ("ISO Speed", "Aperture", etc. appear highlighted)             │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. MetadataEditDialog (`widgets/metadata_edit_dialog.py`)
- **Role**: Handle field editing UI
- **Action**: Creates EditMetadataFieldCommand when user confirms edit
- **Trigger**: Command execution → metadata staging

### 2. MetadataStagingManager (`core/metadata_staging_manager.py`)
- **Role**: Track which fields have been modified
- **Tracks**: Per-file staged changes dict
- **Provides**: `get_staged_changes(file_path)` → set of modified keys

### 3. MetadataTreeView (`widgets/metadata_tree_view.py`)
- **Role**: Display metadata in tree structure
- **Method**: `display_metadata(metadata, context="modification")`
- **Action**: Calls `_render_metadata_view()` → gets modified keys → rebuilds tree

### 4. build_metadata_tree_model (`utils/build_metadata_tree_model.py`)
- **Role**: Build QStandardItemModel with styling
- **Parameters**: 
  - `metadata`: dict of all fields
  - `modified_keys`: set of fields that were modified
  - `extended_keys`: set of fields from extended metadata
  - `display_level`: always "all" (no filtering)
- **Styling Logic** (lines 545-563):
  ```python
  if is_modified:
      # Apply yellow color + bold font to key
      modified_font = QFont()
      modified_font.setBold(True)
      key_item.setFont(modified_font)
      
      modified_color = QColor(255, 255, 0)  # Yellow
      key_item.setForeground(modified_color)
  ```

## Data Flow Example

### Scenario: User edits ISO Speed from 100 to 1600

1. **Initial State**
   - Metadata tree shows: "ISO Speed: 100" (black text, regular font)
   - Staging manager: empty (no staged changes)

2. **User Action**
   - Double-clicks on "ISO Speed" value
   - MetadataEditDialog opens with current value (100)
   - User changes to 1600 and clicks OK

3. **Command Execution**
   ```python
   EditMetadataFieldCommand(
       file=current_file,
       key="ISOSpeed",
       old_value="100",
       new_value="1600"
   ).execute()
   ```

4. **Staging Manager Updates**
   ```python
   staging_manager.stage_change(
       file_path,
       {"ISOSpeed": "1600"}
   )
   ```

5. **Tree Rebuild Triggered**
   ```python
   display_metadata(metadata, context="modification")
   ```

6. **Modified Keys Retrieved**
   ```python
   modified_keys = staging_manager.get_staged_changes(file_path)
   # Result: {"ISOSpeed"}
   ```

7. **Tree Model Built with Styling**
   ```python
   model = build_metadata_tree_model(
       metadata,
       modified_keys={"ISOSpeed"},  # Mark this as modified
       extended_keys=set()
   )
   ```

8. **Visual Result**
   - Metadata tree shows: **"ISO Speed: 1600"** (yellow text, bold font)
   - User sees at a glance that this field was modified

## Styling Rules Priority

When a key has multiple statuses, styling is applied in this order:

1. **Extended Metadata** (if applicable)
   - Font: Italic
   - Color: Blue (100, 150, 255)
   - Indicator: "[Ext]" prefix

2. **Modified Status** (if applicable) ← **OVERRIDES** extended color
   - Font: Bold (combines with Italic if extended)
   - Color: Yellow (255, 255, 0) ← **OVERWRITES** blue
   - No prefix for visual cleanliness

**Example Combinations**:
- Normal: "ISO Speed" (black, regular)
- Modified Only: "ISO Speed" (yellow, bold)
- Extended Only: "[Ext] ISO Speed" (blue, italic)
- Extended + Modified: "[Ext] ISO Speed" (yellow, bold+italic)

## Persistence and State Management

### Modified State Lifecycle

```
CREATED (user edits)
    │
    ▼
STAGED (in staging_manager.staged_changes)
    │
    ├─ SAVED (committed to metadata)
    │  │
    │  └─ CLEARED (staging_manager.clear_staged_changes())
    │
    └─ UNDONE (user presses Ctrl+Z)
       │
       └─ UNSTAGED (removed from staged_changes)
```

### When Styling Clears

1. **After Save**: 
   - User confirms changes
   - MetadataCommandManager commits staged changes
   - Staging manager clears for that file
   - Tree rebuilds without modified styling

2. **After Undo** (Ctrl+Z):
   - EditMetadataFieldCommand.undo() called
   - Staging manager receives updated staged_changes
   - Modified key removed from set
   - Tree rebuilds with styling removed

3. **After Reset**:
   - User discards unsaved changes
   - Staging manager clears for file
   - Tree refreshes

## Testing

### Unit Tests: `tests/test_metadata_tree_visual_feedback.py`

```python
def test_modified_keys_styling():
    """Verify yellow color + bold font for modified keys"""
    
def test_unmodified_keys_normal_styling():
    """Verify unmodified keys remain normal"""
    
def test_empty_modified_keys():
    """Verify no crash with empty modified set"""
    
def test_modified_tooltip():
    """Verify tooltip shows 'Modified value'"""
```

Run tests:
```bash
pytest tests/test_metadata_tree_visual_feedback.py -v
```

## Visual Reference

### Before User Edit
```
File Info (1)
├─ File Name: test.jpg

Camera Settings (4)
├─ Aperture: 2.8              ◄─ Normal (black, regular)
├─ Focal Length: 50.0         ◄─ Normal (black, regular)
├─ ISO Speed: 100             ◄─ Normal (black, regular)
├─ Rotation: 0                ◄─ Normal (black, regular)
```

### After Editing ISO Speed to 1600
```
File Info (1)
├─ File Name: test.jpg

Camera Settings (4)
├─ Aperture: 2.8
├─ Focal Length: 50.0
├─ ISO Speed: 1600            ◄─ Modified (yellow, bold)
├─ Rotation: 0
```

### After Editing Multiple Fields
```
Camera Settings (4)
├─ Aperture: 5.6              ◄─ Modified (yellow, bold)
├─ Focal Length: 35.0         ◄─ Modified (yellow, bold)
├─ ISO Speed: 3200            ◄─ Modified (yellow, bold)
├─ Rotation: 90               ◄─ Normal (black, regular)
```

## Performance Notes

- **Minimal Overhead**: Styling applied during tree model creation (not on every frame update)
- **Scale**: Works efficiently with hundreds of metadata fields
- **Memory**: Modified keys stored as set (O(1) lookup)
- **Rebuild**: Only triggered when display_metadata() called (smart invalidation)

## Future Enhancements

Possible improvements to this system:

1. **Batch Indicators**: Show badge with "3 modified fields" in group header
2. **Highlight Animation**: Fade effect when new modification detected
3. **History Popup**: Hover over modified field to see old value
4. **Color Themes**: User customizable colors for modified/extended/etc.
5. **Diff View**: Side-by-side comparison of old vs. new values
