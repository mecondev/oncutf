"""Pure business logic for rename modules (Qt-free).

Author: Michael Economou
Date: 2026-02-03

This package contains the pure logic implementations of rename modules,
separated from their Qt UI widgets. These functions can be used by the
core layer without Qt dependencies.
"""

from oncutf.modules.logic.counter_logic import CounterLogic
from oncutf.modules.logic.specified_text_logic import SpecifiedTextLogic
from oncutf.modules.logic.text_removal_logic import TextRemovalLogic

__all__ = ["CounterLogic", "SpecifiedTextLogic", "TextRemovalLogic"]
