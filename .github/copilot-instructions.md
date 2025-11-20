<!-- GitHub Copilot / AI agent instructions for this repository -->

# oncutf — AI assistant guidelines

These instructions help AI coding agents work productively and safely in this repository.

## Quick context

- **Project:** OnCutF — PyQt5 desktop app for advanced batch file renaming with EXIF/metadata support and a professional UI.
- **Main focus:** metadata-aware rename engine (preview → validate → execute), safe operations, persistent caches, and responsive UI even with large file sets.

When in doubt, prefer a **stable, extendable** solution over a “clever” one.

---

## Communication & style conventions

- **Human-facing explanations:** Greek. Keep the tone friendly and clear.
- **Code, comments, docstrings, log messages, UI text:** English.
- Always:
  - Add **module-level docstrings** when missing.
  - Add **type annotations** to new functions and methods.
  - Keep **existing loggers, docstrings and comments**; do not delete or drastically restructure code unless the user explicitly asks.

Do **not** fix linting issues (ruff/mypy) unless the user requests it. The repo is configured with strict mypy and ruff/black in `pyproject.toml`. :contentReference[oaicite:4]{index=4}

---

## Architecture map (where to look first)

Read these files in this order when understanding behavior:

1. `main.py` — application entry point, Qt app + main window setup.
2. `main_window.py` — primary UI controller: file loading, metadata actions, rename preview workflow.
3. `config.py` — central configuration for UI defaults, filters, paths, debug flags.

Core services (in `core/`):

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

---

## Safety rules for AI agents

- **Do not run git commands** (commit, pull, push, reset, clean) without explicit user approval.
- For **multi-file or high-impact changes**:
  - First present a **short, structured plan** (bulleted list of files and changes).
  - Wait for user confirmation before applying edits.
- Never remove or significantly restructure logging, docstrings, or comments unless the user asks.
- When unsure which manager or module to extend, propose options and ask the user which direction fits their existing architecture.

If anything is ambiguous, ask the user in Greek which behavior they prefer before proceeding.
