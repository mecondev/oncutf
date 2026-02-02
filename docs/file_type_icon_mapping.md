# File Type Icon Mapping: Feather → Material Design

**Date:** 2026-02-02  
**Purpose:** Map file type icons for CustomFileSystemModel

---

## FILE TYPE ICONS MAPPING

| Feather Icon | Material Design Icon | Material File | Category | File Extensions |
|--------------|----------------------|---------------|----------|-----------------|
| `image` | `image` | `image.svg` | filetypes | jpg, jpeg, png, gif, bmp, tiff, webp, svg, ico, raw, cr2, nef, dng |
| `video` | `movie` | `movie.svg` | filetypes | mp4, avi, mov, mkv, wmv, flv, webm, m4v, 3gp, mpg, mpeg |
| `music` | `audio_file` | `audio_file.svg` | filetypes | mp3, wav, flac, aac, ogg, wma, m4a, opus |
| `file-text` | `description` | `description.svg` | filetypes | txt, md, rtf, doc, docx, pdf, odt |
| `archive` | `folder_zip` | `folder_zip.svg` | filetypes | zip, rar, 7z, tar, gz, bz2, xz |
| `code` | `code` | `code.svg` | filetypes | py, js, html, css, cpp, c, java, php, xml, json, yaml, yml |
| `folder` | `folder` | `folder.svg` | files | (directories) |
| `file` | `draft` | `draft.svg` | files | (default/unknown) |

---

## NEW FEATURE ICONS

| Use Case | Feather Icon | Material Design Icon | Material File | Category |
|----------|--------------|----------------------|---------------|----------|
| **Rotation** |
| Rotate left | `rotate-ccw` | `rotate_left` | `rotate_left.svg` | editing |
| Rotate right | `rotate-cw` | `rotate_right` | `rotate_right.svg` | editing |
| **Zoom** |
| Zoom in | (new) | `zoom_in` | `zoom_in.svg` | utilities |
| Zoom out | (new) | `zoom_out` | `zoom_out.svg` | utilities |
| **View** |
| Grid view | (new) | `grid_view` | `grid_view.svg` | utilities |
| Layers/Stacks | `layers` | `stacks` | `stacks.svg` | utilities |
| **Filters** |
| Filter | (new) | `filter_alt` | `filter_alt.svg` | utilities |
| **Navigation** |
| Search | `search` | `search` | `search.svg` | navigation |
| **Metadata** |
| Reset rotation | (new) | `flip_camera_ios` | `flip_camera_ios.svg` | utilities |
| History | (new) | `history` | `history.svg` | utilities |
| **Progress** |
| Activity/Progress | (new) | `progress_activity` | `progress_activity.svg` | utilities |

---

## CODE UPDATES REQUIRED

### 1. CustomFileSystemModel (oncutf/ui/widgets/custom_file_system_model.py)

**Current:**

```python
FILE_TYPE_ICONS = {
    "jpg": "image",
    "mp4": "video",
    "mp3": "music",
    "txt": "file-text",
    "zip": "archive",
    "py": "code",
}
```

**After Migration:**

```python
FILE_TYPE_ICONS = {
    "jpg": "image",      # Material: image.svg (same name!)
    "mp4": "movie",      # Material: movie.svg (was "video")
    "mp3": "audio_file", # Material: audio_file.svg (was "music")
    "txt": "description",# Material: description.svg (was "file-text")
    "zip": "folder_zip", # Material: folder_zip.svg (was "archive")
    "py": "code",        # Material: code.svg (same name!)
}
```

### 2. Icons Loader (oncutf/ui/helpers/icons_loader.py)

**Update search paths:**

```python
# OLD: Search only in feather_icons/
feather_path = Path(base_dir) / "feather_icons" / f"{name}.svg"

# NEW: Search in categorized folders
search_paths = [
    Path(base_dir) / "filetypes" / f"{name}.svg",
    Path(base_dir) / "utilities" / f"{name}.svg",
    Path(base_dir) / "editing" / f"{name}.svg",
    Path(base_dir) / "files" / f"{name}.svg",
    Path(base_dir) / "navigation" / f"{name}.svg",
    # ... etc
]
```

---

## ICON INVENTORY

### Total Material Design Icons: 51

**By Category:**

- navigation: 6 icons
- editing: 8 icons (6 original + 2 rotation)
- files: 8 icons (7 original + 1 archive)
- selection: 2 icons
- toggles: 4 icons
- utilities: 16 icons (8 original + 8 new)
- metadata: 7 icons
- preview: 4 icons
- **filetypes: 7 icons** (NEW)

### New Icons Added: 15

**Editing (2):**

- rotate_left.svg
- rotate_right.svg

**Utilities (8):**

- zoom_in.svg
- zoom_out.svg
- filter_alt.svg
- grid_view.svg
- history.svg
- flip_camera_ios.svg
- progress_activity.svg
- stacks.svg

**Filetypes (7):**

- image.svg
- movie.svg
- audio_file.svg
- description.svg
- folder_zip.svg
- code.svg
- photo.svg (alternative)

---

## MIGRATION STEPS

### Step 1: Update Icon Names in Code ✅ (READY)

```bash
python tools/migrate_icons.py --migrate --no-dry-run
```

This will update:

- CustomFileSystemModel.FILE_TYPE_ICONS
- All get_menu_icon() calls
- Metadata icon mappings

### Step 2: Update Icon Search Paths

Modify `icons_loader.py` to search in categorized folders instead of flat `feather_icons/`

### Step 3: Test File Tree

```bash
python main.py
```

Verify:

- ✓ Folder icons display
- ✓ Image file icons (jpg, png, etc.)
- ✓ Video file icons (mp4, mov, etc.)
- ✓ Audio file icons (mp3, wav, etc.)
- ✓ Document icons (txt, pdf, etc.)
- ✓ Archive icons (zip, rar, etc.)
- ✓ Code file icons (py, js, etc.)

### Step 4: Cleanup

```bash
rm -rf oncutf/resources/icons/feather_icons/
```

---

## NOTES

- **"image" icon:** Same name in both Feather and Material (no change needed!)
- **"code" icon:** Same name in both (no change needed!)
- **"music" → "audio_file":** Name change required
- **"video" → "movie":** Name change required
- **"file-text" → "description":** Name change required
- **"archive" → "folder_zip":** Name change required
- **"layers" → "stacks":** User requested this change

All Material Design icons verified to exist in source directory.
