# Technical Plan: Viewport Switcher Buttons for FileTable Header

**Author:** Michael Economou  
**Date:** 2026-01-09  
**Status:** COMPLETED (2026-01-10)  
**Implementation:** All sections completed successfully

---

## 1. Overview

Design plan to add two square icon buttons at the top-right of the FileTable header area, positioned next to the "Files" label. These buttons will be used to switch between multiple viewports (e.g., thumbnails preview, alternative view).

### UI/UX Requirements

- Buttons must be **square** (20x20 pixels)
- Match the visual style of the existing footer menu button
- Compact and professional (no classic tabs)
- Positioned top-right, inline with "Files" label
- Must not shift layout when window resizes
- Each button must have an icon and a tooltip

---

## 2. Codebase Analysis

### 2.1 Files Label Location

| Aspect | Details |
|--------|---------|
| **File** | `oncutf/controllers/ui/layout_controller.py` |
| **Method** | `_setup_center_panel()` (lines 264-318) |
| **Current code** | `self.parent_window.files_label = QLabel("Files")` |
| **Layout** | Added directly to `center_layout` (QVBoxLayout) |

### 2.2 Footer Menu Button Pattern (Reference Implementation)

```python
# File: oncutf/controllers/ui/layout_controller.py (lines 547-559)

# Menu button
self.parent_window.menu_button = QPushButton()
self.parent_window.menu_button.setIcon(get_menu_icon("menu"))
self.parent_window.menu_button.setFixedSize(20, 20)
TooltipHelper.setup_tooltip(self.parent_window.menu_button, "Menu", TooltipType.INFO)
self.parent_window.menu_button.setObjectName("menuButton")
```

**Key observations:**
- Uses `QPushButton` (not QToolButton)
- Fixed 20x20 size for square shape
- No explicit QSS styling (relies on app-wide defaults)
- Uses `get_menu_icon()` for icon loading
- Uses `TooltipHelper.setup_tooltip()` for tooltips

### 2.3 Tooltip System

| Aspect | Details |
|--------|---------|
| **File** | `oncutf/utils/ui/tooltip_helper.py` |
| **Import** | `from oncutf.utils.ui.tooltip_helper import TooltipHelper, TooltipType` |
| **Usage** | `TooltipHelper.setup_tooltip(widget, "message", TooltipType.INFO)` |
| **Features** | Supports persistent (hover) tooltips |

### 2.4 Icon Loading System

| Aspect | Details |
|--------|---------|
| **File** | `oncutf/utils/ui/icons_loader.py` |
| **Import** | `from oncutf.utils.ui.icons_loader import get_menu_icon` |
| **Usage** | `get_menu_icon("icon-name")` returns QIcon |
| **Icons path** | `resources/icons/feather_icons/*.svg` |

---

## 3. Design Decisions

### 3.1 Widget Selection

**Decision: `QToolButton`**

Rationale:
- Better suited for toolbar-style button groups (2-3 buttons)
- Built-in support for `setCheckable()` and `setAutoExclusive()` for radio-like behavior
- Cleaner visual appearance for icon-only buttons
- Works well with `get_menu_icon()` system
- Supports `setToolButtonStyle(Qt.ToolButtonIconOnly)` for consistent sizing
- Better integration with QButtonGroup for mutual exclusion

### 3.2 Data-Driven Architecture

**ViewportSpec NamedTuple:**
```python
from typing import NamedTuple

class ViewportSpec(NamedTuple):
    """Specification for a viewport button."""
    id: str           # Unique identifier (e.g., "thumbs", "meta")
    tooltip: str      # Tooltip text
    icon_name: str    # Icon name for get_menu_icon()
    shortcut: str     # Keyboard shortcut (e.g., "F1")
```

**Button specifications:**
```python
VIEWPORT_SPECS: list[ViewportSpec] = [
    ViewportSpec("thumbs", "Thumbnail view", "grid", "F1"),
    ViewportSpec("details", "Details view", "list", "F2"),
    # Future: ViewportSpec("wave", "Waveform view", "activity", "F3"),
]
```

**Benefits:**
- Adding/removing viewports requires only spec list changes
- Consistent button creation via loop
- Easy to extend with additional properties (shortcut, enabled state)
- Buttons stored in dict for easy access: `viewport_buttons["thumbs"]`

### 3.3 Layout Strategy

**Current structure:**
```
center_frame (QFrame)
+-- center_layout (QVBoxLayout)
    +-- files_label (QLabel)        <-- Direct addition
    +-- file_table_view
```

