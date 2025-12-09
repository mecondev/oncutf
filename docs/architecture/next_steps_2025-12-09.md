# Next Steps Implementation Plan

**Date:** 2025-12-09  
**Based on:** `refactor_status_2025-12-09.md`  
**Timeline:** 2-3 weeks  
**Scope:** Immediate, Short-term, Optional improvements

---

## Part 1: IMMEDIATE (This Week)

### Task 1.1: Documentation Cleanup
**Effort:** 2-3 hours  
**Priority:** HIGH

#### Subtasks:
1. **Archive old planning docs** to `docs/archive/`
   ```bash
   mkdir -p docs/archive
   mv docs/architecture/refactor_plan_2025-12-01.md docs/archive/
   # Keep: pragmatic_refactor_2025-12-03.md (reference), streaming_metadata_plan.md
   ```
   
2. **Create `docs/ARCHITECTURE.md`** (new overview)
   - Quick navigation to key docs
   - 3-tier architecture diagram
   - Link to pragmatic plan + current status
   
3. **Update `README.md`** highlights
   - Mention recent refactoring progress
   - 491 tests passing
   - Links to key architecture docs

#### Acceptance Criteria:
- [ ] Old docs moved to archive
- [ ] `docs/ARCHITECTURE.md` created (500-800 words)
- [ ] README.md updated with refactoring highlights
- [ ] All links working

---

### Task 1.2: ColumnManagementMixin Documentation
**Effort:** 1-2 hours  
**Priority:** HIGH

#### What to Create:
File: `docs/architecture/column_management_mixin_guide.md`

**Content Structure:**
```markdown
1. Overview (2 paragraphs)
2. Public API Reference (table)
   - add_column(name, config)
   - remove_column(index)
   - get_visible_columns_list()
   - toggle_column_visibility(index)
   - reset_columns_to_default()
   - auto_fit_columns_to_content()
   - refresh_columns_after_model_change()
3. Usage Examples (3-4 code snippets)
4. Configuration Schema (YAML/JSON example)
5. Internal Methods (brief reference)
```

#### Acceptance Criteria:
- [ ] All 34 methods documented or referenced
- [ ] 3+ usage examples included
- [ ] Configuration schema shown
- [ ] 150-250 words

---

### Task 1.3: Run Full Test Suite & Coverage Check
**Effort:** 1 hour  
**Priority:** HIGH

```bash
# Run full test suite
pytest tests/ -v --tb=short

# Generate coverage report
pytest tests/ --cov=. --cov-report=html

# Check coverage on key modules:
# - widgets/mixins/
# - models/
# - core/selection_store.py
# - utils/selection_provider.py
```

**Success Criteria:**
- [ ] 491/491 tests passing ✅
- [ ] No warnings or errors
- [ ] Coverage report generated
- [ ] Note any modules below 50% coverage

---

## Part 2: SHORT TERM (Next 2-3 Weeks)

### Task 2.1: Add ColumnManagementMixin Unit Tests
**Effort:** 2-3 hours  
**Priority:** MEDIUM

**Test File:** `tests/test_column_management_mixin.py`

#### Test Cases to Add:
```python
# Test 1: add_column() - basic
# Test 2: remove_column() - removal preserves others
# Test 3: toggle_column_visibility() - state changes
# Test 4: get_visible_columns_list() - returns correct subset
# Test 5: reset_columns_to_default() - restores original config
# Test 6: auto_fit_columns_to_content() - calculates widths
# Test 7: refresh_columns_after_model_change() - updates properly
# Test 8: _load_column_width() - persistence works
# Test 9: _save_column_width() - persists to config
# Test 10: _on_column_resized() - debounces updates
```

**Acceptance Criteria:**
- [ ] 10+ tests created
- [ ] All tests passing
- [ ] Coverage > 80% on mixin
- [ ] Tests use fixtures for FileTableView setup

---

### Task 2.2: Performance Profiling (1000+ Files)
**Effort:** 3-4 hours  
**Priority:** MEDIUM

#### What to Test:
1. **Load test with 1000 files**
   - Create test directory with 1000 dummy files
   - Measure load time
   - Monitor memory usage
   - Check UI responsiveness

2. **Profile hot paths**
   ```python
   import cProfile
   cProfile.run('app.load_files()', 'stats.prof')
   ```

3. **Identify bottlenecks**
   - Metadata loading
   - Preview generation
   - Table rendering

#### Acceptance Criteria:
- [ ] Performance profile generated
- [ ] Bottlenecks documented
- [ ] Results recorded in `docs/performance_baseline_2025-12-09.md`
- [ ] No obvious issues found

---

### Task 2.3: unified_rename_engine Cleanup (Optional)
**Effort:** 2-3 days  
**Priority:** LOW

**Files to Review:**
- `core/unified_rename_engine.py` (~400 LOC)
- `core/preview_manager.py` (~300 LOC)

#### Goals:
1. Simplify `preview()` method
   - Break into smaller functions
   - Remove dead code
   - Add unit tests

2. Clarify responsibility between:
   - `unified_rename_engine` (orchestration)
   - `preview_manager` (UI coordination)

