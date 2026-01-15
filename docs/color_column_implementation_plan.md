# Color Column Implementation Plan

**Date:** December 21, 2025  
**Author:** Michael Economou

## Overview

Implement color indicators in the new "color" column with SVG-based icons and context menu selection.

---

## Current Status [COMPLETE]

### Already Completed
1. **Column Configuration** - Added to `config.py`:
   - Index 0 (leftmost column)
   - 50px fixed width, center aligned
   - Non-resizable (`resizable: False`)
   - Visible by default, removable
   
2. **Serialization Support** - Automatic via existing system:
   - `file_table_column_widths` (width persistence)
   - `file_table_columns` (visibility persistence)
   
3. **Header Context Menu** - Automatic alphabetical inclusion

---

## Phase 1: Icon Design & Generation 🎨

### 1.1 Examine Existing Icon System

Current metadata status icons (left column in screenshot):
- **System:** SVG-based via `SVGIconGenerator` class
- **Location:** `oncutf/utils/svg_icon_generator.py`
- **Base icons:** Feather icon set in `resources/icons/feather_icons/`
- **Available:** `square.svg` [OK] Perfect for color swatches!
- **Colors:** Defined in `config.py` → `METADATA_ICON_COLORS`

**Current metadata icons use:**
```python
ICON_MAPPINGS = {
    "basic": "info",
    "extended": "info",
    "invalid": "alert-circle",
    "loaded": "check-circle",
    "modified": "edit-2",
    ...
}
```

### 1.2 Color Palette Definition

**Add to `config.py`:**
```python
# Color column palette (for file tagging/organization)
# 32 colors arranged in 4 rows x 8 columns + custom picker + none
COLOR_PALETTE = [
    # Row 1: Pinks & Reds
    "#e91e63", "#f06292", "#ec407a", "#d81b60", "#c2185b", "#ad1457", "#880e4f", "#ff1744",
    # Row 2: Oranges & Yellows  
    "#ff9800", "#ffb74d", "#ffa726", "#ff6f00", "#f57c00", "#e65100", "#ffeb3b", "#fdd835",
    # Row 3: Greens & Cyans
    "#4caf50", "#81c784", "#66bb6a", "#43a047", "#388e3c", "#2e7d32", "#00bcd4", "#26c6da",
    # Row 4: Blues & Purples
    "#2196f3", "#64b5f6", "#42a5f5", "#1976d2", "#1565c0", "#0d47a1", "#9c27b0", "#ba68c8",
]

# Color palette layout
COLOR_GRID_ROWS = 4
COLOR_GRID_COLS = 8
COLOR_PICKER_IMAGE = "resources/images/color_range.jpg"
```

**Rationale:**
- 32 Material Design colors for rich palette
- Grid layout (4 rows x 8 cols) matching screenshot
- Custom color picker via OS dialog
- "None" option to reset

### 1.3 Create Color Icon Generator Script

**File:** `scripts/generate_color_icons.py`

```python
"""
Generate color swatch icons for the color column.

Creates filled square SVG icons in various colors for file tagging.
Output: resources/icons/color_*.svg (e.g., color_red.svg)
"""

from pathlib import Path
from oncutf.config import COLOR_PALETTE

def generate_color_svg(color_key: str, hex_color: str, size: int = 16) -> str:
    """Generate filled square SVG."""
    # Use rectangle with slight rounding for modern look
    return f'''<svg xmlns="http://www.w3.org/2000/svg" 
        width="{size}" height="{size}" viewBox="0 0 {size} {size}">
        <rect x="2" y="2" width="{size-4}" height="{size-4}" 
              rx="2" fill="{hex_color}" stroke="none"/>
    </svg>'''

def main():
    icons_dir = Path(__file__).parent.parent / "resources" / "icons"
    icons_dir.mkdir(parents=True, exist_ok=True)
    
    for key, data in COLOR_PALETTE.items():
        if key == "none":
            continue  # Skip transparent/none icon
        
        svg_content = generate_color_svg(key, data["color"])
        output_path = icons_dir / f"color_{key}.svg"
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(svg_content)
        
        print(f"Generated: {output_path.name}")

if __name__ == "__main__":
    main()
```

