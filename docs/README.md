# oncutf Documentation

This directory contains comprehensive documentation for the oncutf application, a PyQt5 desktop app for advanced batch file renaming with EXIF/metadata support.

## 📢 Status Update

**Phase 0 Complete** (2025-12-15): All application code successfully migrated to `oncutf/` package structure. See [ROADMAP.md](ROADMAP.md) for details.

## 🚀 Quick Start

- **[ROADMAP](ROADMAP.md)** - Development roadmap and phase tracking
- **[ARCHITECTURE](ARCHITECTURE.md)** - System architecture overview
- **[Keyboard Shortcuts](keyboard_shortcuts.md)** - Complete keyboard shortcuts reference
- **[Database Quick Start](database_quick_start.md)** - Get started with the persistent database system

## 📋 Planning & Architecture

### Development Planning
- **[ARCH_REFACTOR_PLAN.md](ARCH_REFACTOR_PLAN.md)** - Detailed Phase 0-3 refactoring plan
- **[EXECUTION_ROADMAP.md](EXECUTION_ROADMAP.md)** - Step-by-step execution tracking
# oncutf Documentation

Comprehensive documentation for the oncutf application, a PyQt5 desktop app for advanced batch file renaming with EXIF/metadata support.

## Status Update

**Phase 7 In Progress (docs-first)** — Final polish focuses on documentation and stability; versioning/tagging is deferred. See [PROGRESS_SUMMARY.md](PROGRESS_SUMMARY.md) and [PHASE7_EXECUTION_PLAN.md](PHASE7_EXECUTION_PLAN.md).

## Quick Start

- **[ROADMAP](ROADMAP.md)** — Development roadmap and phase tracking
- **[ARCHITECTURE](ARCHITECTURE.md)** — System architecture overview
- **[Keyboard Shortcuts](keyboard_shortcuts.md)** — Complete keyboard shortcuts reference
- **[Database Quick Start](database_quick_start.md)** — Persistent database usage

## Planning & Architecture

### Development Planning
- **[ARCH_REFACTOR_PLAN.md](ARCH_REFACTOR_PLAN.md)** — Strategic refactoring plan
- **[PHASE7_EXECUTION_PLAN.md](PHASE7_EXECUTION_PLAN.md)** — Final polish (docs-first scope)
- **[ROADMAP.md](ROADMAP.md)** — Current development status and next steps
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — High-level architecture overview

### Core Systems Documentation
- **[Application Workflow](application_workflow.md)** — Startup to rename execution flow
- **[Database System](database_system.md)** — SQLite-based persistence architecture
- **[Structured Metadata System](structured_metadata_system.md)** — Metadata organization and processing
- **[Progress Manager System](progress_manager_system.md)** — Unified progress tracking API
- **[Safe Rename Workflow](safe_rename_workflow.md)** — Enhanced rename process with Qt safety
- **[JSON Config System](json_config_system.md)** — Configuration management

## System Architecture

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
- Tests: run `pytest`; type checks via `mypy`; linting via `ruff` (strict subsets enabled per phase).
- Avoid version bump/tag steps until release packaging is requested.

## Troubleshooting


---

**Last Updated**: December 19, 2025
- **Case Handling**: [Case-Sensitive Rename Guide](case_sensitive_rename_guide.md)
