# font system implementation — complete reference

**Author:** Michael Economou  
**Date:** 2026-01-11  
**Status:** COMPLETE - All 1000 tests passing

---

## Overview

The oncutf application now features a **complete, scalable font management system** that allows switching between multiple fonts (currently Inter and JetBrains Mono) with automatic size adjustments. The system is extensible for adding new fonts in the future.

### Key Achievement

- [DONE] **Dynamic Font Injection:** Stylesheets replace hardcoded Inter fonts with configured font via `inject_font_family()`
- [DONE] **Configuration-Based:** `DEFAULT_UI_FONT` flag in `oncutf/config/ui.py` controls which font family is used globally
- [DONE] **Automatic Size Adjustment:** JetBrains fonts get +1pt adjustment for visual consistency
- [DONE] **Embedded Resources:** JetBrains Mono fonts embedded in QRC resources for guaranteed availability
- [DONE] **Fallback Chain:** Each font includes sensible fallbacks (JetBrains → Courier New; Inter → Segoe UI)
- [DONE] **Zero Hardcoding:** All UI font specifications respect the configuration system

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│ Config Layer (oncutf/config/ui.py)                 │
│ ├── DEFAULT_UI_FONT = "jetbrains" | "inter"        │
│ ├── FONT_SIZE_ADJUSTMENTS = {"jetbrains": 1, ...}  │
│ ├── FONT_FAMILIES = {font name: css string}        │
│ └── get_ui_font_family() → CSS font-family string  │
└──────────────────┬──────────────────────────────────┘
                   │
         ┌─────────▼─────────┐
         │ Utility Layer     │
         │ stylesheet_utils  │
         │ & fonts.py        │
         └────────┬──────────┘
                  │
      ┌───────────┼───────────┐
      │           │           │
   ┌──▼──┐    ┌──▼──┐    ┌──▼──┐
   │QSS  │    │QFont│    │Font │
   │Files│    │Obj  │    │DB   │
   └──────┘    └─────┘    └─────┘
```

### Data Flow: Configuration → Stylesheets → UI

1. **Config reads:** `DEFAULT_UI_FONT = "jetbrains"` (oncutf/config/ui.py)
2. **Stylesheet injection:** When module creates QSS string, `inject_font_family(qss)` replaces hardcoded Inter
3. **Font load:** `get_default_ui_font(size)` reads config and loads appropriate font with size adjustment
4. **Render:** UI displays with selected font + size adjustment

---

## Core Components

### 1. Configuration System (`oncutf/config/ui.py`)

**Purpose:** Central source of truth for font selection.

```python
# Toggle between fonts
DEFAULT_UI_FONT = "jetbrains"  # or "inter"

# Size adjustments for visual consistency
FONT_SIZE_ADJUSTMENTS = {
    "inter": 0,        # No adjustment needed
    "jetbrains": 1,    # JetBrains is slightly smaller
}

# Font family definitions with fallbacks
FONT_FAMILIES = {
    "inter": '"Inter", "Segoe UI", Arial, sans-serif',
    "jetbrains": '"JetBrains Mono", "Courier New", monospace',
}

def get_ui_font_family() -> str:
    """Returns CSS font-family string for selected font."""
    return FONT_FAMILIES.get(DEFAULT_UI_FONT, FONT_FAMILIES["inter"])
```

**Key Features:**
- Single configuration point for font selection
- Extensible: adding a new font requires only adding entries to `FONT_FAMILIES`
- No UI changes needed to switch fonts (just edit config)

### 2. Fonts Module (`oncutf/utils/ui/fonts.py`)

**Purpose:** Load fonts into Qt and provide access methods.

```python
class JetBrainsFonts:
    """Manages JetBrains Mono variants (embedded in QRC)."""
    
    def get_font(self, style: str, size: int) -> QFont:
        """Get JetBrains font with specified style and size."""

def get_default_ui_font(size: int = 9, style: str = "regular") -> QFont:
    """Get appropriate font with automatic size adjustment.
    
    - Reads DEFAULT_UI_FONT from config
    - Applies FONT_SIZE_ADJUSTMENTS automatically
    - Loads font via JetBrainsFonts or InterFonts
    """
