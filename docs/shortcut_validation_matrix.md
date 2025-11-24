# Keyboard Shortcuts - Validation & State Requirements Matrix

**Author**: AI Assistant  
**Date**: November 24, 2025  
**Purpose**: Define when each shortcut should be active/enabled based on application state

---

## Executive Summary

This document establishes a **validation matrix** for all keyboard shortcuts in oncutf. Each shortcut has specific requirements for when it should work and what feedback to provide when those requirements are not met.

### Three Key Principles

1. **Graceful Degradation**: Shortcuts don't crash; they provide clear feedback
2. **Context-Aware**: Shortcuts behave differently based on application state
3. **User-Friendly**: Messages tell users exactly what's needed (e.g., "No files selected")

---

## Application States

### State 1: Empty Application
- No files loaded
- No folder opened
- No selections
- Status: "No folder selected"

### State 2: Folder Loaded, No Selection
- Files exist in file_model
- No files currently selected (all deselected)
- Status: "No files selected"

### State 3: Folder Loaded, Partial Selection
- Files exist in file_model
- One or more files selected
- Some files may lack metadata or hash
- Status: Shows count (e.g., "3 of 10 selected")

### State 4: Folder Loaded, All Selected
- Files exist in file_model
- All files selected
- Some files may lack metadata or hash

### State 5: Metadata Tree Has Focus
- User clicked in metadata tree widget
- Undo/redo can operate on metadata changes

### State 6: File Table Has Focus
- User clicked in file table widget
- Selection-based shortcuts are active

---

## Validation Matrix by Shortcut Category

### CATEGORY A: Selection Management (Always Available)

| Shortcut | Action | Activation | Validation | Feedback |
|----------|--------|-----------|-----------|----------|
| **Ctrl+A** | Select All | File table focus + files exist | `file_model.files` count > 0 | If no files: "No files available to select" |
| **Ctrl+Shift+A** | Clear Selection | Always | N/A | None needed |
| **Ctrl+I** | Invert Selection | File table focus + files exist | `file_model.files` count > 0 | If no files: "No files available to invert" |

**Implementation Status**: ✅ Already working
**Notes**: These are foundational and rarely need validation

---

### CATEGORY B: File Operations (File Existence Required)

| Shortcut | Action | Activation | Validation | Feedback | Proposed Change |
|----------|--------|-----------|-----------|----------|-----------------|
| **Ctrl+O** | Browse Files | Always | N/A | N/A | ✅ No change |
| **F5** | Force Reload | Always | N/A | N/A | ✅ No change |
| **Escape** | Cancel Drag | Always | N/A | N/A | ✅ No change |
| **Shift+Escape** | Clear Table | Always | N/A | Shows feedback on clear | ✅ Already implemented |

**Implementation Status**: ✅ Already working
**Notes**: These are safe operations, no files needed

---

### CATEGORY C: Metadata Loading (Selection + No Duplicates)

| Shortcut | Action | Validation | Current Behavior | Issue | Fix |
|----------|--------|-----------|------------------|-------|-----|
| **Ctrl+M** | Load Basic Metadata (Selected) | Must have selection + files without basic metadata | Shows dialog if files need metadata | ❌ No check for existing metadata | Add: Check if selected files already have metadata |
| **Ctrl+E** | Load Extended Metadata (Selected) | Must have selection + files without extended metadata | Shows dialog if files need metadata | ❌ No check for existing metadata | Add: Check if selected files already have extended metadata |
| **Ctrl+Shift+M** | Load All Basic Metadata | Must have files + files without basic metadata | Shows dialog if files need metadata | ❌ Loads even if ALL files already have it | Add: Check if all files already have metadata |
| **Ctrl+Shift+E** | Load All Extended Metadata | Must have files + files without extended metadata | Shows dialog if files need metadata | ❌ Loads even if ALL files already have it | Add: Check if all files already have metadata |

**Implementation Status**: 🟡 Partially implemented (metadata_manager has checks, but not consistently called)

**Current Code Location**: 
- `core/unified_metadata_manager.py` lines 320-354 (shortcut_load_metadata)
- `core/unified_metadata_manager.py` lines 362-407 (shortcut_load_extended_metadata)

