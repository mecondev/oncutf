# Roadmap — Refactor Status

Date: 2025-12-08

Short description: Update on the progress of refactor tasks. Human comments and descriptions are in Greek.

---

## Summary
- Goal: Reduce the complexity of `FileTableView` and isolate column management in a separate mixin.
- Result: `FileTableView` reduced from ~2069 LOC to 976 LOC. Created `ColumnManagementMixin` (~1179 LOC).
- Test status: 491 tests passed.

---

## Step Status (Ticked)

- [x] Phase 1: MetadataTreeView decomposition
- [x] Analyze streaming metadata ROI
- [x] Decide to skip streaming integration (add configurable option later)
- [x] Plan FileTableView Phase 2 extraction (identify methods, line ranges)
- [x] Create `widgets/mixins/column_management_mixin.py` (skeleton)
- [x] Extract Batch 1 — Configuration methods (10 methods)
- [x] Extract Batch 2 — Width management methods (7 methods)
- [x] Extract Batch 3-5 — Event / Visibility / Utilities methods (17 methods)
- [x] Integrate `ColumnManagementMixin` into `FileTableView` (add to inheritance)
- [x] Remove extracted methods from `widgets/file_table_view.py`
- [x] Update `widgets/mixins/__init__.py` to export `ColumnManagementMixin`
- [x] Run test suite and verify (491 passed)
- [x] Commit changes (single commit for easy rollback)

## In Progress / Next (Not checked)
- [ ] Update user-facing docs explaining the new mixin API (short guide)
- [ ] Add unit tests targeting `ColumnManagementMixin` behavior in isolation
- [ ] Consider exposing configuration toggles (e.g., streaming metadata flag)
- [ ] Phase 3: Identify next large component to refactor (TBD)

---

## Technical Notes
- The export was done in 5 logical batches to avoid errors and facilitate verification.
- All public APIs were retained (`add_column`, `remove_column`, `get_visible_columns_list`, `refresh_columns_after_model_change`).
- The non-column Qt handlers (`resizeEvent`, `update_placeholder_visibility`, `_update_scrollbar_visibility`) remained in `FileTableView`.

## Changed Files
- `NEW: widgets/mixins/column_management_mixin.py` — new mixin with 34 methods
- `MOD: widgets/file_table_view.py` — extracted methods removed, now inherits `ColumnManagementMixin`
- `MOD: widgets/mixins/__init__.py` — added export for `ColumnManagementMixin`
- `NEW: docs/architecture/file_table_view_phase_2_plan.md` — (automatically generated in a previous step)
- `NEW: docs/architecture/streaming_metadata_plan.md` — (automatically generated in a previous step)

---

## Proposed Next Steps (shorter)
1. Update technical documentation for `ColumnManagementMixin` (API, usage examples).
2. Write small test units that call the public methods of the mixin.
3. Exploration Phase 3: I suggest we look into `unified_rename_engine` or `table_manager` for further modularization.

---

If you want, I can:
- I will create the technical documentation (README) for `ColumnManagementMixin` now.
- Start writing unit tests for important behaviors of the mixin.
- I suggest specific files for Phase 3 and to create a detailed plan.

Which one should I proceed with?