**Proposed structure:**
```
center_frame (QFrame)
+-- center_layout (QVBoxLayout)
    +-- files_header_widget (QWidget)        <-- NEW: horizontal wrapper
    |   +-- files_header_layout (QHBoxLayout)
    |       +-- files_label (QLabel)
    |       +-- stretch
    |       +-- viewport_buttons (QWidget)   <-- NEW: button container
    |           +-- buttons_layout (QHBoxLayout)
    |               +-- viewport_buttons["thumbs"] (QToolButton)
    |               +-- viewport_buttons["details"] (QToolButton)
    +-- file_table_view
```

**Layout specifications:**
- `files_header_layout`: `setContentsMargins(0, 0, 0, 0)`, `setSpacing(0)`
- `buttons_layout`: `setContentsMargins(0, 0, 0, 0)`, `setSpacing(4)`
- `files_header_widget.setFixedHeight(24)` to match footer
- Stretch between label and buttons ensures right alignment

### 3.4 DPI-Aware Sizing

**Problem:** Fixed pixel sizes (20x20) may appear too small on high-DPI displays.

**Solution:** Use logical pixels with Qt's automatic scaling:

```python
from PyQt5.QtWidgets import QApplication

def get_scaled_size(base_size: int) -> int:
    """Scale size based on screen DPI."""
    # Qt handles most scaling automatically, but for explicit sizes:
    ratio = QApplication.instance().devicePixelRatio()
    # For high-DPI, we want logical pixels, not physical
    # Qt's setFixedSize uses logical pixels, so base_size is usually fine
    return base_size

# Constants (logical pixels - Qt scales automatically)
VIEWPORT_BUTTON_SIZE = 20
VIEWPORT_BUTTON_SPACING = 4
FILES_HEADER_HEIGHT = 24
```

**Qt's Automatic Scaling:**
- Already enabled in `main.py` line 148: `QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)`
- `setFixedSize(20, 20)` becomes 40x40 physical pixels on 2x DPI displays
- Icons from SVG scale automatically
- No manual calculations needed for most cases

### 3.5 Icon Selection

| Button | Icon Name | File | Semantic Fit |
|--------|-----------|------|--------------|
| **Viewport 1** (Thumbnails) | `grid` | `grid.svg` | Visual grid of items - perfect for thumbnails |
| **Viewport 2** (Details) | `list` | `list.svg` | Line-based list - perfect for details view |

**Alternative options (for future consideration):**
- `image.svg` - More explicit for thumbnail/preview view
- `columns.svg` - Tabular data representation
- `layers.svg` - Stacked panels concept

### 3.6 Object Naming Convention

Follow existing camelCase pattern, derived from spec ID:
```python
# For spec with id="thumbs"
button.setObjectName(f"viewport{spec.id.title()}Button")  # "viewportThumbsButton"

# For spec with id="details"
button.setObjectName(f"viewport{spec.id.title()}Button")  # "viewportDetailsButton"
```

This allows future QSS styling if needed:
```css
QToolButton#viewportThumbsButton:checked {
    background-color: #3daee9;
}
```

---

## 4. Implementation Details

### 4.1 Required Imports

```python
# New imports needed:
from typing import NamedTuple
from PyQt5.QtWidgets import QToolButton, QButtonGroup, QShortcut
from PyQt5.QtGui import QKeySequence

# Already imported in layout_controller.py:
from oncutf.utils.ui.icons_loader import get_menu_icon
from oncutf.utils.ui.tooltip_helper import TooltipHelper, TooltipType
```

### 4.2 ViewportSpec Definition

**Add to top of file or in separate module (`oncutf/ui/viewport_specs.py`):**
```python
from typing import NamedTuple


class ViewportSpec(NamedTuple):
    """Specification for a viewport button."""
    id: str           # Unique identifier
    tooltip: str      # Tooltip text  
    icon_name: str    # Icon name for get_menu_icon()
    shortcut: str     # Keyboard shortcut (e.g., "F1")


# Viewport button specifications - single source of truth
VIEWPORT_SPECS: list[ViewportSpec] = [
    ViewportSpec("thumbs", "Thumbnail view", "grid", "F1"),
    ViewportSpec("details", "Details view", "list", "F2"),
]

# Layout constants (logical pixels - Qt scales for high-DPI)
VIEWPORT_BUTTON_SIZE = 20
VIEWPORT_BUTTON_SPACING = 4
FILES_HEADER_HEIGHT = 24
```

### 4.3 Code Changes in `_setup_center_panel()`