**Analysis**:
- ✅ `shortcut_load_metadata()` HAS metadata check
- ✅ `shortcut_load_extended_metadata()` HAS metadata check
- ❌ `shortcut_load_metadata_all()` is missing check
- ❌ `shortcut_load_extended_metadata_all()` is missing check

**Fix Required**: Add metadata checks to "all" versions

---

### CATEGORY D: Metadata Saving (Modified Metadata Required)

| Shortcut | Action | Validation | Current | Issue | Fix |
|----------|--------|-----------|---------|-------|-----|
| **Ctrl+S** | Save Selected Metadata | Must have selection + modified metadata | No validation | ❌ No check for modifications | Add: Check if any selected file has modified metadata |
| **Ctrl+Shift+S** | Save All Metadata | Must have modified metadata | No validation | ❌ No check for modifications | Add: Check if any file in model has modified metadata |

**Implementation Status**: ❌ Missing validation

**Current Code Location**: 
- `core/unified_metadata_manager.py` → `save_metadata_for_selected()`
- `core/unified_metadata_manager.py` → `save_all_modified_metadata()`

**Fix Required**: Add modified metadata detection

---

### CATEGORY E: Hash Operations (File Selection + Hash State)

| Shortcut | Action | Validation | Current | Issue | Fix |
|----------|--------|-----------|---------|-------|-----|
| **Ctrl+H** | Calculate Hash (Selected) | Selection required + files without hash | Check via event_handler_manager | ⚠️ Shows dialog even if all have hash | ✅ Already handled in unified_metadata_manager |
| **Ctrl+Shift+H** | Calculate Hash (All) | Files exist + files without hash | Check via event_handler_manager | ⚠️ Shows dialog even if all have hash | ✅ Already handled in application_service |
| **Ctrl+L** | Show Results List | Files with hash exist | Check file_model | ❌ Shows empty dialog if no files | ✅ Already added validation (commit bd173a06) |

**Implementation Status**: 🟢 Mostly complete
- ✅ Ctrl+H has validation (shortcut uses event_handler_manager checks)
- ✅ Ctrl+Shift+H has validation (application_service checks)
- ✅ Ctrl+L has validation (shortcut_manager checks for files)

**Current Code Location**: 
- `core/shortcut_manager.py` line 227 (show_results_hash_list - HAS validation)
- `core/application_service.py` line 161 (calculate_hash_selected - HAS checks)
- `core/application_service.py` line 178 (calculate_hash_all - HAS checks)

**Notes**: Hash operations already have smart validation

---

### CATEGORY F: Undo/Redo Operations (Context-Aware)

| Shortcut | Context | Validation | Current | Issue | Fix |
|----------|---------|-----------|---------|-------|-----|
| **Ctrl+Z** | Metadata Tree Focus | Command available in history | Handler in place | ❌ No check if in metadata tree | ✅ Implemented locally in metadata_tree_view |
| **Ctrl+R** | Metadata Tree Focus | Command available in history | Handler in place | ❌ No check if in metadata tree | ✅ Implemented locally in metadata_tree_view |
| **Ctrl+Shift+Z** | Global (Always) | N/A | Shows history dialog | ✅ Works anywhere | ✅ Already working |

**Implementation Status**: 🟢 Complete

**Current Code Location**:
- `widgets/metadata_tree_view.py` lines 985-1005 (_setup_shortcuts - LOCAL shortcuts)
- `core/shortcut_manager.py` line 90-142 (undo/redo via global shortcuts)

**Notes**: 
- Local Ctrl+Z/R on metadata tree ✅ 
- Global Ctrl+Shift+Z for history ✅

---

## Proposed Validation System

### Validation Function Pattern

```python
def validate_shortcut_preconditions(
    shortcut_name: str,
    state: dict
) -> tuple[bool, str]:
    """
    Check if shortcut preconditions are met.
    
    Returns:
        (is_valid, feedback_message)
    """
    pass
```

### States to Check

```python
state = {
    'has_files': len(file_model.files) > 0,
    'has_selection': len(selected_files) > 0,
    'selected_count': len(selected_files),
    'total_count': len(file_model.files),
    'files_without_metadata': get_files_without_metadata(selected_files),
    'files_without_hash': get_files_without_hashes(selected_files),
    'has_modified_metadata': check_any_modified_metadata(),
    'can_undo': command_manager.can_undo(),
    'can_redo': command_manager.can_redo(),
}
```

