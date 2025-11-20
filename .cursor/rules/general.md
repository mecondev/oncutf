# General rules for oncutf (Cursor AI)

## Project identity

- This repository is **oncutf**, a PyQt5 desktop app for **batch file renaming** with EXIF/metadata awareness and a professional UI.
- Main entry points:
  - `main.py` — application startup.
  - `main_window.py` — central UI controller and high-level workflow.
  - `config.py` — configuration for UI, filters, and behavior.

## Communication & language

- When talking to the user:
  - **Always reply in Greek**, with a friendly, clear, and chatty tone.
- In code:
  - **All identifiers, comments, docstrings, log messages, and UI text must be in English.**
- Prefer stable, maintainable solutions over “clever” one-liners.

## Style & tooling

- The project uses:
  - Python 3.12+
  - Strict `mypy` configuration.
  - `ruff` + `black` for linting/formatting.
- When adding or editing code:
  - Always add **type annotations** to new functions and methods.
  - Add **module-level docstrings** where they are missing.
  - Keep existing **loggers, comments, and docstrings**; do not remove them unless explicitly asked.

## Safety & scope

- Do **not** run `git` commands (commit, pull, push, reset, clean) on behalf of the user.
- Do **not** delete files, move directories, or alter backups/archives.
- For large or multi-file changes:
  - First propose a **short plan** (which files, what changes).
  - Wait for explicit confirmation from the user before applying edits.

## Architecture orientation

- Core logic is mostly under:
  - `core/` — application context, managers, rename engine, metadata management, UI and table managers.
  - `modules/` — rename modules.
  - `widgets/` — custom PyQt5 widgets and views.
  - `utils/` — helpers (paths, metadata export, drag & drop, icons, timers, logging).
- When implementing new features:
  - Prefer to extend the appropriate **manager** or **module**, rather than adding ad-hoc logic into `main_window.py`.
  - Keep UI logic in widgets/managers; keep business logic in core/modules.

## Tests & commands

- To run the app: `python main.py`
- To run tests: `pytest` (markers: `unit`, `integration`, `gui`, `exiftool`, `slow`, etc.).
- Some tests and features require `exiftool` available in `PATH`.

If in doubt about where a feature should live (core, module, widget, utils), ask the user in Greek and propose 1–2 options.
