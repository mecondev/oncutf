#!/usr/bin/env python3
"""Test script to demonstrate single instance lock protection.

This script shows how the lock file prevents multiple instances from running.
"""

import subprocess
import sys
import time


def test_single_instance():
    """Test that only one instance can run at a time."""
    print("=" * 70)
    print("SINGLE INSTANCE LOCK TEST")
    print("=" * 70)
    print()
    print("This test will:")
    print("1. Start the oncutf application in background")
    print("2. Wait 2 seconds")
    print("3. Try to start a second instance (should fail)")
    print("4. Terminate the first instance")
    print("5. Verify lock file is cleaned up")
    print()
    print("=" * 70)
    print()

    # Start first instance in background
    print("Starting first instance...")
    proc1 = subprocess.Popen(
        [sys.executable, "main.py"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )

    # Wait for it to start
    time.sleep(3)

    # Try to start second instance (should fail immediately)
    print("Attempting to start second instance (should fail)...")
    proc2 = subprocess.Popen(
        [sys.executable, "main.py"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )

    # Wait a bit and check if second instance exited
    time.sleep(2)
    returncode = proc2.poll()

    if returncode is not None and returncode != 0:
        print(f"✓ SUCCESS: Second instance was blocked (exit code: {returncode})")
        # Get output from second instance
        output = proc2.communicate(timeout=1)[0]
        if "Another instance" in output:
            print("✓ Correct error message displayed")
    else:
        print("✗ FAIL: Second instance should have been blocked")

    print()
    print("Terminating first instance...")
    proc1.terminate()
    proc1.wait(timeout=10)

    print()
    print("Verifying lock file cleanup...")
    time.sleep(1)

    import os
    from pathlib import Path

    from oncutf.utils.paths import AppPaths

    lock_file = AppPaths.get_user_data_dir() / ".oncutf.lock"
    if not lock_file.exists():
        print("✓ SUCCESS: Lock file was cleaned up properly")
    else:
        print("✗ WARNING: Lock file still exists (may be stale)")
        print(f"  Location: {lock_file}")

    print()
    print("=" * 70)
    print("TEST COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    test_single_instance()
