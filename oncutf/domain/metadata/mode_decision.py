"""Module: mode_decision.py.

Author: Michael Economou
Date: 2026-04-17

Domain type for metadata loading mode decisions.

Replaces the previous ``tuple[bool, bool]`` return type used across the
metadata pipeline, which was a boolean-trap (callers had to remember
positional meaning at every site).

NamedTuple is used instead of a frozen dataclass so existing call sites
that perform tuple unpacking (``skip, ext = ...``) keep working without
any code change while also getting named access (``decision.use_extended``).
"""

from __future__ import annotations

from typing import NamedTuple


class MetadataModeDecision(NamedTuple):
    """Decision about how (or whether) to load metadata for a file batch.

    Semantics (matches the historical positional tuple):

    - ``skip_metadata=True``: do not perform any metadata scan.
    - ``skip_metadata=False, use_extended=False``: fast metadata scan.
    - ``skip_metadata=False, use_extended=True``: extended metadata scan.

    Attributes:
        skip_metadata: When True, no metadata scan should run.
        use_extended: When True (and skip_metadata is False), perform an
            extended metadata scan instead of the fast one.

    """

    skip_metadata: bool
    use_extended: bool