### Messages Template

```python
VALIDATION_MESSAGES = {
    # Empty state
    'no_files': 'No files loaded. Use Ctrl+O to browse files.',
    'no_selection': 'No files selected. Use Ctrl+A to select all.',
    
    # Metadata
    'all_have_metadata': 'All {count} file(s) already have metadata.',
    'all_have_extended': 'All {count} file(s) already have extended metadata.',
    
    # Hash
    'all_have_hash': 'All {count} file(s) already have checksums.',
    
    # Save
    'no_modified_metadata': 'No metadata changes to save.',
    
    # Undo/Redo
    'nothing_to_undo': 'No operations to undo.',
    'nothing_to_redo': 'No operations to redo.',
}
```

---

## Implementation Checklist

### Priority 1: Critical Missing Validations
- [ ] Add metadata checks to `shortcut_load_metadata_all()`
- [ ] Add metadata checks to `shortcut_load_extended_metadata_all()`
- [ ] Add modified metadata check to `shortcut_save_selected_metadata()`
- [ ] Add modified metadata check to `shortcut_save_all_metadata()`

### Priority 2: Consistency & Messaging
- [ ] Standardize feedback messages across all shortcuts
- [ ] Create centralized validation module
- [ ] Add debug logging for shortcut validation

### Priority 3: Future Enhancements
- [ ] Create customizable shortcut system
- [ ] Add shortcut conflict detection
- [ ] Implement shortcut remapping UI

---

## Testing Checklist

### State: Empty Application
- [ ] Ctrl+A → Message: "No files available"
- [ ] Ctrl+M → Message: "No files selected"
- [ ] Ctrl+L → Message: "No Files Selected"
- [ ] Ctrl+H → Message: "No files selected"
- [ ] Ctrl+S → Message: "No files selected"

### State: Folder Loaded, No Selection
- [ ] Ctrl+A → Selects all files
- [ ] Ctrl+M → Message: "No files selected"
- [ ] Ctrl+Shift+M → Shows dialog or message (check if all have metadata)
- [ ] Ctrl+H → Message: "No files selected"
- [ ] Ctrl+Shift+H → Shows dialog if needed

### State: Folder Loaded, 3 of 10 Selected
- [ ] Ctrl+M → Check if files already have metadata
- [ ] Ctrl+H → Check if files already have hash
- [ ] Ctrl+S → Check if any metadata modified
- [ ] Ctrl+Shift+M → Works for all 10 files
- [ ] Ctrl+Shift+S → Works for all 10 files

### State: Metadata Tree Focus
- [ ] Ctrl+Z → Undo metadata change (if available)
- [ ] Ctrl+R → Redo metadata change (if available)

---

## Expected Behaviors After Implementation

### Empty Application
```
User: Ctrl+M
System: Footer shows "No files selected"
Result: No dialog opens
```

### All Files Have Metadata
```
User: Ctrl+Shift+M
System: Footer shows "All 10 file(s) already have fast metadata"
Result: No dialog opens
```

### Some Files Need Hash
```
User: Ctrl+H (3 of 10 selected, 1 has hash)
System: Shows hash dialog with "2 of 3 files need checksums"
Result: Calculates hash for 2 files
```

### No Modified Metadata
```
User: Ctrl+S
System: Footer shows "No metadata changes to save"
Result: No save operation
```

---

## Configuration

Shortcut constants stored in `core/config_imports.py`:

```python
UNDO_REDO_SETTINGS = {
    'UNDO_SHORTCUT': 'Ctrl+Z',           # Local to metadata tree
    'REDO_SHORTCUT': 'Ctrl+R',           # Local to metadata tree
    'HISTORY_SHORTCUT': 'Ctrl+Shift+Z',  # Global
    'RESULTS_HASH_LIST_SHORTCUT': 'Ctrl+L',  # Global
}
```

---

## References

- Keyboard shortcuts guide: `docs/keyboard_shortcuts.md`
- Event handler analysis: `core/event_handler_manager.py`
- Shortcut implementation: `core/shortcut_manager.py`
- Metadata operations: `core/unified_metadata_manager.py`
- Application service: `core/application_service.py`

