# Metadata rules (EXIF, structured metadata, caching)

## Scope

These rules apply when working in:

- `core/unified_metadata_manager.py`
- `core/structured_metadata_manager.py`
- Any metadata-related managers or services in `core/`.
- `utils/metadata_exporter.py`
- ExifTool wrappers and helpers.

## Responsibilities

- Metadata loading must:
  - Be **centralized** via dedicated managers.
  - Use caching where possible to avoid repeated expensive reads.
  - Cooperate with the rename engine so metadata remains consistent after renames.

## ExifTool & performance

- Prefer the **persistent ExifTool wrapper** for standard metadata reads.
- Use extended metadata (e.g., `-ee` mode) only when explicitly requested by the user.
- Do not start and stop new ExifTool processes repeatedly for the same session if a persistent process is already available.

## Caching and consistency

- After renames, metadata cache entries must be **remapped** to new file paths.
- Do not store huge or recursive structures inside metadata entries (e.g., no deep preview maps inside metadata).
- If adding new metadata fields:
  - Keep the structure consistent.
  - Document keys and value types in docstrings or developer docs.

## Threading & background work

- Long metadata operations should:
  - Run in worker threads or async tasks.
  - Report progress via the existing progress/status mechanisms (managers in `core/`).
- Avoid directly updating UI elements from metadata threads; use signals to the main thread.

When modifying metadata behavior, always verify how it interacts with:

1. The rename engine (preview/execute pipeline).
2. The metadata viewer (tree view, details widgets).
3. The caching layer (so that no stale or missing entries appear after rename).
