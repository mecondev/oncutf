# Single Instance Lock File Protection

## Overview

The oncutf application uses a **lock file** mechanism to prevent multiple instances from running simultaneously. This protects the configuration and database files from corruption caused by concurrent access.

## Implementation

### Lock File Location

```text
Linux/macOS: ~/.local/share/oncutf/.oncutf.lock
Windows: %LOCALAPPDATA%\oncutf\.oncutf.lock
```

### Lock File Format

```text
<PID> <hostname> <timestamp>
```

Example:

```text
12345 laptop.local 2026-02-01 22:15:30
```

## How It Works

### 1. Application Startup

- Checks if `.oncutf.lock` exists
- If exists: reads PID and checks if process is still running
- If process running: exits with error message
- If process dead: removes stale lock (normal after crash)
- Creates new lock file with current PID

### 2. Normal Shutdown

- Lock file is removed in `cleanup_on_exit()`
- Called via `atexit` handler or signal handler

### 3. Crash Recovery

- Stale lock files are automatically detected and removed
- Uses OS-level process checks:
  - **Windows:** `OpenProcess()` via ctypes
  - **Linux/macOS:** `os.kill(pid, 0)`

## Benefits

✅ **Prevents data corruption** from concurrent writes to:

- config.json
- oncutf_data.db (additional to SQLite locking)
- semantic_metadata_aliases.json

✅ **Cross-platform compatible**

- Works on Windows, Linux, and macOS
- No special permissions required

✅ **Automatic stale lock cleanup**

- Detects crashed instances
- Removes orphaned locks automatically

✅ **Clear error messages**

- User-friendly message when blocked
- Logs PID of running instance

## Testing

Run the test script to verify functionality:

```bash
python test_lock_file.py
```

## Technical Details

### Why Not file.open() Exclusive Mode?

- Not cross-platform compatible
- Windows: file locks released on process exit
- Linux: advisory locks only (not enforced)

### Why Not Read-Only Permissions?

- Owner can still modify files (doesn't protect on Linux/macOS)
- Requires permission juggling (error-prone)
- Lock file is simpler and more reliable

### SQLite Database

SQLite already has its own locking via WAL mode:

- `-wal` file for write-ahead log
- `-shm` file for shared memory
- Lock file provides additional instance-level protection

## API Reference

```python
from oncutf.utils.lock_file import acquire_lock, release_lock, is_locked

# Acquire lock (returns False if another instance running)
if not acquire_lock():
    print("Another instance is running")
    sys.exit(1)

# Check if lock is held
if is_locked():
    print("Lock is active")

# Release lock (called automatically at exit)
release_lock()
```

## Error Scenarios

### Scenario 1: Normal Second Instance

```console
$ python main.py  # First instance
$ python main.py  # Second instance
ERROR: Another instance of oncutf is already running.
Please close the other instance first.
```

### Scenario 2: Stale Lock After Crash

```console
$ python main.py  # Starts normally
[INFO] Removing stale lock file (PID: 12345)
[INFO] Lock acquired (PID: 67890)
```

### Scenario 3: Permission Error

```text
[ERROR] Failed to create lock file: [Errno 13] Permission denied
# Application starts anyway (degraded mode)
```

## Future Enhancements

- [ ] Lock file with more metadata (user, app version)
- [ ] Network lock support for shared drives
- [ ] GUI dialog when blocked (instead of console message)
- [ ] Optional multi-instance mode for advanced users