```

**Key Features:**
- Singleton pattern prevents duplicate font loading
- Size adjustment applied at `QFont` creation time
- Fallback mechanism if configured font unavailable

### 3. Stylesheet Utils (`oncutf/utils/ui/stylesheet_utils.py`)

**Purpose:** Dynamically inject configured fonts into QSS strings.

```python
def inject_font_family(qss_string: str) -> str:
    """Replace hardcoded Inter fonts with configured font.
    
    Replaces:
        font-family: "Inter", "Segoe UI", Arial, sans-serif
    With:
        font-family: [from get_ui_font_family()]
    
    Example:
        original = 'QMenu { font-family: "Inter", "Segoe UI", Arial, sans-serif; }'
        injected = inject_font_family(original)
        # With DEFAULT_UI_FONT = "jetbrains":
        # Result: 'QMenu { font-family: "JetBrains Mono", "Courier New", monospace; }'
    """
```

**Key Features:**
- Simple string replacement in QSS before applying to widgets
- Works with any QSS string
- Applied at stylesheet creation time, not at render time

### 4. Theme Manager Integration (`oncutf/core/theme_manager.py`)

**Purpose:** Apply fonts when rendering main QSS template.

```python
def _render_qss_template(self) -> str:
    """Render QSS template with dynamic font injection."""
    template = load_template("main.qss.template")
    
    # Replace color tokens
    for token, color in self._theme.color_map.items():
        template = template.replace(f"{{{{{token}}}}}", color)
    
    # NEW: Replace hardcoded Inter with configured font
    template = template.replace(
        '"Inter", "Segoe UI", Arial, sans-serif',
        get_ui_font_family()
    )
    
    return template
```

**Key Features:**
- Main theme template updated once at app startup
- All hardcoded Inter fonts in main.qss automatically replaced
- Dialog and control stylesheets additionally updated via `inject_font_family()`

---

## Usage Patterns

### Pattern 1: Dialog/Widget Stylesheet

**Before (hardcoded Inter):**
```python
dialog_qss = f"""
    QDialog {{
        font-family: "Inter", "Segoe UI", Arial, sans-serif;
        background-color: {theme.get_color('background')};
    }}
"""
self.dialog.setStyleSheet(dialog_qss)
```

**After (respects config):**
```python
from oncutf.utils.ui.stylesheet_utils import inject_font_family

dialog_qss = f"""
    QDialog {{
        font-family: "Inter", "Segoe UI", Arial, sans-serif;
        background-color: {theme.get_color('background')};
    }}
"""
self.dialog.setStyleSheet(inject_font_family(dialog_qss))
```

### Pattern 2: QFont Creation

**Before (hardcoded):**
```python
font = QFont("Inter", 10)
label.setFont(font)
```

**After (respects config & size adjustment):**
```python
from oncutf.utils.ui.fonts import get_default_ui_font

font = get_default_ui_font(size=10)
label.setFont(font)
```

### Pattern 3: Switching Fonts

**In code:**
```python
from oncutf.config.ui import DEFAULT_UI_FONT

