# Phase 1D Quick Reference

## Πλάνο Εκτέλεσης (Quick Guide)

### ✅ Prerequisites
- Phase 1A (FileLoadController) - DONE
- Phase 1B (MetadataController) - DONE  
- Phase 1C (RenameController) - DONE

### 🎯 Στόχος
Δημιουργία MainWindowController ως orchestration layer που συντονίζει όλους τους controllers.

---

## Βήματα Εκτέλεσης

### 📋 Βήμα 1D.1: Skeleton (30 λεπτά)
```bash
# Git
git checkout -b phase1d-main-window-controller

# Create
# - oncutf/controllers/main_window_controller.py (skeleton)

# Validate
python -c "from oncutf.controllers.main_window_controller import MainWindowController"
pytest -q
ruff check oncutf/controllers/main_window_controller.py

# Commit
git add oncutf/controllers/main_window_controller.py
git commit -m "feat(controllers): add MainWindowController skeleton"
```

---

### 📋 Βήμα 1D.2: Methods Map (45 λεπτά)
```bash
# Create
# - docs/PHASE1D_METHODS_MAP.md (document orchestration methods)

# Validate
# Manual review

# Commit
git add docs/PHASE1D_METHODS_MAP.md
git commit -m "docs(phase1d): document orchestration methods to extract"
```

---

### 📋 Βήμα 1D.3: First Method + Tests (1 ώρα)
```bash
# Implement
# - load_files_and_metadata() in MainWindowController
# - tests/test_main_window_controller.py

# Validate
pytest tests/test_main_window_controller.py -v
pytest -q
ruff check oncutf/controllers/main_window_controller.py
mypy oncutf/controllers/main_window_controller.py

# Commit
git add oncutf/controllers/main_window_controller.py tests/test_main_window_controller.py
git commit -m "feat(controllers): implement load_files_and_metadata in MainWindowController"
```

---

### 📋 Βήμα 1D.4: Wire to MainWindow (1 ώρα)
```bash
# Modify
# - oncutf/ui/main_window.py (add controller + feature flag)

# Validate
python main.py  # Test with flag=True
# Edit flag to False, test again
pytest -q
ruff check .

# Commit
git add oncutf/ui/main_window.py
git commit -m "feat(ui): wire MainWindowController to MainWindow (behind flag)"
```

---

### 📋 Βήμα 1D.5: Remove Old Code (30 λεπτά)
```bash
# Modify
# - oncutf/ui/main_window.py (remove flag, remove old methods)

# Validate
pytest -q
python main.py
git diff oncutf/ui/main_window.py  # Check deletions

# Commit
git add oncutf/ui/main_window.py
git commit -m "refactor(ui): remove old orchestration code from MainWindow"
```

---

### 📋 Βήμα 1D.6: Remaining Methods (1.5 ώρες)
```bash
# Implement per method:
# - reload_files_after_rename()
# - handle_batch_operation_complete()
# - (2-3 more as needed)

# Validate per method
pytest tests/test_main_window_controller.py::test_method -v
pytest -q
python main.py  # Manual test
ruff check .

# Commit per method
git commit -m "feat(controllers): add [method_name] orchestration"
```

---

### 📋 Βήμα 1D.7: Final Cleanup (45 λεπτά)
```bash
# Tasks
# - Add/fix docstrings
# - Remove unused imports
# - Update architecture docs
# - Run full validation

# Validate
pytest tests/ -v
pytest --cov=oncutf.controllers.main_window_controller tests/test_main_window_controller.py
ruff check .
mypy oncutf/controllers/
python main.py  # Smoke test
wc -l oncutf/ui/main_window.py  # Check line reduction

# Commit
git commit -m "chore(phase1d): final cleanup for MainWindowController"
```

---

### 📋 Βήμα 1D.8: Merge & Cleanup (15 λεπτά)
```bash
# Merge to main
git checkout main
git merge phase1d-main-window-controller
git branch -d phase1d-main-window-controller

# Final validation
pytest -q
ruff check .
python main.py

# Update docs
# Edit docs/PHASE1_EXECUTION_PLAN.md (mark as complete)
git add docs/PHASE1_EXECUTION_PLAN.md
git commit -m "docs: mark Phase 1D as complete"
```

---

## 🛡️ Safety Checklist (Μετά από κάθε βήμα)

```bash
# Always run these after each commit:
pytest -q                    # All tests pass
ruff check .                 # Linter clean
python main.py               # App launches
# Manual smoke test          # Drag files, rename, etc.
git status                   # Clean working directory
```

---

## 🔥 Rollback Plan

```bash
# Undo last commit
git reset --hard HEAD~1

# Nuclear option (restart from main)
git checkout main
git branch -D phase1d-main-window-controller
```

---

## 📊 Progress Tracking

- [ ] 1D.1: Skeleton ✅
- [ ] 1D.2: Methods Map ✅
- [ ] 1D.3: First Method + Tests ✅
- [ ] 1D.4: Wire to MainWindow ✅
- [ ] 1D.5: Remove Old Code ✅
- [ ] 1D.6: Remaining Methods ✅
- [ ] 1D.7: Final Cleanup ✅
- [ ] 1D.8: Merge & Cleanup ✅

**Total Time:** ~6 hours (+ 1 hour buffer = 7 hours)

---

## 🎯 Success Criteria

✅ MainWindowController exists  
✅ Orchestrates FileLoad, Metadata, Rename controllers  
✅ MainWindow simplified  
✅ All tests pass (549+)  
✅ No regressions  
✅ Test coverage > 85%  
✅ Ruff clean  

---

## 🚀 Ready to Start?

```bash
git checkout -b phase1d-main-window-controller
```

**Επόμενο βήμα:** 1D.1 - Create Skeleton (30 min)
