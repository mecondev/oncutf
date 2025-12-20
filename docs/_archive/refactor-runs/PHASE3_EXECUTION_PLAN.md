# Phase 3: Metadata Module Fix - Execution Plan

> **Status**: IN PROGRESS  
> **Created**: December 17, 2025  
> **Author**: Michael Economou  
> **Branch**: `phase3-metadata-module-fix`  
> **Governing Document**: [ARCH_REFACTOR_PLAN.md](ARCH_REFACTOR_PLAN.md)

---

## Overview

Phase 3 focuses on fixing the Metadata Module issues identified in the architecture review:

1. **ComboBox styling** - doesn't respect QSS theming properly
2. **UI/Logic coupling** - MetadataModule mixes UI concerns with business logic
3. **Preview updates** - not triggered immediately when settings change
4. **EXIF metadata fetching** - inconsistent behavior

---

## Pre-Phase Checklist

- [x] Phase 2 (State Management) completed
- [x] All tests passing (592+)
- [x] Branch created: `phase3-metadata-module-fix`
- [ ] Current metadata module analyzed

---

## Phase 3 Steps

### Step 3.1: Create MetadataExtractor (Domain Layer)

**Goal**: Extract pure Python logic from `MetadataModule` into a new `MetadataExtractor` class that has no UI dependencies.

**Files to Create**:
```
oncutf/domain/                     # NEW directory
oncutf/domain/__init__.py          # NEW file
oncutf/domain/metadata/            # NEW directory  
oncutf/domain/metadata/__init__.py # NEW file
oncutf/domain/metadata/extractor.py # NEW - core extraction logic
```

**Implementation**:
```python
# oncutf/domain/metadata/extractor.py
"""
Pure Python metadata extraction logic.
No Qt dependencies - fully testable in isolation.
"""
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
from typing import Any

@dataclass
class ExtractionResult:
    """Result of metadata extraction."""
    value: str
    source: str  # 'filesystem', 'exif', 'hash', 'fallback'
    raw_value: Any = None

class MetadataExtractor:
    """Extract metadata values from files - pure domain logic."""
    
    def extract(
        self, 
        file_path: Path, 
        field: str, 
        category: str = "file_dates",
        metadata: dict | None = None
    ) -> ExtractionResult: ...
    
    def get_available_fields(self, category: str) -> list[str]: ...
    
    def clean_for_filename(self, value: str) -> str: ...
```

**Allowed**:
- Creating new domain directory structure
- Moving extraction logic from MetadataModule.apply_from_data()
- Creating clean, testable interfaces

**Forbidden**:
- Importing Qt/PyQt5 modules
- Breaking existing MetadataModule API
- Changing existing tests

**Tests to Create**:
- `tests/unit/domain/test_metadata_extractor.py` (15+ tests)
  - Test file date extraction (various formats)
  - Test hash extraction  
  - Test EXIF metadata extraction
  - Test filename cleaning
  - Test fallback behavior

**Commit Message**:
```
feat(domain): add MetadataExtractor for pure metadata extraction logic

- Create oncutf/domain/metadata/extractor.py
- Extract logic from MetadataModule without Qt dependencies
- Add comprehensive unit tests
- Preserve MetadataModule API for backwards compatibility
```

**Definition of Done**:
- [ ] Domain directory structure created
- [ ] MetadataExtractor class implemented
- [ ] All extraction logic moved (filesystem, hash, EXIF)
- [ ] clean_for_filename() method working
- [ ] 15+ unit tests passing
- [ ] `pytest tests/ -x -q` passes
- [ ] `ruff check .` passes
- [ ] `python main.py` launches successfully
- [ ] Committed and pushed

---

### Step 3.2: Create StyledComboBox Widget

**Goal**: Create a reusable `StyledComboBox` that properly integrates with the theme system.

**Files to Create**:
```
oncutf/ui/widgets/styled_combo_box.py  # NEW file
```

**Implementation**:
```python
# oncutf/ui/widgets/styled_combo_box.py
"""
StyledComboBox - ComboBox with proper theme integration.
"""
from PyQt5.QtWidgets import QComboBox
from oncutf.ui.widgets.ui_delegates import ComboBoxItemDelegate
from oncutf.utils.theme_engine import ThemeEngine

class StyledComboBox(QComboBox):
    """ComboBox with automatic theme delegate setup."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_delegate()
        self._apply_theme()
    
    def _setup_delegate(self) -> None:
        theme = ThemeEngine()
        self.setItemDelegate(ComboBoxItemDelegate(self, theme))
    
    def _apply_theme(self) -> None:
        theme = ThemeEngine()
        self.setFixedHeight(theme.get_constant("combo_height"))
```

