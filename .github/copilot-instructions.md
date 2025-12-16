<!-- GitHub Copilot / AI agent instructions for this repository -->

# oncutf — AI assistant guidelines

These instructions help AI coding agents work productively and safely in this repository.

## Quick context

- **Project:** oncutf — PyQt5 desktop app for advanced batch file renaming with EXIF/metadata support and a professional UI.
- **Main focus:** metadata-aware rename engine (preview → validate → execute), safe operations, persistent caches, and responsive UI even with large file sets.

When in doubt, prefer a **stable, extendable** solution over a “clever” one.

---

## Communication & style conventions

- **Human-facing explanations:** Greek. Keep the tone friendly and clear.
- **Code, comments, docstrings, log messages, UI text:** English.
- Communicate with the user in Greek.
- All code-related output (commit messages, comments, docstrings, variables, filenames, documentation) must be in English.

- Always:
  - Add **module-level docstrings** when missing.
  - Add Author/Date headers in new modules (Michael Economou, current date).
  - Use **clear, descriptive names** for variables, functions, classes, and modules.
  - Follow **PEP 8** style guidelines.
  - Use **f-strings** for string formatting.
  - Add **type hints** for function signatures.
  - Use **__Future__ imports** for annotations when needed.
  - Use If __typing.TYPE_CHECKING__ for imports needed only for type hints.
  - Add **type annotations** to new functions and methods.
  - Keep **existing loggers, docstrings and comments**; do not delete or drastically restructure code unless the user explicitly asks.
  - **Use only ASCII characters** in code, comments, log messages, and docstrings. **Never use emoji or Unicode symbols** (✓, ✗, →, •, etc.) in logger output. This ensures Windows console compatibility with non-UTF8 encodings (e.g., cp1253 Greek locale).
  - Don't use fstrings in log messages; use %-formatting instead (e.g., logger.info("Processing %d files", count)).
  - Run all tests after code changes to ensure nothing is broken.
  - Run linters (ruff, mypy) after code changes to ensure style compliance.

Do **not** fix linting issues (ruff/mypy) unless the user requests it. The repo is configured with strict mypy and ruff/black in `pyproject.toml`.

---

## Architecture map (where to look first)

Read these files in this order when understanding behavior:

1. `main.py` — application entry point, Qt app + main window setup.
2. `oncutf/ui/main_window.py` — primary UI view: delegates to controllers for business logic.
3. `oncutf/controllers/` — **NEW (Phase 1)** orchestration layer separating UI from business logic.
4. `oncutf/config.py` — central configuration for UI defaults, filters, paths, debug flags.

**Controllers (in `oncutf/controllers/`)** — Phase 1 refactoring (in progress):

- `file_load_controller.py` — orchestrates file loading: drag & drop, directory scanning, companion files.
- `metadata_controller.py` — coordinates metadata loading and EXIF operations (planned).
- `rename_controller.py` — handles rename preview and execution workflows (planned).
- `main_window_controller.py` — high-level orchestration between all controllers (planned).

Core services (in `oncutf/core/`):

- `application_context.py` — centralized application state.
- `application_service.py` — high-level API to operations (reduces MainWindow complexity).
- `unified_rename_engine.py` — main rename engine (preview, validation, conflict handling, execution).
- `unified_metadata_manager.py` + `structured_metadata_manager.py` — metadata loading and structuring.
- `unified_column_service.py` — single source of truth for column configuration.
- `backup_manager.py`, `persistent_hash_cache.py`, `metadata_command_manager.py` — database, caching, and command/undo system.
- `thread_pool_manager.py`, `async_operations_manager.py` — async and threaded work scheduling.
- `ui_manager.py`, `table_manager.py`, `status_manager.py`, `shortcut_manager.py`, `splitter_manager.py`, `window_config_manager.py` — overall UI layout, table behavior, status bar, shortcuts, splitters, and window layout persistence.

Rename modules (in `modules/`):

- `base_module.py` — base class and contracts for all rename modules.
- `specified_text_module.py`, `counter_module.py`, `metadata_module.py`, `name_transform_module.py`, `text_removal_module.py`, etc.
- Each module produces **name fragments** and exposes configuration; the final name is built by composing active modules in order.

UI widgets (in `widgets/`):

- `file_table_view.py`, `file_tree_view.py`, `interactive_header.py` — custom views and header with advanced selection & drag behavior.
- `rename_module_widget.py`, `final_transform_container.py` — visual management for rename modules and final transforms.
- `custom_message_dialog.py`, `rename_conflict_resolver.py`, `custom_splash_screen.py` — dialogs, conflict resolution, splash screen.
- `ui_delegates.py` — custom item delegates (hover, combobox, tree).

Utilities (in `utils/`):

- `file_drop_helper.py`, `drag_zone_validator.py` — drag & drop logic.
- `filename_validator.py`, `path_utils.py`, `path_normalizer.py` — filename and path validation/normalization.
- `icon_cache.py`, `icons_loader.py`, `multiscreen_helper.py` — visual helpers and multi-screen support.
- `metadata_exporter.py`, `timer_manager.py`, `logger_helper.py` — metadata export, timers, and logging helpers.

For deeper architectural context, see `docs/` (workflow, metadata system, database, progress manager, safe rename workflow). :contentReference[oaicite:12]{index=12}

---

## Developer workflows

Preferred commands (Python 3.12+): :contentReference[oaicite:13]{index=13}

- Install runtime deps:
  - `pip install -r requirements.txt`
- Install dev deps:
  - `pip install -e .[dev]`
- Run the app:
  - `python main.py`
- Run tests:
  - `pytest` or `pytest tests -q`
  - Use markers from `pyproject.toml` (`unit`, `integration`, `gui`, `exiftool`, `slow`, etc.).

Many tests and metadata features require `exiftool` to be installed and available in `PATH`.

---

## Patterns to follow

When modifying or adding rename-related logic:

- Keep rename modules **pure and composable**:
  - Input: file/metadata state + module settings.
  - Output: string fragment (or empty when `is_effective()` is false).
- Do not perform filesystem operations in modules; actual rename is handled by `unified_rename_engine` and related managers.
- Respect the preview → validate → execute flow; do not bypass the unified engine.

When working with metadata:

- Always go through the metadata managers in `core/` and the caching layer.
- Avoid storing large or recursive structures in metadata entries.

When working on the UI:

- Let `ui_manager.py`, `table_manager.py`, `status_manager.py` and the custom widgets handle layout, selection, and visual behavior.
- Keep business logic out of widgets whenever possible, using managers/services instead.

When working with controllers (Phase 1 refactoring):

- Controllers orchestrate between UI and domain services (managers in `core/`).
- Controllers are UI-agnostic: testable without Qt/GUI, no direct widget manipulation.
- Follow the pattern: **write new controller code first, test it, wire to MainWindow with feature flag, then remove old code**.
- Each controller handles one domain: FileLoad, Metadata, Rename, MainWindow orchestration.
- All new controller files must include **author/date headers** (Michael Economou, current date) in module docstring.

---

- **During Phase 1 refactoring**: Follow the execution plan in `docs/PHASE1_EXECUTION_PLAN.md`. Each step is atomic and testable. Never skip validation steps (tests, ruff, app launch).

If anything is ambiguous, ask the user in Greek which behavior they prefer before proceeding.
