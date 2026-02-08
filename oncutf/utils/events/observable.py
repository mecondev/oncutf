"""Module: observable.py.

Author: Michael Economou
Date: 2025-02-03

Observable - Pure Python Observer pattern implementation.

Provides Qt signal-like functionality without Qt dependency:
- Signal descriptor for defining events
- Observable base class for state management
- Connect/disconnect/emit interface
- Thread-safe signal emission

Replaces QObject/pyqtSignal in non-UI layers (core, app, infra).
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any
from weakref import WeakSet

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)

__all__ = ["Observable", "Signal", "SignalInstance"]


class Signal:
    """Descriptor for defining observable signals.

    Usage:
        class MyClass(Observable):
            value_changed = Signal(int)  # Signal with int argument
            done = Signal()  # Signal with no arguments

        obj = MyClass()
        obj.value_changed.connect(callback)
        obj.value_changed.emit(42)
    """

    def __init__(self, *arg_types: type):
        """Initialize signal with expected argument types.

        Args:
            *arg_types: Type hints for signal arguments (for documentation only)

        """
        self.arg_types = arg_types
        self.name = ""  # Set by __set_name__
        self._instances: WeakSet[Observable] = WeakSet()

    def __set_name__(self, owner: type, name: str) -> None:
        """Called when signal is assigned to class attribute."""
        self.name = name

    def __get__(self, obj: Observable | None, _objtype: type | None = None) -> SignalInstance:
        """Get signal instance for object."""
        if obj is None:
            return self  # type: ignore[return-value]

        # Create signal instance for this object if not exists
        attr_name = f"_signal_{self.name}"
        if not hasattr(obj, attr_name):
            signal_instance = SignalInstance(self.name, self.arg_types)
            setattr(obj, attr_name, signal_instance)

        return getattr(obj, attr_name)


class SignalInstance:
    """Instance of a signal for a specific object."""

    def __init__(self, name: str, arg_types: tuple[type, ...]):
        """Initialize signal instance.

        Args:
            name: Signal name (for debugging)
            arg_types: Expected argument types

        """
        self.name = name
        self.arg_types = arg_types
        self._callbacks: list[Callable[..., Any]] = []
        self._lock = threading.Lock()

    def connect(self, callback: Callable[..., Any], _connection_type: Any = None) -> None:
        """Connect callback to signal.

        Args:
            callback: Function to call when signal is emitted
            connection_type: Optional Qt connection type (ignored for pure Python signals,
                kept for API compatibility with Qt signals)

        """
        with self._lock:
            if callback not in self._callbacks:
                self._callbacks.append(callback)
                callback_name = getattr(callback, "__name__", repr(callback))
                logger.debug(
                    "Signal connected: %s -> %s",
                    self.name,
                    callback_name,
                    extra={"dev_only": True},
                )

    def disconnect(self, callback: Callable[..., Any] | None = None) -> None:
        """Disconnect callback from signal.

        Args:
            callback: Callback to remove. If None, removes all callbacks.

        """
        with self._lock:
            if callback is None:
                count = len(self._callbacks)
                self._callbacks.clear()
                logger.debug(
                    "All callbacks disconnected from %s (count: %d)",
                    self.name,
                    count,
                    extra={"dev_only": True},
                )
            elif callback in self._callbacks:
                self._callbacks.remove(callback)
                logger.debug(
                    "Signal disconnected: %s -> %s",
                    self.name,
                    callback.__name__,
                    extra={"dev_only": True},
                )

    def emit(self, *args: Any) -> None:
        """Emit signal with arguments.

        Args:
            *args: Arguments to pass to connected callbacks

        """
        # Snapshot callbacks under lock
        with self._lock:
            callbacks = self._callbacks.copy()

        # Call outside lock to avoid deadlocks
        for callback in callbacks:
            try:
                callback(*args)
            except Exception:
                logger.exception("Error in signal callback: %s -> %s", self.name, callback.__name__)


class Observable:
    """Base class for objects with observable signals.

    Provides Qt signal-like functionality without Qt dependency.
    Use Signal descriptor to define events:

        class Counter(Observable):
            value_changed = Signal(int)

            def increment(self):
                self._value += 1
                self.value_changed.emit(self._value)
    """

    def __init__(self) -> None:
        """Initialize observable."""
        super().__init__()
