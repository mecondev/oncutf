# Color Column Database Implementation

## Database Schema Change

Add `color_tag` column to `file_paths` table:

```sql
ALTER TABLE file_paths ADD COLUMN color_tag TEXT DEFAULT 'none';
```

## Implementation Steps

1. **Database Migration (database_manager.py)**
   - Add migration from version 3 to version 4
   - Add `color_tag` column to existing databases
   - Update SCHEMA_VERSION to 4

2. **Save Color Tag (color_column_delegate.py)**
   - Call database_manager.set_color_tag(file_path, hex_color) in _set_files_color()

3. **Load Color Tag (file_table_model.py)**
   - Load color from database when FileItem is created
   - Add database_manager.get_color_tag(file_path) method

4. **Sorting Support (file_table_view.py / interactive_header.py)**
   - Color column already in config with sortable=True
   - Sorting works automatically via FileItem.color property

## Database Methods to Add

```python
def set_color_tag(self, file_path: str, color_hex: str) -> bool:
    """Set color tag for a file."""
    
def get_color_tag(self, file_path: str) -> str:
    """Get color tag for a file. Returns 'none' if not set."""
```

## Data Format

- Store as HEX color string: `#ff00aa` or `none`
- Always lowercase hex values
- Validation: Must match pattern `^#[0-9a-f]{6}$` or be `'none'`