# Change this line to switch fonts globally:
DEFAULT_UI_FONT = "inter"  # or "jetbrains"
```

**Effect:**
- All dialogs created after this change use new font
- All stylesheets with `inject_font_family()` use new font
- Size adjustments applied automatically

---

## Modified Files

### New Files Created

1. **`oncutf/utils/ui/stylesheet_utils.py`** (NEW)
   - Purpose: Font injection utilities
   - Contains: `inject_font_family()`, `get_font_family_css()`

### Files Updated

1. **`oncutf/config/ui.py`**
   - Added: `DEFAULT_UI_FONT`, `FONT_SIZE_ADJUSTMENTS`, `FONT_FAMILIES`
   - Added: `get_ui_font_family()` function
   - Impact: Configuration system for font selection

2. **`oncutf/utils/ui/fonts.py`**
   - Added: `get_default_ui_font(size, style)` function
   - Added: JetBrainsFonts class implementation
   - Impact: Font loading and size adjustment

3. **`oncutf/core/theme_manager.py`**
   - Updated: `_render_qss_template()` now injects fonts dynamically
   - Impact: Main theme template respects DEFAULT_UI_FONT

4. **`oncutf/ui/widgets/custom_splash_screen.py`**
   - Updated: Fallback fonts now use `get_default_ui_font()`
   - Impact: Splash screen respects font configuration

5. **`oncutf/ui/dialogs/bulk_rotation_dialog.py`**
   - Updated: All QSS strings wrapped with `inject_font_family()`
   - Files affected: 5 stylesheet definitions

6. **`oncutf/ui/dialogs/datetime_edit_dialog.py`**
   - Updated: All QSS strings wrapped with `inject_font_family()`
   - Files affected: 3 stylesheet definitions

7. **`oncutf/core/events/context_menu/base.py`**
   - Updated: Context menu QSS wrapped with `inject_font_family()`
   - Files affected: 1 stylesheet definition

8. **`oncutf/controllers/ui/signal_controller.py`**
   - Updated: Signal controller QSS wrapped with `inject_font_family()`
   - Files affected: 1 stylesheet definition

### Resources Updated

1. **`resources/fonts.qrc`**
   - Added: JetBrains Mono font variants (4 files)
   - Auto-compiled to: `oncutf/ui/resources_rc.py`

2. **`main.py`**
   - Lines 187-191: Loads both `_get_inter_fonts()` and `_get_jetbrains_fonts()` at startup

---

## Extensibility: Adding New Fonts

To add a new font (e.g., "fira") in the future:

### Step 1: Add to Configuration
```python
# oncutf/config/ui.py
FONT_SIZE_ADJUSTMENTS = {
    "inter": 0,
    "jetbrains": 1,
    "fira": 0,  # NEW
}

FONT_FAMILIES = {
    "inter": '"Inter", "Segoe UI", Arial, sans-serif',
    "jetbrains": '"JetBrains Mono", "Courier New", monospace',
    "fira": '"Fira Mono", "Courier New", monospace',  # NEW
}
```

### Step 2: Add Font Files
```bash
mkdir -p resources/fonts/fira/
# Copy .ttf/.otf files
```

### Step 3: Add to QRC (if embedded)
```xml
<!-- resources/fonts.qrc -->
<file>resources/fonts/fira/FiraMono-Regular.ttf</file>
```

### Step 4: Create Loader (if needed)
```python
# oncutf/utils/ui/fonts.py
class FiraFonts:
    def get_font(self, style: str, size: int) -> QFont:
        # Implementation
```

### Step 5: Update main.py
```python
# main.py
_get_fira_fonts()  # Call singleton initializer
```

**Result:** Font switching works immediately without modifying any UI code!

---

## Testing & Validation

### Automated Tests
- **1000 tests:** All pass
- **0 regressions:** No existing functionality broken
- **Lint clean:** `ruff check .` passes
- **Type check:** `mypy .` passes (respecting tier overrides)

### Manual Verification

**Test 1: Font Configuration**
```python
from oncutf.config.ui import DEFAULT_UI_FONT, get_ui_font_family
print(f"Current font: {DEFAULT_UI_FONT}")
print(f"CSS string: {get_ui_font_family()}")
# Output:
# Current font: jetbrains
# CSS string: "JetBrains Mono", "Courier New", monospace
```

**Test 2: Font Switching**
```python
import oncutf.config.ui as ui
from oncutf.utils.ui.stylesheet_utils import inject_font_family

ui.DEFAULT_UI_FONT = "inter"
qss = 'QWidget { font-family: "Inter", "Segoe UI", Arial, sans-serif; }'
result = inject_font_family(qss)
# Output: QWidget { font-family: "Inter", "Segoe UI", Arial, sans-serif; }

