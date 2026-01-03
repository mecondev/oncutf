# Documentation Index

## Project Status & Planning

**Primary Reference:**
- **[PROJECT_STATUS_2026-01-04.md](../PROJECT_STATUS_2026-01-04.md)** — Current project status (root), metrics, completed refactorings

**Architecture Evolution:**
- **[REFACTORING_ROADMAP.md](REFACTORING_ROADMAP.md)** — Monster files tracker (Phase 4+ active)
- **[MIGRATION_STANCE.md](MIGRATION_STANCE.md)** — Architecture migration policy: legacy vs modern patterns
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — System architecture (4-tier MVC, core layers)
- **[UI_ARCHITECTURE_PATTERNS.md](UI_ARCHITECTURE_PATTERNS.md)** — UI patterns: Behaviors vs Mixins vs Handlers

## Application Systems

- **[application_workflow.md](application_workflow.md)** — Initialization, shutdown, event flow
- **[database_system.md](database_system.md)** — SQLite design, schema, migrations
- **[database_quick_start.md](database_quick_start.md)** — Quick database reference
- **[structured_metadata_system.md](structured_metadata_system.md)** — Metadata handling
- **[safe_rename_workflow.md](safe_rename_workflow.md)** — Rename operation safety
- **[color_tagging_system.md](color_tagging_system.md)** — Color tagging implementation
- **[keyboard_shortcuts.md](keyboard_shortcuts.md)** — All keyboard bindings
- **[dialog_ui_rules.md](dialog_ui_rules.md)** — Dialog design patterns

## Implementation References

- **[database_split_plan.md](database_split_plan.md)** — Database manager refactoring
- **[progress_manager_system.md](progress_manager_system.md)** — Progress tracking API
- **[json_config_system.md](json_config_system.md)** — Configuration management
- **[PHASE5_SUMMARY.md](PHASE5_SUMMARY.md)** — Phase 5 completion summary
- **[WINDOWS_FIXES.md](WINDOWS_FIXES.md)** — Windows-specific issues and solutions

## Archived Documentation

Completed refactoring plans are in **[_archive/](_archive/)** — implementation complete.

---

**Last Updated:** 2026-01-04 | **Active Phase:** Final Polish (Phase 7) | **Status:** 949/949 tests ✅

Layered structure with controllers separating UI from core services:

```
oncutf/
├── main.py                  # Application entry point
├── config.py                # Central configuration
├── ui/                      # UI layer (PyQt5)
│   └── main_window.py       # Main window wiring to controllers
├── controllers/             # UI-agnostic orchestration
│   ├── file_load_controller.py
│   ├── metadata_controller.py
│   ├── rename_controller.py
│   └── main_window_controller.py
├── core/                    # Business logic and managers
│   ├── application_context.py
│   ├── unified_rename_engine.py
│   ├── persistent_hash_cache.py
│   ├── persistent_metadata_cache.py
│   ├── backup_manager.py
│   └── ...
├── modules/                 # Rename modules
├── models/                  # Domain models
├── utils/                   # Helper utilities
└── tests/                   # Comprehensive test suite
```

## Key Features

- Persistent metadata and hash caching with SQLite-backed LRU
- Modular rename pipeline (specified text, counters, metadata, transforms)
- Safe rename workflow with conflict resolution and undo/redo
- Rich PyQt5 UI with drag-and-drop, previews, and keyboard shortcuts
- Profiling scripts for startup and memory: see `scripts/profile_startup.py`, `scripts/profile_memory.py`

## Developer Notes

- Documentation and code comments are in English; user-facing text follows app locale guidelines.
- Tests: run `pytest`; type checks via `mypy`; linting via `ruff`.
- For historical phase documentation, see `_archive/refactor-runs/`.

---

**Last Updated**: December 20, 2025
