"""Module: metadata_mode_indicator.py.

Author: Michael Economou
Date: 2026-04-18

Status-bar indicator showing which metadata scan mode would run if the
user invoked a load/drop action right now. Reflects keyboard modifiers
in real time:

- No modifiers     -> "Metadata: Skip"      (skip_metadata=True)
- Ctrl             -> "Metadata: Fast"      (skip=False, extended=False)
- Ctrl+Shift       -> "Metadata: Extended"  (skip=False, extended=True)

Driven by ``MetadataShortcutHandler.determine_metadata_mode``, which
returns a :class:`MetadataModeDecision` (see Phase 5).
"""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QWidget

from oncutf.config import STATUS_COLORS
from oncutf.domain.metadata import MetadataModeDecision


class MetadataModeIndicator(QLabel):
    """Compact status-bar label that shows the current metadata scan mode.

    The label is purely presentational; callers feed it either a fully
    resolved :class:`MetadataModeDecision` or the current Qt modifier
    state.
    """

    _PREFIX = "Metadata: "

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the indicator with the default 'Skip' state."""
        super().__init__(parent)
        self.setObjectName("metadataModeIndicator")
        self.setTextFormat(Qt.RichText)
        # Tight padding so it sits naturally in the controls row.
        self.setContentsMargins(8, 0, 8, 0)
        self._current: MetadataModeDecision | None = None
        self.set_decision(MetadataModeDecision(skip_metadata=True, use_extended=False))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_decision(self, decision: MetadataModeDecision) -> None:
        """Update the indicator to reflect ``decision``.

        Idempotent: re-rendering only happens when the decision changes,
        which keeps the label cheap to call from a high-frequency
        keyboard event filter.
        """
        if self._current == decision:
            return
        self._current = decision

        label, color_key = self._format(decision)
        color = STATUS_COLORS.get(color_key, "")
        if color:
            self.setText(f"<span style='color:{color};'>{self._PREFIX}{label}</span>")
        else:
            self.setText(f"{self._PREFIX}{label}")
        self.setToolTip(self._tooltip(decision))

    def update_from_modifiers(self, modifiers: int) -> None:
        """Refresh the indicator from raw Qt keyboard modifier flags.

        The mapping mirrors :class:`MetadataShortcutHandler` exactly so
        the status bar never disagrees with what an actual load action
        would do.
        """
        ctrl = bool(modifiers & Qt.ControlModifier)
        shift = bool(modifiers & Qt.ShiftModifier)
        self.set_decision(
            MetadataModeDecision(
                skip_metadata=not ctrl,
                use_extended=ctrl and shift,
            )
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _format(decision: MetadataModeDecision) -> tuple[str, str]:
        """Return (label, STATUS_COLORS key) for ``decision``."""
        if decision.skip_metadata:
            return "Skip", "metadata_skipped"
        if decision.use_extended:
            return "Extended", "metadata_extended"
        return "Fast", "metadata_basic"

    @staticmethod
    def _tooltip(decision: MetadataModeDecision) -> str:
        """Explain what each state means and which modifier triggers it."""
        if decision.skip_metadata:
            return "No metadata scan on next load. Hold Ctrl for Fast, Ctrl+Shift for Extended."
        if decision.use_extended:
            return "Ctrl+Shift held: extended metadata scan on next load."
        return "Ctrl held: fast metadata scan on next load. Add Shift for Extended."
