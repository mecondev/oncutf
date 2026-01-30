"""Module: test_counter_module.py

Author: Michael Economou
Date: 2025-05-13

This module provides functionality for the oncutf batch file renaming application.
"""

from oncutf.modules.counter_module import CounterModule
from tests.mocks import MockFileItem


def test_counter_module_default():
    data = {"type": "counter"}
    file_item = MockFileItem(filename="a.txt")
    result = CounterModule.apply_from_data(data, file_item, index=0)
    assert result == "0001"


def test_counter_module_custom_start():
    data = {"type": "counter", "start": 5}
    file_item = MockFileItem(filename="b.txt")
    result = CounterModule.apply_from_data(data, file_item, index=0)
    assert result == "0005"


def test_counter_module_custom_padding():
    data = {"type": "counter", "start": 1, "padding": 2}
    file_item = MockFileItem(filename="c.txt")
    result = CounterModule.apply_from_data(data, file_item, index=9)
    assert result == "10"  # Corrected from "19"


def test_counter_module_step_and_index():
    data = {"type": "counter", "start": 1, "padding": 3, "step": 5}
    file_item = MockFileItem(filename="d.txt")
    result = CounterModule.apply_from_data(data, file_item, index=2)
    assert result == "011"


def test_counter_module_zero_padding():
    data = {"type": "counter", "start": 1, "padding": 0}
    file_item = MockFileItem(filename="e.txt")
    result = CounterModule.apply_from_data(data, file_item, index=3)
    assert result == "4"  # no padding expected


def test_counter_module_negative_start():
    data = {"type": "counter", "start": -5, "padding": 3}
    file_item = MockFileItem(filename="f.txt")
    result = CounterModule.apply_from_data(data, file_item, index=2)
    assert result == "-03"  # -5 + 2 → -3 padded


def test_counter_module_negative_index():
    data = {"type": "counter", "start": 10, "step": 2, "padding": 4}
    file_item = MockFileItem(filename="g.txt")
    result = CounterModule.apply_from_data(data, file_item, index=-1)
    assert result == "0008"  # 10 - 2


def test_counter_module_zero_step():
    data = {"type": "counter", "start": 7, "step": 0, "padding": 3}
    file_item = MockFileItem(filename="h.txt")
    result = CounterModule.apply_from_data(data, file_item, index=3)
    assert result == "007"  # always 7


def test_counter_module_invalid_input():
    data = {"type": "counter", "start": "bad", "padding": "xx", "step": None}
    file_item = MockFileItem(filename="i.txt")
    result = CounterModule.apply_from_data(data, file_item, index=0)
    assert result == "####"


def test_counter_module_negative_step():
    """Test counter with negative step (counting backwards)."""
    data = {"type": "counter", "start": 10, "step": -2, "padding": 3}
    file_item = MockFileItem(filename="neg.txt")
    # index=0: 10, index=1: 8, index=2: 6
    assert CounterModule.apply_from_data(data, file_item, index=0) == "010"
    assert CounterModule.apply_from_data(data, file_item, index=1) == "008"
    assert CounterModule.apply_from_data(data, file_item, index=2) == "006"
