"""Module: test_rename_logic.py

Author: Michael Economou
Date: 2025-05-12

This module provides functionality for the oncutf batch file renaming application.
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from oncutf.utils.naming.rename_logic import build_rename_plan, execute_rename_plan


class MockFile:
    def __init__(self, filename):
        self.filename = filename


# ---------- Fixtures ----------


@pytest.fixture
def temp_dir():
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path)


# ---------- Tests ----------


def test_build_plan_no_conflicts(temp_dir):
    # Setup: files to rename to unique names
    (Path(temp_dir) / "a.txt").touch()
    files = [MockFile("a.txt")]
    pairs = [("a.txt", "b.txt")]

    plan = build_rename_plan(files, pairs, temp_dir)

    assert len(plan) == 1
    assert plan[0]["conflict"] is False
    assert plan[0]["src"] == "a.txt"
    assert plan[0]["dst"] == "b.txt"


def test_build_plan_with_conflict(temp_dir):
    # Setup: destination already exists
    (Path(temp_dir) / "a.txt").touch()
    (Path(temp_dir) / "b.txt").touch()
    files = [MockFile("a.txt")]
    pairs = [("a.txt", "b.txt")]

    plan = build_rename_plan(files, pairs, temp_dir)

    assert len(plan) == 1
    assert plan[0]["conflict"] is True


def test_execute_rename_plan(temp_dir):
    # Setup: rename a.txt -> b.txt
    src_path = Path(temp_dir) / "a.txt"
    src_path.write_text("hello")

    files = [MockFile("a.txt")]
    pairs = [("a.txt", "b.txt")]
    plan = build_rename_plan(files, pairs, temp_dir)

    for entry in plan:
        entry["action"] = "rename"

    count = execute_rename_plan(plan)

    assert count == 1
    assert (Path(temp_dir) / "b.txt").exists()
    assert not src_path.exists()


def test_execute_rename_skips_invalid_action(temp_dir):
    (Path(temp_dir) / "a.txt").touch()
    files = [MockFile("a.txt")]
    pairs = [("a.txt", "b.txt")]
    plan = build_rename_plan(files, pairs, temp_dir)

    for entry in plan:
        entry["action"] = "skip"

    count = execute_rename_plan(plan)

    assert count == 0
    assert (Path(temp_dir) / "a.txt").exists()
    assert not (Path(temp_dir) / "b.txt").exists()
