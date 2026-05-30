# oncutf — TODO & Unfinished-Work Catalogue

Honest catalogue of what is unfinished, half-built, or known-broken. Verified
against the live codebase.

**Last verified:** 2026-05-31

> **Strategic context:** a C++ rewrite is planned once the C++ build of exopsis
> lands (~2-3 weeks out). The decision is to **finish the Python app first**, so
> feature designs settle in fast-iterating Python and then transfer as a clean
> translation. Architecture/refactor polish that won't carry into C++ is
> deprioritised; feature completion and design clarity are prioritised.

---

## In-progress / half-built features

### Thumbnail view (~80%)

**Status:** Phase 1–4 done, integrated via `ui/boot/bootstrap_manager.py`.
**Code:** `ui/widgets/thumbnail_viewport.py`, `ui/delegates/thumbnail_delegate.py`,
`ui/thumbnail/{providers,thumbnail_cache,thumbnail_manager,thumbnail_worker}.py`.
**Remaining:**

- Phase 5 — model sync / sorting parity with the file table
- Phase 6 — testing & polish
- Deferred: video preview dialog (frame picker, "set this frame as thumbnail")

### Node editor (built but NOT integrated)

**Status:** A substantial generic node-editor widget exists (~53 files under
`ui/widgets/node_editor/`: scene, graphics, nodes, persistence, themes, history)
but it is **not wired into the application** (no imports outside the package)
and the rename-specific nodes are **unimplemented** (`nodes/rename_nodes/` is an
empty package).
**Remaining:**

- Implement `rename_nodes/` (a node per rename module: counter, metadata,
  original_name, specified_text, remove_text, transform)
- Bidirectional conversion: linear module list ↔ node graph
- Integrate into the main UI (open editor, run graph through `UnifiedRenameEngine`)
- The node editor already has its own snapshot-based undo (`node_editor/core/history.py`)
  — fold it under the unified undo contract (see Known issues → Undo/redo)

> **Correction:** earlier TODO items referenced `core/rename_graph/` and
> `controllers/rename_graph_controller.py` with a `graph_model`/`graph_validator`
> (cycle detection, topological sort, (de)serialization). **None of that exists**
> — that architecture was abandoned in favour of `ui/widgets/node_editor/`. Those
> ghost items have been removed.

---

## Not-started features

### Dockable widgets

Detachable/floating panels (file table, metadata tree, preview, modules) via
`QDockWidget`, with layout persistence in session state. Not started.

### Metadata database search

`StructuredMetadataManager.search_files_by_metadata()` currently returns an empty
list (stub). Needs SQL over the metadata JSON column (`json_extract`), wildcard/
regex support, and file-table filtering integration.
**Location:** `oncutf/core/metadata/structured_manager.py`.

### Icon migration (Feather → Material)

Migrate UI icons from Feather to Google Material Symbols.
**Note:** the old TODO hard-coded a Linux source path (`/mnt/data_1/...`) that
does not apply on this Windows setup — re-source before starting.
**Reference:** `docs/file_type_icon_mapping.md`, `docs/current_icon_inventory.md`.

---

## Known issues / tech debt

### Unified undo/redo (fragmented)

Four independent undo mechanisms exist with no shared contract:

1. `core/metadata/command_manager.py` — `MetadataCommandManager` (+ `commands.py`;
   `infra/folder_color_command.py` already rides this base)
2. `core/metadata/metadata_key_registry.py` — snapshot undo for key mappings
3. `ui/widgets/node_editor/core/history.py` — snapshot undo for the node scene
4. `app/services/rename_history_service.py` — persistent, cross-session rename log

**Design:** see [docs/undo_redo_architecture.md](docs/undo_redo_architecture.md)
for the proposed unified `Command` / `UndoStack` / `UndoGroup` contract
(context-scoped, maps 1:1 to Qt `QUndoCommand`/`QUndoStack`/`QUndoGroup` for the
C++ rewrite). **Prerequisite already shipped:** rename now preserves a file's
identity via the DB `path_id` (`_relink_renamed_file`), so out-of-order
context-scoped undo is safe.

### Startup: background worker does no real work

`ui/boot/bootstrap_worker.py` `_validate_database`/`_warmup_caches` are
placeholders; the heavy init (`detect_external_tools` subprocess probing, DB
fresh-start/migrations) runs **synchronously on the main thread** during
`MainWindow` construction. The finished-signal GC bug that forced every startup
through the timeout fallback is fixed (see CHANGELOG), but moving the real work
into the worker is still open (medium effort, needs thread-safety review of
`detect_external_tools`).

### Rename pipeline: post-transform applied more than once

`NameTransformModule.apply()` is invoked in multiple places (preview + execute).
Should be applied exactly once. See `docs/subsystems/rename_engine.md`.

### Rename-history storage location

Rename history is persisted via `app/services/rename_history_service.py` over the
`file_rename_history` table (`infra/db`). Extracting it into a dedicated store is
optional cleanup, not a blocker. (The previously-listed
`core/database/backup_store.py` does not exist.)

---

## Notes

- Items here are verified against code on 2026-05-31. Stale node-editor "graph"
  items and dead file references from the previous TODO were removed.
- No critical/blocking bugs are open; the startup ERROR-on-every-launch issue
  was resolved this session.
