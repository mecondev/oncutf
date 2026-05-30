# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`oncutf` is a batch file renamer with a PyQt5 GUI, exopsis-based metadata extraction, and SQLite-backed persistence. It targets photographers and archivists who need precise, safe, and previewed rename workflows.

External dependencies: **exopsis** Python package (metadata backbone), **FFmpeg/FFprobe** binaries (video support).

## Commands

```bash
# Run application
python main.py
python main.py --debug --no-splash   # fast dev loop

# Code quality (run in this order)
ruff check .
ruff format .
mypy .
vulture .

# Architecture audit (also runs as pre-commit hook)
python tools/audit_boundaries.py --no-external-check

# Tests
pytest tests/ -v
pytest tests/ -m "not slow"
pytest tests/ -m "unit"
pytest tests/ -m "integration"
pytest tests/ -m "gui"
pytest tests/ -m "metadata"
pytest tests/ -k "test_metadata"         # pattern match
pytest --cov=. --cov-report=html

# Makefile shortcuts
make lint && make format && make type-check
make test
make test-cov
```

Pre-commit runs ruff + audit_boundaries.py automatically on every commit.

## Architecture

Four-tier clean architecture (strict layer boundaries):

```Architecture
UI (PyQt5)  →  Controllers  →  App Services (Facades)  →  Core / Domain / Infra
```

| Layer | Package | Role |
| ----- | ------- | ---- |
| UI | `oncutf/ui/` | PyQt5 widgets, behaviors (composition), dialogs, delegates |
| Controllers | `oncutf/controllers/` | UI-agnostic orchestration (FileLoad, Metadata, Rename, MainWindow) |
| App Services | `oncutf/app/` | Ports, services, use cases, events, state — clean arch facades |
| Core | `oncutf/core/` | Business logic: UnifiedRenameEngine, UnifiedMetadataManager, caching, DB |
| Domain | `oncutf/domain/` | Pure entities + rules: data models (FileItem, MetadataEntry, FileGroup, CounterScope, ValidationResult) in `domain/models/`, keyboard enums, field validators, metadata-mode decision, service protocols/ports. Stdlib only — **no Qt/UI/infra/utils**. Qt-bound models live in `oncutf/ui/models/` |
| Infra | `oncutf/infra/` | External tools (exopsis, ffmpeg), cache, SQLite, filesystem ops |
| Modules | `oncutf/modules/` | Composable rename-fragment implementations (counter, metadata, text, datetime…) |

**Cross-layer imports must target the subpackage, not its implementation files.**
Each subpackage's `__init__.py` re-exports the public API (`__all__`); treat that as the contract.

- `from oncutf.core.rename import UnifiedRenameEngine`  ✓
- `from oncutf.core.rename.unified_rename_engine import UnifiedRenameEngine`  ✗

The architecture audit tool enforces layer-to-layer rules (e.g. `ui → infra` is blocked, `domain` must stay pure). It does **not** enforce the subpackage-only convention — that one is a code-review rule.

## MyPy Strictness Tiers

Three tiers, configured in `pyproject.toml`:

- **Tier 1** (`app/`, `domain/`, `infra/`): strict equivalent
- **Tier 2** (`controllers/`, `core/`, `models/`): strict but pragmatic
- **Tier 3** (`ui/`): targeted suppression for Qt stub noise

`dict[str, Any]` is legitimate in metadata code (EXIF data is untyped at the boundary). Avoid `Any` elsewhere.

## Key Coding Rules (from PROJECT_RULES.md)

- Max **3–5 files** and **300 LOC** per change-set.
- Prefer `pathlib.Path` over `os.path`.
- Public functions must have explicit return types.
- Formatting-only changes must be isolated from logic changes.
- Before editing: locate the exact symbol definition and all call sites (`rg` is your friend).
- When touching rename logic, preview, execution, metadata caching, or exopsis integration — add or update tests.
- Vulture findings are candidates, not automatic deletions — verify call sites and dynamic usage first.

## Startup Flow

`main.py` → early splash + CLI args → logging → DPI/theme → `configure_default_services()` (DI) → `run_startup()` (`boot/startup_orchestrator.py`) → `MainWindow` → Qt event loop → `perform_graceful_shutdown()`

## Further Reading

- [docs/architecture.md](docs/architecture.md) — 4-tier design detail
- [docs/application_workflow.md](docs/application_workflow.md) — init/shutdown event flow
- [docs/safe_rename_workflow.md](docs/safe_rename_workflow.md) — rename safety guarantees
- [docs/database_system.md](docs/database_system.md) — SQLite schema and migrations
- [PROJECT_RULES.md](PROJECT_RULES.md) — authoritative project rules (non-negotiable)
- [DEVELOPMENT.md](DEVELOPMENT.md) — quick-start guide
