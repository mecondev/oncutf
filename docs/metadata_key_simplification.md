# Metadata Key Simplification - User Guide

**Author:** Michael Economou  
**Date:** 2026-01-15  
**Version:** 1.0

---

## Overview

The **Metadata Key Simplification** feature makes metadata easier to read and work with by automatically converting long, technical metadata keys into shorter, human-friendly names.

**Example:**
- Before: `Audio Format Audio Rec Port Audio Codec`
- After: `Audio Codec`

This feature works across all metadata views in oncutf: the metadata tree viewer and the metadata rename module.

---

## Key Features

### 1. Simplified Display Names

Long metadata keys are automatically simplified using smart algorithms:

| Original Key | Simplified Key |
|--------------|----------------|
| `Audio Format Audio Rec Port Audio Codec` | `Audio Codec` |
| `Video Format Info Codec` | `Video Codec` |
| `EXIF:ImageSensorType` | `Image Sensor Type` |
| `File:FileModifyDate` | `File Modify Date` |

### 2. Semantic Aliases (Common Fields)

The most commonly used metadata fields are unified across different file formats using **semantic aliases**. This means the same field name works for JPG, MP4, MOV, and other formats:

| Unified Name | Works With |
|--------------|------------|
| **Creation Date** | EXIF:DateTimeOriginal, XMP:CreateDate, QuickTime:CreateDate |
| **Camera Model** | EXIF:Model, XMP:Model, MakerNotes:CameraModelName |
| **Duration** | QuickTime:Duration, Video:Duration, Audio:Duration |
| **Frame Rate** | QuickTime:VideoFrameRate, Video:FrameRate, H264:FrameRate |
| **Audio Codec** | Audio Format Audio Rec Port Audio Codec, QuickTime:AudioFormat |
| **Video Codec** | QuickTime:VideoCodec, Video:Codec, H264:CodecID |
| **GPS Latitude** | EXIF:GPSLatitude, XMP:GPSLatitude, Composite:GPSLatitude |
| **ISO** | EXIF:ISO, XMP:ISO, MakerNotes:ISO |
| **Aperture** | EXIF:Aperture, XMP:Aperture, Composite:Aperture |