3. Add focused unit tests

#### Acceptance Criteria:
- [ ] `unified_rename_engine.preview()` < 100 LOC
- [ ] 5+ unit tests added
- [ ] All tests passing
- [ ] No functional changes (behavior preserved)

---

### Task 2.4: table_manager Simplification (Optional)
**Effort:** 2-3 days  
**Priority:** LOW

**Files to Review:**
- `core/table_manager.py` (~500 LOC)
- `widgets/file_table_view.py` (now 976 LOC)

#### Goals:
1. Clarify responsibility boundaries
   - What should table_manager do?
   - What should FileTableView do?
   - Are there overlaps?

2. Document division of labor

3. Suggest consolidation if warranted

#### Acceptance Criteria:
- [ ] Responsibility map created
- [ ] Overlaps documented
- [ ] Recommendation written
- [ ] No changes applied yet (analysis only)

---

## Part 3: OPTIONAL (Future Sprints)

### Task 3.1: unified_metadata_manager Streaming
**Effort:** 8-10 days  
**Priority:** VERY LOW

**Status:** Deferred based on ROI analysis  
**See:** `docs/architecture/streaming_metadata_plan.md`

**Only do if:**
- User reports significant lag with 5000+ files
- Performance baseline shows metadata loading > 500ms
- Streaming shows >20% improvement in benchmarks

---

### Task 3.2: ViewModel Layer (Not Recommended)
**Effort:** 3-4 weeks  
**Priority:** VERY LOW

**Status:** Explicitly deferred (pragmatic approach)

**Why deferred:**
- High complexity, low immediate benefit
- Existing architecture is adequate
- Risk of introducing bugs

---

## Weekly Checklist

### Week 1 (Dec 9-15)
- [ ] Task 1.1: Documentation cleanup
- [ ] Task 1.2: ColumnManagementMixin documentation
- [ ] Task 1.3: Test suite verification
- [ ] Commit: "docs: architecture cleanup and migration guides"

### Week 2 (Dec 16-22)
- [ ] Task 2.1: ColumnManagementMixin unit tests
- [ ] Task 2.2: Performance profiling (1000 files)
- [ ] Commit: "test: add ColumnManagementMixin unit tests"
- [ ] Commit: "docs: performance baseline 2025-12-09"

### Week 3 (Dec 23-29)
- [ ] Task 2.3 OR 2.4 (choose one based on priority)
- [ ] Final review of all documentation
- [ ] Commit: "refactor: cleanup optional component"

---

## Success Criteria (All Tasks)

### Must Achieve:
- ✅ All tests passing (491+)
- ✅ Documentation complete and current
- ✅ Performance baseline established
- ✅ No regressions introduced

### Nice to Have:
- ✅ ColumnManagementMixin tests added
- ✅ Optional cleanup tasks started
- ✅ Performance profile published

### Don't Care:
- ❌ 100% test coverage (aim for 80%)
- ❌ Perfect documentation (aim for clear)
- ❌ Zero warnings (pragmatic acceptance)

---

## Git Commit Message Templates

### Week 1:
```
docs: architecture cleanup and ColumnManagementMixin guide

- Archive old planning docs to docs/archive/
- Create docs/ARCHITECTURE.md overview
- Add column_management_mixin_guide.md
- Update README with refactoring highlights

Closes #<issue_number> (if applicable)
```

### Week 2:
```
test: add ColumnManagementMixin unit tests

Add 10+ unit tests covering:
- Column visibility toggles
- Width persistence
- Auto-fit logic
- Config defaults

Coverage: 80%+ on mixin
All 491 tests passing
```

```
docs: add performance baseline

Profile with 1000 files:
- Load time: XXms
- Memory: XXmb
- Bottlenecks: <list>

See: docs/performance_baseline_2025-12-09.md
```

### Week 3:
```
refactor: simplify unified_rename_engine

- Break preview() into smaller functions
- Remove dead code paths
- Add 5+ unit tests
- Behavior preserved (all tests passing)
```

---

## Risk Assessment

### Low Risk ✅
- Documentation cleanup
- Unit tests for existing code
- Performance profiling

### Medium Risk ⚠️
- unified_rename_engine refactoring
- table_manager analysis

### High Risk ❌
- Streaming metadata implementation
- ViewModel layer (not recommended)

---

## Dependencies & Notes

1. **Task 1.3 must complete before Task 2.1**
   - Ensure test suite stability first

2. **Task 2.2 can run in parallel with 2.1**
   - Performance profiling independent

3. **Tasks 2.3 and 2.4 are optional**
   - Choose based on pain points
   - Analysis > implementation

4. **Avoid changing test structure**
   - Use existing test utilities
   - Keep pytest conventions

---

## Questions to Answer (Before Starting Week 2)

1. Are there any UI performance issues users have reported?
2. Does preview generation feel responsive?
3. Are there specific rename modules causing slowdowns?
4. Should we prioritize 2.3 or 2.4 first?

---

*Generated: 2025-12-09*  
*Next Review: 2025-12-16 (after Week 1)*
