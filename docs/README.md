# Documentation Index

Navigation for the `oncutf` documentation set. Project-level rules and quick
references live in the repository root; subsystem and feature documentation
lives here in `docs/`.

> **Last verified:** 2026-05-31 against the live codebase
> (Python 3.13, ~500 source files, 1158 tests passing).

## Root references (authoritative)

- **[../CLAUDE.md](../CLAUDE.md)** — Architecture, commands, coding rules (agent + contributor entry point)
- **[../PROJECT_RULES.md](../PROJECT_RULES.md)** — Non-negotiable project rules
- **[../DEVELOPMENT.md](../DEVELOPMENT.md)** — Quick-start dev guide
- **[../TODO.md](../TODO.md)** — Active features, unfinished work, known issues
- **[../CHANGELOG.md](../CHANGELOG.md)** — Notable changes
- **[../README.md](../README.md)** — Product overview

## Architecture & process

- **[architecture.md](architecture.md)** — Four-tier clean architecture (UI → Controllers → App Services → Core/Domain/Infra)
- **[migration_stance.md](migration_stance.md)** — Which patterns to use when (canonical vs legacy)
- **[application_workflow.md](application_workflow.md)** — Initialization, shutdown, event flow

## Subsystems (technical maps)

- **[subsystems/file_engine.md](subsystems/file_engine.md)** — File discovery, loading, monitoring
- **[subsystems/metadata_engine.md](subsystems/metadata_engine.md)** — Metadata extraction, caching, staging
- **[subsystems/rename_engine.md](subsystems/rename_engine.md)** — Rename pipeline: preview, validate, execute, undo

## Application systems

- **[database_system.md](database_system.md)** — SQLite schema, `path_id` design, migrations
- **[database_quick_start.md](database_quick_start.md)** — Quick database reference
- **[structured_metadata_system.md](structured_metadata_system.md)** — Structured metadata storage & categories
- **[metadata_key_simplification.md](metadata_key_simplification.md)** — Human-readable metadata key mapping (user guide)
- **[safe_rename_workflow.md](safe_rename_workflow.md)** — Rename safety & stable-identity guarantees
- **[color_tagging_system.md](color_tagging_system.md)** — Per-file color tags
- **[json_config_system.md](json_config_system.md)** — Configuration management (JSON + DB hybrid)
- **[progress_manager_system.md](progress_manager_system.md)** — Progress tracking API
- **[single_instance_lock.md](single_instance_lock.md)** — Single-instance lock-file protection
- **[bundled_tools_integration.md](bundled_tools_integration.md)** — FFmpeg/FFprobe integration

## UI / UX reference

- **[keyboard_shortcuts.md](keyboard_shortcuts.md)** — All keyboard bindings
- **[dialog_ui_rules.md](dialog_ui_rules.md)** — Dialog design patterns
- **[file_table_header.md](file_table_header.md)** — File-table header features & shortcuts
- **[font_system_implementation.md](font_system_implementation.md)** — Font system reference
- **[widget_type_aware_fonts.md](widget_type_aware_fonts.md)** — Per-widget font defaults
- **[file_type_icon_mapping.md](file_type_icon_mapping.md)** — File-type → icon mapping
- **[current_icon_inventory.md](current_icon_inventory.md)** — Icon inventory

## Platform

- **[windows_fixes.md](windows_fixes.md)** — Windows-specific issues and solutions

---

**Note on history:** completed migration/refactor plans and abandoned feature
specs were removed on 2026-05-31 (recoverable via git history) to keep this set
matching the current codebase. See `CHANGELOG.md` for what shipped.
