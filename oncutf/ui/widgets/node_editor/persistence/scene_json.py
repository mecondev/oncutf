"""JSON persistence adapter for Scene snapshots.

This module intentionally lives outside `node_editor.core` so that core
remains IO-free. It reads/writes Scene snapshots produced by
`Scene.serialize_snapshot()` / consumed by `Scene.deserialize_snapshot()`.

Author:
    Michael Economou

Date:
    2025-12-14
"""

from __future__ import annotations

import json
import os
from typing import Any

from oncutf.ui.widgets.node_editor.utils.helpers import dump_exception


class InvalidFileError(Exception):
    """Raised when file loading fails due to invalid format or content."""


def read_snapshot_from_file(filename: str) -> dict[str, Any]:
    """Read a snapshot dict from disk."""
    with open(filename) as file:
        raw_data = file.read()

    try:
        data = json.loads(raw_data)
        if not isinstance(data, dict):
            raise InvalidFileError(f"{os.path.basename(filename)} does not contain a JSON object")
        return data
    except json.JSONDecodeError:
        raise InvalidFileError(f"{os.path.basename(filename)} is not a valid JSON file") from None


def write_snapshot_to_file(snapshot: dict[str, Any], filename: str) -> None:
    """Write a snapshot dict to disk."""
    with open(filename, "w") as file:
        file.write(json.dumps(snapshot, indent=4))


def save_scene_to_file(scene: Any, filename: str) -> None:
    """Persist a Scene via its snapshot API."""
    snapshot = scene.serialize_snapshot()
    write_snapshot_to_file(snapshot, filename)
    scene.has_been_modified = False
    scene.filename = filename


def load_scene_from_file(scene: Any, filename: str) -> None:
    """Load a Scene via its snapshot API."""
    data = read_snapshot_from_file(filename)

    try:
        scene.filename = filename
        scene.deserialize_snapshot(data)
        scene.has_been_modified = False
    except Exception as e:
        dump_exception(e)
        raise
