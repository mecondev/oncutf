# Column Reordering Implementation Plan

**Author:** Michael Economou  
**Date:** 2026-01-08  
**Status:** Completed

---

## Overview

Full column reordering with drag & drop, persistence, and lock/unlock toggle.

**Current Status:** Completed

---

## Implementation Summary (Completed)

### Features Delivered

- Column reordering (drag & drop)
- Lock/Unlock Columns toggle (prevents reordering when locked)
- Persisted lock state in config: `window.columns_locked`
- Persisted column order in config: `window.column_order`
- Reset Column Order action (disabled when locked)

### Notes

- The Status column is not movable.
- Columns with fixed resize behavior are not movable.

### Testing

```bash
ruff check .    # clean
mypy .          # Success: no issues found
pytest          # project test suite (requires exiftool)
```

---

## Phase 5: Future Enhancements (Optional)

**Duration:** Variable  
**Priority:** Low

### Possible Features

1. **Column presets** (20 min)
   - Save/load named column configurations
   - "Photography", "Video Editing", "Audio" presets
   - Quick switch between presets

2. **Visual feedback during drag** (15 min)
   - Drop indicator line between columns
   - Ghost column during drag

3. **Keyboard shortcuts** (10 min)
   - Ctrl+Left/Right to move focused column
   - Ctrl+R to reset order

4. **Column grouping** (30 min)
   - Keep related columns together
   - "File Info", "Image Data", "Device Info" groups
   - Groups can't be split when reordering

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

### Phase 2 Tests
- [ ] Drag column → restart → order preserved
- [ ] Drag multiple columns → order correct
- [ ] sectionMoved signal fires correctly
- [ ] Config saves/loads order

### Phase 3 Tests
- [ ] get_visible_columns_list() returns visual order
- [ ] Color delegate appears in correct visual position
- [ ] Sorting works after reordering
- [ ] Width saving uses correct indices

### Phase 4 Tests
- [ ] Status column can't be moved
- [ ] Add column → reorder → remove → order maintained
- [ ] Reset to default works
- [ ] Lock/unlock preserves current order

### Phase 5 Tests (if implemented)
- [ ] Column presets save/load correctly
- [ ] Visual feedback during drag
- [ ] Keyboard shortcuts work

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

**Immediate (Phase 1):** ✅ COMPLETE  
**High Priority (Phases 2-3):** Required for useful feature (~50 min)  
**Medium Priority (Phase 4):** Polish and edge cases (~15 min)  
**Low Priority (Phase 5):** Nice to have enhancements (optional)

**Total Core Implementation Time:** ~65 minutes  
**Total with Polish:** ~80 minutes

---

## Next Steps

1. ✅ Complete Phase 1 (Lock/Unlock Toggle)
2. ⏳ Implement Phase 2 (Order Persistence)
3. ⏳ Implement Phase 3 (Model Sync)
4. ⏳ Test thoroughly with real workflow
5. ⏳ Implement Phase 4 (Edge cases)
6. ⏳ Consider Phase 5 based on user feedback

---

## References

- [Qt QHeaderView Documentation](https://doc.qt.io/qt-5/qheaderview.html)
- [Column Management Behavior](../oncutf/ui/behaviors/column_management/)
- [Interactive Header](../oncutf/ui/widgets/interactive_header.py)
- [Config System](../oncutf/config/columns.py)
