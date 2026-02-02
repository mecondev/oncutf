# Bracket Refactor Checklist

Use bracketed checkboxes to track progress. Keep items short and verifiable.

## Phase 0: Safety Nets

- [ ] Add golden-file tests for rename preview and execution.
- [ ] Add integration tests for selection sync and thumbnail viewport.
- [ ] Add CI jobs for ruff, mypy, and pytest.
- [ ] Document local test commands and known flakiness.

## Phase 1: Domain Boundaries

- [ ] Define domain models (FileRecord, MetadataRecord, RenamePlan).
- [ ] Extract rename logic into a Qt-free domain module.
- [ ] Remove database access from FileItem.
- [ ] Introduce ports for filesystem, metadata, hashing, and thumbnails.

## Phase 2: Infrastructure Cleanup

- [ ] Consolidate ExifTool and FFmpeg access into infra clients.
- [ ] Unify metadata and hash caches behind a single interface.
- [ ] Move persistent cache logic to infra.
- [ ] Ensure infra modules contain all external I/O.

## Phase 3: UI Refactor

- [ ] Replace delegate layers with view-model or use-case bindings.
- [ ] Reduce MainWindow initialization complexity.
- [ ] Move Qt models into ui/models.
- [ ] Remove core-to-ui imports.

## Phase 4: Typing Tightening

- [ ] Categorize all mypy ignores and add error codes.
- [ ] Replace Any with TypedDicts, Protocols, or dataclasses.
- [ ] Add type guards for common narrowing patterns.
- [ ] Enforce strict mypy for domain and app layers.

## Phase 5: Cleanup and Documentation

- [ ] Remove barrel imports and re-export shims.
- [ ] Delete duplicate rename and metadata paths.
- [ ] Update architecture docs with dependency rules.
- [ ] Add a maintenance ruleset for new modules.

## Verification Checklist

- [ ] Rename preview outputs match golden fixtures.
- [ ] Rename execution handles conflicts correctly.
- [ ] Metadata load works in fast and extended modes.
- [ ] Thumbnail viewport loads and caches without UI freezes.
- [ ] Startup and shutdown complete without orphaned processes.

## Definition of Done

- [ ] No core-to-ui imports remain.
- [ ] Domain layer has zero Qt dependencies.
- [ ] No new Any types without justification.
- [ ] Tests and CI are green.
