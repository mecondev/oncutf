<!-- GitHub Copilot / AI agent instructions for oncutf -->

# oncutf — AI assistant guidelines

## Quick context

- **Project:** PyQt5 desktop app for batch file renaming with EXIF/metadata support.
- **Architecture:** 4-tier MVC (UI → Controllers → Core Services → Data Layer).
- **Status:** Phase 7 (Final Polish) — 592+ tests, controllers complete.
- Prefer **stable, extendable** solutions over "clever" ones.

## Naming & Branding (IMPORTANT)

- **Brand name:** oncut (lowercase in all contexts)
- **Product name:** oncutf (lowercase in code, packages, technical contexts) — the application itself
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

## Architecture (where to look first)

```
main.py → oncutf/ui/main_window.py → oncutf/controllers/ → oncutf/core/
```

**Controllers** (`oncutf/controllers/`): UI-agnostic orchestration layer:
- `file_load_controller.py` — file loading, drag & drop, directory scanning
- `metadata_controller.py` — metadata loading, EXIF operations
- `rename_controller.py` — rename preview → validate → execute workflow
- `main_window_controller.py` — high-level multi-service orchestration

**Core services** (`oncutf/core/`): Business logic:
- `application_context.py` — singleton app state, manager registry
- `unified_rename_engine.py` — rename orchestration (never bypass this)
- `unified_metadata_manager.py` — metadata loading with caching
- `persistent_hash_cache.py`, `backup_manager.py` — SQLite persistence

**Rename modules** (`oncutf/modules/`): Pure composable name fragment generators.

- Delegator methods marked as "Backward compatibility" are temporary.
- New code MUST NOT use backward compatibility properties or methods.
- Application Service layer is the canonical entry point for operations.

---

## Required helpers (use instead of raw Qt)

```python
from oncutf.utils.cursor_helper import wait_cursor      # not QApplication.setOverrideCursor()
from oncutf.utils.logger_factory import get_cached_logger  # not logging.getLogger()
from oncutf.ui.widgets.custom_message_dialog import CustomMessageDialog  # not QMessageBox
from oncutf.utils.path_normalizer import normalize_path  # cross-platform paths
```

---

## Developer commands

```bash
pip install -e .[dev]    # Install with dev dependencies
python main.py           # Run application
pytest                   # Run tests (requires exiftool in PATH)
ruff check .             # Lint (no auto-fix)
ruff check . --fix       # Lint with auto-fix (only when explicitly asked)
mypy .                   # Type check (many modules have ignore_errors=true)
```

## Quality Gates (MANDATORY) — Do not skip

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
When to Run Full vs Targeted Checks
Default: run the full baseline commands above.

You may run a targeted subset during development, but NEVER for the final result:

If only formatting/typing changed:

ruff format --check .

ruff check .

mypy .

If only a small unit was touched:

pytest -q (or pytest -q -k <pattern>)

If boundaries-related files changed (imports / package moves / new modules):

ALWAYS run: python tools/audit_boundaries.py (no exceptions)

Final output must always pass the full baseline commands.

If a Gate Fails
Do not add new global ignores.

Do not broaden exclusions.

Do not modify rules to "make it green".

Fix the underlying issue and re-run the failed gate.

Formatting Policy
Formatter of record: ruff format.

Use ruff format . only when explicitly requested or as the final step after review.

The repo must remain stable: avoid format churn not related to the change.

Architecture Boundary Policy
tools/audit_boundaries.py is authoritative.

If a change introduces a boundary violation, refactor the code to comply.

No new "import aggregator" modules are allowed to hide dependencies.

Dead/Unused Code Policy
Use vulture oncutf --min-confidence 80 for triage.

If vulture reports a legitimate unused symbol, remove it.

If it is a false positive:

Prefer adding a local # noqa: <rule> or a narrow whitelist entry.

Never mass-ignore warnings across the codebase.

Pytest Policy
Prefer adding/adjusting tests when behavior changes.

Tests must remain deterministic and not depend on local machine state.

If a test requires external tools (exiftool), use appropriate markers.


**Test markers:** `unit`, `integration`, `gui`, `exiftool`, `slow`.

---

## Key patterns

1. **Rename flow:** Always respect preview → validate → execute via `unified_rename_engine`.
2. **Rename modules:** Pure functions returning name fragments; no filesystem operations.
3. **Controllers:** UI-agnostic, testable without Qt, orchestrate between UI and services.
4. **Metadata:** Always go through managers in `core/`; use caching layer.
5. **mypy:** Check `pyproject.toml` overrides — many modules have `ignore_errors=true`.

---

## Canonical sources (Single Source of Truth)

| Domain | Canonical | Legacy/Supporting |
|--------|-----------|-------------------|
| **Rename Pipeline** | `UnifiedRenameEngine` | `utils/naming/*` (helpers only) |
| **Column Management** | `UnifiedColumnService` (`core/ui_managers/column_service.py`) | `ColumnManager` (adapter), `models/file_table/column_manager.py` (model-level) |
| **UI Components** | Behaviors (`ui/behaviors/`) | Mixins (no new mixins) |
| **Metadata Loading** | `UnifiedMetadataManager` | `MetadataController` (orchestration) |
| **File Loading** | `FileLoadController` | `FileLoadManager` (legacy) |

**Rules:**
- All rename operations MUST go through `UnifiedRenameEngine`.
- New UI code uses **Behaviors**, NOT Mixins.
- New column logic goes in `UnifiedColumnService`.
- New features: controller → core service → domain. NO new logic in `ui_managers/` or `MainWindow`.

See [PROJECT_RULES.md](../PROJECT_RULES.md) for policy and detailed patterns.

### Hard Constraints (Do Not Violate)
- Never add new ruff ignores/exclusions without explicit user request.
- Never weaken mypy settings to silence errors; fix types or scope with narrow overrides.
- Never bypass `UnifiedRenameEngine` or `UnifiedMetadataManager`.
- Never introduce new wildcard imports or import-aggregator modules.

---

## Refactoring workflow

When user approves refactoring:
- Execute without re-asking; prefer clarity over minimal diffs.
- Run quality gates at phase end: `ruff check .` → `mypy .` → `pytest`.
- Branch naming: `refactor/YYYY-MM-DD/<topic>-phase-N`.
- Merge with `git merge --no-ff` (no fast-forward or squash).
