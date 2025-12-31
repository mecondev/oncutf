# Windows-Specific Fixes

This document describes Windows-specific issues and their fixes.

## Issue 1: Infinite Loop in File Tree Refresh

### Problem

On Windows, the file tree refresh could enter an infinite loop when directory changes were detected. The sequence was:

1. Directory changes → `FilesystemMonitor` detects change
2. Triggers `_on_directory_changed()` in `FileTreeView`
3. Calls `model.refresh()` to update the view
4. **Windows QFileSystemModel** triggers another `directoryChanged` signal during refresh
5. Loop back to step 2 → **infinite loop**

This issue was specific to Windows due to how `QFileSystemModel` handles directory watching and refresh operations on that platform.

### Solution

Added a `_refresh_in_progress` flag to prevent recursive calls:

```python
# In FileTreeView.__init__():
self._refresh_in_progress = False

# In _on_directory_changed():
if self._refresh_in_progress:
    return  # Ignore nested refresh events

try:
    self._refresh_in_progress = True
    model.refresh()
    # ...
finally:
    self._refresh_in_progress = False
```

**File**: [oncutf/ui/widgets/file_tree_view.py](../oncutf/ui/widgets/file_tree_view.py)

---

## Issue 2: Mypy Version Mismatch (300+ Warnings)

### Problem

The `pyproject.toml` was configured with `python_version = "3.13"`, but:
- Project requirements specify Python 3.12 (`requires-python = ">=3.12"`)
- Windows environment might have Python 3.12 installed
- This mismatch caused mypy to:
  - Use wrong type stubs for stdlib
  - Generate 300+ spurious warnings about type mismatches
  - Ignore properly configured error suppressions

### Solution

Changed mypy configuration to match project requirements:

```toml
[tool.mypy]
python_version = "3.12"  # Changed from "3.13"
```

**File**: [pyproject.toml](../pyproject.toml)

### Why This Matters

When mypy's `python_version` doesn't match the actual Python version:
- Type stubs may be incompatible
- Generic types behave differently (e.g., `list[str]` vs `List[str]`)
- Error suppressions (`disable_error_code`) may not work correctly
- Cross-platform CI/CD may produce inconsistent results

---

## Testing on Windows

After these fixes, verify:

1. **File tree refresh works without hanging:**
   - Press F5 to refresh file tree
   - Change directory contents externally (add/remove files)
   - Verify UI remains responsive

2. **Mypy produces consistent results:**
   ```bash
   mypy .
   ```
   - Error count should match Linux environment
   - `ignore_errors=true` modules should be properly suppressed

3. **No infinite loops in logs:**
   Check `logs/oncutf.log` for repeating patterns of:
   ```
   [FileTreeView] Directory changed: ...
   [FileTreeView] Model refreshed after directory change
   ```

---

## Related Files

- [oncutf/ui/widgets/file_tree_view.py](../oncutf/ui/widgets/file_tree_view.py) — FileTreeView with refresh guard
- [oncutf/core/file/monitor.py](../oncutf/core/file/monitor.py) — FilesystemMonitor with debouncing
- [pyproject.toml](../pyproject.toml) — Project configuration with mypy settings

---

## Platform Differences

### QFileSystemModel Behavior

| Platform | Refresh Trigger | Recursive Events |
|----------|----------------|------------------|
| **Linux** | Manual only | No |
| **Windows** | Auto + Manual | **Yes** (during refresh) |
| **macOS** | Auto + Manual | Sometimes |

### Mitigation Strategy

1. **Guard flags** — Prevent recursion (`_refresh_in_progress`)
2. **Debouncing** — Group rapid events (500ms timer in `FilesystemMonitor`)
3. **Pause mechanism** — Disable monitoring during critical operations (metadata save)

---

## Future Improvements

Consider implementing:
- [ ] Per-platform refresh strategies (conditional code)
- [ ] Configurable debounce intervals
- [ ] Monitoring statistics/diagnostics panel
- [ ] Auto-detection of refresh loops with circuit breaker
