# Keyboard Shortcuts - Application State Requirements

**Author**: Michael Economou
**Date**: November 24, 2025  
**Status**: Analysis + Implementation Plan  

---

## Overview

This document establishes **when each shortcut should work** based on the application state. It provides a comprehensive matrix of shortcuts with their preconditions, validation logic, and user feedback messages.

---

## Application States

### 1️⃣ Empty Application State
```
Condition: No folder opened
file_model.files = []
selected_files = []
Status: "No folder selected"

Active Shortcuts:
- Ctrl+O (Browse Files)
- F5 (Force Reload) 
- Escape (Cancel Drag)

Inactive Shortcuts:
- All file/metadata operations require files first
```

### 2️⃣ Folder Loaded, No Selection
```
Condition: Folder opened, no files selected
file_model.files = [10 files]
selected_files = []
Status: "10 files loaded, no selection"

Active Shortcuts:
- Ctrl+A (Select All)
- Ctrl+Shift+M (Load metadata for all)
- Ctrl+Shift+E (Load extended for all)
- Ctrl+Shift+H (Calculate hash for all)

Inactive with Feedback:
- Ctrl+M → "No files selected"
- Ctrl+H → "No files selected"
- Ctrl+S → "No files selected"
```

### 3️⃣ Folder Loaded, Partial Selection
```
Condition: 3 of 10 files selected
file_model.files = [10 files]
selected_files = [3 files]
Status: "3 of 10 selected"

Active Shortcuts:
- Ctrl+I (Invert Selection)
- Ctrl+M (Load metadata for selection) - if needed
- Ctrl+H (Calculate hash for selection) - if needed
- Ctrl+S (Save selection metadata) - if modified

Conditional Shortcuts:
- Ctrl+M → Active only if selected files need metadata
- Ctrl+H → Active only if selected files need hash
- Ctrl+S → Active only if selected files have changes
```

### 4️⃣ Metadata Tree Focus
```
Condition: User clicked in metadata tree widget
Active Widget: metadata_tree_view
Status: Can undo/redo metadata changes

Local Shortcuts (Override Global):
- Ctrl+Z → Undo last field edit
- Ctrl+R → Redo last field edit

Global Still Available:
- Ctrl+Shift+Z → Show full history dialog
```

---

## Detailed Shortcut Matrix

### Category A: Selection Management ✅ (No Changes Needed)

| Shortcut | Precondition | Feedback If Blocked | Status |
|----------|--------------|-------------------|--------|
| Ctrl+A | `file_model.files` > 0 | "No files to select" | ✅ Works |
| Ctrl+Shift+A | None (always works) | N/A | ✅ Works |
| Ctrl+I | `file_model.files` > 0 | "No files to invert" | ✅ Works |

**Implementation**: Already complete - these are foundational.

---

### Category B: File Operations ✅ (No Changes Needed)

| Shortcut | Precondition | Feedback | Status |
|----------|--------------|----------|--------|
| Ctrl+O | None | N/A | ✅ Works |
| F5 | None | N/A | ✅ Works |
| Escape | None | N/A | ✅ Works |
| Shift+Escape | None | Shows "Table cleared" | ✅ Works |

**Implementation**: Already complete - safe operations.

---

### Category C: Metadata Loading 🟡 (PARTIALLY FIXED)

#### Current Implementation Status

✅ **shortcut_load_metadata()** - Lines 316-354
- **HAS** metadata check ✓
- Shows message if all files already have metadata ✓
- Prevents unnecessary loading ✓

✅ **shortcut_load_extended_metadata()** - Lines 358-407
- **HAS** metadata check ✓
- Shows message if all files already have extended metadata ✓
- Prevents unnecessary loading ✓

✅ **shortcut_load_metadata_all()** - Lines 421-467 (JUST FIXED)
- **NOW HAS** metadata check ✓
- Validates if ALL files already have metadata ✓
- Shows "All {N} files already have fast metadata" message ✓

✅ **shortcut_load_extended_metadata_all()** - Lines 469-515 (JUST FIXED)
- **NOW HAS** metadata check ✓
- Validates if ALL files already have extended metadata ✓
- Shows "All {N} files already have extended metadata" message ✓

| Shortcut | Precondition | Validation | Feedback | Status |
|----------|--------------|-----------|----------|--------|
| Ctrl+M | Selection exists | Files don't have metadata | "All selected files already have metadata" | ✅ Fixed |
| Ctrl+E | Selection exists | Files don't have extended | "All selected files already have extended metadata" | ✅ Fixed |
| Ctrl+Shift+M | Files exist | Not all have metadata | "All 10 files already have fast metadata" | ✅ Fixed |
| Ctrl+Shift+E | Files exist | Not all have extended | "All 10 files already have extended metadata" | ✅ Fixed |

**Implementation**: ✅ **NOW COMPLETE** - All four methods have validation

