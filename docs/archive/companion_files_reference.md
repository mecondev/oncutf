# Companion Files Reference Guide

## Overview

Companion files are metadata or preview files that are automatically synchronized when you rename the main file. OnCutF automatically detects and renames companion files even when they're hidden from the UI.

## Main File ↔ Companion File Relationships

### Video Files

| Main File | Companion Files | Example | Source |
|-----------|-----------------|---------|--------|
| **MP4, MOV** | `M01.XML`, `M02.XML` (metadata), `.srt`, `.vtt`, `.ass` (subtitles) | `video.mp4` → `videoM01.XML`, `video.srt` | Sony video cameras + any subtitle source |
| **MTS, M2TS** | `M01.XML`, `M02.XML` (metadata) | `video.mts` → `videoM01.XML` | AVCHD format (Sony) |
| **MKV, AVI, WMV** | `.srt`, `.vtt`, `.ass`, `.ssa` (subtitles) | `video.mkv` → `video.srt` | User-added subtitles |

### RAW + JPEG Preview Pairs

| Main File | Companion Files | Example | Camera Manufacturer |
|-----------|-----------------|---------|---------------------|
| **CR2** (Canon RAW) | `.jpg`, `.jpeg` (preview), `.xmp` (metadata), `.vrd` (DPP recipe) | `photo.cr2` → `photo.jpg`, `photo.xmp` | Canon |
| **NEF** (Nikon RAW) | `.jpg`, `.jpeg` (preview), `.xmp` (metadata), `.nxd` (recipe) | `photo.nef` → `photo.jpg`, `photo.xmp` | Nikon |
| **ARW** (Sony RAW) | `.jpg`, `.jpeg` (preview), `.xmp` (metadata) | `photo.arw` → `photo.jpg`, `photo.xmp` | Sony |
| **DNG** (Adobe DNG) | `.jpg`, `.jpeg` (preview), `.xmp` (metadata) | `photo.dng` → `photo.jpg`, `photo.xmp` | Adobe/Universal |
| **ORF** (Olympus RAW) | `.jpg`, `.jpeg` (preview), `.xmp` (metadata) | `photo.orf` → `photo.jpg`, `photo.xmp` | Olympus |
| **RW2** (Panasonic RAW) | `.jpg`, `.jpeg` (preview), `.xmp` (metadata) | `photo.rw2` → `photo.jpg`, `photo.xmp` | Panasonic |
| **PEF** (Pentax RAW) | `.jpg`, `.jpeg` (preview), `.xmp` (metadata) | `photo.pef` → `photo.jpg`, `photo.xmp` | Pentax |

### JPEG/Image Files with Metadata

| Main File | Companion Files | Example | Source |
|-----------|-----------------|---------|--------|
| **JPG, JPEG** | `.xmp` (metadata), RAW files (CR2, NEF, ARW, etc.) | `photo.jpg` → `photo.xmp` | Lightroom, darktable, RawTherapee, etc. |
| **PNG, TIFF, TIF, GIF, WEBP** | `.xmp` (metadata) | `image.png` → `image.xmp` | Post-processing software |

## Valid Match Examples ✓

### Video Pairs
```
video.mp4          ↔ videoM01.XML       ✓ Sony camera metadata
video.mp4          ↔ videoM02.XML       ✓ Sony camera metadata (second file)
video.mp4          ↔ video.srt          ✓ Subtitle
video.mp4          ↔ video.vtt          ✓ WebVTT subtitle
video.mp4          ↔ video.ass          ✓ ASS subtitle
video.mts          ↔ videoM01.XML       ✓ AVCHD (Sony) metadata
video.mkv          ↔ video.srt          ✓ Embedded subtitle sidecar
```

### RAW + JPEG Pairs (Critical!)
```
photo.cr2          ↔ photo.jpg          ✓ Canon RAW + preview JPEG
photo.cr2          ↔ photo.jpeg         ✓ Canon RAW + preview JPEG
photo.nef          ↔ photo.jpg          ✓ Nikon RAW + preview JPEG
photo.arw          ↔ photo.jpg          ✓ Sony RAW + preview JPEG
photo.dng          ↔ photo.jpg          ✓ Adobe DNG + preview JPEG
photo.orf          ↔ photo.jpg          ✓ Olympus RAW + preview JPEG
photo.rw2          ↔ photo.jpg          ✓ Panasonic RAW + preview JPEG
photo.pef          ↔ photo.jpg          ✓ Pentax RAW + preview JPEG
```

### Metadata XMP Pairs
```
photo.cr2          ↔ photo.xmp          ✓ RAW + XMP sidecar (Lightroom, etc.)
photo.jpg          ↔ photo.xmp          ✓ JPEG + XMP sidecar
photo.jpg          ↔ photo.cr2          ✓ JPG preview + RAW (bidirectional)
photo.jpg          ↔ photo.nef          ✓ JPG preview + RAW (bidirectional)
```

## Invalid Match Examples ✗

