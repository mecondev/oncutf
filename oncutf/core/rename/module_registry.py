"""oncutf.core.rename.module_registry.

Centralised registry mapping module type strings to their logic classes.

This is the single source of truth for which logic class handles each
rename module type.  Both ``UnifiedPreviewManager`` (via ``NameComposer``)
and the standalone helper functions use this registry instead of maintaining
their own parallel dictionaries or ``if/elif`` chains.

Author: Michael Economou
Date: 2026-03-08
"""

from __future__ import annotations

from typing import Any

from oncutf.modules.logic.counter_logic import CounterLogic
from oncutf.modules.logic.specified_text_logic import SpecifiedTextLogic
from oncutf.modules.logic.text_removal_logic import TextRemovalLogic
from oncutf.modules.metadata_module import MetadataModule
from oncutf.modules.original_name_module import OriginalNameModule

# Canonical mapping -- add new module types here.
MODULE_TYPE_MAP: dict[str, Any] = {
    "specified_text": SpecifiedTextLogic,
    "counter": CounterLogic,
    "metadata": MetadataModule,
    "original_name": OriginalNameModule,
    "remove_text_from_original_name": TextRemovalLogic,
}


def get_logic_class(module_type: str) -> Any | None:
    """Return the logic class for *module_type*, or ``None`` if unknown."""
    return MODULE_TYPE_MAP.get(module_type)
