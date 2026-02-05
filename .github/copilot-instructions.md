<!-- GitHub Copilot / AI agent instructions for oncutf -->

# oncutf -- AI assistant guidelines

## Quick context

- **Project:** PyQt5 desktop app for batch file renaming with EXIF/metadata support.
- **Architecture:** Layered MVC (UI -> Controllers -> Core Services -> Domain/Infra).
- **Python:** 3.12, line-length=100, double quotes.
- **Status:** Active development; run `pytest -q` for current test count.
- Prefer **stable, extendable** solutions over "clever" ones.

## Naming & Branding (IMPORTANT)

- **Brand name:** oncut (lowercase in all contexts)
- **Product name:** oncutf (lowercase in code, packages, technical contexts)
- **Trademark:** Both names are trademarks of the oncut project. Use consistently, always lowercase.

---

## Communication & style

- **User communication:** Greek. **Code/comments/logs:** English.
- **Logging:** Use %-formatting: `logger.info("Processing %d files", count)`.
- **Characters:** ASCII only in code/logs (Windows cp1253 compatibility).
- **NO EMOJIS:** Never use emojis anywhere (code, comments, logs, git commits, scripts, reports). Use ASCII symbols only.
- **New modules:** Add Author/Date headers (Michael Economou, current date).
- **Type hints:** Use `if TYPE_CHECKING:` for type-only imports.

---

## Architecture

### Boot sequence

```
main.py -> oncutf/boot/app_factory.py -> oncutf/ui/main_window.py -> oncutf/controllers/ -> oncutf/core/
```

### Layer structure

```
oncutf/
  app/           # Ports, services, state (AppContext), use cases, events
  boot/          # Composition root: app_factory.py, infra_wiring.py (ONLY place infra is wired)
  config/        # Configuration management
  controllers/   # UI-agnostic orchestration (no Qt UI imports allowed)
  core/          # Business logic (no Qt imports allowed via boundary audit)
  domain/        # Pure domain models, validation, ports (no external deps)
  infra/         # Infrastructure: cache, db, filesystem, external tools
  models/        # FileItem, FileTableModel and related
  modules/       # Pure composable rename fragment generators
  ui/            # Widgets, behaviors, adapters, boot/, managers/
  utils/         # Logging, filesystem, naming helpers
```

### Boot / DI

- `oncutf/boot/app_factory.py` -- `create_app_context()` is the composition root
- `oncutf/boot/infra_wiring.py` -- ONLY place infra implementations are imported/registered
- `oncutf/ui/boot/` -- multi-phase MainWindow bootstrap (orchestrator -> manager -> worker)

### Controllers (`oncutf/controllers/`)

UI-agnostic orchestration layer. **Must NOT import from `oncutf.ui`.**

- `file_load_controller.py` -- file loading, drag & drop, directory scanning
- `metadata_controller.py` -- metadata loading, EXIF operations
- `rename_controller.py` -- rename preview -> validate -> execute workflow
- `main_window_controller.py` -- high-level multi-service orchestration
- `thumbnail_viewport_controller.py` -- thumbnail loading, selection, sorting
- `module_orchestrator.py` -- rename module pipeline coordination

### Core services (`oncutf/core/`)

Business logic. **No Qt imports allowed** (enforced by boundary audit).

- `application_service.py` -- application service facade
- `rename/unified_rename_engine.py` -- rename orchestration (never bypass this)
- `metadata/metadata_service.py` -- metadata service entry point
- `metadata/metadata_loader.py`, `metadata/metadata_cache_service.py` -- loading + caching
- `backup_manager.py` -- SQLite persistence

### Boundary rules (enforced by `tools/audit_boundaries.py`)

- **domain**: pure -- no ui/app/infra/core/controllers deps
- **app**: no ui/infra/core/boot deps
- **infra**: no ui/app/controllers/boot deps
- **core**: no ui deps, no direct Qt imports
- **controllers**: no ui deps (use signals/protocols)
- **ui**: no direct infra imports (go through app/boot services)
- Qt forbidden in: domain, app, core layers
- `TYPE_CHECKING` imports are excluded from runtime boundary checks

### Key domain files

- `oncutf/models/file_item.py` -- `FileItem` class (single file entry)
- `oncutf/app/state/context.py` -- application state/manager registry
- `oncutf/infra/cache/persistent_hash_cache.py` -- SQLite hash persistence
- `oncutf/modules/` -- pure composable name fragment generators

---

## Required helpers (use instead of raw Qt)

```python
from oncutf.utils.cursor_helper import wait_cursor                    # not QApplication.setOverrideCursor()
from oncutf.utils.logging.logger_factory import get_cached_logger     # not logging.getLogger()
from oncutf.ui.dialogs.custom_message_dialog import CustomMessageDialog  # not QMessageBox
from oncutf.utils.filesystem.path_normalizer import normalize_path    # cross-platform paths
```

### Qt enum workaround in controllers

Controllers cannot import Qt classes directly (boundary rule). Use literal values:

```python
file_item = index.data(0x0100)   # Qt.UserRole
selection_model.select(index, 0x0002)  # QItemSelectionModel.Select
```

---

## Developer commands

```bash
pip install -e .[dev]    # Install with dev dependencies
python main.py           # Run application
pytest                   # Run tests (requires exiftool in PATH)
ruff check .             # Lint (no auto-fix)
ruff check . --fix       # Lint with auto-fix (only when explicitly asked)
mypy .                   # Type check (3-tier: strict for controllers/core, pragmatic for ui)
```

## Quality Gates (MANDATORY) -- Do not skip