**Replace:**
```python
self.parent_window.files_label = QLabel("Files")
center_layout.addWidget(self.parent_window.files_label)
```

**With:**
```python
# Create header row for label + viewport buttons
files_header_widget = QWidget()
files_header_widget.setFixedHeight(FILES_HEADER_HEIGHT)
files_header_layout = QHBoxLayout(files_header_widget)
files_header_layout.setContentsMargins(0, 0, 0, 0)
files_header_layout.setSpacing(0)

# Files label
self.parent_window.files_label = QLabel("Files")
files_header_layout.addWidget(self.parent_window.files_label)

# Stretch to push buttons right
files_header_layout.addStretch()

# Viewport buttons container
viewport_container = QWidget()
buttons_layout = QHBoxLayout(viewport_container)
buttons_layout.setContentsMargins(0, 0, 0, 0)
buttons_layout.setSpacing(VIEWPORT_BUTTON_SPACING)

# Button group for mutual exclusion (radio-like behavior)
self.parent_window.viewport_button_group = QButtonGroup()
self.parent_window.viewport_button_group.setExclusive(True)

# Create buttons from specs (data-driven)
self.parent_window.viewport_buttons: dict[str, QToolButton] = {}

for i, spec in enumerate(VIEWPORT_SPECS):
    btn = QToolButton()
    btn.setIcon(get_menu_icon(spec.icon_name))
    btn.setFixedSize(VIEWPORT_BUTTON_SIZE, VIEWPORT_BUTTON_SIZE)
    btn.setFocusPolicy(Qt.NoFocus)
    btn.setCheckable(True)
    btn.setAutoRaise(True)  # Flat appearance until hover/checked
    btn.setObjectName(f"viewport{spec.id.title()}Button")
    
    # Tooltip includes shortcut hint
    tooltip_text = f"{spec.tooltip} ({spec.shortcut})"
    TooltipHelper.setup_tooltip(btn, tooltip_text, TooltipType.INFO)
    
    # Keyboard shortcut
    shortcut = QShortcut(QKeySequence(spec.shortcut), self.parent_window)
    shortcut.activated.connect(btn.click)
    
    # Add to button group (mutual exclusion)
    self.parent_window.viewport_button_group.addButton(btn, i)
    
    # Store in dict for easy access
    self.parent_window.viewport_buttons[spec.id] = btn
    buttons_layout.addWidget(btn)

# Set default selection (first button)
if VIEWPORT_SPECS:
    self.parent_window.viewport_buttons[VIEWPORT_SPECS[0].id].setChecked(True)

files_header_layout.addWidget(viewport_container)

# Add header to center layout
center_layout.addWidget(files_header_widget)
```

### 4.4 Protocol Updates

Add to `oncutf/controllers/ui/protocols.py`:

```python
from PyQt5.QtWidgets import QToolButton, QButtonGroup

# In the protocol class:
viewport_buttons: dict[str, "QToolButton"]
viewport_button_group: "QButtonGroup"
```

---

## 5. Extensibility

### Adding a 3rd Button Later

Simply add to `VIEWPORT_SPECS`:

```python
VIEWPORT_SPECS: list[ViewportSpec] = [
    ViewportSpec("thumbs", "Thumbnail view", "grid", "F1"),
    ViewportSpec("details", "Details view", "list", "F2"),
    ViewportSpec("wave", "Waveform view", "activity", "F3"),  # NEW
]
```

**That's it!** No other code changes required because:
- Buttons are created from specs in a loop
- Button group handles mutual exclusion automatically
- Layout spacing is consistent
- Dict storage allows access via `viewport_buttons["wave"]`

### Future Spec Extensions

The ViewportSpec can be extended with additional properties:

```python
class ViewportSpec(NamedTuple):
    id: str
    tooltip: str
    icon_name: str
    shortcut: str             # Keyboard shortcut (required)
    enabled: bool = True      # Can be disabled
    default: bool = False     # Is this the default selection?
```

---

## 6. Risks and Mitigations

### 6.1 DPI Scaling

| Risk | Mitigation |
|------|------------|
| Fixed pixel sizes may appear too small on high-DPI displays | Qt handles automatic scaling when `AA_EnableHighDpiScaling` is enabled. Use logical pixels (20x20) - Qt converts to physical pixels automatically. SVG icons scale perfectly. Verify `main.py` has `QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)` before QApplication creation. |

### 6.2 Theme/QSS Interaction

| Risk | Mitigation |
|------|------------|
| QToolButtons may not match theme | Use `setAutoRaise(True)` for flat appearance that integrates well with most themes. `setObjectName()` provides styling hook. Example QSS for checked state: `QToolButton:checked { background-color: palette(highlight); }` |

