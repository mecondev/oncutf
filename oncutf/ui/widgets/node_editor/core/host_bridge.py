"""Host bridge interfaces for embedding node graphs.

The core graph model can optionally communicate with a parent application
(host) through a bridge object. This enables integration (e.g., external
variables, services, IO) without importing Qt or application code in core.

The default bridge is a no-op.

Author:
    Michael Economou

Date:
    2025-12-14
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class NodeHostBridge(Protocol):
    """Interface for host-provided services/data."""

    def get(self, node_sid: str, key: str) -> object | None:
        """Retrieve a value from the host."""

    def set(self, node_sid: str, key: str, value: object) -> None:
        """Store a value in the host."""


class NullNodeHostBridge:
    """Default no-op host bridge."""

    def get(self, _node_sid: str, _key: str) -> object | None:
        return None

    def set(self, _node_sid: str, _key: str, _value: object) -> None:
        return
