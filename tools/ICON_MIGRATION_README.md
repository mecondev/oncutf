# Icon Migration Tools

## Overview

Two tools for migrating from Feather Icons to Material Design Icons:

1. **icon_migration_viewer.py** - GUI visual comparison tool
2. **migrate_icons.py** - Command-line migration script

---

## 1. Icon Migration Viewer (GUI)

Visual tool για σύγκριση Feather vs Material Design icons.

### Usage

```bash
python tools/icon_migration_viewer.py
```

### Features

- **Side-by-side comparison**: Feather icon (left) → Material Design icon (right)
- **Visual preview**: Icons displayed at 32px, 48px, or 64px
- **Search/filter**: Find specific icons by name
- **Large preview**: Click row to see 128px preview at bottom
- **Missing detection**: Shows red ❌ for missing Material Design icons
- **Category display**: Shows which folder (navigation, editing, files, etc.)
- **Path info**: Full file paths in bottom panel

### Columns

| Column | Description |
| -------- | ------------- |
| Feather Icon | Original Feather icon name |
| Preview | Small preview of Feather icon |
| → | Migration arrow |
| Material Icon | New Material Design icon name |
| Preview | Small preview of Material icon (or ❌ if missing) |
| Category | Target folder (navigation, editing, files, etc.) |

### Controls

- **Search box**: Filter icons by name
- **32px/48px/64px**: Change preview size
- **Show Missing Material Icons**: Toggle to show/hide missing icons
- **Refresh**: Reload all icons

---

## 2. Migration Script (CLI)

Command-line tool για αυτόματη μετατροπή icon names στον κώδικα.

### Usage

```bash
# Show icon mapping table
python tools/migrate_icons.py --show-mapping

# Find all icon usages
python tools/migrate_icons.py --find

# Dry-run migration (preview changes)
python tools/migrate_icons.py --migrate

# Actually apply changes
python tools/migrate_icons.py --migrate --no-dry-run
```

### Icon Mapping

Total: **39 icon mappings**

Categories:

- Navigation: 5 icons (chevron-up/down/right, x, menu)
- Editing: 6 icons (scissors, clipboard, copy, edit, rotate-ccw/cw)
- Files: 8 icons (folder, file, save, download, refresh, etc.)
- Selection: 2 icons (check-square, square)
- Toggles: 4 icons (plus, minus, toggle-left/right)
- Utilities: 8 icons (info, list, clock, hash, palette, columns, layers, more-vertical)
- Metadata: 6 icons (circle, check-circle, edit-2, alert-circle/triangle, key)

### Examples

```python
# Before (Feather)
get_menu_icon("chevron-up")
get_menu_icon("scissors")
get_menu_icon("folder-plus")

# After (Material Design)
get_menu_icon("keyboard_arrow_up")
get_menu_icon("content_cut")
get_menu_icon("create_new_folder")
```

---

## Icon Folders

### Old Structure (Feather)

```tree
oncutf/resources/icons/
└── feather_icons/         (289 SVG files)
    ├── chevron-up.svg
    ├── scissors.svg
    └── ...
```

### New Structure (Material Design)

```tree
oncutf/resources/icons/
├── navigation/            (6 icons)
│   ├── keyboard_arrow_up.svg
│   └── ...
├── editing/               (6 icons)
│   ├── content_cut.svg
│   └── ...
├── files/                 (7 icons)
├── selection/             (2 icons)
├── toggles/               (4 icons)
├── utilities/             (8 icons)
├── metadata/              (7 icons)
└── preview/               (4 icons)
```

---

## Migration Workflow

### Step 1: Visual Verification ✅ (DONE)

```bash
python tools/icon_migration_viewer.py
```

- Verify all Material Design icons are copied
- Check visual appearance
- Confirm naming is correct

### Step 2: Find Icon Usages

```bash
python tools/migrate_icons.py --find
```

- Shows all files that need updating
- Lists Feather → Material name changes

### Step 3: Dry-Run Migration

```bash
python tools/migrate_icons.py --migrate
```

- Preview all changes
- No files modified (dry-run mode)

### Step 4: Apply Migration

```bash
python tools/migrate_icons.py --migrate --no-dry-run
```

- Updates all Python files
- Replaces Feather names with Material names

### Step 5: Test Application

```bash
python main.py
```

- Verify all icons display correctly
- Check UI elements

### Step 6: Cleanup

```bash
# Delete old Feather icons folder
rm -rf oncutf/resources/icons/feather_icons/
```

---

## Files Updated by Migration

The migration script updates ~69 Python files:

- **Icon loaders**: `icons_loader.py`, `smart_icon_cache.py`, `svg_icon_generator.py`
- **UI widgets**: 15+ widget files
- **Context menus**: 2 files
- **Behaviors**: 3 files
- **Controllers**: 2 files
- **Modules**: 3 files
- **Tests**: 6 test files
- **Examples**: 1 file
- **Tools**: 3 files (including self-reference)

---

## Notes

- **Backward compatibility**: Old Feather icons remain until Step 6
- **Categorized structure**: Icons organized by function (easier to find)
- **SVG format**: All icons are SVG (scalable, colorable)
- **96% confidence**: Most mappings are perfect/good matches
- **Missing icons**: GUI shows red ❌ for any missing Material icons

---

## See Also

- [docs/icon_migration_mapping.md](../docs/icon_migration_mapping.md) - Complete mapping table
- [docs/icon_migration_next_steps.md](../docs/icon_migration_next_steps.md) - Migration plan
- [docs/current_icon_inventory.md](../docs/current_icon_inventory.md) - Full icon inventory