**Allowed**:
- Creating new widget class
- Using existing theme infrastructure

**Forbidden**:
- Breaking existing ComboBox usage
- Changing ThemeEngine API

**Tests to Create**:
- `tests/unit/widgets/test_styled_combo_box.py` (5+ tests)
  - Test delegate is set correctly
  - Test theme height applied
  - Test items render properly

**Commit Message**:
```
feat(ui): add StyledComboBox with theme integration

- Create oncutf/ui/widgets/styled_combo_box.py
- Automatic ComboBoxItemDelegate setup
- Theme-aware height configuration
- Add unit tests
```

**Definition of Done**:
- [ ] StyledComboBox class implemented
- [ ] ComboBoxItemDelegate properly set
- [ ] Theme height constant used
- [ ] Unit tests passing
- [ ] `pytest tests/ -x -q` passes
- [ ] `python main.py` launches successfully
- [ ] Committed and pushed

---

### Step 3.3: Refactor MetadataModule to Use Extractor

**Goal**: Update `MetadataModule.apply_from_data()` to delegate to `MetadataExtractor`.

**Files to Modify**:
```
oncutf/modules/metadata_module.py  # MODIFY - delegate to extractor
```

**Implementation**:
```python
# In MetadataModule.apply_from_data():
@staticmethod
def apply_from_data(data: dict, file_item: FileItem, index: int = 0, 
                    metadata_cache: dict | None = None) -> str:
    from oncutf.domain.metadata.extractor import MetadataExtractor
    
    extractor = MetadataExtractor()
    result = extractor.extract(
        file_path=Path(file_item.full_path),
        field=data.get("field", ""),
        category=data.get("category", "file_dates"),
        metadata=_get_metadata_dict(file_item, metadata_cache)
    )
    return result.value
```

**Allowed**:
- Delegating to MetadataExtractor
- Simplifying apply_from_data()
- Keeping backwards compatibility

**Forbidden**:
- Breaking existing API
- Removing any functionality
- Changing method signatures

**Tests to Run**:
- All existing MetadataModule tests must pass unchanged
- `pytest tests/unit/modules/test_metadata_module.py -v`

**Commit Message**:
```
refactor(modules): delegate MetadataModule to MetadataExtractor

- apply_from_data() now uses MetadataExtractor internally
- Simplified implementation, same API
- All existing tests still passing
```

**Definition of Done**:
- [ ] MetadataModule delegates to MetadataExtractor
- [ ] API unchanged (backwards compatible)
- [ ] All existing tests passing
- [ ] `pytest tests/ -x -q` passes
- [ ] `python main.py` launches successfully
- [ ] Rename preview works correctly
- [ ] Committed and pushed

---

### Step 3.4: Update MetadataWidget to Use StyledComboBox

**Goal**: Replace manual ComboBox setup in `MetadataWidget` with `StyledComboBox`.

**Files to Modify**:
```
oncutf/ui/widgets/metadata_widget.py  # MODIFY - use StyledComboBox
```

**Implementation**:
```python
# Replace:
self.category_combo = QComboBox()
self.category_combo.setFixedWidth(150)
self.category_combo.setFixedHeight(theme.get_constant("combo_height"))
# ...
self.category_combo.setItemDelegate(ComboBoxItemDelegate(...))

# With:
from oncutf.ui.widgets.styled_combo_box import StyledComboBox
self.category_combo = StyledComboBox()
self.category_combo.setFixedWidth(150)
```

**Allowed**:
- Replacing QComboBox with StyledComboBox
- Removing redundant delegate setup code
- Removing redundant height setup code

**Forbidden**:
- Changing signal connections
- Changing data population logic
- Breaking existing functionality

**Commit Message**:
```
refactor(ui): use StyledComboBox in MetadataWidget

- Replace manual combo setup with StyledComboBox
- Remove redundant delegate and height configuration
- Consistent theme integration
```

**Definition of Done**:
- [ ] category_combo uses StyledComboBox
- [ ] Redundant setup code removed
- [ ] Visual appearance unchanged
- [ ] All functionality preserved
- [ ] `pytest tests/ -x -q` passes
- [ ] `python main.py` launches successfully
- [ ] Committed and pushed

---

### Step 3.5: Add Instant Preview Updates

**Goal**: Ensure preview updates immediately when any metadata setting changes.