**Run:**
```bash
python scripts/generate_color_icons.py
```

---

## Phase 2: File Model Integration 🗂️

### 2.1 Add Color Property to File Data

**Location:** Where file data is stored (need to identify exact model)

**Add field:**
```python
{
    "path": "/path/to/file.jpg",
    "filename": "file.jpg",
    "color": "none",  # Default: no color tag
    ...
}
```

### 2.2 Update FileModel Data Method

**Find:** File model that handles `data()` for table display

**Add DecorationRole for color column:**
```python
if role == Qt.DecorationRole and column_key == "color":
    file_color = file_data.get("color", "none")
    if file_color != "none":
        return load_color_icon(file_color)
    return None  # No icon for "none"
```

### 2.3 Persistence in Database

**Add to database schema:**
- Table: `file_metadata` or similar
- Column: `color_tag TEXT DEFAULT 'none'`

**Migration:**
```sql
ALTER TABLE file_metadata ADD COLUMN color_tag TEXT DEFAULT 'none';
```

---

## Phase 3: Context Menu Implementation 🎨

### 3.1 Create ColorGridMenu Widget

**File:** `oncutf/ui/widgets/color_grid_menu.py`

```python
"""
Custom color grid menu widget.

Layout:
┌─────────────────────────┬───────┐
│ Color Grid (4 rows x 8) │ Color │
│                         │ Picker│
│                         │ Image │
├─────────────────────────┴───────┤
│            None                 │
└─────────────────────────────────┘
"""

class ColorButton(QToolButton):
    """Single color button in grid."""
    clicked_with_color = pyqtSignal(str)  # Emits hex color
    
    def __init__(self, color: str, parent=None):
        super().__init__(parent)
        self.color = color
        self.setFixedSize(20, 20)
        self.setStyleSheet(f"""
            QToolButton {{
                background-color: {color};
                border: 1px solid #555;
                border-radius: 2px;
            }}
            QToolButton:hover {{
                border: 2px solid #fff;
            }}
        """)
        self.clicked.connect(lambda: self.clicked_with_color.emit(self.color))


class ColorGridMenu(QWidget):
    """Color grid menu with picker and none option."""
    color_selected = pyqtSignal(str)  # Emits selected color or "none"
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Top section: Grid + Picker
        top_layout = QHBoxLayout()
        
        # Color grid (4 rows x 8 cols)
        grid_layout = QGridLayout()
        grid_layout.setSpacing(2)
        
        from oncutf.config import COLOR_PALETTE, COLOR_GRID_ROWS, COLOR_GRID_COLS
        
        for i, color in enumerate(COLOR_PALETTE):
            row = i // COLOR_GRID_COLS
            col = i % COLOR_GRID_COLS
            
            btn = ColorButton(color)
            btn.clicked_with_color.connect(self._on_color_selected)
            grid_layout.addWidget(btn, row, col)
        
        top_layout.addLayout(grid_layout)
        
        # Color picker button (image)
        picker_btn = QToolButton()
        picker_btn.setFixedSize(60, 80)
        
        from oncutf.config import COLOR_PICKER_IMAGE
        pixmap = QPixmap(COLOR_PICKER_IMAGE)
        picker_btn.setIcon(QIcon(pixmap))
        picker_btn.setIconSize(QSize(58, 78))
        picker_btn.setToolTip("Custom color picker")
        picker_btn.clicked.connect(self._open_color_picker)
        
        top_layout.addWidget(picker_btn)
        layout.addLayout(top_layout)
        
        # Bottom: None button
        none_btn = QPushButton("None - Reset the color")
        none_btn.setFixedHeight(25)
        none_btn.clicked.connect(lambda: self._on_color_selected("none"))
        layout.addWidget(none_btn)
        
        # Style
        self.setStyleSheet("""
            ColorGridMenu {
                background-color: #2b2b2b;
                border: 1px solid #555;
            }
            QPushButton {
                background-color: #3a3a3a;
                color: #ddd;
                border: 1px solid #555;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
        """)
    
    def _on_color_selected(self, color: str):
        self.color_selected.emit(color)
        self.close()
    
    def _open_color_picker(self):
        from PyQt5.QtWidgets import QColorDialog
        
        color = QColorDialog.getColor()
        if color.isValid():
            hex_color = color.name()  # Returns #RRGGBB
            self._on_color_selected(hex_color)
```