```
video.mp4          ✗ photo.xmp          Different file types
photo.cr2          ✗ photo.mov          Different file types

video.mp4          ✗ video.SUB          SUB not in video subtitle patterns
photo.cr2          ✗ photo.TXT          TXT not a recognized companion

photo.cr2          ✗ image.jpg          Different stems ("photo" vs "image")
video.mp4          ✗ myvideo.srt        Different stems ("video" vs "myvideo")
```

## Matching Rules

1. **Stem must match exactly**: File names before the extension must be identical
   - ✓ `photo.cr2` + `photo.jpg` (stems match: "photo" = "photo")
   - ✗ `photo.cr2` + `photo_copy.jpg` (stems differ: "photo" ≠ "photo_copy")

2. **Extension must be in companion patterns**: Only supported extensions are matched
   - ✓ `photo.cr2` + `photo.jpg` (JPG is in CR2 patterns)
   - ✗ `photo.cr2` + `photo.psd` (PSD not in CR2 patterns)

3. **Case-insensitive matching**: Extensions are matched regardless of case
   - ✓ `photo.CR2` + `photo.XMP` (case ignored)
   - ✓ `photo.crw` + `photo.XMP` (case ignored)

4. **Bidirectional relationships**: Both directions work
   - ✓ `photo.cr2` → `photo.jpg` (RAW with JPEG companion)
   - ✓ `photo.jpg` → `photo.cr2` (JPEG with RAW companion)

## Real-World Workflow Example

### Scenario: Importing RAW + JPEG from Canon Camera

**Initial folder state:**
```
vacation/
  photo_001.cr2          ← Canon RAW (main file)
  photo_001.jpg          ← Camera-generated JPEG preview
  photo_002.cr2
  photo_002.jpg
```

**User action:** Rename `photo_001.cr2` → `sunset_beach.cr2`

**OnCutF automatically renames:**
```
vacation/
  sunset_beach.cr2       ← Renamed
  sunset_beach.jpg       ← Auto-renamed (companion)
  photo_002.cr2
  photo_002.jpg
```

**UI display** (with `SHOW_COMPANION_FILES_IN_TABLE = False`):
- Shows only: `sunset_beach.cr2` and `photo_002.cr2` (JPGs are hidden)

### Scenario: Lightroom Workflow with XMP Sidecars

**Initial folder state:**
```
photos/
  photo_001.cr2          ← Canon RAW (main file)
  photo_001.jpg          ← Preview JPEG
  photo_001.xmp          ← Lightroom metadata sidecar
  photo_002.cr2
  photo_002.jpg
  photo_002.xmp
```

**User action:** Rename `photo_001.cr2` → `event_sunset.cr2`

**OnCutF automatically renames:**
```
photos/
  event_sunset.cr2       ← Renamed
  event_sunset.jpg       ← Auto-renamed (JPEG preview companion)
  event_sunset.xmp       ← Auto-renamed (XMP metadata companion)
  photo_002.cr2
  photo_002.jpg
  photo_002.xmp
```

## Supported Camera Manufacturers

| Manufacturer | RAW Format | Metadata Format | Notes |
|-------------|-----------|-----------------|-------|
| Canon | CR2, CRW | XMP, VRD (DPP recipes) | Dual record: CR2 + JPG |
| Nikon | NEF, NRW | XMP, NXD (NX Studio) | Dual record: NEF + JPG |
| Sony | ARW, SRF | XMP | Dual record: ARW + JPG; XML for video |
| Adobe | DNG | XMP | Universal RAW format |
| Olympus | ORF | XMP | Dual record: ORF + JPG |
| Panasonic | RW2 | XMP | Dual record: RW2 + JPG |
| Pentax | PEF | XMP | Dual record: PEF + JPG |

## Post-Processing Software Integration

These applications create XMP sidecars that OnCutF will keep synchronized:

- **Lightroom Classic/CC** - Creates `.xmp` files
- **Capture One** - Creates `.xmp` files
- **Darktable** - Creates `.xmp` files  
- **RawTherapee** - Creates `.xmp` files
- **digiKam** - Creates `.xmp` files
- **Affinity Photo** - Creates `.xmp` files

## FAQ

**Q: My CR2 + JPG pairs aren't being treated as companions?**
A: Make sure they have identical base names (e.g., `photo.cr2` + `photo.jpg`, not `photo.cr2` + `photo_preview.jpg`)

**Q: Will renaming my RAW file also rename the JPEG preview?**
A: Yes, automatically! When you rename `photo.cr2` → `sunset.cr2`, the paired `photo.jpg` becomes `sunset.jpg`

**Q: What if I don't want the JPG renamed?**
A: Currently OnCutF automatically renames all detected companions. You could move the JPG to a different folder to break the pairing.

**Q: Are XMP files always created?**
A: No, only if you use post-processing software like Lightroom. Camera-generated JPG companions are always created if "Dual Record" mode is enabled on supported cameras.

**Q: Will subtitles be renamed with video files?**
A: Yes! If you rename `video.mp4` → `edited.mp4`, all paired subtitles (`video.srt`, `video.vtt`, etc.) automatically become `edited.srt`, `edited.vtt`, etc.
