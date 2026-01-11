"""Module: test_counter.py

Author: Michael Economou
Date: 2025-05-12

This module provides functionality for the oncutf batch file renaming application.
"""

import warnings

from oncutf.modules.counter_module import CounterModule

warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*coroutine.*never awaited")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)


def test_counter_default():
    data = {"type": "counter", "start": 1, "step": 1, "padding": 3}
    assert CounterModule.apply_from_data(data, None, index=0) == "001"
    assert CounterModule.apply_from_data(data, None, index=4) == "005"


def test_counter_step_padding():
    data = {"type": "counter", "start": 10, "step": 5, "padding": 2}
    assert CounterModule.apply_from_data(data, None, index=0) == "10"
    assert CounterModule.apply_from_data(data, None, index=2) == "20"
