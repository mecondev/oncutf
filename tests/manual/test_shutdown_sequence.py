"""Manual test for shutdown logging sequence.

This test demonstrates the enhanced shutdown logging with visible markers.
Run with: pytest -v -m manual -s tests/manual/test_shutdown_sequence.py

Author: Michael Economou
Date: 2026-02-05
"""

import subprocess
import sys
import time
from pathlib import Path

import pytest


@pytest.mark.manual
@pytest.mark.integration
def test_shutdown_logging():
    """Test that shutdown sequence logs are visible and correct.

    This test:
    1. Starts the oncutf application
    2. Waits for initialization
    3. Sends SIGTERM to trigger shutdown
    4. Verifies shutdown logs contain expected markers
    """
    print("\n" + "=" * 70)
    print("SHUTDOWN LOGGING TEST")
    print("=" * 70)
    print("\nLook for visible markers with [SHUTDOWN], [CLEANUP], [MAIN], [SIGNAL] prefixes")
    print("=" * 70)

    # Start the app
    proc = subprocess.Popen(
        [sys.executable, "main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        cwd=Path(__file__).parent.parent.parent,
    )

    print("\nApplication started, waiting 3 seconds...")
    time.sleep(3)

    print("Sending SIGTERM to trigger shutdown...")
    proc.terminate()

    # Wait for process to finish and collect output
    stdout, _ = proc.communicate(timeout=10)

    print("\n" + "=" * 70)
    print("SHUTDOWN LOGS:")
    print("=" * 70)
    print(stdout)
    print("=" * 70)

    # Verify expected shutdown markers are present
    assert "[SHUTDOWN]" in stdout, "Should contain [SHUTDOWN] marker"
    assert "shutdown initiated" in stdout.lower(), "Should log shutdown initiation"

    # Verify clean exit
    assert proc.returncode == 0, f"Should exit cleanly (got exit code {proc.returncode})"

    print("✓ Shutdown markers found")
    print("✓ Clean exit (code 0)")
    print("=" * 70)
    print("TEST PASSED")
    print("=" * 70)
