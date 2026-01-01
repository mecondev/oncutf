<!-- GitHub Copilot / AI agent instructions for oncutf -->

# oncutf — AI assistant guidelines

## Quick context

- **Project:** PyQt5 desktop app for batch file renaming with EXIF/metadata support.
- **Architecture:** 4-tier MVC (UI → Controllers → Core Services → Data Layer).
- **Status:** Phase 7 (Final Polish) — 592+ tests, controllers complete.
- Prefer **stable, extendable** solutions over "clever" ones.

---

## Communication & style

- **User communication:** Greek. **Code/comments/logs:** English.
- **Logging:** Use %-formatting: `logger.info("Processing %d files", count)`.
- **Characters:** ASCII only in code/logs (Windows cp1253 compatibility).
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
| **Column Management** | `UnifiedColumnService` | `ColumnManager` (thin adapter) |
| **UI Components** | Behaviors (`ui/behaviors/`) | Mixins (no new mixins) |

**Rules:**
- All rename operations MUST go through `UnifiedRenameEngine`.
- New UI code uses **Behaviors**, NOT Mixins.
- New column logic goes in `UnifiedColumnService`.

See [docs/REFACTORING_ROADMAP.md](../docs/REFACTORING_ROADMAP.md) for technical debt tracking.

---

## Refactoring workflow

When user approves refactoring:
- Execute without re-asking; prefer clarity over minimal diffs.
- Run quality gates at phase end: `ruff check .` → `mypy .` → `pytest`.
- Branch naming: `refactor/YYYY-MM-DD/<topic>-phase-N`.
- Merge with `git merge --no-ff` (no fast-forward or squash).