See the full list of 25+ semantic aliases in the [Configuration File](#configuration-file) section.

### 3. Original Key Tooltips

When a metadata key has been simplified, you can hover over it to see the original technical name:

- **Displayed:** `Creation Date`
- **Tooltip:** `Original key: EXIF:DateTimeOriginal`

This helps when you need to know the exact metadata field being used.

---

## Where Simplification Appears

### Metadata Tree Viewer

The metadata tree (right side of main window) shows simplified keys:

```
File Info (5 fields)
  ├─ File Name: video.mp4
  ├─ File Size: 1.5 MB
  └─ Modification Date: 2026-01-15 10:30

Camera Settings (3 fields)
  ├─ Camera Model: Canon EOS R5        ← Simplified from EXIF:Model
  ├─ ISO: 400                          ← Simplified from EXIF:ISO
  └─ Aperture: f/2.8                   ← Simplified from EXIF:Aperture

Audio Info (2 fields)
  ├─ Audio Codec: AAC                  ← Simplified from Audio Format...
  └─ Duration: 120.5s
```

### Metadata Rename Module

When using metadata fields in file renaming, the dropdown shows:

**Common Fields** (always at top)
- Creation Date
- Camera Model
- Duration
- Frame Rate
- Audio Codec
- (and other semantic aliases)

**Camera Settings**
- ISO
- Shutter Speed
- Focal Length

**Image Info**
- Image Width
- Image Height
- Color Space

---

## Configuration File

Semantic aliases are stored in a JSON configuration file that is **automatically created** the first time you use oncutf:

### Location

**Linux:**
```
~/.local/share/oncutf/semantic_metadata_aliases.json
```

**Windows:**
```
%APPDATA%\oncutf\semantic_metadata_aliases.json
```

**macOS:**
```
~/Library/Application Support/oncutf/semantic_metadata_aliases.json
```

### File Format

The file contains a mapping of unified names to original metadata keys:

```json
{
  "Creation Date": [
    "EXIF:DateTimeOriginal",
    "XMP:CreateDate",
    "IPTC:DateCreated",
    "QuickTime:CreateDate"
  ],
  "Camera Model": [
    "EXIF:Model",
    "XMP:Model",
    "MakerNotes:CameraModelName"
  ]
}
```

### Priority

When multiple original keys are listed, oncutf uses the **first available key** in the file. For example:
- If a JPG has `EXIF:DateTimeOriginal`, it will be used for "Creation Date"
- If an MP4 has `QuickTime:CreateDate`, it will be used for "Creation Date"

---

## Advanced: Manual Editing

**For advanced users only:** You can manually edit the semantic aliases file to add custom unified names.

### Steps

1. **Close oncutf** (important - changes made while running will be overwritten)

2. **Open the configuration file** in a text editor:
   ```bash
   # Linux
   nano ~/.local/share/oncutf/semantic_metadata_aliases.json
   ```

3. **Add your custom alias:**
   ```json
   {
     "Creation Date": [...],
     "My Custom Field": [
       "XMP:CustomTag",
       "EXIF:MySpecialField"
     ]
   }
   ```

4. **Save and restart oncutf**

### Important Notes

- **Backup first:** oncutf creates automatic backups with timestamps if the file is corrupted
- **Valid JSON required:** Use a JSON validator to check syntax
- **Array format:** Each unified name maps to an **array of strings**, even if just one key
- **No UI editor:** There is no built-in UI for editing aliases (by design, to keep it simple)

---

## Troubleshooting

### Simplified names not showing

1. **Check if metadata is loaded:**
   - Drag files into oncutf
   - Right-click → Load Metadata
   - Check metadata tree on the right

2. **Check configuration file exists:**
   ```bash
   ls ~/.local/share/oncutf/semantic_metadata_aliases.json
   ```

3. **Reload oncutf** if you edited the configuration file manually

### Original keys still showing

The simplification only applies to keys with:
- Recognizable patterns (e.g., `Audio Format Audio Rec Port Audio Codec`)
- Semantic aliases configured
- Prefixes like `EXIF:`, `XMP:`, `QuickTime:`

Simple keys like `FileName` or `FileSize` are already readable and are not simplified.

### Configuration file corrupted

If you see errors about the configuration file:

1. Check `~/.local/share/oncutf/` for backup files:
   ```
   semantic_metadata_aliases.json.backup_YYYYMMDD_HHMMSS
   ```

2. Restore from backup:
   ```bash
   cp semantic_metadata_aliases.json.backup_20260115_103000 \
      semantic_metadata_aliases.json
   ```

3. If no backup, delete the file and restart oncutf (defaults will be recreated):
   ```bash
   rm ~/.local/share/oncutf/semantic_metadata_aliases.json
   ```

---

## Technical Details

### Simplification Algorithm

Keys are simplified using a three-tier approach:

1. **Semantic Alias Resolution**  
   - If key matches a semantic alias, use the unified name
   - Example: `EXIF:DateTimeOriginal` → `Creation Date`

2. **Algorithmic Simplification**  
   - Remove repetitive tokens (e.g., "Audio Format Audio" → "Audio")
   - Detect common prefixes across multiple keys
   - Remove redundant segments
   - Example: `Audio Format Audio Rec Port Audio Codec` → `Audio Codec`

3. **camelCase Splitting**  
   - For unprefixed keys, split on capital letters
   - Example: `ImageSensorType` → `Image Sensor Type`

### Original Key Preservation

**Important:** Simplified keys are **display-only**. All operations (renaming, copying, etc.) use the **original metadata keys** internally. This ensures:

- No data loss
- Compatibility with external tools
- Correct metadata extraction from files

---

## FAQ

**Q: Can I disable simplification?**  
A: Not currently. However, you can always see the original key in the tooltip.

**Q: Will this work with my custom EXIF tags?**  
A: Yes, if they follow recognizable patterns. You can also add them to the semantic aliases file manually.

**Q: Does this affect the actual metadata in my files?**  
A: No. Simplification is display-only. File metadata is never modified by this feature.

**Q: Can I export my custom aliases?**  
A: Yes. Simply copy the `semantic_metadata_aliases.json` file to another machine.

**Q: What happens if two keys simplify to the same name?**  
A: The simplification algorithm detects collisions and keeps keys unique by preserving distinguishing parts.

---

## Related Documentation

- [Metadata Key Simplification Plan](metadata_key_simplification_plan.md) - Technical implementation details
- [Application Workflow](application_workflow.md) - Overall application usage
- [Safe Rename Workflow](safe_rename_workflow.md) - Using metadata in file renaming

---

## Support

If you encounter issues with metadata simplification:

1. Check this guide's [Troubleshooting](#troubleshooting) section
2. Look for error messages in the application log
3. Report issues with sample files and metadata keys

**Note:** Please do not edit the configuration file while oncutf is running. Changes will be lost when the application closes.
