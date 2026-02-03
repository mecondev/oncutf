"""Module: __init__.py.

Author: Michael Economou
Date: 2025-02-03

Infrastructure - Event System.

Pure Python event/signal implementation for decoupling observers from state changes.
This replaces PyQt5 QObject/pyqtSignal in non-UI layers.
"""

from oncutf.utils.events.observable import Observable, Signal

__all__ = ["Observable", "Signal"]
