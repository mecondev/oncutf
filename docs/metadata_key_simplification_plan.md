# Metadata Key Simplification - Implementation Plan

**Author:** Michael Economou  
**Date:** 2026-01-15  
**Status:** In Progress (Phases 1-3 Complete)

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

**Location:** `~/.local/share/oncutf/semantic_metadata_aliases.json` (auto-created)

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
      key_simplifier.py                      # DONE - Phase 1.1
      simplified_metadata.py                 # DONE - Phase 1.2
      metadata_key_registry.py               # DONE - Phase 1.3
      semantic_aliases_manager.py            # DONE - Phase 2.1
      metadata_simplification_service.py     # DONE - Phase 3.1
  ui/
    widgets/
      metadata_tree/
        service.py                           # MODIFIED - Phase 3.2
        controller.py                        # MODIFIED - Phase 3.2
      metadata/
        metadata_keys_handler.py             # MODIFIED - Phase 3.3
    dialogs/
      metadata_key_selection_dialog.py       # TODO - Phase 4.1

tests/
  core/
    metadata/
      test_key_simplifier.py                     # DONE (23 tests)
      test_simplified_metadata.py                # DONE (23 tests)
      test_metadata_key_registry.py              # DONE (33 tests)
      test_semantic_aliases_manager.py           # DONE (21 tests)
      test_metadata_simplification_service.py    # DONE (17 tests)
  integration/
    test_metadata_simplification_workflow.py     # TODO - Phase 5

docs/
  metadata_key_simplification.md     # NEW (user-facing)

~/.local/share/oncutf/
  semantic_metadata_aliases.json     # DONE - AUTO-CREATED
  custom_metadata_mappings.json      # TODO - EXPORT FEATURE
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

| Phase | Duration | Status | Actual |
|-------|----------|--------|--------|
| Phase 1 | 2-3 days | DONE | 1 day (2026-01-15) |
| Phase 2 | 1 day | DONE | 0.5 days (2026-01-15) |
| Phase 3 | 2-3 days | DONE | 1 day (2026-01-15) |
| Phase 4 | 1-2 days | TODO | - |
| Phase 5 | 2 days | TODO | - |

**Total: 8-11 working days (2.5 days completed, 3-4 days remaining)**

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
  - [x] Core algorithm with collision resolution
  - [x] 23 unit tests (all passing)
  - [x] Edge case handling (unicode, camelCase, URL encoding, etc.)
  - [x] Code quality verified (ruff + mypy clean)
- [x] 1.2 SimplifiedMetadata (Completed: 2026-01-15)
  - [x] Bidirectional mapping (original <-> simplified)
  - [x] Transparent access with both key types
  - [x] User override support
  - [x] Collision detection method
  - [x] 23 unit tests (all passing)
  - [x] Code quality verified (ruff + mypy clean)
- [x] 1.3 MetadataKeyRegistry (Completed: 2026-01-15)
  - [x] Undo/redo with history snapshots (max 50)
  - [x] Semantic aliases with priority-based resolution
  - [x] Export/import JSON functionality
  - [x] 25+ default semantic aliases (Lightroom-style)
  - [x] resolve_key_with_fallback() method
  - [x] 33 unit tests (all passing)
  - [x] Code quality verified (ruff + mypy clean)

### Phase 2: Semantic Aliases
- [x] 2.1 Default aliases file (Completed: 2026-01-15)
  - [x] SemanticAliasesManager implementation
  - [x] Auto-create semantic_metadata_aliases.json with defaults
  - [x] Load/save/reload functionality
  - [x] Corrupted file backup with timestamps
  - [x] Add/remove/reset individual aliases
  - [x] Unicode support
  - [x] 21 unit tests (all passing)
  - [x] Code quality verified (ruff + mypy clean)
- [N/A] 2.2 JsonConfigManager update
  - [SKIP] Already has get_user_data_dir() via AppPaths

### Phase 3: Integration
- [x] 3.1 MetadataSimplificationService (Completed: 2026-01-15)
  - [x] Integration service layer combining all Phase 1 & 2 components
  - [x] get_simplified_metadata() for FileItem wrapping
  - [x] get_metadata_value() with semantic fallback
  - [x] get_simplified_keys() for UI dropdowns
  - [x] get_semantic_groups() for category grouping
  - [x] Singleton pattern with factory method
  - [x] 17 unit tests (all passing)
  - [x] Code quality verified (ruff + mypy clean)