### 3.2 Create ColorColumnDelegate

**File:** `oncutf/ui/delegates/color_column_delegate.py`

```python
"""Custom delegate for color column."""

class ColorColumnDelegate(QStyledItemDelegate):
    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.RightButton:
                self._show_color_menu(event.globalPos(), model, index)
                return True
        return super().editorEvent(event, model, option, index)
    
    def _show_color_menu(self, pos, model, index):
        from oncutf.ui.widgets.color_grid_menu import ColorGridMenu
        
        menu = ColorGridMenu()
        menu.color_selected.connect(
            lambda color: self._set_file_color(model, index, color)
        )
        menu.move(pos)
        menu.show()
    
    def _set_file_color(self, model, index, color):
        # Get file path from model
        # Update color in database
        # Update model data
        # Emit dataChanged for refresh
        pass
```

### 3.3 Register Delegate in FileTableView

```python
from oncutf.ui.delegates.color_column_delegate import ColorColumnDelegate

color_delegate = ColorColumnDelegate()
self.setItemDelegateForColumn(color_column_index, color_delegate)
```

---

## Phase 4: Icon Loading 🖼️

### 4.1 Add Color Icon Loader

**File:** `oncutf/utils/icons_loader.py`

```python
_color_icons_cache: dict[str, QIcon] = {}

def load_color_icon(color_key: str) -> QIcon:
    """Load cached color icon."""
    if color_key in _color_icons_cache:
        return _color_icons_cache[color_key]
    
    icon_path = get_icons_dir() / f"color_{color_key}.svg"
    icon = QIcon(str(icon_path))
    _color_icons_cache[color_key] = icon
    return icon
```

---

## Phase 5: Testing & Polish ✨

### 5.1 Test Cases
- [ ] Color icons display correctly in column
- [ ] Context menu shows all colors with icons
- [ ] Color selection persists across sessions
- [ ] Color survives file reload/refresh
- [ ] Multiple files can have same color
- [ ] Color filters work (future feature)

### 5.2 UI Polish
- [ ] Tooltip on color cell: "Right-click to set color"
- [ ] Visual feedback when hovering over color cell
- [ ] Keyboard shortcut for color menu (Ctrl+K?)

---

## Alternative: Use Existing Feather `square.svg`

Instead of generating separate SVG files, we can **reuse the SVG colorization system**:

**Advantages:**
- No new files needed
- Consistent with metadata icon system
- Dynamic color changes possible

**Implementation:**
```python
# In svg_icon_generator.py
COLOR_ICON_MAPPINGS = {
    "red": "square",
    "orange": "square",
    "yellow": "square",
    ...
}

# Use existing colorize_svg method
def generate_color_icon(color_key: str) -> QPixmap:
    svg_content = load_svg_content("square")
    hex_color = COLOR_PALETTE[color_key]["color"]
    colored_svg = colorize_svg(svg_content, hex_color)
    return render_svg_to_pixmap(colored_svg, size=16)
```

**Recommendation:** Use this approach! It's cleaner and leverages existing infrastructure.

---

## Summary

**Complexity:** Medium  
**Estimated Time:** 3-4 hours  
**Key Files:**
1. `config.py` - Color palette definition
2. `svg_icon_generator.py` - Color icon generation
3. `file_model.py` - Color property storage
4. `color_column_delegate.py` - Context menu (NEW)
5. `icons_loader.py` - Icon caching

**Dependencies:**
- Existing SVG icon system [OK]
- Feather `square.svg` icon [OK]
- Database schema update ⚠️
- File model color property ⚠️

**Next Steps:**
1. Review plan with user
2. Decide: Generate SVG files OR use dynamic colorization?
3. Identify correct file model location
4. Implement Phase 1 (icons first)
