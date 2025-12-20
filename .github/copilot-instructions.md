
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
  - Add **Author/Date** headers in new modules (Michael Economou, current date).
  - Use **clear, descriptive names** for variables, functions, classes, and modules.
  - Follow **PEP 8** style guidelines.
  - Use **f-strings** for string formatting.
  - Add **type hints** for function signatures.
  - Use **__future__ imports** for annotations when needed.
  - Use `if TYPE_CHECKING:` for imports needed only for type hints.
  - Add **type annotations** to new functions and methods.
  - Keep **existing loggers, docstrings and comments**; do not delete them unless the user explicitly asks.
  - Use only **ASCII characters** in code, comments, log messages, and docstrings.
    - Never use emoji or Unicode symbols (✓, ✗, →, •, etc.) in logger output.
    - This ensures Windows console compatibility with non-UTF8 encodings (e.g., cp1253 Greek locale).
  - Don't use f-strings in log messages; use %-formatting instead (e.g., `logger.info("Processing %d files", count)`).

### Refactoring permission clarifications

- "Drastic restructure" means: changing external behavior, removing user-facing features, deleting large blocks of logic without replacement, or breaking public APIs without a migration plan.
- Refactoring that **preserves external behavior** but changes **internal structure**, responsibilities, or file layout is **allowed** when the user approves it.

---

## Approved refactoring mode (execution mode)

When the user explicitly approves a refactoring plan or says to proceed:

- The refactoring decision is final and must not be reconsidered.
- Do not suggest avoiding, postponing, or scaling back the refactor.
- Do not re-ask for confirmation.
- Assume version control is clean and rollback is available.

In this mode:
- Prefer architectural clarity over minimal diffs.
- Temporary intermediate breakage is acceptable during a phase, as long as it is resolved by the end of that phase.
- Large or multi-file changes are explicitly allowed.
- Your role switches from advisor to executor.

---

## Ruff / mypy enforcement mode (when requested)

By default: do **not** fix linting or typing issues unless the user asks.

When the user explicitly asks to run/fix Ruff and/or mypy:
- Fix **all** reported issues and warnings without hesitation.
- Do not stop early.
- If a rule is inapplicable or creates noise, propose an adjustment to configuration **only after** fixing issues where reasonable.
- Prefer real fixes over ignores.
- Preserve behavior.

---

## Architecture map (where to look first)

Read these files in this order when understanding behavior:

1. `main.py` — application entry point, Qt app + main window setup.
2. `oncutf/ui/main_window.py` — primary UI view: delegates to controllers for business logic.
3. `oncutf/controllers/` — orchestration layer separating UI from business logic.
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
- `ui_manager.py`, `table_manager.py`, `status_manager.py`, `shortcut_manager.py`, `splitter_manager.py`, `window_config_manager.py` — UI layout, table behavior, status bar, shortcuts, splitters, and window layout persistence.

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

For deeper architectural context, see `docs/` (workflow, metadata system, database, progress manager, safe rename workflow).

---

## Developer workflows

Preferred commands (Python 3.12+):

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

## Large refactoring workflow (branch per phase + quality gates)

For large refactorings, work in explicit phases. Each phase must be atomic and end in a clean, validated state.



### Phase workflow

For each phase:

1. **Create a new branch for the phase**
   - Branch name convention:
     - `refactor/<topic>/<phase-N>-short-title`
   - Example:
     - `refactor/controllers/phase-1-extract-file-load`

2. **Implement only what belongs to this phase**
   - Keep changes focused.
   - Preserve external behavior unless the user explicitly requests behavior changes.

3. **At the end of the phase, run quality gates**
   - `ruff check .`
   - `mypy .`
   - `pytest`

4. **If any gate fails**
   - Fix issues until all pass.
   - Do not leave failing checks at phase completion.

5. **Update the plan / tracking docs**
   - Update the relevant plan file in `docs/` (e.g., `docs/PHASE1_EXECUTION_PLAN.md`)
   - Mark the phase as completed, note key changes, and record follow-ups.

6. **Commit**
   - Use a clear commit message in English.
   - Prefer conventional style:
     - `refactor: <summary>`
     - `fix: <summary>`
     - `docs: <summary>`

7. **Merge into main**
   - Merge the phase branch into `main` after all gates pass.
   - Use non-destructive merges unless the user requests otherwise.

8. **Push**
   - Push `main` and the branch (if desired) to the remote.

### Branch naming and merge policy (mandatory)

All refactoring work must follow these rules:

#### Branch naming
- Each refactoring phase must use a dedicated branch.
- Branch names MUST start with an ISO date.

Format:
- `refactor/YYYY-MM-DD/<topic>-phase-N`

Examples:
- `refactor/2025-12-20/controllers-phase-1`
- `refactor/2025-12-22/metadata-cache-phase-2`

#### Merge policy
- All refactoring branches MUST be merged using:
  - `git merge --no-ff`
- Fast-forward merges are NOT allowed for refactoring phases.
- Squash merges are NOT allowed for refactoring phases.

Rationale:
- Each refactoring phase represents a conceptual and architectural milestone.
- The merge commit marks the completion of a phase and must remain visible in history.

### Agent output requirement

If the agent cannot execute git commands directly, it must:
- Provide the exact git commands to run (copy-paste ready).
- Provide the exact commands for ruff/mypy/pytest.
- Provide the expected order of operations.

---

## Phase 1 plan reference

During Phase 1 refactoring:
- Follow the execution plan in `docs/PHASE1_EXECUTION_PLAN.md`.
- Each step is atomic and testable.
- Never skip phase-end validation (ruff, mypy, pytest).

If anything is ambiguous, ask the user in Greek which behavior they prefer before proceeding.

**IMPORTANT - mypy limitations:**
- Many modules have `ignore_errors=true` in pyproject.toml due to Qt attribute noise.
- When asked to "fix all mypy errors", only fix errors in modules where `ignore_errors=false`.
- Check pyproject.toml [[tool.mypy.overrides]] sections to see which modules are actively checked.
- Use `ruff check .` (without --fix) to check; use `ruff check . --fix` only when explicitly asked to auto-fix.

