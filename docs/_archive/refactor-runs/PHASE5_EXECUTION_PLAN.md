# Phase 5: Theme Consolidation — Execution Plan

> **Status:** PLANNED  
> **Created:** December 18, 2025  
> **Author:** Michael Economou  
> **Governing Document:** [ARCH_REFACTOR_PLAN.md](ARCH_REFACTOR_PLAN.md)

---

## Executive Summary

### Goal
Consolidate the fragmented theme system into a single, unified `ThemeManager` with:
- Token-based color access
- Single source of truth for all theming
- QSS template rendering
- Optional `ThemedWidget` base class

### Current State (Problems)
The codebase currently has **3 separate theme systems** that overlap and cause confusion:

| File | Lines | Role | Issues |
|------|-------|------|--------|
| `utils/theme_engine.py` | ~1610 | Primary styling, QSS generation | Large monolith, hardcoded colors |
| `core/theme_manager.py` | ~239 | Token-based theming, signals | Underutilized, incomplete integration |
| `utils/theme.py` | ~45 | Wrapper/helper functions | Redundant layer |

### Usage Analysis
- **ThemeEngine:** Used in ~30+ files (widgets, modules, mixins)
- **ThemeManager (get_theme_manager):** Used in ~12 files
- **theme.py helpers:** Used in ~5 files

### Target State
Single `ThemeManager` class that:
1. Provides color token resolution (`get_color()`)
2. Generates complete QSS stylesheets (`get_qss()`)
3. Supports runtime theme switching with signals
4. Offers backwards-compatible `ThemeEngine` facade (optional)
5. Eliminates redundant `utils/theme.py`

---

## Execution Rules (Non-Negotiable)

1. **One file per step** — never mix multiple file changes
2. **Tests → Lint → App → Commit** after every step
3. **App must be runnable** at every checkpoint
4. **Backwards compatibility first** — deprecate, don't break
5. **No "while we're here" changes** — strict scope discipline

---

## Phase 5 Steps

### Step 5.1: Audit and Document Current Usage

**Goal:** Create complete mapping of all theme usage patterns.

**Tasks:**
- [ ] List all files importing ThemeEngine
- [ ] List all files importing get_theme_manager/ThemeManager
- [ ] List all files importing from utils/theme.py
- [ ] Document which colors/methods are actually used
- [ ] Identify circular import risks

**Allowed:**
- Creating documentation only
- Running grep/analysis scripts

**Forbidden:**
- Any code changes

**Commit Message:**
```
docs: audit theme system usage across codebase
```

**Definition of Done:**
- [ ] Usage audit document created
- [ ] App launches successfully
- [ ] All tests pass

---

### Step 5.2: Unify Color Definitions

**Goal:** Consolidate all color definitions into `config.THEME_TOKENS`.

**Current State:**
- `theme_engine.py`: Has hardcoded `self.colors = {...}` (~100 color definitions)
- `config.py`: Has `THEME_TOKENS` dict (incomplete)
- Some widgets have inline colors

**Tasks:**
- [ ] Merge all colors from `theme_engine.py` into `config.THEME_TOKENS`
- [ ] Ensure dark/light theme variants exist
- [ ] Keep color keys consistent with existing usage
- [ ] Add missing tokens (tooltip variants, special states)

**Files Changed:**
- `oncutf/config.py` — expand `THEME_TOKENS`

**Allowed:**
- Adding/expanding color definitions in config.py
- Ensuring all existing color keys are preserved

**Forbidden:**
- Changing any usage in widgets yet
- Removing any existing colors

**Tests to Run:**
```bash
pytest tests/ -x -q
python main.py  # Verify launch
```

**Commit Message:**
```
feat(theme): consolidate all color definitions in config.THEME_TOKENS
```

**Definition of Done:**
- [ ] All colors from ThemeEngine exist in THEME_TOKENS
- [ ] pytest passes
- [ ] App launches successfully

---

### Step 5.3: Extend ThemeManager API

**Goal:** Add ThemeEngine-compatible methods to ThemeManager.

**Tasks:**
- [ ] Add `get_constant()` method for numeric values (heights, widths)
- [ ] Add `get_font_sizes()` method
- [ ] Add `apply()` method for applying theme to QApplication
- [ ] Add `get_combo_qss()`, `get_button_qss()` convenience methods (optional)
- [ ] Ensure `colors` property works like ThemeEngine

