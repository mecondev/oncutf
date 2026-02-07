"""Menu Dismiss Guard - prevents selection clearing when dismissing context menu.

Author: Michael Economou
Date: 2026-02-07

Temporarily disables selection mode to prevent selection loss when menu closes.
"""

from typing import TYPE_CHECKING

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QAbstractItemView

from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from PyQt5.QtCore import QItemSelection
    from PyQt5.QtWidgets import QListView

logger = get_cached_logger(__name__)


class MenuDismissGuard:
    """Prevents selection clearing when dismissing context menu with click.

    When a context menu is open and user clicks outside to dismiss it,
    Qt's default behavior clears the selection. This guard disables
    selection changes temporarily to prevent this.

    Usage:
        saved_selection = selection_model.selection()
        guard = MenuDismissGuard.install(list_view, saved_selection)
        try:
            menu.exec_(global_position)  # Blocks here
        finally:
            guard.uninstall()
    """

    def __init__(self, list_view: "QListView", saved_selection: "QItemSelection"):
        """Initialize guard.

        Args:
            list_view: QListView to protect
            saved_selection: Selection to restore if cleared

        """
        self._list_view = list_view
        self._saved_selection = saved_selection
        self._original_selection_mode = list_view.selectionMode()

    def activate(self) -> None:
        """Activate guard by disabling selection changes."""
        # Set to NoSelection to prevent any selection changes
        self._list_view.setSelectionMode(QAbstractItemView.NoSelection)
        logger.debug("[MenuDismissGuard] Selection mode disabled")

    def deactivate(self) -> None:
        """Deactivate guard and restore selection."""
        # Restore original selection mode
        self._list_view.setSelectionMode(self._original_selection_mode)

        # Restore selection after a brief delay (ensure mode is applied first)
        QTimer.singleShot(0, self._restore_selection)

    def _restore_selection(self) -> None:
        """Restore saved selection."""
        selection_model = self._list_view.selectionModel()
        if not selection_model:
            return

        from PyQt5.QtCore import QItemSelectionModel

        # Restore selection
        if not self._saved_selection.isEmpty():
            selection_model.select(self._saved_selection, QItemSelectionModel.ClearAndSelect)
            logger.debug(
                "[MenuDismissGuard] Selection restored (%d items)",
                len(self._saved_selection.indexes()),
            )

    @classmethod
    def install(
        cls, list_view: "QListView", saved_selection: "QItemSelection"
    ) -> "MenuDismissGuard":
        """Install guard (disables selection mode).

        Args:
            list_view: QListView to protect
            saved_selection: Selection to restore after menu closes

        Returns:
            Guard instance (must call uninstall when done)

        """
        guard = cls(list_view, saved_selection)
        guard.activate()
        logger.debug("[MenuDismissGuard] Installed")
        return guard

    def uninstall(self) -> None:
        """Remove guard and restore selection mode."""
        self.deactivate()
        logger.debug("[MenuDismissGuard] Uninstalled")
