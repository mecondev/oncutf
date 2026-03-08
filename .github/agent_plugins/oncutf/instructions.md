# oncutf Agent Plugin Instructions

## Overview

This plugin provides specialized support for oncutf development, enforcing architectural patterns, quality gates, and project conventions.

## Core Principles

- **Architecture First:** Respect MVC layering and boundary rules
- **Quality Non-Negotiable:** All quality gates must pass before completion
- **Naming Consistency:** Brand names (oncut, oncutf) are lowercase trademarks
- **ASCII-Only Code:** Windows cp1253 compatibility

## Quick Reference

### Project Structure

```tree
oncutf/
  app/           # Ports, services, state, use cases
  boot/          # Composition root (DI wiring)
  config/        # Configuration
  controllers/   # UI-agnostic orchestration
  core/          # Business logic (no Qt)
  domain/        # Pure domain models (no external deps)
  infra/         # Infrastructure implementations
  models/        # FileItem, table models
  modules/       # Rename fragment generators
  ui/            # PyQt5 widgets and behaviors
  utils/         # Helpers
```

### Key Rules

1. **No UI in core/app/domain:** `tools/audit_boundaries.py` enforces this
2. **All renames via UnifiedRenameEngine:** Never bypass this
3. **Controllers:** No Qt imports (use literal values for enums)
4. **Metadata:** Always use core services, not direct filesystem access
5. **New UI:** Use Behaviors, not Mixins

### Quality Gate Sequence

Always run in this order when finalizing changes:

```bash
ruff format --check .
ruff check .
python tools/audit_boundaries.py
mypy .
pytest
vulture oncutf --min-confidence 80
```

### Logging

Use %-formatting:

```python
from oncutf.utils.logging.logger_factory import get_cached_logger
logger = get_cached_logger(__name__)
logger.info("Processing %d files", count)
```

### Required Helpers

- Cursor: `from oncutf.utils.cursor_helper import wait_cursor`
- Logger: `from oncutf.utils.logging.logger_factory import get_cached_logger`
- Dialogs: `from oncutf.ui.dialogs.custom_message_dialog import CustomMessageDialog`
- Paths: `from oncutf.utils.filesystem.path_normalizer import normalize_path`

## Commands

```bash
pip install -e .[dev]       # Setup
python main.py              # Run app
pytest                      # Tests (requires exiftool)
pytest -q                   # Quick test run
pytest -q -k <pattern>      # Filtered tests
ruff check . --fix          # Auto-fix (only when explicitly asked)
mypy .                      # Type check
vulture oncutf --min-confidence 80  # Dead code scan
```

## Hard Constraints

- ✗ Never add new ruff ignores without explicit user request
- ✗ Never weaken mypy to silence errors
- ✗ Never bypass UnifiedRenameEngine
- ✗ Never add new wildcard imports
- ✗ Never introduce undeclared dependencies
- ✗ Never mix unrelated changes in a single changeset
- ✗ Never exceed 300 LOC per change-set (prevents massive AI diffs)
- ✗ Never import directly across layers; use `.api` modules:
  - ✓ `from oncutf.core.rename.api import UnifiedRenameEngine`
  - ✗ `from oncutf.core.rename.unified_rename_engine import UnifiedRenameEngine`

## Type Checking Tiers

- **Tier 1 (pragmatic-strict):** app, domain, infra
- **Tier 2 (strict):** controllers, core, models
- **Tier 3 (selective):** ui, Qt modules

## Canonical Sources

| Domain | Canonical | Details |
| -------- | ----------- | --------- |
| **Rename** | `UnifiedRenameEngine` | `core/rename/unified_rename_engine.py` |
| **Columns** | `UnifiedColumnService` | `ui/managers/column_service.py` |
| **Metadata** | `core/metadata/` services | Loading, caching, etc. |
| **File Loading** | `FileLoadController` | `controllers/file_load_controller.py` |
| **Thumbnails** | `ThumbnailViewportController` | `controllers/thumbnail_viewport_controller.py` |

## Developer Workflow

When implementing features:

1. Plan in domain (models, validation)
2. Implement business logic in core
3. Create controller for orchestration
4. Wire in `boot/app_factory.py`
5. Expose via UI/signals
6. Run quality gates
7. Add/update tests

See `PROJECT_RULES.md` (repo root) for detailed patterns.
