# Color Tagging System Documentation

## Overview

The color tagging system allows users to assign colors to files for organization and quick visual identification. Colors persist across application restarts and follow files when they are renamed.

## Architecture

### Database Storage (Schema v4)

Colors are stored in the `file_paths` table:

```sql
CREATE TABLE file_paths (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL UNIQUE,
    filename TEXT NOT NULL,
    file_size INTEGER,
    modified_time TIMESTAMP,
    color_tag TEXT DEFAULT 'none',  -- Hex color (#rrggbb) or "none"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### Color Format

- **Hex colors**: `#rrggbb` (lowercase, 7 characters)
- **No color**: `"none"`
- Custom colors from QColorDialog are stored as hex values

### Migration

Existing databases are automatically migrated from schema v3 to v4:

```sql
ALTER TABLE file_paths ADD COLUMN color_tag TEXT DEFAULT 'none'
```

## Implementation

### Database Methods

**DatabaseManager.set_color_tag(file_path, color_hex)**
- Validates hex format (`#[0-9a-f]{6}` or "none")
- Updates `color_tag` column for the file
- Returns `True` on success

**DatabaseManager.get_color_tag(file_path)**
- Returns hex color string or "none"
- Defaults to "none" if file not found

**DatabaseManager.update_file_path(old_path, new_path)**
- Updates file path after rename
- Preserves all associated data (color_tag, metadata, hashes)
- Called automatically by `Renamer.rename()`

### FileItem Integration

**FileItem.__init__**
- Automatically loads saved color from database:
  ```python
  db_manager = get_database_manager()
  self.color = db_manager.get_color_tag(path)
  ```

### Color Assignment

**ColorColumnDelegate._set_files_color(color)**
1. Updates `FileItem.color` property (in-memory)
2. Saves to database via `db_manager.set_color_tag()`
3. Emits `dataChanged` signal to update UI

### Rename Workflow

When files are renamed:

1. `Renamer.rename()` performs filesystem rename
2. Updates metadata cache with new path
3. **NEW**: Calls `db_manager.update_file_path(old_path, new_path)`
4. Database preserves `color_tag` by updating path while keeping same `path_id`

### Sorting

Files can be sorted by color via column header:

```python
# FileTableModel.sort()
elif column_key == "color":
    # "none" first, then alphabetically by hex value
    self.files.sort(key=lambda f: (f.color != "none", f.color.lower()), reverse=reverse)
```

## User Workflow

1. **Assign Color**
   - Right-click color column (index 0)
   - Select color from grid or use system picker
   - Color is saved immediately to database

2. **Multi-Select Coloring**
   - Select multiple files
   - Right-click color column on any selected file
   - All selected files get the same color

3. **Remove Color**
   - Right-click color column
   - Select "None" button
   - Color is set to "none" in database

4. **Sort by Color**
   - Click color column header
   - Files are grouped: no color, then sorted by hex value

5. **Persistence**
   - Colors survive application restarts
   - Colors follow files when renamed
   - Colors are per-file, independent of location

## Configuration

**config.py**
```python
FILE_TABLE_COLUMN_CONFIG = {
    "color": {
        "index": 0,
        "label": "",
        "width": 50,
        "alignment": "center",
        "resizable": False,
        "sortable": True,
    },
}

COLOR_PALETTE = [
    # 32 Material Design colors (4 rows × 8 columns)
    "#e57373", "#f06292", "#ba68c8", ...
]

COLOR_GRID_ROWS = 4
COLOR_GRID_COLS = 8
COLOR_SWATCH_SIZE = 22  # Icon size in table
```

## Technical Details

### Thread Safety

- Database operations use context managers (`with self._get_connection()`)
- Each operation commits immediately
- No long-running transactions during color operations

### Performance

- Color loading happens once per FileItem creation
- Color saving is instant (single UPDATE query)
- Path updates during rename are atomic
- Indexed queries on `file_paths.file_path` for fast lookups

### Error Handling

- Invalid hex colors are rejected (logged as warning)
- Missing files default to "none" color
- Database errors are logged, operations return `False`
- UI remains functional even if database operations fail

## Future Enhancements

- Color presets (save/load color schemes)
- Color-based filtering in file table
- Bulk color operations (color all .jpg files)
- Color tags in metadata export
- Color-coded statistics (count files by color)
