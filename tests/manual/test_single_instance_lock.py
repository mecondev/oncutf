"""Manual test for single instance lock protection.

This test demonstrates how the lock file prevents multiple instances from running.
Run with: pytest -v -m manual tests/manual/test_single_instance_lock.py

Author: Michael Economou
Date: 2026-02-05
"""

import subprocess
import sys
import time
from pathlib import Path

import pytest

from oncutf.utils.paths import AppPaths


@pytest.mark.manual
@pytest.mark.integration
def test_single_instance_protection():
    """Test that only one instance can run at a time.

    This test:
    1. Starts the oncutf application in background
    2. Waits for initialization
    3. Tries to start a second instance (should fail)
    4. Terminates the first instance
    5. Verifies lock file is cleaned up
    """
    print("\n" + "=" * 70)
    print("SINGLE INSTANCE LOCK TEST")
    print("=" * 70)

    # Start first instance in background
    print("\nStarting first instance...")
    proc1 = subprocess.Popen(
        [sys.executable, "main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=Path(__file__).parent.parent.parent,
    )

    # Wait for it to start
    time.sleep(3)

    # Try to start second instance (should fail immediately)
    print("Attempting to start second instance (should fail)...")
    proc2 = subprocess.Popen(
        [sys.executable, "main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=Path(__file__).parent.parent.parent,
    )

    # Wait and check if second instance exited
    time.sleep(2)
    returncode = proc2.poll()

    # Get output from second instance
    output, _ = proc2.communicate(timeout=2)

    # Verify second instance was blocked
    assert returncode is not None, "Second instance should have exited"
    assert returncode != 0, f"Second instance should fail (got exit code {returncode})"
    assert "Another instance" in output, "Should show 'Another instance' error message"

    print(f"✓ Second instance was blocked (exit code: {returncode})")
    print("✓ Correct error message displayed")

    # Terminate first instance
    print("\nTerminating first instance...")
    proc1.terminate()
    proc1.wait(timeout=10)

    # Verify lock file cleanup
    print("Verifying lock file cleanup...")
    time.sleep(1)

    lock_file = AppPaths.get_user_data_dir() / ".oncutf.lock"
    assert not lock_file.exists(), f"Lock file should be cleaned up: {lock_file}"

    print("✓ Lock file was cleaned up properly")
    print("=" * 70)
    print("TEST PASSED")
    print("=" * 70)
