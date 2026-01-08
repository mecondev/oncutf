# Column Reordering Implementation Plan

**Author:** Michael Economou  
**Date:** 2026-01-08  
**Last Updated:** 2026-01-08 (Final Implementation Complete)
**Status:** [COMPLETE] FULLY IMPLEMENTED & TESTED

---

## Overview

Full column reordering with drag & drop, persistence, lock/unlock toggle, and visual feedback.

**Current Status:** Production Ready

---

## Implementation Summary (Completed)

### [COMPLETE] Features Delivered (Phase 1-4)

#### Phase 1: Lock/Unlock Columns
- [x] Toggle lock state via context menu
- [x] Persist lock state in config: `window.columns_locked`
- [x] UI feedback: lock state displayed in context menu
- [x] Header styling reflects lock state (no hover when locked)

#### Phase 2: Column Reordering (Drag & Drop)
- [x] Drag column headers to reorder
- [x] Visual drag overlay with column name
- [x] Drag overlay shows table selection background color (#748cab)
- [x] Drag overlay shows table header text color (#f0ebd8)
- [x] Drag overlay has opacity/transparency (0.3 alpha for subtle effect)
- [x] Drag overlay positioned dynamically during mouse movement
- [x] Status column (0) is locked and non-movable
- [x] Sections movable state toggled via lock mechanism

#### Phase 3: Order Persistence
- [x] Save column order to config: `window.column_order`
- [x] Restore order on app startup
- [x] Column order stored as `list[column_key]`
- [x] Status column excluded from saved order

#### Phase 4: Model Sync & Edge Cases
- [x] Visual indices properly synchronized with model
- [x] Color column delegate appears in correct position
- [x] Sorting works correctly after reordering
- [x] Column width saved/loaded using correct indices
- [x] Add/remove column workflows maintain order
- [x] Reset Column Order action restores default order
- [x] Reset action disabled when columns locked

#### Phase 5: Polish (Latest)
- [x] Drag overlay visual improvements
- [x] Better color theming for drag feedback
- [x] Responsive opacity handling with RGBA colors
- [x] Context menu grouped by column categories
- [x] Column visibility toggle with visual indicators
- [x] Lock/unlock icons in context menu

### Architecture: Header & Drag Feedback

**InteractiveHeader (`oncutf/ui/widgets/interactive_header.py`):**
```python
def _create_drag_overlay(self, width: int, title: str):
    # Creates floating label for column drag feedback
    # Colors from theme: table_selection_bg + table_header_text
    # RGBA transparency: rgba(116, 138, 171, 0.3) = semi-transparent blue
    # Tracks mouse position and updates overlay dynamically
```

**Overlay Features:**
- Follows mouse cursor during drag
- Shows column name/title
- Theme-aware colors (auto-adapts to light/dark mode)
- Semi-transparent (30% opacity) for clean look
- WA_TransparentForMouseEvents to prevent interference

### Notes

- Status column (0) is not movable (always locked)
- Columns with fixed resize behavior remain responsive
- Lock state UI: toggle-left icon = locked, toggle-right = unlocked
- All column operations use canonical UnifiedColumnService API
- Theme colors: bg=#748cab (blue-gray), text=#f0ebd8 (cream)

### Testing

```bash
ruff check .    # clean
mypy .          # Success: no issues found
pytest          # project test suite (requires exiftool)
```

---

## Phase 6: Future Enhancements (Optional, Not Started)

**Priority:** Low  
**Time Estimate:** 30-50 minutes total

### Possible Features

1. **Column presets** (20 min)
   - Save/load named column configurations
   - "Photography", "Video Editing", "Audio" presets
   - Quick switch between presets
   - Status: NOT STARTED

2. **Keyboard shortcuts** (10 min)
   - Ctrl+Left/Right to move focused column
   - Ctrl+R to reset order
   - Status: NOT STARTED

3. **Column grouping** (30 min)
   - Keep related columns together
   - "File Info", "Image Data", "Device Info" groups
   - Groups can't be split when reordering
   - Status: NOT STARTED

---

## Architecture Notes

### Key Design Decisions

1. **Visual vs Logical Indices:**
   - Qt separates visual (display) order from logical (model) order
   - `header.logicalIndex(visual_index)` converts visual → logical
   - `header.visualIndex(logical_index)` converts logical → visual
   - Model always uses logical indices
   - Display uses visual indices

2. **Order Storage:**
   - Store visual order as `list[column_key]` in config
   - On restore: map column_key → logical_index → set visual position
   - Status column (0) always excluded from saved order

3. **Delegate Updates:**
   - Delegates bind to visual indices (what user sees)
   - Must update when order changes
   - Color column delegate most critical

4. **Selection Preservation:**
   - Already implemented in Phase 1
   - Works with row indices (unaffected by column order)

### Compatibility

- **Qt Version:** PyQt5 5.15+ (sectionsMovable supported)
- **Python:** 3.10+ (type hints with `|` operator)
- **Backward Compatibility:** Users without saved order get default order

---

## Testing Checklist

### [PASSED] Phase 1-4 Tests (PASSED)
- [x] Drag column → restart → order preserved
- [x] Drag multiple columns → order correct
- [x] sectionMoved signal fires correctly
- [x] Config saves/loads order
- [x] get_visible_columns_list() returns visual order
- [x] Color delegate appears in correct visual position
- [x] Sorting works after reordering
- [x] Width saving uses correct indices
- [x] Status column can't be moved
- [x] Add column → reorder → remove → order maintained
- [x] Reset to default works
- [x] Lock/unlock preserves current order
- [x] Context menu grouping works
- [x] Column visibility toggle functional
- [x] UI theme colors applied correctly

### [PASSED] Phase 5 Tests (PASSED)
- [x] Drag overlay displays with correct colors
- [x] Drag overlay positioned accurately
- [x] Opacity/transparency works (RGBA colors)
- [x] Column name shows in drag overlay
- [x] Overlay follows mouse movement
- [x] Theme-aware color adaptation
- [x] No visual glitches during drag
- [x] Responsive on different resolutions

### Quality Gates
- [OK] 974+ tests passing
- [OK] ruff check . — CLEAN
- [OK] mypy . — CLEAN (strict typing for Protocols)

---

## Migration Path

### Existing Users

1. **No saved order:** Default FILE_TABLE_COLUMN_CONFIG order used
2. **First drag:** Order saved to config automatically
3. **Upgrade:** No breaking changes, feature is additive

### Config Format

```json
{
  "window": {
    "columns_locked": false,
    "column_order": [
      "color",
      "filename", 
      "file_size",
      "type",
      "modified"
    ],
    "file_table_columns": {
      "color": true,
      "filename": true,
      "file_size": true,
      ...
    }
  }
}
```

---

## Implementation Priority

**Phase 1 (Lock/Unlock Toggle):** [DONE] COMPLETE (Jan 8, 2026)  
**Phase 2 (Drag & Drop):** [DONE] COMPLETE (Jan 8, 2026)  
**Phase 3 (Persistence):** [DONE] COMPLETE (Jan 8, 2026)  
**Phase 4 (Model Sync & Polish):** [DONE] COMPLETE (Jan 8, 2026)  
**Phase 5 (Visual Polish):** [DONE] COMPLETE (Jan 8, 2026)  

**Total Implementation Time:** ~150 minutes (2.5 hours)  
**Status:** Production Ready [OK]

---

## What's Completed

[+] Full column reordering workflow  
[+] Lock/unlock mechanism with UI controls  
[+] Persistent configuration (config.json)  
[+] Drag & drop visual feedback (overlay)  
[+] Theme-aware colors and styling  
[+] Context menu integration  
[+] Reset to default functionality  
[+] Column visibility toggle  
[+] All tests passing (974+)  
[+] Code quality gates (ruff, mypy clean)  

---

## What's NOT Completed (Future Work)

[-] **Column presets** - Save/load named configurations (20 min)  
[-] **Keyboard shortcuts** - Ctrl+Left/Right for movement (10 min)  
[-] **Column grouping** - Keep related columns together (30 min)  

These are **OPTIONAL enhancements** for future consideration. The core feature is fully complete and production-ready.

---

## References

- [Qt QHeaderView Documentation](https://doc.qt.io/qt-5/qheaderview.html)
- [Column Management Behavior](../oncutf/ui/behaviors/column_management/)
- [Interactive Header](../oncutf/ui/widgets/interactive_header.py)
- [Config System](../oncutf/config/columns.py)