These checks are the project's non-negotiable safety rails.
Any code change must be validated locally before proposing it.

### Golden Rule

- DO NOT relax rules to make checks pass (no new ignores, no "quick disable").
- DO NOT bypass architecture boundaries.
- Fix the code, not the tooling.

### Required Tools

Always use the project's tooling (do not invent alternatives):

- ruff (lint + formatter)
- mypy (type checking)
- pytest (tests)
- vulture (dead/unused code scan)
- tools/audit_boundaries.py (architecture boundary enforcement)

### Baseline Commands

Run these in this exact order when finishing a change-set:

```bash
ruff format --check .
ruff check .
python tools/audit_boundaries.py
mypy .
pytest
vulture oncutf --min-confidence 80
```

### When to Run Full vs Targeted Checks

Default: run the full baseline commands above.

You may run a targeted subset during development, but NEVER for the final result:

- If only formatting/typing changed: `ruff format --check .` + `ruff check .` + `mypy .`
- If only a small unit was touched: `pytest -q` (or `pytest -q -k <pattern>`)
- If boundaries-related files changed (imports / package moves / new modules):
  ALWAYS run `python tools/audit_boundaries.py` (no exceptions)

Final output must always pass the full baseline commands.

### If a Gate Fails

- Do not add new global ignores.
- Do not broaden exclusions.
- Do not modify rules to "make it green".
- Fix the underlying issue and re-run the failed gate.

### Formatting Policy

- Formatter of record: `ruff format`.
- Use `ruff format .` only when explicitly requested or as the final step after review.
- The repo must remain stable: avoid format churn not related to the change.

### Architecture Boundary Policy

- `tools/audit_boundaries.py` is authoritative.
- If a change introduces a boundary violation, refactor the code to comply.
- No new "import aggregator" modules are allowed to hide dependencies.

### Dead/Unused Code Policy

- Use `vulture oncutf --min-confidence 80` for triage.
- If vulture reports a legitimate unused symbol, remove it.
- If it is a false positive: prefer a local `# noqa` or narrow whitelist entry.
- Never mass-ignore warnings across the codebase.

### Pytest Policy

- Prefer adding/adjusting tests when behavior changes.
- Tests must remain deterministic and not depend on local machine state.
- If a test requires external tools (exiftool), use appropriate markers.
- **Test markers:** `unit`, `integration`, `gui`, `exiftool`, `slow`, `manual`, `local_only`.

---

## Key patterns

1. **Rename flow:** Always respect preview -> validate -> execute via `unified_rename_engine`.
2. **Rename modules:** Pure functions returning name fragments; no filesystem operations.
3. **Controllers:** UI-agnostic, testable without Qt, orchestrate between UI and services.
4. **Metadata:** Always go through services in `core/metadata/`; use caching layer.
5. **mypy:** 3-tier system in `pyproject.toml` -- Tier 1 pragmatic-strict (app/domain/infra),
   Tier 2 strict (controllers/core/models), Tier 3 selective (UI/Qt modules).
6. **New UI:** Use Behaviors (`ui/behaviors/`), NOT Mixins.
7. **New features flow:** controller -> core service -> domain. NO new logic in `ui/managers/` or `MainWindow`.

---

## Canonical sources (Single Source of Truth)

| Domain | Canonical | Legacy/Supporting |
|--------|-----------|-------------------|
| **Rename Pipeline** | `UnifiedRenameEngine` (`core/rename/unified_rename_engine.py`) | `utils/naming/*` (helpers only) |
| **Column Management** | `UnifiedColumnService` (`ui/managers/column_service.py`) | `ColumnManager` (adapter), `models/file_table/column_manager.py` (model-level) |
| **UI Components** | Behaviors (`ui/behaviors/`) | Mixins (no new mixins) |
| **Metadata Loading** | `core/metadata/metadata_service.py` + `metadata_loader.py` + `metadata_cache_service.py` | `MetadataController` (orchestration), `ui/managers/metadata_unified_manager.py` (UI facade) |
| **File Loading** | `FileLoadController` (`controllers/file_load_controller.py`) | `FileLoadManager` (legacy) |
| **Thumbnail Viewport** | `ThumbnailViewportController` (`controllers/thumbnail_viewport_controller.py`) | Widget delegates to controller |

**Rules:**
- All rename operations MUST go through `UnifiedRenameEngine`.
- New UI code uses **Behaviors**, NOT Mixins.
- New column logic goes in `UnifiedColumnService` (`ui/managers/column_service.py`).
- Delegator methods marked as "Backward compatibility" are temporary; new code MUST NOT use them.
- Application Service layer is the canonical entry point for operations.

See [PROJECT_RULES.md](../PROJECT_RULES.md) for policy and detailed patterns.

### Hard Constraints (Do Not Violate)

- Never add new ruff ignores/exclusions without explicit user request.
- Never weaken mypy settings to silence errors; fix types or scope with narrow overrides.
- Never bypass `UnifiedRenameEngine` or the core metadata services.
- Never introduce new wildcard imports or import-aggregator modules.
- Never introduce new dependencies unless explicitly requested.
- Never mix unrelated changes in a single change-set.

---

## Refactoring workflow

When user approves refactoring:

- Execute without re-asking; prefer clarity over minimal diffs.
- Run quality gates at phase end: `ruff check .` -> `mypy .` -> `pytest`.
- Branch naming: `refactor/YYYY-MM-DD/<topic>-phase-N`.
- Merge with `git merge --no-ff` (no fast-forward or squash).
- Maximum 3-5 files per iteration.
