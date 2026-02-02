"""Module: layout_calculators.py.

Author: Michael Economou
Date: 2026-01-13

Utility functions for calculating layout dimensions from ratios and constraints.
"""

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


def calculate_splitter_sizes_from_ratios(
    ratios: list[float], total_width: int, min_sizes: list[int] | None = None
) -> list[int]:
    """Calculate splitter panel sizes from ratios.

    Args:
        ratios: List of ratios (must sum to approximately 1.0)
        total_width: Total available width in pixels
        min_sizes: Optional minimum sizes for each panel

    Returns:
        List of panel sizes in pixels

    """
    if not ratios:
        return []

    if min_sizes and len(min_sizes) != len(ratios):
        logger.warning("min_sizes length mismatch with ratios, ignoring min_sizes")
        min_sizes = None

    sizes = [int(total_width * ratio) for ratio in ratios]

    if min_sizes:
        for i, min_size in enumerate(min_sizes):
            if sizes[i] < min_size:
                deficit = min_size - sizes[i]
                sizes[i] = min_size

                redistributed = 0
                for j in range(len(sizes)):
                    if j != i and sizes[j] > (min_sizes[j] if min_sizes else 0):
                        reduction = min(
                            deficit - redistributed,
                            sizes[j] - (min_sizes[j] if min_sizes else 0),
                        )
                        sizes[j] -= reduction
                        redistributed += reduction
                        if redistributed >= deficit:
                            break

    adjustment = total_width - sum(sizes)
    if adjustment != 0:
        sizes[-1] += adjustment

    return sizes


def calculate_column_width_from_ratio(
    ratio: float, panel_width: int, min_width: int = 50, max_width: int | None = None
) -> int:
    """Calculate column width from ratio.

    Args:
        ratio: Width ratio (0.0 to 1.0)
        panel_width: Total panel width in pixels
        min_width: Minimum allowed width
        max_width: Maximum allowed width (optional)

    Returns:
        Column width in pixels

    """
    width = int(panel_width * ratio)
    width = max(width, min_width)

    if max_width:
        width = min(width, max_width)

    return width


def calculate_dynamic_filename_width(
    panel_width: int,
    fixed_column_widths: dict[str, int],
    min_width: int = 80,
    reserved_space: int = 50,
) -> int:
    """Calculate filename column width dynamically.

    Args:
        panel_width: Total panel width in pixels
        fixed_column_widths: Dictionary of fixed column widths
        min_width: Minimum filename width
        reserved_space: Reserved space for scrollbars/margins

    Returns:
        Filename column width in pixels

    """
    fixed_total = sum(fixed_column_widths.values())
    available = panel_width - fixed_total - reserved_space
    return max(available, min_width)


def get_metadata_tree_widths_from_ratios(
    panel_width: int,
    ratios: dict[str, float],
    min_widths: dict[str, int],
    max_widths: dict[str, int] | None = None,
) -> dict[str, int]:
    """Calculate metadata tree column widths from ratios.

    Args:
        panel_width: Total panel width in pixels
        ratios: Dictionary with 'tag' and 'value' ratios
        min_widths: Minimum widths for each column
        max_widths: Maximum widths for each column (optional)

    Returns:
        Dictionary with calculated widths

    """
    widths = {}

    for column_name, ratio in ratios.items():
        min_width = min_widths.get(column_name, 50)
        max_width = max_widths.get(column_name) if max_widths else None

        widths[column_name] = calculate_column_width_from_ratio(
            ratio, panel_width, min_width, max_width
        )

    return widths
