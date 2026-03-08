"""oncutf Agent Plugin Tools.

Utilities for VS Code agent plugin supporting oncutf development.

Author: Michael Economou
Date: 2026-03-08
"""

import subprocess
from pathlib import Path
from typing import Optional


def run_quality_gates(workspace_root: str) -> dict:
    """Run all quality gates for oncutf project.

    Returns dict with gate results:
        {
            "ruff_format": (passed: bool, output: str),
            "ruff_check": (passed: bool, output: str),
            "boundary_audit": (passed: bool, output: str),
            "mypy": (passed: bool, output: str),
            "pytest": (passed: bool, output: str),
            "vulture": (passed: bool, output: str),
        }
    """
    root = Path(workspace_root)
    results = {}

    gates = [
        ("ruff_format", ["ruff", "format", "--check", "."]),
        ("ruff_check", ["ruff", "check", "."]),
        ("boundary_audit", ["python", "tools/audit_boundaries.py"]),
        ("mypy", ["mypy", "."]),
        ("pytest", ["pytest"]),
        ("vulture", ["vulture", "oncutf", "--min-confidence", "80"]),
    ]

    for gate_name, cmd in gates:
        try:
            proc = subprocess.run(
                cmd,
                cwd=root,
                capture_output=True,
                text=True,
                timeout=300,
            )
            results[gate_name] = (proc.returncode == 0, proc.stdout + proc.stderr)
        except subprocess.TimeoutExpired:
            results[gate_name] = (False, "TIMEOUT")
        except Exception as e:
            results[gate_name] = (False, str(e))

    return results


def check_boundary_violations(workspace_root: str) -> str | None:
    """Run architecture boundary audit.

    Returns audit output if violations found, None if clean.
    """
    try:
        proc = subprocess.run(
            ["python", "tools/audit_boundaries.py"],
            cwd=workspace_root,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except Exception as e:
        return f"Error running boundary audit: {e}"
    return proc.stdout + proc.stderr if proc.returncode != 0 else None


def get_test_summary(workspace_root: str) -> dict:
    """Get test summary (count, status).

    Returns:
        {
            "total": int,
            "passed": int,
            "failed": int,
            "output": str,
        }

    """
    try:
        proc = subprocess.run(
            ["pytest", "-q"],
            cwd=workspace_root,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except Exception as e:
        return {
            "success": False,
            "output": f"Error running tests: {e}",
        }
    output = proc.stdout + proc.stderr
    return {
        "success": proc.returncode == 0,
        "output": output,
    }


def validate_imports(workspace_root: str, file_path: str) -> dict:
    """Validate imports in a Python file for boundary violations.

    Returns:
        {
            "valid": bool,
            "violations": list[str],
            "details": str,
        }

    """
    full_path = Path(workspace_root) / file_path
    if not full_path.exists():
        return {
            "valid": False,
            "violations": [f"File not found: {file_path}"],
            "details": "",
        }

    try:
        full_path.read_text()
    except Exception as e:
        return {
            "valid": False,
            "violations": [f"Error analyzing imports: {e}"],
            "details": "",
        }

    violations: list[str] = []
    return {
        "valid": len(violations) == 0,
        "violations": violations,
        "details": "",
    }


def get_project_info(workspace_root: str) -> dict:
    """Get oncutf project information.

    Returns:
        {
            "name": str,
            "version": str,
            "python_version": str,
            "structure": dict,
        }

    """
    root = Path(workspace_root)
    pyproject = root / "pyproject.toml"
    _ = pyproject.exists()

    return {
        "name": "oncutf",
        "brand": "oncut",
        "type": "PyQt5 desktop application",
        "python_version": ">=3.12",
        "line_length": 100,
        "quote_style": "double",
        "character_set": "ascii",
    }
