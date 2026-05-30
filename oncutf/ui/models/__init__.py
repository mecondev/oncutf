"""oncutf.ui.models package.

Qt-bound model classes (QAbstractTableModel subclasses and related Qt model
machinery). These depend on PyQt5 and therefore live under the UI layer,
distinct from the pure data entities in ``oncutf.models``.

Author: Michael Economou
Date: 2026-05-30
"""

from oncutf.ui.models.results_table_model import ResultsTableModel

__all__ = ["ResultsTableModel"]