### 6.3 Focus / Keyboard Navigation

| Risk | Mitigation |
|------|------------|
| Tab order may include buttons unexpectedly | Set `setFocusPolicy(Qt.NoFocus)` on buttons to exclude from tab navigation. |

### 6.4 Window Resize

| Risk | Mitigation |
|------|------------|
| Layout shifts when resizing | Using QHBoxLayout with stretch ensures buttons stay right-aligned regardless of window width. |

### 6.5 Icon Theme Consistency

| Risk | Mitigation |
|------|------------|
| Icons may not be visible in certain themes | Feather icons are monochrome SVG, work in both light/dark themes. `get_menu_icon()` handles theme-appropriate loading. |

---

## 7. Files to Modify

| File | Change Type | Description |
|------|-------------|-------------|
| `oncutf/controllers/ui/layout_controller.py` | **Modify** | Main implementation in `_setup_center_panel()` |
| `oncutf/controllers/ui/protocols.py` | **Modify** (optional) | Add button type hints if storing on MainWindow |

**No new files required.**

---

## 8. Validation Checklist

All items completed successfully:

- [x] **Placement:** Buttons appear at top-right of FileTable area, inline with "Files" label
- [x] **Size:** Each button is 20x20 logical pixels (scales on high-DPI)
- [x] **Icons:** Button 1 shows grid icon, Button 2 shows list icon
- [x] **Tooltips:** Hovering shows "Thumbnail view (F1)" and "Details view (F2)" respectively
- [x] **Shortcuts:** F1 activates thumbs view, F2 activates details view
- [x] **Alignment:** Buttons stay right-aligned when window resizes
- [x] **Spacing:** 4px gap between the two buttons
- [x] **Style:** Buttons have flat/raised appearance (QToolButton with autoRaise)
- [x] **Mutual exclusion:** Only one button can be checked at a time
- [x] **Default selection:** First button is checked on startup
- [x] **No focus:** Buttons don't receive keyboard focus (Tab key skips them)
- [x] **Theme:** Icons visible in both light and dark themes
- [x] **High-DPI:** Buttons and icons scale correctly on high-DPI displays
- [x] **Data-driven:** Adding a 3rd button requires only 1 line in VIEWPORT_SPECS
- [x] **Dict access:** Buttons accessible via `viewport_buttons["thumbs"]`
- [x] **No regressions:** Files label still updates correctly with selection count
- [x] **Syntax check:** `ruff check .` passes
- [x] **Type check:** `mypy .` passes
- [x] **Tests:** `pytest` passes (no regressions)

---

## 9. Future Considerations

### Signal Connections (Not in Scope)

The button group provides a single signal for viewport changes:

```python
# Connect to button group signal (preferred - single handler)
self.parent_window.viewport_button_group.buttonClicked.connect(self._on_viewport_changed)

# Or connect to individual buttons if different handling needed
self.parent_window.viewport_buttons["thumbs"].clicked.connect(self._on_thumbs_view)
self.parent_window.viewport_buttons["details"].clicked.connect(self._on_details_view)
```

### Active State Indication (Already Implemented)

QToolButton with `setCheckable(True)` provides:
- Visual checked state automatically via Qt styling
- QButtonGroup ensures mutual exclusion
- Can enhance with QSS if needed:
```css
QToolButton:checked {
    background-color: palette(highlight);
    border-radius: 2px;
}
```

---

## 11. Implementation Summary

**Completed:** 2026-01-10

### Files Created:
- `oncutf/ui/viewport_specs.py` - ViewportSpec NamedTuple and VIEWPORT_SPECS list

### Files Modified:
- `oncutf/controllers/ui/layout_controller.py` - Added viewport buttons to _setup_center_panel()
- `oncutf/controllers/ui/protocols.py` - Added type hints for viewport_buttons and viewport_button_group

### Quality Gates:
- ruff check: All checks passed
- mypy: Success, no issues found in 480 source files
- pytest: 1000 passed, 6 skipped

### Next Steps (Out of Scope):
- Signal connections for viewport switching logic
- Implementation of thumbnail and details viewports
- Optional QSS styling for enhanced visual feedback

---

## 10. References

- Footer menu button implementation: `layout_controller.py` lines 547-559
- Tooltip system: `oncutf/utils/ui/tooltip_helper.py`
- Icon loader: `oncutf/utils/ui/icons_loader.py`
- Feather icons: `resources/icons/feather_icons/`
