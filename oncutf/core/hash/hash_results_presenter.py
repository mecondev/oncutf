"""Hash Results Presentation Layer.

Author: Michael Economou
Date: 2026-01-04

Handles the presentation of hash operation results to the user through dialogs and status updates.
Separated from business logic for better maintainability.

Uses ResultsDisplayPort for UI decoupling (Phase 5).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QWidget

    from oncutf.app.ports.results_display import ResultsDisplayPort
    from oncutf.models.file_item import FileItem

from oncutf.app.services.user_interaction import show_info_message
from oncutf.config import STATUS_COLORS
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class HashResultsPresenter:
    """Presents hash operation results through UI dialogs and status updates.

    This class is responsible for:
    - Showing duplicate detection results
    - Displaying external folder comparison results
    - Presenting checksum calculation results
    - Updating application status based on results
    """

    def __init__(
        self,
        parent_window: QWidget,
        results_display: ResultsDisplayPort | None = None,
    ) -> None:
        """Initialize the results presenter.

        Args:
            parent_window: Reference to the main window for status updates
            results_display: Port for showing results dialogs (injected)

        """
        self.parent_window: Any = parent_window
        self._results_display = results_display

    @property
    def results_display(self) -> ResultsDisplayPort:
        """Lazy-load results display adapter from ApplicationContext."""
        if self._results_display is None:
            from oncutf.ui.adapters.application_context import get_app_context

            context = get_app_context()
            self._results_display = context.get_manager("results_display")
            if self._results_display is None:
                raise RuntimeError("ResultsDisplayPort not registered in ApplicationContext")
        return self._results_display

    def show_duplicate_results(
        self, duplicates: dict[str, list[FileItem]], scope: str
    ) -> None:
        """Show duplicate detection results to the user.

        Args:
            duplicates: Dictionary with hash as key and list of duplicate FileItem objects as value
            scope: Either "selected" or "all" for display purposes

        """
        if not duplicates:
            show_info_message(
                self.parent_window,
                "Duplicate Detection Results",
                f"No duplicates found in {scope} files.",
            )
            if hasattr(self.parent_window, "set_status"):
                self.parent_window.set_status(
                    f"No duplicates found in {scope} files",
                    color=STATUS_COLORS["operation_success"],
                    auto_reset=True,
                )
            return

        # Build results message
        duplicate_count = sum(len(files) for files in duplicates.values())
        duplicate_groups = len(duplicates)

        message_lines = [
            f"Found {duplicate_count} duplicate files in {duplicate_groups} groups:\n"
        ]

        for i, (hash_val, files) in enumerate(duplicates.items(), 1):
            message_lines.append(f"Group {i} ({len(files)} files):")
            for file_item in files:
                message_lines.append(f"  • {file_item.filename}")
            message_lines.append(f"  Hash: {hash_val[:16]}...")
            message_lines.append("")

        # Show results dialog
        show_info_message(
            self.parent_window, "Duplicate Detection Results", "\n".join(message_lines)
        )

        # Update status
        if hasattr(self.parent_window, "set_status"):
            self.parent_window.set_status(
                f"Found {duplicate_count} duplicates in {duplicate_groups} groups",
                color=STATUS_COLORS["duplicate_found"],
                auto_reset=True,
            )

        logger.info(
            "[HashResultsPresenter] Showed duplicate results: %d files in %d groups",
            duplicate_count,
            duplicate_groups,
        )

    def show_comparison_results(
        self, results: dict[str, Any], external_folder: str
    ) -> None:
        """Show external folder comparison results to the user.

        Args:
            results: Dictionary with comparison results
            external_folder: Path to the external folder that was compared

        """
        if not results:
            show_info_message(
                self.parent_window,
                "External Comparison Results",
                f"No matching files found in:\n{external_folder}",
            )
            if hasattr(self.parent_window, "set_status"):
                self.parent_window.set_status(
                    "No matching files found",
                    color=STATUS_COLORS["no_action"],
                    auto_reset=True,
                )
            return

        # Count matches and differences
        matches = sum(1 for r in results.values() if r["is_same"])
        differences = len(results) - matches

        # Build results message
        message_lines = [
            f"Comparison with: {external_folder}\n",
            f"Files compared: {len(results)}",
            f"Identical: {matches}",
            f"Different: {differences}\n",
        ]

        if differences > 0:
            message_lines.append("Different files:")
            for filename, data in results.items():
                if not data["is_same"]:
                    message_lines.append(f"  • {filename}")

        if matches > 0:
            message_lines.append("\nIdentical files:")
            for filename, data in results.items():
                if data["is_same"]:
                    message_lines.append(f"  • {filename}")

        # Show results dialog
        show_info_message(
            self.parent_window, "External Comparison Results", "\n".join(message_lines)
        )

        # Update status
        if hasattr(self.parent_window, "set_status"):
            if differences > 0:
                self.parent_window.set_status(
                    f"Found {differences} different files, {matches} identical",
                    color=STATUS_COLORS["alert_notice"],
                    auto_reset=True,
                )
            else:
                self.parent_window.set_status(
                    f"All {matches} files are identical",
                    color=STATUS_COLORS["operation_success"],
                    auto_reset=True,
                )

        logger.info(
            "[HashResultsPresenter] Showed comparison results: %d identical, %d different",
            matches,
            differences,
        )

    def show_hash_results(
        self, hash_results: dict[str, dict[str, str]], was_cancelled: bool = False
    ) -> None:
        """Show checksum calculation results to the user.

        Args:
            hash_results: Dictionary with filename as key and hash data as value
            was_cancelled: Whether the operation was cancelled (for partial results)

        """
        if not hash_results:
            if was_cancelled:
                show_info_message(
                    self.parent_window,
                    "Checksum Results",
                    "Operation was cancelled before any checksums could be calculated.",
                )
            else:
                show_info_message(
                    self.parent_window,
                    "Checksum Results",
                    "No checksums could be calculated.",
                )
            if hasattr(self.parent_window, "set_status"):
                status_msg = (
                    "Operation cancelled" if was_cancelled else "No checksums calculated"
                )
                self.parent_window.set_status(
                    status_msg, color=STATUS_COLORS["no_action"], auto_reset=True
                )
            return

        # Show results in the new table dialog
        self.results_display.show_hash_results(
            parent=self.parent_window,
            hash_results=hash_results,
            was_cancelled=was_cancelled,
        )

        # Update status
        if hasattr(self.parent_window, "set_status"):
            if was_cancelled:
                self.parent_window.set_status(
                    f"Calculated checksums for {len(hash_results)} files (cancelled)",
                    color=STATUS_COLORS["hash_success"],
                    auto_reset=True,
                )
            else:
                self.parent_window.set_status(
                    f"Calculated checksums for {len(hash_results)} files",
                    color=STATUS_COLORS["hash_success"],
                    auto_reset=True,
                )

        logger.info(
            "[HashResultsPresenter] Showed checksum results for %d files%s",
            len(hash_results),
            " (cancelled)" if was_cancelled else "",
        )
