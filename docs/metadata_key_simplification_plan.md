# Metadata Key Simplification - Implementation Plan

**Author:** Michael Economou  
**Date:** 2026-01-15  
**Status:** Planned

---

## Overview

**Goal:** Simplify long metadata keys for display while maintaining original keys for operations, with semantic aliasing for cross-format consistency.

**Problem:** MP4 and other video files have extremely long metadata keys like `Audio Format Audio Rec Port Audio Codec` that are difficult to read and use in the UI.

**Solution:** Algorithmic simplification with bidirectional mapping, plus semantic aliases for unified field names across formats (like Lightroom).

---

## Components

1. **SmartKeySimplifier** - Algorithmic key simplification
2. **SimplifiedMetadata** - Wrapper with bidirectional mapping
3. **MetadataKeyRegistry** - Undo/redo, conflicts, export/import, semantic aliases
4. **UI Integration** - Metadata viewer, module configuration

---

## Phase 1: Core Infrastructure

**Duration:** 2-3 days

### 1.1 Create SmartKeySimplifier

**File:** `oncutf/core/metadata/key_simplifier.py`

**Contents:**
- `SmartKeySimplifier` class
- Tokenization with delimiter normalization (space, underscore, dash, dot)
- Common prefix detection across keys
- Repetition removal (consecutive duplicate tokens)
- Adaptive max_segments based on key length
- Collision detection and resolution

**Edge Cases to Handle:**
- Empty/whitespace keys
- Single-word keys
- Unicode/non-ASCII characters
- Numeric tokens (preserve)
- Version numbers (preserve)
- Mixed delimiters
- CamelCase splitting
- Very long single tokens

**Dependencies:** None (pure Python)

**Tests:** `tests/core/metadata/test_key_simplifier.py`

---

### 1.2 Create SimplifiedMetadata Wrapper

**File:** `oncutf/core/metadata/simplified_metadata.py`

**Contents:**
- `SimplifiedMetadata` class
- Bidirectional mapping (original <-> simplified)
- `__getitem__` access with both key types
- `items_simplified()` iterator
- `items_original()` iterator
- `get_original_key()` method
- `get_simplified_key()` method
- `has_collision()` method
- `override_simplified()` method (for user overrides)

**Dependencies:** `key_simplifier.py`

**Tests:** `tests/core/metadata/test_simplified_metadata.py`

---

### 1.3 Create MetadataKeyRegistry

**File:** `oncutf/core/metadata/metadata_key_registry.py`

**Contents:**
- `KeyMapping` dataclass
- `RegistrySnapshot` dataclass
- `MetadataKeyRegistry` class with:
  - Undo/redo with history snapshots (max 50)
  - Conflict resolution storage
  - Export/import (JSON format)
  - Semantic aliases loading from user folder
  - Default aliases (hardcoded fallback)
  - `resolve_key_with_fallback()` method

**Dependencies:** `json_config_manager.py`

**Tests:** `tests/core/metadata/test_metadata_key_registry.py`

---

## Phase 2: Semantic Aliases Configuration

**Duration:** 1 day

### 2.1 Semantic Aliases File

**Location:** `~/.oncutf/semantic_metadata_aliases.json` (auto-created)

**Behavior:**
- Auto-create with defaults on first run
- Load existing if present
- Reload method for manual edits
- NOT editable from UI (advanced users edit manually)

**Default Aliases:**

