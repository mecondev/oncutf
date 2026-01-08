# Documentation Index

## Project Status & Planning

**Primary Reference:**
- **[PROJECT_STATUS_2026-01-04.md](../PROJECT_STATUS_2026-01-04.md)** — Project status snapshot (root directory)

**Active Architecture Documentation:**
- **[migration_stance.md](migration_stance.md)** — Architecture migration policy: legacy vs modern patterns
- **[architecture.md](architecture.md)** — System architecture (4-tier MVC, core layers)

**Completed & Archived:**
- **[_archive/REFACTORING_ROADMAP_COMPLETED.md](_archive/REFACTORING_ROADMAP_COMPLETED.md)** — Monster files eliminated (DONE)
- **[_archive/PHASE5_SUMMARY_COMPLETED.md](_archive/PHASE5_SUMMARY_COMPLETED.md)** — 5-phase refactoring complete (DONE)
- **[_archive/BEHAVIORS_REFACTORING_PLAN_COMPLETED.md](_archive/BEHAVIORS_REFACTORING_PLAN_COMPLETED.md)** — Behaviors extraction complete (DONE)
- **[_archive/UI_ARCHITECTURE_PATTERNS_COMPLETED.md](_archive/UI_ARCHITECTURE_PATTERNS_COMPLETED.md)** — UI patterns guide (DONE)
- **[_archive/mixin_to_behavior_extraction_COMPLETED.md](_archive/mixin_to_behavior_extraction_COMPLETED.md)** — Mixin migration log (DONE)

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
- **[windows_fixes.md](windows_fixes.md)** — Windows-specific issues and solutions

## Planning Documents (Future Features)

- **[color_column_implementation_plan.md](color_column_implementation_plan.md)** — Color column feature plan
- **[color_database_implementation.md](color_database_implementation.md)** — Color database design
- **[node_editor_integration_plan.md](node_editor_integration_plan.md)** — Node editor future integration
- **[file_table_header.md](file_table_header.md)** — File table header design

---

**Last Updated:** 2026-01-09 | **Status:** Production Ready | **Tests:** 986/986 passing | **Docstring Coverage:** 99.9%+

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

## Architecture Highlights

**Layered Design:**
- **Controllers** (`controllers/`) — UI-agnostic orchestration, testable without Qt
- **Core Services** (`core/`) — Business logic, caching, metadata, rename engine
- **Behaviors** (`ui/behaviors/`) — Reusable UI interactions (composition over mixins)
- **Domain Models** (`models/`) — Pure data structures

**Key Features:**
- Persistent metadata and hash caching with SQLite-backed LRU
- Modular rename pipeline (specified text, counters, metadata, transforms)
- Safe rename workflow with conflict resolution and undo/redo
- Rich PyQt5 UI with drag-and-drop, previews, and keyboard shortcuts
- 99.9%+ docstring coverage for maintainability

## Quality Metrics

- **Tests:** 986 passing, 6 skipped
- **Type Safety:** mypy clean (478 source files)
- **Linting:** ruff clean
- **Docstring Coverage:** 99.9%+ (only auto-generated files excluded)
- **Architecture:** Monster files eliminated, all behaviors <600 lines

## Developer Notes

- Documentation and code comments are in English
- Run tests: `pytest`
- Type checks: `mypy .`
- Linting: `ruff check .`
- Docstring coverage: `python scripts/generate_project_report.py --mode structure-full --missing`
- Historical refactoring documentation in `_archive/`