from modules.counter_module import CounterModule

def test_counter_default():
    data = {"type": "counter", "start": 1, "step": 1, "padding": 3}
    assert CounterModule.apply_from_data(data, None, index=0) == "001"
    assert CounterModule.apply_from_data(data, None, index=4) == "005"

def test_counter_step_padding():
    data = {"type": "counter", "start": 10, "step": 5, "padding": 2}
    assert CounterModule.apply_from_data(data, None, index=0) == "10"
    assert CounterModule.apply_from_data(data, None, index=2) == "20"