| Unified Name | Original Keys |
|--------------|---------------|
| Creation Date | EXIF:DateTimeOriginal, XMP:CreateDate, IPTC:DateCreated, QuickTime:CreateDate |
| Modification Date | EXIF:ModifyDate, XMP:ModifyDate, File:FileModifyDate |
| Camera Model | EXIF:Model, XMP:Model, MakerNotes:CameraModelName |
| Camera Make | EXIF:Make, XMP:Make |
| Image Width | EXIF:ImageWidth, File:ImageWidth, PNG:ImageWidth |
| Image Height | EXIF:ImageHeight, File:ImageHeight, PNG:ImageHeight |
| Duration | QuickTime:Duration, Video:Duration, Audio:Duration |
| Frame Rate | QuickTime:VideoFrameRate, Video:FrameRate, H264:FrameRate |
| Audio Codec | Audio Format Audio Rec Port Audio Codec, QuickTime:AudioFormat, Audio:Codec |
| Video Codec | QuickTime:VideoCodec, Video:Codec, H264:CodecID |
| GPS Latitude | EXIF:GPSLatitude, XMP:GPSLatitude, Composite:GPSLatitude |
| GPS Longitude | EXIF:GPSLongitude, XMP:GPSLongitude, Composite:GPSLongitude |
| Copyright | EXIF:Copyright, XMP:Rights, IPTC:CopyrightNotice |
| Artist | EXIF:Artist, XMP:Creator, IPTC:By-line, ID3:Artist |
| Title | XMP:Title, IPTC:ObjectName, QuickTime:DisplayName, ID3:Title |
| ISO | EXIF:ISO, XMP:ISO, MakerNotes:ISO |
| Shutter Speed | EXIF:ShutterSpeed, XMP:ShutterSpeed, Composite:ShutterSpeed |
| Aperture | EXIF:Aperture, XMP:Aperture, Composite:Aperture |
| Focal Length | EXIF:FocalLength, XMP:FocalLength |
| Sample Rate | Audio:SampleRate, QuickTime:AudioSampleRate, RIFF:SampleRate |
| Bit Rate | Audio:BitRate, Video:BitRate, File:AvgBitrate |
| Channels | Audio:Channels, Audio Format Num Of Channel, QuickTime:AudioChannels |
| Color Space | EXIF:ColorSpace, ICC_Profile:ColorSpaceData |
| Orientation | EXIF:Orientation, XMP:Orientation |

---

### 2.2 Update JsonConfigManager

**File:** `oncutf/utils/shared/json_config_manager.py`

**Changes:**
- Add `get_user_config_dir()` method (if not exists)
- Consistent path handling for Windows/Linux/macOS

---

## Phase 3: Integration with Existing Systems

**Duration:** 2-3 days

### 3.1 Update UnifiedMetadataManager

**File:** `oncutf/core/metadata/unified_metadata_manager.py`

**Changes:**
- Add `SmartKeySimplifier` instance
- Add `MetadataKeyRegistry` instance
- Modify `get_metadata()` to return `SimplifiedMetadata`
- Add `get_metadata_value()` with semantic fallback
- Add `_apply_registry_overrides()` method

---

### 3.2 Update Metadata Viewer

**File:** `oncutf/ui/widgets/metadata_viewer.py` (or relevant file)

**Changes:**
- Display simplified keys
- Add tooltip with original key
- Optional: Group semantic aliases separately

---

### 3.3 Update Metadata Rename Module

**File:** `oncutf/modules/metadata.py`

**Changes:**
- Configuration dialog shows simplified keys
- Dropdown groups: "Common Fields" (semantic) + "File-Specific"
- Store both `selected_key_original` and `selected_key_display`
- `get_fragment()` uses `resolve_key_with_fallback()`

---

## Phase 4: Configuration Dialog UI

**Duration:** 1-2 days

### 4.1 Metadata Key Selection Dialog

**File:** `oncutf/ui/dialogs/metadata_key_selection_dialog.py`

**Contents:**
- Dropdown/tree with simplified keys
- Section: "Common Fields (All Formats)" - semantic aliases
- Section: "File-Specific Fields" - file metadata
- Preview value for selected key
- Tooltip shows original key name

---

### 4.2 Undo/Redo UI (Optional)

**File:** `oncutf/ui/widgets/metadata_mapping_manager.py`

**Contents:**
- Undo/Redo buttons
- Export/Import buttons
- Current mappings display (optional)

---

## Phase 5: Testing and Polish

**Duration:** 2 days

### 5.1 Integration Tests

**File:** `tests/integration/test_metadata_simplification_workflow.py`

**Scenarios:**
- Load MP4 file -> simplified keys displayed
- Select semantic alias -> works across MP4/MOV/JPG
- User override -> persists after restart
- Export -> Import on different machine
- Undo/Redo cycle
- Edge case files (unusual metadata)

---

### 5.2 Performance Tests

**File:** `tests/performance/test_key_simplification_performance.py`

**Scenarios:**
- 1000 files with 50 metadata keys each
- Memory usage with large caches
- Simplification computation time