- [x] 3.2 Metadata Viewer (Completed: 2026-01-15)
  - [x] MetadataTreeService.format_key() uses simplification
  - [x] Semantic aliases displayed (Creation Date vs EXIF:DateTimeOriginal)
  - [x] Smart algorithmic simplification (Audio Codec vs Audio Format Audio Rec Port Audio Codec)
  - [x] Tooltips show original keys when simplified
  - [x] Fallback to camelCase splitting for unprefixed keys
  - [x] 121 metadata tests passing
  - [x] Code quality verified (ruff + mypy clean)
- [x] 3.3 Metadata Rename Module (Completed: 2026-01-15)
  - [x] MetadataKeysHandler uses simplification service
  - [x] "Common Fields" group at top of hierarchical combo
  - [x] Displays semantic aliases with high priority
  - [x] Auto-selects first available semantic alias
  - [x] All category keys simplified for display
  - [x] Original keys preserved for operations
  - [x] 121 metadata tests passing
  - [x] Code quality verified (ruff + mypy clean)

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
- Advanced users can manually edit `~/.local/share/oncutf/semantic_metadata_aliases.json`
- Custom user alias management is out of scope (YAGNI)
- Localization (Greek field names) is out of scope

---

## Implementation Summary (Phases 1-3)

### Architecture

**Service Layer Pattern:**
```
UI Layer (MetadataTreeView, MetadataWidget)
    ↓
MetadataSimplificationService (singleton)
    ↓
┌─────────────────────┬─────────────────────┬─────────────────────┐
│ SmartKeySimplifier  │ SimplifiedMetadata  │ MetadataKeyRegistry │
│ (algorithm)         │ (wrapper)           │ (aliases + history) │
└─────────────────────┴─────────────────────┴─────────────────────┘
    ↓
SemanticAliasesManager (JSON persistence)
    ↓
~/.local/share/oncutf/semantic_metadata_aliases.json
```

### Key Design Decisions

1. **No Direct UnifiedMetadataManager Modification**
   - UnifiedMetadataManager is a facade delegating to specialized handlers
   - Created MetadataSimplificationService as separate integration layer
   - Preserves existing architecture without breaking delegation pattern

2. **Tooltip Strategy**
   - Tooltips show original keys ONLY when simplification occurred
   - Example: "Creation Date" shows tooltip "Original key: EXIF:DateTimeOriginal"
   - Unprefixed keys like "FileName" have no tooltip (no simplification needed)

3. **Common Fields Priority**
   - Semantic aliases grouped at top of metadata selection combo
   - Uses first available key from priority list (e.g., EXIF > XMP > File)
   - Remaining keys categorized by domain (Camera Settings, GPS, etc.)

4. **Backward Compatibility**
   - Original keys preserved in all operations
   - Simplified keys are display-only
   - FileItem.metadata remains unchanged (dict[str, Any])
   - Rename modules use original keys for metadata extraction

### Git Commits

| Commit | Phase | Description |
|--------|-------|-------------|
| 762fcf66 | 2.1 | SemanticAliasesManager with 21 tests |
| 6dcfd2a2 | Docs | Removed all emojis from documentation |
| 2efd11ea | 3.1 | MetadataSimplificationService with 17 tests |
| a8c058c5 | 3.2 | MetadataTreeView integration (simplified keys + tooltips) |
| 6751bc40 | 3.3 | MetadataWidget integration (Common Fields group) |

### Test Coverage

**Total: 117 tests passing**
- SmartKeySimplifier: 23 tests
- SimplifiedMetadata: 23 tests
- MetadataKeyRegistry: 33 tests
- SemanticAliasesManager: 21 tests
- MetadataSimplificationService: 17 tests

### Performance Notes

- Simplification is lazy (computed on-demand)
- Registry loads once at startup
- Semantic aliases cached in memory
- No impact on file loading performance (metadata extraction unchanged)

### Next Steps (Phases 4-5)

1. **Phase 4:** Optional UI for metadata key management
   - Undo/redo dialog for registry changes
   - Export/import user mappings
   - Key conflict resolution UI

2. **Phase 5:** Testing and documentation
   - Integration tests with real media files
   - Performance benchmarks (1000+ files)
   - User-facing documentation