**Code Changes**:
```python
# Example from shortcut_load_metadata_all():
metadata_analysis = self.parent_window.event_handler_manager._analyze_metadata_state(all_files)

if not metadata_analysis["enable_fast_selected"]:
    # All files already have metadata - show message
    show_info_message(...)
    return

# Only proceed if some files need loading
load_metadata_for_items(all_files, use_extended=False, source="shortcut_all")
```

---

### Category D: Metadata Saving 🟡 (PARTIALLY FIXED)

#### Current Implementation Status

✅ **save_metadata_for_selected()** - Lines 1167-1201 (JUST FIXED)
- Checks if files selected ✓
- Checks if any modified metadata exists ✓
- **NOW SHOWS** status message if nothing to save ✓
- Messages:
  - "No files selected" → if no selection
  - "No metadata changes to save" → if no modifications
  - "No changes in selected files" → if selected files have no changes

✅ **save_all_modified_metadata()** - Lines 1209-1243 (JUST FIXED)
- Checks if any modified metadata exists ✓
- **NOW SHOWS** status message if nothing to save ✓
- Messages:
  - "No metadata changes to save" → if no modifications
  - "No metadata changes to save" → if no files have changes

| Shortcut | Precondition | Validation | Feedback | Status |
|----------|--------------|-----------|----------|--------|
| Ctrl+S | Selection exists | Selection has modifications | "No metadata changes to save" | ✅ Fixed |
| Ctrl+Shift+S | Files exist | Files have modifications | "No metadata changes to save" | ✅ Fixed |

**Implementation**: ✅ **NOW COMPLETE** - Both save methods have validation and messages

**Code Changes**:
```python
# In save_metadata_for_selected():
if not all_modified_metadata:
    if hasattr(self.parent_window, "status_manager"):
        self.parent_window.status_manager.set_file_operation_status(
            "No metadata changes to save", success=False, auto_reset=True
        )
    return
```

---

### Category E: Hash Operations 🟢 (COMPLETE)

| Shortcut | Precondition | Validation | Feedback | Status |
|----------|--------------|-----------|----------|--------|
| Ctrl+H | Selection exists | Files don't have hash | Shows dialog with "X of Y files need checksums" | ✅ Complete |
| Ctrl+Shift+H | Files exist | Not all have hash | Shows dialog if needed | ✅ Complete |
| Ctrl+L | Files exist | Files with hash exist | "No Files Selected" if empty | ✅ Complete |

**Implementation**: ✅ **ALREADY COMPLETE** - All hash operations have smart validation

**Code Locations**:
- `core/shortcut_manager.py` line 227 (show_results_hash_list) - HAS file check
- `core/application_service.py` line 161 (calculate_hash_selected) - HAS analysis
- `core/application_service.py` line 178 (calculate_hash_all) - HAS analysis

---

### Category F: History & Undo/Redo 🟢 (COMPLETE)

#### Undo/Redo (Local to Metadata Tree)

| Shortcut | Widget | Precondition | Status |
|----------|--------|--------------|--------|
| Ctrl+Z | metadata_tree | Undo available | ✅ Local shortcut implemented |
| Ctrl+R | metadata_tree | Redo available | ✅ Local shortcut implemented |

**Implementation**: ✅ **COMPLETE**
- Local to metadata_tree_view (widget-specific)
- Doesn't interfere with other widgets
- Code: `widgets/metadata_tree_view.py` lines 985-1005

#### History Dialog (Global)

| Shortcut | Scope | Precondition | Status |
|----------|-------|--------------|--------|
| Ctrl+Shift+Z | Global | Always | ✅ Shows history dialog |

**Implementation**: ✅ **COMPLETE**
- Global shortcut (works everywhere)
- Code: `core/shortcut_manager.py` line 190 (show_history_dialog)

---

## Validation Feedback Messages

### By Scenario

#### No Files Loaded
```
User Action: Any shortcut
System Response: Footer shows "No files loaded. Use Ctrl+O to browse files."
Result: No operation performed
```

#### Files Loaded, No Selection
```
User Action: Ctrl+M (Load metadata for selection)
System Response: Footer shows "No files selected"
Result: No dialog opens
```

#### All Files Already Have Metadata
```
User Action: Ctrl+Shift+M (Load metadata for all)
System Response: Info dialog appears
Message: "All 10 file(s) already have fast metadata or better."
Result: No loading operation
```

#### Some Files Need Hash
```
User Action: Ctrl+H with 5 files selected (2 need hash)
System Response: Hash dialog opens
Message: "Calculate checksums for 2 of 5 file(s) that need them"
Result: Hash calculation starts for 2 files
```

#### No Modified Metadata
```
User Action: Ctrl+S (Save selected metadata)
System Response: Footer shows "No metadata changes to save"
Result: No save operation
```

---

## Testing Checklist

