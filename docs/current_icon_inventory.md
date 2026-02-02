# COMPLETE IMAGE LOGGING - oncutf

**Date:** 2026-02-02
**Status:** Feather Icons (pre-transition to Material Design)

---

## A. PNG ICONS (6 files)

**Location:** `oncutf/resources/icons/`
**Usage:** Preview / Footer StatusBar (rename status indicators)

| Icon | Filename | Usage |
| ------ | ---------- | ------- |
| ✅ | `valid.png` | Rename status: Valid (green checkmark) |
| ❌ | `invalid.png` | Rename status: Invalid (red X) |
| ➖ | `unchanged.png` | Rename status: Unchanged (gray dash) |
| 📋 | `duplicate.png` | Rename status: Duplicate (yellow warning) |
| ▼ | `chevron-down.png` | Tree expand indicator (expanded) |
| ▶ | `chevron-right.png` | Tree expand indicator (collapsed) |

**Note:** These PNGs should be retained or replaced with corresponding SVGs.

---

## B. SVG METADATA/HASH ICONS (8 status types)

**Location:** `oncutf/resources/icons/feather_icons/` (dynamically colored)
**Usage:** File table metadata/hash indicators (top corners of thumbnails)
**Generator:** `oncutf/ui/helpers/svg_icon_generator.py`

| Status | Feather Icon | Color | Hex | Usage |
| -------- | -------------- | ------- | ----- | ------- |
| `none` | `circle.svg` | Dark gray | `#404040` | No metadata |
| `loaded` | `check-circle.svg` | Green | `#51cf66` | Fast metadata loaded |
| `extended` | `info.svg` | Blue | `#0e7bdb` | Extended metadata |
| `modified` | `edit-2.svg` | Yellow | `#fffd9c` | Modified metadata |
| `invalid` | `alert-circle.svg` | Red | `#ff6b6b` | Invalid metadata |
| `partial` | `alert-triangle.svg` | Orange | `#ffd139` | Partial metadata |
| `hash` | `key.svg` | Purple | `#ce93d8` | Hash calculated |
| `basic` | `info.svg` | Light blue | `#e8f4fd` | Basic metadata |

**Note:** These are dynamically colorized by the SVGIconGenerator. They can remain as Feather or be replaced.

---

## C. FEATHER ICONS - UI ELEMENTS (32 unique + 289 total)

**Location:** `oncutf/resources/icons/feather_icons/`
**Usage:** Buttons, context menus, trees, drag cursors, toolbar
**Total Usage:** 99 `get_menu_icon()` calls

### 1. NAVIGATION (7 icons)

| Icon | Feather Name | Usage |
| ------ | -------------- | ------- |
| ▲ | `chevron-up.svg` | Sort ascending, collapse |
| ▼ | `chevron-down.svg` | Sort descending, expand |
| ▶ | `chevron-right.svg` | Tree collapsed state |
| ◀ | `chevron-left.svg` | (Potentially - does not appear to be used) |
| 🔍 | (missing - needs search.svg) | Search field |
| ✕ | `x.svg` | Clear, close, invalid drop |
| ☰ | `menu.svg` | Menu button |

### 2. EDITING & CLIPBOARD (6 icons)

| Icon | Feather Name | Usage |
| ------ | -------------- | ------- |
| ✂ | `scissors.svg` | Cut action |
| 📋 | `clipboard.svg` | Paste action |
| 📄 | `copy.svg` | Copy action, duplicate detection |
| ✏️ | `edit.svg` | Edit metadata |
| ↶ | `rotate-ccw.svg` | Undo, reset rotation |
| ↷ | `rotate-cw.svg` | Redo |

### 3. FILE OPERATIONS (7 icons)

| Icon | Feather Name | Usage |
| ------ | -------------- | ------- |
| 📁 | `folder.svg` | Select folder, compare folder, drag cursor |
| 📂 | `folder-plus.svg` | Browse folder button |
| 📄 | `file.svg` | File operations, drag cursor, load metadata |
| 📝 | `file-plus.svg` | Load extended metadata |
| 💾 | `save.svg` | Save metadata |
| 📥 | `download.svg` | Export metadata |
| 🔄 | `refresh-cw.svg` | Reload folder, invert selection |

