# GUI rules (PyQt5 UI, widgets, views)

## Scope

These rules apply when working in:

- `main_window.py`
- `widgets/` (e.g., `file_table_view.py`, `file_tree_view.py`, `interactive_header.py`,
  `rename_module_widget.py`, `final_transform_container.py`, dialogs, delegates).
- UI-related managers in `core/`:
  - `ui_manager.py`
  - `table_manager.py`
  - `status_manager.py`
  - `shortcut_manager.py`
  - `splitter_manager.py`
  - `window_config_manager.py`

## Principles

- **Never block the UI thread.**
  - Long-running tasks (metadata loading, hashing, heavy IO) belong in worker threads or async operations.
- Use the existing managers:
  - Let managers handle table selection, sorting, header behavior, and status updates.
  - Avoid duplicating logic in multiple widgets.

## Behavior and patterns

- Keep UI classes focused on:
  - Wiring signals/slots.
  - Presenting data from core and modules.
  - Triggering core actions via managers/services.
- Avoid:
  - Complex business rules implemented directly inside `QWidget`/`QMainWindow` subclasses.
  - Direct filesystem operations in widgets (use core managers instead).

## Selection & interaction

- The file table uses **custom selection behavior** (Ctrl/Shift, custom header toggles, info icons).
- When modifying selection logic:
  - Keep behavior consistent with file preview and rename engine.
  - Ensure selection updates are reflected in the preview area and metadata views.

## Visual consistency

- Respect existing styling and delegates (hover effects, icons, comboboxes, tree view).
- When introducing new widgets:
  - Follow patterns in existing widgets for:
    - Naming.
    - Signals and slots.
    - Layout and spacing.

If a change would significantly alter user interaction (shortcuts, header behavior, double-click actions), describe it clearly and get user approval before applying code changes.
