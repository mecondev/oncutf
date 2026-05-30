# Unified Undo/Redo Architecture

> **Status:** Design (not yet implemented)
> **Date:** 2026-05-31
> **Goal:** one coherent undo/redo contract across metadata edits, the node
> editor, and (in-session) rename — designed in Python now so it translates
> 1:1 to Qt's `QUndoStack`/`QUndoCommand`/`QUndoGroup` in the planned C++ rewrite.

## Why

Undo/redo is currently **fragmented** across four independent mechanisms with no
shared interface:

| # | Mechanism | Paradigm | Scope |
| - | --------- | -------- | ----- |
| 1 | `core/metadata/command_manager.py` (`MetadataCommandManager` + `commands.py`) | **Command** (execute/undo) | Metadata edits; `infra/folder_color_command.py` already rides this base |
| 2 | `core/metadata/metadata_key_registry.py` (`RegistrySnapshot`) | Snapshot | Key-mapping config |
| 3 | `ui/widgets/node_editor/core/history.py` (`SceneHistory`) | Snapshot (full scene serialize) | Node editor scene |
| 4 | `app/services/rename_history_service.py` (`RenameHistoryManager`) | Persistent DB log | Rename batches (cross-session rollback) |

These split into **three categories**, and that split is partly *correct*:

- **A. In-session document-edit undo** (classic Ctrl+Z): metadata edits (1),
  node editor scene (3). **These should share one contract.**
- **B. Config/settings undo**: key registry (2). Should *not* sit on the same
  stack as document edits (you don't want Ctrl+Z during metadata editing to undo
  a key-mapping config change).
- **C. Persistent operation log**: rename history (4). Durable, cross-session,
  filesystem rollback — fundamentally different from in-memory Ctrl+Z and stays
  separate (it may still expose the same `Command` interface for an in-session
  "undo last rename").

## The paradigm clash, reconciled

Metadata uses the **command** pattern (memory-efficient, semantic descriptions);
the node editor uses **snapshots** (serialize the whole scene — the standard,
robust choice for a node graph, where reversible per-edge/per-node commands would
be painful). These are not in conflict: **a snapshot is expressible as a
command.** A `SnapshotCommand` stores before/after state and `undo()` restores
"before". Qt's `QUndoStack` accepts both semantic commands and snapshot-style
commands on the same stack — so one contract covers both.

## The contract (Qt-free, C++-portable)

Define in `core/undo/` (or `domain/`), with **no Qt imports**, so it ports
directly to C++/Qt later:

```python
class Command(Protocol):
    def execute(self) -> bool: ...
    def undo(self) -> bool: ...
    def redo(self) -> bool: ...          # default: execute()
    description: str
    def merge_with(self, other: "Command") -> bool: ...   # grouping/coalescing

class UndoStack(Observable):             # ~ what MetadataCommandManager already is
    def push(self, cmd: Command) -> bool: ...   # execute + record, clear redo
    def undo(self) -> bool: ...
    def redo(self) -> bool: ...
    def can_undo(self) -> bool: ...
    def can_redo(self) -> bool: ...
    def undo_text(self) -> str: ...
    def redo_text(self) -> str: ...
    def begin_macro(self, text: str) -> None: ...   # grouping
    def end_macro(self) -> None: ...
    # signals: index_changed, can_undo_changed, can_redo_changed

class UndoGroup:                         # ~ QUndoGroup
    def add_stack(self, stack: UndoStack) -> None: ...
    def set_active(self, stack: UndoStack) -> None: ...
    def undo(self) -> bool: ...          # delegates to active stack
    def redo(self) -> bool: ...
```

### Key decision: context-scoped, not global

**Multiple stack instances, one interface.** Each context (metadata panel, node
editor scene) owns its own `UndoStack`; an `UndoGroup` tracks which is active and
routes the single Undo/Redo action to it. This is how Lightroom / DaVinci behave
and is exactly Qt's `QUndoGroup` model.

A **global** single stack was rejected: it forces strict LIFO across unrelated
domains. Example — rename a file, then change its rotation; to undo the rename
you would first have to undo the rotation. Context-scoped stacks let each panel's
Ctrl+Z act independently.

#### Safety prerequisite (shipped)

Out-of-order context-scoped undo is only safe if operations on the same file are
*independent*. Metadata is keyed by the DB **`path_id`** surrogate, and rename now
calls `_relink_renamed_file` (`core/file/operations_manager.py`) →
`DatabaseManager.update_file_path` (in-place, preserves `path_id`) + in-memory
cache key remap. So a rename no longer detaches a file's metadata, and undoing a
rename without first undoing a metadata edit (or vice-versa) leaves consistent
state. This prerequisite is **already in place**.

## Migration path (incremental, low-risk)

1. Extract the contract above into `core/undo/` (or `domain/`). `MetadataCommand`
   → `Command`, `MetadataCommandManager` → `UndoStack` (it is already an
   `Observable` with grouping, max-history, and the right signals — ~90% there).
2. Folder-color already subclasses `MetadataCommand` → no change beyond the rename.
3. Node editor: wrap `SceneHistory` as a `SnapshotCommand` pushed onto a node-editor
   `UndoStack`, *or* have `SceneHistory` implement the same interface. Either way
   it joins the `UndoGroup`.
4. Add an `UndoGroup` at the UI level; bind the global Undo/Redo actions (Ctrl+Z /
   Ctrl+Shift+Z) to the group; switch the active stack on panel focus.
5. Rename history (4) and key registry (2) stay separate but may implement
   `Command` where an in-session undo makes sense.

## C++ rewrite mapping

| Python contract | Qt/C++ |
| --------------- | ------ |
| `Command` | `QUndoCommand` (subclass per operation) |
| `UndoStack` | `QUndoStack` |
| `UndoGroup` | `QUndoGroup` |
| `begin_macro`/`end_macro` | `QUndoStack::beginMacro`/`endMacro` |
| `merge_with` | `QUndoCommand::mergeWith` + `id()` |
| snapshot command | `QUndoCommand` storing before/after blobs |

Designing to this contract now means the C++ undo system is a near-mechanical
translation rather than a redesign.
