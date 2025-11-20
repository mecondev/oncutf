# Rename engine and modules rules

## Scope

These rules apply when working on:

- `core/unified_rename_engine.py` and related rename services.
- Files under `modules/`:
  - `base_module.py`
  - `specified_text_module.py`
  - `counter_module.py`
  - `metadata_module.py`
  - `name_transform_module.py`
  - `text_removal_module.py`
  - Any future rename/transform modules.

## Core concepts

- The rename system is **modular**:
  - Each module produces a **name fragment** based on file state, metadata, and its own configuration.
  - The final filename is built by composing active modules in order.
- The original filename is **not assumed** unless an explicit “original name”/“name transform” module participates in the pipeline.

## Module design

- Each module should:
  - Encapsulate one clear behavior (e.g., prepend text, add counter, inject metadata, transform case).
  - Provide a way to preview its contribution (preview fragment).
  - Respect an `is_effective()`-style check:
    - Return `False` when the module would have no effect (e.g., empty text, default transform).
- Modules must **not**:
  - Perform actual filesystem renames.
  - Talk directly to UI widgets.
  - Manage global state.

## Rename engine

- The unified rename engine is responsible for:
  - Building previews from active modules.
  - Detecting conflicts (duplicate names, collisions).
  - Validating names (using validators from `utils/` where appropriate).
  - Executing rename operations safely.

## Patterns to follow

- When adding a new module:
  - Start from an existing module (e.g., `specified_text_module.py` or `counter_module.py`) as a reference.
  - Implement clear docstrings and type annotations.
  - Keep configuration simple and explicit (no hidden magic).
- When updating the rename engine:
  - Preserve the preview → validate → execute pipeline.
  - Ensure that changes do not break existing UI expectations (e.g., preview always reflects current modules).

For risky or complex changes (new module types, conflict resolution strategies, batch operations), propose a short plan and get explicit approval from the user before editing code.