**Files Changed:**
- `oncutf/core/theme_manager.py` — extend API

**Allowed:**
- Adding new methods
- Expanding existing methods

**Forbidden:**
- Changing method signatures of existing public methods
- Breaking existing tests

**Tests to Run:**
```bash
pytest tests/test_theme_manager.py -v
pytest tests/ -x -q
```

**Commit Message:**
```
feat(theme): extend ThemeManager API for ThemeEngine compatibility
```

**Definition of Done:**
- [ ] ThemeManager has compatible API
- [ ] test_theme_manager.py passes
- [ ] All tests pass

---

### Step 5.4: Create ThemeEngine Facade (Backwards Compatibility)

**Goal:** Make ThemeEngine delegate to ThemeManager internally.

**Tasks:**
- [ ] Refactor ThemeEngine to use get_theme_manager() internally
- [ ] Keep all existing public methods working
- [ ] Add deprecation warnings to old patterns (optional, Phase 5.4b)
- [ ] Ensure zero behavior change for existing callers

**Files Changed:**
- `oncutf/utils/theme_engine.py` — refactor to delegate

**Allowed:**
- Changing internal implementation
- Adding delegation to ThemeManager
- Keeping public API identical

**Forbidden:**
- Removing any public methods
- Changing return types
- Breaking any existing callers

**Tests to Run:**
```bash
pytest tests/test_theme_integration.py -v
pytest tests/ -x -q
python main.py  # Full visual verification
```

**Commit Message:**
```
refactor(theme): ThemeEngine delegates to ThemeManager internally
```

**Definition of Done:**
- [ ] ThemeEngine works identically from caller perspective
- [ ] All tests pass
- [ ] App launches with correct styling

---

### Step 5.5: Migrate utils/theme.py to ThemeManager

**Goal:** Point theme.py helpers to ThemeManager.

**Tasks:**
- [ ] Update `get_theme_color()` to use ThemeManager
- [ ] Update `get_current_theme_colors()` to use ThemeManager
- [ ] Update `get_qcolor()` to use ThemeManager
- [ ] Keep function signatures identical

**Files Changed:**
- `oncutf/utils/theme.py` — update to use ThemeManager

**Allowed:**
- Changing internal implementation
- Keeping function signatures identical

**Forbidden:**
- Removing any functions
- Changing return types

**Tests to Run:**
```bash
pytest tests/ -x -q
python main.py
```

**Commit Message:**
```
refactor(theme): theme.py helpers use ThemeManager internally
```

**Definition of Done:**
- [ ] All helper functions work identically
- [ ] All tests pass
- [ ] App launches successfully

---

### Step 5.6: Add ThemedWidget Base Class (Optional)

**Goal:** Create optional base class for themed widgets.

**Tasks:**
- [ ] Create `oncutf/ui/components/themed_widget.py`
- [ ] Implement auto-theme application on init
- [ ] Implement theme change listener
- [ ] Add convenience methods (`get_color()`, `get_constant()`)
- [ ] Document usage pattern

**Files Created:**
- `oncutf/ui/components/__init__.py`
- `oncutf/ui/components/themed_widget.py`

**Allowed:**
- Creating new files
- Adding new classes

**Forbidden:**
- Modifying existing widgets yet
- Making ThemedWidget required

**Tests to Run:**
```bash
pytest tests/ -x -q
python main.py
```

**Commit Message:**
```
feat(theme): add ThemedWidget base class for themed widgets
```

**Definition of Done:**
- [ ] ThemedWidget class created and documented
- [ ] All tests pass
- [ ] App launches successfully

---

### Step 5.7: Create Theme System Tests

**Goal:** Comprehensive test coverage for unified theme system.

**Tasks:**
- [ ] Test ThemeManager singleton behavior
- [ ] Test color token resolution
- [ ] Test QSS generation
- [ ] Test theme switching signals
- [ ] Test ThemedWidget base class
- [ ] Test backwards compatibility (ThemeEngine, theme.py)

**Files Created:**
- `tests/test_theme_consolidation.py`

**Allowed:**
- Adding new test files
- Adding test cases

**Forbidden:**
- Modifying existing tests (unless fixing bugs)