---

### 5.3 Documentation

**File:** `docs/metadata_key_simplification.md` (user-facing)

**Contents:**
- Feature overview
- Configuration file location and format
- How to add custom semantic aliases (manual edit)
- Troubleshooting

---

## File Structure

```
oncutf/
  core/
    metadata/
      key_simplifier.py              # NEW - Phase 1.1
      simplified_metadata.py         # NEW - Phase 1.2
      metadata_key_registry.py       # NEW - Phase 1.3
      unified_metadata_manager.py    # MODIFY - Phase 3.1
  modules/
    metadata.py                      # MODIFY - Phase 3.3
  ui/
    dialogs/
      metadata_key_selection_dialog.py  # NEW/MODIFY - Phase 4.1
    widgets/
      metadata_viewer.py             # MODIFY - Phase 3.2

tests/
  core/
    metadata/
      test_key_simplifier.py         # NEW
      test_simplified_metadata.py    # NEW
      test_metadata_key_registry.py  # NEW
  modules/
    test_metadata_module_simplified.py  # NEW
  integration/
    test_metadata_simplification_workflow.py  # NEW

docs/
  metadata_key_simplification.md     # NEW (user-facing)

~/.oncutf/
  semantic_metadata_aliases.json     # AUTO-CREATED
  custom_metadata_mappings.json      # CREATED ON EXPORT
```

---

## Dependencies Between Phases

```
Phase 1.1 (SmartKeySimplifier)
    |
    v
Phase 1.2 (SimplifiedMetadata)
    |
    v
Phase 1.3 (MetadataKeyRegistry) <-- Phase 2 (Aliases Config)
    |
    v
Phase 3 (Integration)
    |
    v
Phase 4 (UI)
    |
    v
Phase 5 (Testing)
```

---

## Estimated Duration

| Phase | Duration | Cumulative |
|-------|----------|------------|
| Phase 1 | 2-3 days | 2-3 days |
| Phase 2 | 1 day | 3-4 days |
| Phase 3 | 2-3 days | 5-7 days |
| Phase 4 | 1-2 days | 6-9 days |
| Phase 5 | 2 days | 8-11 days |

**Total: 8-11 working days**

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking existing metadata loading | SimplifiedMetadata wraps, doesn't replace |
| Performance with large files | Lazy simplification, cache mappings |
| Edge case metadata keys | Extensive test suite with real samples |
| Config file corruption | Fallback to hardcoded defaults |
| Backward compatibility | Store original keys in module config |

---

## Success Criteria

1. Long MP4 metadata keys display as simplified in UI
2. Semantic aliases work across file formats (JPG/MP4/MOV)
3. Metadata module uses simplified selection with correct value retrieval
4. Undo/redo works for user overrides
5. Export/import preserves user mappings
6. No regression in existing metadata functionality
7. All tests pass (unit, integration, performance)

---

## Progress Tracking

### Phase 1: Core Infrastructure
- [x] 1.1 SmartKeySimplifier (Completed: 2026-01-15)
  - ✅ Core algorithm with collision resolution
  - ✅ 23 unit tests (all passing)
  - ✅ Edge case handling (unicode, camelCase, URL encoding, etc.)
  - ✅ Code quality verified (ruff + mypy clean)
- [ ] 1.2 SimplifiedMetadata
- [ ] 1.3 MetadataKeyRegistry

### Phase 2: Semantic Aliases
- [ ] 2.1 Default aliases file
- [ ] 2.2 JsonConfigManager update

### Phase 3: Integration
- [ ] 3.1 UnifiedMetadataManager
- [ ] 3.2 Metadata Viewer
- [ ] 3.3 Metadata Rename Module

### Phase 4: UI
- [ ] 4.1 Metadata Key Selection Dialog
- [ ] 4.2 Undo/Redo UI (optional)

### Phase 5: Testing
- [ ] 5.1 Integration tests
- [ ] 5.2 Performance tests
- [ ] 5.3 Documentation

---

## Notes

- Semantic aliases are NOT user-editable from UI (like Lightroom)
- Advanced users can manually edit `~/.oncutf/semantic_metadata_aliases.json`
- Custom user alias management is out of scope (YAGNI)
- Localization (Greek field names) is out of scope
