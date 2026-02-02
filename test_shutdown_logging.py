#!/usr/bin/env python3
"""Test script to demonstrate enhanced shutdown logging.

This script starts the oncutf application and exits after a brief delay
to demonstrate the visible shutdown sequence in the logs.
"""

import subprocess
import sys
import time


def test_shutdown_logging():
    """Start app, wait briefly, then send SIGTERM to trigger shutdown logging."""
    print("=" * 70)
    print("SHUTDOWN LOGGING TEST")
    print("=" * 70)
    print()
    print("This test will:")
    print("1. Start the oncutf application")
    print("2. Wait 3 seconds")
    print("3. Send SIGTERM to trigger shutdown")
    print("4. Display the shutdown logs")
    print()
    print("Look for visible markers with [SHUTDOWN], [CLEANUP], [MAIN], [SIGNAL] prefixes")
    print("=" * 70)
    print()

    # Start the app
    proc = subprocess.Popen(
        [sys.executable, "main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    print("Application started, waiting 3 seconds...")
    time.sleep(3)

    print("Sending SIGTERM to trigger shutdown...")
    proc.terminate()

    # Wait for process to finish and collect output
    stdout, _ = proc.communicate(timeout=10)

    print("=" * 70)
    print("SHUTDOWN LOGS:")
    print("=" * 70)
    print(stdout)
    print("=" * 70)
    print("TEST COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    test_shutdown_logging()
