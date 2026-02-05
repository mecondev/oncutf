# Manual Tests

This directory contains integration tests that require **manual execution** and should **not** run automatically in the CI/CD pipeline.

## Available Tests

### 1. Single Instance Lock Protection

**File:** `test_single_instance_lock.py`  
**Purpose:** Verifies that the application prevents multiple instances from running simultaneously.

**Run with:**

```bash
pytest -v -m manual tests/manual/test_single_instance_lock.py
```

**What it tests:**

- First instance acquires lock successfully
- Second instance is blocked with proper error message  
- Lock file is cleaned up on shutdown

---

### 2. Shutdown Logging Sequence

**File:** `test_shutdown_sequence.py`  
**Purpose:** Validates that shutdown logs contain expected markers and sequence is clean.

**Run with:**

```bash
pytest -v -m manual -s tests/manual/test_shutdown_sequence.py
```

**What it tests:**

- Application starts and initializes
- SIGTERM triggers proper shutdown sequence
- Shutdown markers ([SHUTDOWN], [CLEANUP]) appear in logs
- Clean exit (code 0)

---

## Running Manual Tests

To run **all manual tests:**

```bash
pytest -v -m manual tests/manual/
```

To run with **visible output** (recommended for shutdown test):

```bash
pytest -v -m manual -s tests/manual/
```

## Excluding from Automated Runs

By default, these tests **DO NOT** run with `pytest` or `pytest tests/` because:

- They use `@pytest.mark.manual` decorator
- They require subprocess execution (slow)
- They need Qt GUI environment

To **exclude manual tests explicitly:**

```bash
pytest -v -m "not manual"
```

## Notes

- These tests launch actual application instances via subprocess
- They may require 5-10 seconds each to complete
- They verify system-level integration, not unit logic
- Best run locally before major releases
