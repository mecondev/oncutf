# oncutf — TODO & Unfinished-Work Catalogue

Honest catalogue of what is unfinished, half-built, or known-broken. Verified
against the live codebase.

**Last verified:** 2026-05-31

> **Strategic context:** a C++ rewrite is planned once the C++ build of exopsis
> lands (~2-3 weeks out). The decision is to **finish the Python app first**, so
> feature designs settle in fast-iterating Python and then transfer as a clean
> translation. **Current focus: close the open/half-built items** (thumbnails,
> metadata-tree fixes). Large new features (undo/redo, audio sync, node-editor
> integration, dockable widgets) are tracked below as *planned*, not in progress.

---

## 🔨 Closing now (active)

### Thumbnail view — complete Phase 5 + 6

**Status:** Phase 1–4 done (~80%), integrated via `ui/boot/bootstrap_manager.py`.
**Code:** `ui/widgets/thumbnail_viewport.py`, `ui/delegates/thumbnail_delegate.py`,
`ui/thumbnail/{providers,thumbnail_cache,thumbnail_manager,thumbnail_worker}.py`.
**To close:**

- **Phase 5 — model sync / sorting:** keep the thumbnail viewport in sync with
  the file-table model (add/remove/rename/reload) and match its sort order.
- **Phase 6 — testing & polish:** integration tests for sync + sorting; stabilise
  selection/scroll; handle missing/failed thumbnails gracefully.
- Deferred (can stay in *planned*): video preview dialog (frame picker,
  "set this frame as thumbnail").

### Metadata-tree value fixes

**Scope (per review):** value **formatting** and **edit/save behaviour**.
**Code:** `ui/widgets/metadata_tree/service.py` (format/build), `core/metadata/`
(staging, commands), `infra/external/exopsis_wrapper.py` (normalisation).
**To do:** collect concrete examples (which key/value, which file type), then fix
formatting (units/dates/fractions/acronyms) and any staging/save/edit glitches.
*Awaiting specific examples to pin exact cases.*

---

## 🧭 Planned features (future — carry into the C++ rewrite)

### Unified undo/redo

Replace the four fragmented mechanisms with one context-scoped contract.
**Design:** [docs/undo_redo_architecture.md](docs/undo_redo_architecture.md).
Prerequisite (stable `path_id` identity on rename) is already shipped.

### Audio sync / sync session

Professional multi-camera + audio synchronization: sync user-selected video/audio
files, build a timeline representation, export to NLEs (Avid via linked AAF).
Operates on file-table selection; reuses metadata cache + path-based device
identity. Large feature — full spec was removed from `docs/` but is recoverable
from git history (`docs/audio_sync_spec.txt`, `docs/sync_session_implementation_plan.md`)
and will be re-specced when picked up.

### Node editor — integration

A substantial generic node-editor widget exists (~53 files under
`ui/widgets/node_editor/`) but is **not wired into the app** and the
rename-specific nodes are **unimplemented** (`nodes/rename_nodes/` is empty).
**To do:** implement `rename_nodes/` (one node per rename module), bidirectional
linear ↔ graph conversion, integrate into the UI (run the graph through
`UnifiedRenameEngine`), and fold its snapshot history under the unified undo
contract.

> The old `core/rename_graph/` + `controllers/rename_graph_controller.py`
> architecture (graph_model/validator, cycle detection, topo-sort) was
> **never built** and has been dropped in favour of `ui/widgets/node_editor/`.

### Dockable widgets

Detachable/floating panels (file table, metadata tree, preview, modules) via
`QDockWidget`, with layout persistence in session state. Not started.

### Metadata database search

`StructuredMetadataManager.search_files_by_metadata()` is a stub returning `[]`.
Needs SQL over the metadata JSON column (`json_extract`), wildcard/regex, and
file-table filtering integration. **Location:** `core/metadata/structured_manager.py`.

### Icon migration (Feather → Material)

Migrate UI icons from Feather to Google Material Symbols. The old TODO hard-coded
a Linux source path that does not apply here — re-source before starting.
**Reference:** `docs/file_type_icon_mapping.md`, `docs/current_icon_inventory.md`.

---

## 🐞 Known issues / tech debt

- **Startup worker does no real work:** `ui/boot/bootstrap_worker.py`
  `_validate_database`/`_warmup_caches` are placeholders; the heavy init
  (`detect_external_tools` subprocess probing, DB fresh-start) runs synchronously
  on the main thread during `MainWindow` construction. The finished-signal GC bug
  (timeout ERROR on every launch) is fixed; offloading the real work is open.
- **Post-transform applied more than once:** `NameTransformModule.apply()` runs in
  both preview and execute paths; should run exactly once. See
  `docs/subsystems/rename_engine.md`.
- **Rename-history storage:** persisted via `app/services/rename_history_service.py`
  over `file_rename_history` (`infra/db`); extracting a dedicated store is optional
  cleanup (the previously-listed `core/database/backup_store.py` does not exist).

---

## Notes

- Verified against code on 2026-05-31. Stale node-editor "graph" items and dead
  file references from the previous TODO were removed.
- No critical/blocking bugs open; the startup ERROR-on-every-launch was resolved.