**Tests to Run:**
```bash
pytest tests/test_theme*.py -v
pytest tests/ -x -q
```

**Commit Message:**
```
test(theme): add comprehensive theme consolidation tests
```

**Definition of Done:**
- [ ] New tests pass
- [ ] All existing tests pass
- [ ] Coverage for main use cases

---

### Step 5.8: Gradual Widget Migration (Optional)

**Goal:** Migrate high-impact widgets to use ThemeManager directly.

**Candidate Widgets (by usage frequency):**
1. `file_table_view.py` — most visible component
2. `rename_modules_area.py` — frequently used
3. `preview_tables_view.py` — critical for UX
4. `styled_combo_box.py` — already themed

**Tasks per widget:**
- [ ] Replace `ThemeEngine()` instantiation with `get_theme_manager()`
- [ ] Update color access to `theme.get_color("token")`
- [ ] Test visual appearance
- [ ] Verify no regressions

**Allowed:**
- One widget per commit
- Using get_theme_manager() singleton

**Forbidden:**
- Breaking widget functionality
- Changing visual appearance

**Commit Message (per widget):**
```
refactor(ui): {widget_name} uses ThemeManager directly
```

**Definition of Done (per widget):**
- [ ] Widget works identically
- [ ] Visual appearance unchanged
- [ ] All tests pass

---

### Step 5.9: Documentation Update

**Goal:** Update all documentation to reflect unified theme system.

**Tasks:**
- [ ] Update ARCHITECTURE.md with theme system section
- [ ] Create `docs/theme_system.md` with usage guide
- [ ] Update docstrings in theme_manager.py
- [ ] Add deprecation notes for old patterns
- [ ] Update copilot-instructions.md if needed

**Files Changed:**
- `docs/ARCHITECTURE.md`
- `docs/theme_system.md` (new)
- Various docstrings

**Commit Message:**
```
docs(theme): document unified theme system
```

**Definition of Done:**
- [ ] Documentation complete
- [ ] Usage examples included
- [ ] Deprecation path documented

---

### Step 5.10: Cleanup and Finalization

**Goal:** Mark Phase 5 complete, update ROADMAP.

**Tasks:**
- [ ] Update ROADMAP.md Phase 5 status to COMPLETE
- [ ] Create PHASE5_COMPLETE.md summary
- [ ] Review for any remaining TODOs
- [ ] Final full test run

**Commit Message:**
```
docs: mark Phase 5 Theme Consolidation complete
```

**Definition of Done:**
- [ ] ROADMAP.md updated
- [ ] PHASE5_COMPLETE.md created
- [ ] All tests pass (full suite)
- [ ] App runs correctly

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Visual regressions | Medium | High | Screenshot comparison before/after |
| Circular imports | Low | High | Use TYPE_CHECKING guards |
| Breaking ThemeEngine callers | Low | Medium | Facade pattern preserves API |
| Missing color tokens | Medium | Low | Add missing tokens on demand |

## Rollback Strategy

Each step is atomic and reversible:
- Step 5.1: Documentation only — no rollback needed
- Steps 5.2-5.7: Can revert individual commits
- Step 5.8: Optional — can skip entirely
- Steps 5.9-5.10: Documentation — no code risk

---

## Estimated Timeline

| Step | Complexity | Estimated Time |
|------|------------|----------------|
| 5.1 Audit | Low | 30 min |
| 5.2 Color Consolidation | Medium | 1 hour |
| 5.3 ThemeManager API | Medium | 1 hour |
| 5.4 ThemeEngine Facade | High | 2 hours |
| 5.5 theme.py Migration | Low | 30 min |
| 5.6 ThemedWidget | Medium | 1 hour |
| 5.7 Tests | Medium | 1 hour |
| 5.8 Widget Migration | Variable | 2-4 hours |
| 5.9 Documentation | Low | 1 hour |
| 5.10 Finalization | Low | 30 min |

**Total Estimated Time:** 10-13 hours (across multiple sessions)

---

## Success Criteria

1. ✅ Single `get_theme_manager()` entry point for all theming
2. ✅ ThemeEngine continues to work (backwards compatible)
3. ✅ All 780+ tests pass
4. ✅ Visual appearance unchanged
5. ✅ Runtime theme switching works
6. ✅ Documentation complete

---

*Document version: 1.0*  
*Phase 5 ready to begin*