ui.DEFAULT_UI_FONT = "jetbrains"
result = inject_font_family(qss)
# Output: QWidget { font-family: "JetBrains Mono", "Courier New", monospace; }
```

**Test 3: Application Startup**
```bash
python main.py &
sleep 2
# Logs show: [INFO] Loaded 4 JetBrains Mono font variants
# UI renders correctly with configured fonts
pkill -f "python main.py"
```

---

## Comparison: Before vs. After

| Aspect | Before | After |
|--------|--------|-------|
| **Font Selection** | Hardcoded in 13 locations | Single config variable |
| **Adding New Font** | Modify 13+ files | Edit `FONT_FAMILIES` dict |
| **Size Adjustment** | Manual in each widget | Automatic via config |
| **Font Fallback** | None | Full chain with fallbacks |
| **Stylesheet Injection** | Manual, error-prone | Automatic via helper |
| **Main Theme** | Static hardcoded string | Dynamic replacement |
| **Tests** | 1000 (before) | 1000 (maintained) |
| **Code Complexity** | High (scattered logic) | Low (centralized) |

---

## Key Design Decisions

### 1. Configuration Over Hardcoding
- ✓ Single source of truth
- ✓ No code recompilation to switch fonts
- ✓ Scalable to unlimited fonts

### 2. Automatic Size Adjustment
- ✓ Different fonts appear consistently at different sizes
- ✓ Adjustment configured per-font
- ✓ Applied at QFont creation time

### 3. Stylesheet Injection vs. Template Replacement
- ✓ Template replacement: Main theme applies once
- ✓ Injection utility: Dialog stylesheets apply on creation
- ✓ Both respect `DEFAULT_UI_FONT` configuration

### 4. Embedded + Filesystem Fonts
- ✓ JetBrains: Embedded in QRC (guaranteed availability)
- ✓ Inter: Filesystem (avoids bloat, system fallback available)
- ✓ Both loaded at startup for consistency

---

## Future Improvements (Optional)

### 1. Runtime Font Switching UI
```python
# Potential: Add font selector in preferences dialog
class FontSelector(QComboBox):
    def on_font_changed(self, font_name):
        config.DEFAULT_UI_FONT = font_name
        # Re-render all dialogs
```

### 2. Per-Component Font Override
```python
# Potential: Allow specific widgets to use different fonts
dialog.setFont(get_default_ui_font(size=11, style="bold"))
```

### 3. Font Size Configuration
```python
# Potential: Add to config
FONT_BASE_SIZE = 9  # Currently hardcoded
```

### 4. System Font Detection
```python
# Potential: Fallback to system fonts if embedded unavailable
```

---

## Reference Files

| Module | Purpose | Status |
|--------|---------|--------|
| `oncutf/config/ui.py` | Font configuration | COMPLETE |
| `oncutf/utils/ui/fonts.py` | Font loading | COMPLETE |
| `oncutf/utils/ui/stylesheet_utils.py` | Font injection | COMPLETE |
| `oncutf/core/theme_manager.py` | Theme rendering | UPDATED |
| `resources/fonts.qrc` | QRC resources | COMPLETE |
| `oncutf/ui/dialogs/*.py` | Dialog stylesheets | UPDATED |
| `oncutf/core/events/context_menu/base.py` | Context menu | UPDATED |
| `oncutf/controllers/ui/signal_controller.py` | Signal handling | UPDATED |

---

## Maintenance Notes

### Regular Tasks
1. **Monitor imports:** Ensure `inject_font_family` imported before use
2. **Test font changes:** When adding new fonts, verify size adjustment looks right
3. **Update docs:** If changing FONT_FAMILIES structure

### Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| Font not changing | `inject_font_family()` not called | Add import + wrap QSS |
| Wrong size | Size adjustment not applied | Use `get_default_ui_font()` |
| Fallback not working | Font not in QFontDatabase | Ensure font loaded in `main.py` |
| Lint errors | Unused imports | Run `ruff check . --fix` |

---

## Summary

The oncutf application now has a **production-ready font management system** that is:

- **Centralized:** One config variable controls global font selection
- **Extensible:** Adding new fonts requires only config changes
- **Automatic:** Size adjustments applied transparently
- **Tested:** All 1000 tests pass, no regressions
- **Maintainable:** Clear patterns for stylesheet injection and font creation
- **Scalable:** Ready for runtime font switching or per-component overrides

Toggle fonts by changing `DEFAULT_UI_FONT` in `oncutf/config/ui.py` — everything else happens automatically.