### 4. SELECTION & CHECKBOXES (3 icons)

| Icon | Feather Name | Usage |
| ------ | -------------- | ------- |
| ☑ | `check-square.svg` | Select all |
| ☐ | `square.svg` | Deselect all |
| 🔳 | (missing checkbox variant) | |

### 5. TOGGLES & BUTTONS (6 icons)

| Icon | Feather Name | Usage |
| ------ | -------------- | ------- |
| ➕ | `plus.svg` | Add button, counter increment |
| ➖ | `minus.svg` | Remove button, counter decrement |
| 🔘 | `toggle-left.svg` | Toggle OFF state (locked) |
| 🔘 | `toggle-right.svg` | Toggle ON state (unlocked) |
| 🔄 | `refresh.svg` | Refresh/reset action |
| 🔃 | (refresh variants) | |

### 6. UTILITIES & INFO (8 icons)

| Icon | Feather Name | Usage |
| ------ | -------------- | ------- |
| ℹ️ | `info.svg` | Info, metadata drag indicator |
| 📃 | `list.svg` | Show lists, history |
| ⏱ | `clock.svg` | History menu |
| #️⃣ | `hash.svg` | Calculate checksums |
| 🎨 | `palette.svg` | Auto-color by folder |
| 📊 | `columns.svg` | Column visibility menu |
| 📚 | `layers.svg` | Find duplicates in all |
| 🎯 | `more-vertical.svg` | Drag handle (rename modules) |

---

## D. DRAG & DROP ICONS (6 base icons)

**Location:** `oncutf/ui/drag/drag_visual_manager.py`
**Usage:** Drag cursors with status overlays

| Drag Type | Base Icon | Valid Drop | Invalid Drop | Info Drop |
| ----------- | ----------- | ------------ | -------------- | ----------- |
| FILE | `file` | ✓ | `x` | `info` |
| FOLDER | `folder` | ✓ | `x` | `info` |
| MULTIPLE | `copy` | ✓ | `x` | `info` |

**Overlay icons:**

- ✓ (checkmark for valid)
- `x` (X for invalid)
- `info` (i for metadata tree drop)

---

## E. FEATHER ICONS - FULL LIST (289 total)

**Important items that are not used but exist:**

- `alert-triangle.svg`, `alert-octagon.svg` (warnings)
- `image.svg`, `video.svg`, `music.svg` (media types)
- `archive.svg` (compression)
- `settings.svg` (settings)
- `trash.svg`, `trash-2.svg` (delete)
- `eye.svg`, `eye-off.svg` (visibility)
- Many others (communication, social, navigation, shapes, etc.)

---

## USAGE SUMMARY

### Icons that MUST exist (mandatory)

**PNG (6 - for preview status bar):**

- valid, invalid, unchanged, duplicate
- chevron-down, chevron-right

**SVG Metadata (8 feather - dynamic coloring):**

- circle, check-circle, info, edit-2, alert-circle, alert-triangle, key

**SVG UI Elements (32 feather - actively used):**

- Navigation: chevron-up/down/right, x, menu
- Edit: scissors, clipboard, copy, edit, rotate-ccw, rotate-cw
- Files: folder, folder-plus, file, file-plus, save, download, refresh, refresh-cw
- Selection: check-square, square
- Toggles: plus, minus, toggle-left, toggle-right, refresh
- Utils: info, list, clock, hash, palette, columns, layers, more-vertical

**Drag & Drop (3 base + 2 overlays):**

- Base: file, folder, copy
- Overlays: x, info

---

## MIGRATION SUGGESTIONS

### Priority 1: Critical UI Icons (32 Feather)

These need to be replaced immediately with Material Design equivalents.

### Priority 2: Metadata/Hash Icons (8 Feather)

They can remain as Feather with dynamic coloring or be replaced.

### Priority 3: Preview PNG Icons (6)

Convert to SVG or find Material Design equivalents.

### Priority 4: Chevron PNG (2)

If there are Material Design chevrons, replace them.

---

**TOTAL ICONS REQUIRED:**

- 6 PNG (preview status)
- 8 SVG (metadata/hash with dynamic colors)
- 32 SVG (UI elements)
- 3 SVG (drag base icons)
- **TOTAL: ~49 unique icons**

(Out of 289 Feather, we use only ~40)
