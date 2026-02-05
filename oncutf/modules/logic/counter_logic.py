"""Pure counter logic (Qt-free).

Author: Michael Economou
Date: 2026-02-03

This module contains the pure business logic for counter-based renaming,
extracted from CounterModule to eliminate Qt dependencies in the core layer.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from oncutf.models.file_item import FileItem

from oncutf.models.counter_scope import CounterScope
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class CounterLogic:
    """Pure counter logic without Qt dependencies."""

    @staticmethod
    def apply_from_data(
        data: dict[str, Any],
        _file_item: "FileItem",
        index: int = 0,
        _metadata_cache: dict | None = None,
    ) -> str:
        """Applies counter-based formatting using the given config and index.

        Parameters
        ----------
        data : dict
            Configuration dictionary with keys:
                - 'type': 'counter'
                - 'start': int, the starting number
                - 'padding': int, number of digits (e.g. 4 -> 0001)
                - 'step': int, increment step
                - 'scope': str, counter scope ('global', 'per_folder', 'per_selection')
        file_item : FileItem
            The file to rename (not used by counter).
        index : int, optional
            The position of the file in the list (used for offsetting).
            NOTE: For PER_FOLDER scope, this should be the index within the folder group,
                  not the global index. The preview engine is responsible for providing
                  the correct index based on the scope.
        metadata_cache : dict, optional
            Not used in this module but accepted for API compatibility.

        Returns
        -------
        str
            The stringified counter value with proper padding.

        """
        try:
            start = int(data.get("start", 1))
            step = int(data.get("step", 1))
            padding = int(data.get("padding", 4))
            scope = data.get("scope", CounterScope.PER_FOLDER.value)

            value = start + index * step
            result = f"{value:0{padding}d}"
            logger.debug(
                "[CounterLogic] index: %d, value: %d, padded: %s, scope: %s",
                index,
                value,
                result,
                scope,
                extra={"dev_only": True},
            )
        except Exception:
            logger.exception("[CounterLogic] Failed to apply counter logic")
            return "####"
        else:
            return result

    @staticmethod
    def is_effective_data(_data: dict[str, Any]) -> bool:
        """Check if counter module data is effective (always True).

        Counter module is always active regardless of configuration.

        Args:
            _data: Module configuration dictionary (unused)

        Returns:
            Always True

        """
        return True