### Empty Application
- [ ] Ctrl+M → "No files selected" (footer status)
- [ ] Ctrl+L → "No Files Selected" (footer status)
- [ ] Ctrl+H → "No files selected" (footer status)
- [ ] Ctrl+S → "No files selected" (footer status)
- [ ] Ctrl+Shift+M → "No files available" (footer status)
- [ ] Ctrl+Shift+E → "No files available" (footer status)

### Folder Loaded, No Selection
- [ ] Ctrl+A → Selects all files
- [ ] Ctrl+M → "No files selected" (footer status)
- [ ] Ctrl+Shift+M → Works (loads for all)
- [ ] Ctrl+Shift+E → Works (loads for all)
- [ ] Ctrl+Shift+H → Works (calculates hash for all)

### Folder Loaded, 3 of 10 Selected
- [ ] Ctrl+M → Check metadata state analysis
  - If all have metadata → Shows message
  - If some need metadata → Shows dialog
- [ ] Ctrl+H → Check hash state analysis
  - If all have hash → Shows message
  - If some need hash → Shows dialog
- [ ] Ctrl+S → Check modifications
  - If no changes → "No metadata changes to save"
  - If changes exist → Saves metadata

### Folder Loaded, All Files Have Metadata
- [ ] Ctrl+Shift+M → Shows "All 10 files already have fast metadata"
- [ ] Ctrl+M → Shows "All 3 files already have fast metadata"
- [ ] Ctrl+Shift+E → Shows "All 10 files already have extended metadata"

### Metadata Tree Focus
- [ ] Ctrl+Z → Undo metadata change (if available)
- [ ] Ctrl+R → Redo metadata change (if available)
- [ ] Ctrl+Shift+Z → Show history dialog (still works globally)

---

## Implementation Summary

### Changes Made ✅

1. **shortcut_load_metadata_all()** - Added metadata check
   - File: `core/unified_metadata_manager.py` line 421
   - Added: `_analyze_metadata_state()` check
   - Added: Status message if all files already have metadata

2. **shortcut_load_extended_metadata_all()** - Added metadata check
   - File: `core/unified_metadata_manager.py` line 469
   - Added: `_analyze_metadata_state()` check
   - Added: Status message if all files already have extended metadata

3. **save_metadata_for_selected()** - Added status messages
   - File: `core/unified_metadata_manager.py` line 1167
   - Added: Status message "No files selected"
   - Added: Status message "No metadata changes to save"
   - Added: Status message "No changes in selected files"

4. **save_all_modified_metadata()** - Added status messages
   - File: `core/unified_metadata_manager.py` line 1209
   - Added: Status message "No metadata changes to save" (two cases)

### Category Status

| Category | Status | Notes |
|----------|--------|-------|
| Selection Management | ✅ Complete | Already working, no changes needed |
| File Operations | ✅ Complete | Already working, no changes needed |
| Metadata Loading | ✅ Complete | FIXED: Added checks to all/extended |
| Metadata Saving | ✅ Complete | FIXED: Added status messages |
| Hash Operations | ✅ Complete | Already working, no changes needed |
| Undo/Redo | ✅ Complete | Already working, no changes needed |

---

## Future Enhancements

### Phase 2: Advanced Validation
- [ ] Create centralized validation module (`core/shortcut_validation.py`)
- [ ] Implement conflict detection between shortcuts
- [ ] Add shortcut remapping UI

### Phase 3: User Customization
- [ ] Store custom shortcut mappings in config
- [ ] Provide shortcut scheme presets
- [ ] Add settings dialog for shortcut customization

### Phase 4: Advanced Features
- [ ] Implement rename module local shortcuts (Ctrl+Z/R)
- [ ] Add batch operation validation
- [ ] Implement shortcut help/discovery UI

---

## References

**Documentation**:
- `docs/keyboard_shortcuts.md` - User guide
- `docs/shortcut_validation_matrix.md` - Validation requirements

**Code Files**:
- `core/shortcut_manager.py` - Main shortcut handlers
- `core/unified_metadata_manager.py` - Metadata shortcut handlers (JUST UPDATED)
- `core/application_service.py` - Application service shortcuts
- `core/event_handler_manager.py` - Smart state analysis
- `widgets/metadata_tree_view.py` - Local tree shortcuts

**Configuration**:
- `core/config_imports.py` - Shortcut constants

---

## Conclusion

**Status**: ✅ **All shortcuts now have proper validation and user feedback**

- ✅ Selection management - working
- ✅ File operations - working
- ✅ Metadata loading - FIXED with state checks
- ✅ Metadata saving - FIXED with status messages
- ✅ Hash operations - working
- ✅ Undo/redo - working

**User Experience Improved**:
1. Users get clear feedback when shortcuts can't perform
2. Unnecessary operations are prevented
3. Status bar shows helpful messages
4. Dialogs inform about pre-existing state (e.g., "All files already have metadata")