**Files to Modify**:
```
oncutf/ui/widgets/metadata_widget.py  # MODIFY - add signal emissions
```

**Implementation**:
```python
class MetadataWidget(QWidget):
    settings_changed = pyqtSignal(dict)  # NEW signal
    
    def _emit_settings_changed(self) -> None:
        """Emit settings_changed on ANY user interaction."""
        config = self.get_data()
        self.settings_changed.emit(config)
        # Also emit legacy 'updated' signal for compatibility
        self.updated.emit(config)
    
    # Connect all inputs to emit signal:
    # In setup_ui():
    self.category_combo.currentIndexChanged.connect(self._emit_settings_changed)
    self.options_combo.selection_confirmed.connect(self._emit_settings_changed)
```

**Allowed**:
- Adding new signal
- Connecting existing widgets to new handler
- Emitting on any change

**Forbidden**:
- Removing existing signals
- Breaking existing connections
- Adding debouncing that delays preview

**Tests to Create**:
- `tests/unit/widgets/test_metadata_widget_signals.py` (5+ tests)
  - Test signal emitted on category change
  - Test signal emitted on field change
  - Test signal contains correct data

**Commit Message**:
```
feat(ui): add instant preview updates for MetadataWidget

- Add settings_changed signal
- Emit on any combo box change
- Preserve backwards compatibility with 'updated' signal
- Add signal emission tests
```

**Definition of Done**:
- [ ] settings_changed signal added
- [ ] Emitted on category change
- [ ] Emitted on field/option change
- [ ] Preview updates immediately in app
- [ ] Unit tests passing
- [ ] `pytest tests/ -x -q` passes
- [ ] `python main.py` launches successfully
- [ ] Committed and pushed

---

### Step 3.6: Integration Testing & Documentation

**Goal**: Verify all changes work together and document the new architecture.

**Files to Create/Update**:
```
docs/PHASE3_COMPLETE.md           # NEW - completion summary
tests/integration/test_metadata_widget_integration.py  # NEW tests
```

**Integration Tests**:
- Test MetadataWidget → MetadataModule → MetadataExtractor flow
- Test preview updates in real scenario
- Test ComboBox styling with theme changes

**Documentation Updates**:
- Update PHASE3_EXECUTION_PLAN.md with completion status
- Create PHASE3_COMPLETE.md summary
- Update copilot-instructions.md if needed

**Commit Message**:
```
docs: complete Phase 3 - Metadata Module Fix

- Add integration tests for metadata flow
- Create PHASE3_COMPLETE.md summary
- Update documentation
- All 600+ tests passing
```

**Definition of Done**:
- [ ] All Phase 3 steps completed
- [ ] Integration tests passing
- [ ] Documentation updated
- [ ] `pytest tests/ -x -q` passes (all tests)
- [ ] `ruff check .` passes
- [ ] `python main.py` launches successfully
- [ ] App manual testing: metadata rename works correctly
- [ ] Branch ready for merge to main

---

## Validation Checklist (Run After Each Step)

```bash
# 1. Run all tests
pytest tests/ -x -q

# 2. Run linter
ruff check .

# 3. Launch app and verify
python main.py

# 4. Manual test: 
#    - Load files with EXIF metadata
#    - Select Metadata rename module
#    - Change category → verify preview updates
#    - Change field → verify preview updates
#    - Execute rename → verify correct filenames
```

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing tests | HIGH | Run tests after each change |
| Preview not updating | MEDIUM | Manual testing after Step 3.5 |
| Theme styling regression | LOW | Visual inspection |
| Performance regression | LOW | Benchmark metadata extraction |

---

## Rollback Plan

If issues are found after a step:

1. `git stash` any uncommitted changes
2. `git checkout main`
3. Analyze what went wrong
4. Create fix on new branch or continue on phase3 branch

---

## Phase 3 Timeline Estimate

| Step | Estimated Time |
|------|----------------|
| 3.1: MetadataExtractor | 2-3 hours |
| 3.2: StyledComboBox | 30 min |
| 3.3: Refactor MetadataModule | 1 hour |
| 3.4: Update MetadataWidget | 30 min |
| 3.5: Instant Preview | 1 hour |
| 3.6: Integration & Docs | 1 hour |
| **Total** | **6-7 hours** |

---

## Next Phase

After Phase 3 completion, proceed to **Phase 4: Text Removal Module Fix** which includes:
- Match preview with highlighting
- Visual UI improvements
- Edge case handling
