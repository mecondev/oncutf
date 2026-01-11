"""Module: test_rename_logic.py

Author: Michael Economou
Date: 2025-05-12

This module provides functionality for the oncutf batch file renaming application.
"""

import os
import shutil
import tempfile
import warnings

import pytest

from oncutf.utils.naming.rename_logic import build_rename_plan, execute_rename_plan

warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*coroutine.*never awaited")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)


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
    open(os.path.join(temp_dir, "a.txt"), "w").close()
    files = [MockFile("a.txt")]
    pairs = [("a.txt", "b.txt")]

    plan = build_rename_plan(files, pairs, temp_dir)

    assert len(plan) == 1
    assert plan[0]["conflict"] is False
    assert plan[0]["src"] == "a.txt"
    assert plan[0]["dst"] == "b.txt"


def test_build_plan_with_conflict(temp_dir):
    # Setup: destination already exists
    open(os.path.join(temp_dir, "a.txt"), "w").close()
    open(os.path.join(temp_dir, "b.txt"), "w").close()
    files = [MockFile("a.txt")]
    pairs = [("a.txt", "b.txt")]

    plan = build_rename_plan(files, pairs, temp_dir)

    assert len(plan) == 1
    assert plan[0]["conflict"] is True


def test_execute_rename_plan(temp_dir):
    # Setup: rename a.txt -> b.txt
    src_path = os.path.join(temp_dir, "a.txt")
    with open(src_path, "w") as f:
        f.write("hello")

    files = [MockFile("a.txt")]
    pairs = [("a.txt", "b.txt")]
    plan = build_rename_plan(files, pairs, temp_dir)

    for entry in plan:
        entry["action"] = "rename"

    count = execute_rename_plan(plan)

    assert count == 1
    assert os.path.exists(os.path.join(temp_dir, "b.txt"))
    assert not os.path.exists(src_path)


def test_execute_rename_skips_invalid_action(temp_dir):
    open(os.path.join(temp_dir, "a.txt"), "w").close()
    files = [MockFile("a.txt")]
    pairs = [("a.txt", "b.txt")]
    plan = build_rename_plan(files, pairs, temp_dir)

    for entry in plan:
        entry["action"] = "skip"

    count = execute_rename_plan(plan)

    assert count == 0
    assert os.path.exists(os.path.join(temp_dir, "a.txt"))
    assert not os.path.exists(os.path.join(temp_dir, "b.txt"))
