"""Module: state_handler.py.

Author: Michael Economou
Date: 2026-01-02

State persistence handler for file tree view.

Manages saving and restoring expanded state, selection,
and scroll position for the tree view.
"""

from __future__ import annotations

import os
import platform
from pathlib import Path
from typing import TYPE_CHECKING

from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from PyQt5.QtCore import QModelIndex

    from oncutf.ui.widgets.file_tree.view import FileTreeView

logger = get_cached_logger(__name__)


class StateHandler:
    """Handles state persistence for the file tree view.

    Manages saving and restoring of expanded paths, selection,
    and scroll position. Supports incremental restoration to
    keep UI responsive during large tree operations.
    """

    def __init__(self, view: FileTreeView) -> None:
        """Initialize state handler.

        Args:
            view: The file tree view widget to handle state for

        """
        self._view = view
        self._pending_expand_paths: list[str] = []
        self._pending_select_path: str | None = None
        self._restore_in_progress = False

    def save_expanded_state(self) -> list[str]:
        """Save currently expanded paths.

        Returns:
            List of file paths that are currently expanded

        """
        expanded_paths: list[str] = []
        model = self._view.model()

        if not model or not hasattr(model, "filePath"):
            return expanded_paths

        visited_paths: set[str] = set()

        def collect_expanded(parent_index: QModelIndex, depth: int = 0) -> None:
            """Recursively collect expanded indices with protection against infinite loops."""
            if depth > 100:
                logger.warning(
                    "[StateHandler] Maximum recursion depth reached in save_expanded_state",
                )
                return

            row_count = model.rowCount(parent_index)
            for row in range(row_count):
                index = model.index(row, 0, parent_index)
                if not index.isValid():
                    continue

                if self._view.isExpanded(index):
                    path = model.filePath(index)
                    if path:
                        if path in visited_paths:
                            continue
                        visited_paths.add(path)
                        expanded_paths.append(path)
                        collect_expanded(index, depth + 1)

        root = "" if platform.system() == "Windows" else "/"
        root_index = model.index(root)
        collect_expanded(root_index, 0)

        logger.debug(
            "[StateHandler] Saved %d expanded paths",
            len(expanded_paths),
            extra={"dev_only": True},
        )
        return expanded_paths

    def restore_expanded_state(self, paths: list[str]) -> None:
        """Restore expanded state from saved paths.

        Args:
            paths: List of file paths to expand

        """
        model = self._view.model()
        if not model or not hasattr(model, "index"):
            return

        if len(paths) > 500:
            logger.warning(
                "[StateHandler] Too many expanded paths (%d), limiting to 500",
                len(paths),
            )
            paths = paths[:500]

        # Build complete set of paths including all parent directories
        all_paths_to_expand: set[str] = set()
        root = "" if platform.system() == "Windows" else "/"

        for path in paths:
            if not path or not Path(path).exists():
                continue

            all_paths_to_expand.add(path)
            parent = str(Path(path).parent)
            while parent and parent != root:
                all_paths_to_expand.add(parent)
                parent = str(Path(parent).parent)
            if path:
                all_paths_to_expand.add(root)

        # Sort by depth (shallow to deep) to ensure parents are expanded first
        sorted_paths = sorted(all_paths_to_expand, key=lambda p: p.count(os.sep))

        restored_count = 0
        max_operations = 1000
        for i, path in enumerate(sorted_paths):
            if i >= max_operations:
                logger.warning(
                    "[StateHandler] Reached maximum expansion operations (%d), stopping",
                    max_operations,
                )
                break

            try:
                index = model.index(path)
                if index.isValid():
                    self._view.setExpanded(index, True)
                    restored_count += 1
            except Exception as e:
                logger.debug(
                    "[StateHandler] Failed to expand path %s: %s",
                    path,
                    e,
                    extra={"dev_only": True},
                )

        logger.debug(
            "[StateHandler] Restored %d/%d expanded paths (including %d parents)",
            restored_count,
            len(paths),
            len(all_paths_to_expand) - len(paths),
            extra={"dev_only": True},
        )

    def restore_tree_state(
        self, expanded_paths: list[str], selected_path: str, scroll_position: int
    ) -> None:
        """Restore complete tree state: expanded paths, selection, and scroll position.

        Args:
            expanded_paths: List of paths that were expanded
            selected_path: Path that was selected
            scroll_position: Vertical scroll position

        """
        self.restore_expanded_state(expanded_paths)

        if selected_path and Path(selected_path).exists():
            self._view.select_path(selected_path)
            logger.debug(
                "[StateHandler] Restored selection: %s",
                selected_path,
                extra={"dev_only": True},
            )

        if scroll_position > 0:
            self._view.verticalScrollBar().setValue(scroll_position)
            logger.debug(
                "[StateHandler] Restored scroll position: %d",
                scroll_position,
                extra={"dev_only": True},
            )

    def start_incremental_restore(
        self, expanded_paths: list[str], selected_path: str | None
    ) -> None:
        """Start incremental restoration of tree state (non-blocking).

        Args:
            expanded_paths: Paths to expand incrementally
            selected_path: Path to select after expansion complete

        """
        if self._restore_in_progress:
            from oncutf.utils.shared.timer_manager import get_timer_manager

            get_timer_manager().cancel("tree_incremental_restore")

        root = "" if platform.system() == "Windows" else "/"

        valid_paths = [path for path in expanded_paths if path and Path(path).exists()]

        # Build parent paths and sort by depth
        all_paths_to_expand: set[str] = set()
        for path in valid_paths:
            all_paths_to_expand.add(path)
            parent = str(Path(path).parent)
            while parent and parent != root:
                all_paths_to_expand.add(parent)
                parent = str(Path(parent).parent)

        self._pending_expand_paths = sorted(all_paths_to_expand, key=lambda p: p.count(os.sep))
        self._pending_select_path = selected_path
        self._restore_in_progress = True

        logger.debug(
            "[StateHandler] Starting incremental restore of %d paths",
            len(self._pending_expand_paths),
            extra={"dev_only": True},
        )

        self._process_next_restore_batch()

    def _process_next_restore_batch(self) -> None:
        """Process next batch of paths to expand (called via timer)."""
        if not self._restore_in_progress or not self._pending_expand_paths:
            self._restore_in_progress = False
            if self._pending_select_path and Path(self._pending_select_path).exists():
                try:
                    self._view.select_path(self._pending_select_path)
                    logger.debug(
                        "[StateHandler] Restored selection: %s",
                        self._pending_select_path,
                        extra={"dev_only": True},
                    )
                except Exception as e:
                    logger.debug(
                        "[StateHandler] Failed to restore selection: %s",
                        e,
                        extra={"dev_only": True},
                    )
            self._pending_select_path = None
            logger.debug(
                "[StateHandler] Incremental restore complete",
                extra={"dev_only": True},
            )
            return

        # Take next batch (10 paths at a time)
        batch_size = 10
        batch = self._pending_expand_paths[:batch_size]
        self._pending_expand_paths = self._pending_expand_paths[batch_size:]

        model = self._view.model()
        if model:
            for path in batch:
                try:
                    index = model.index(path)
                    if index.isValid():
                        self._view.setExpanded(index, True)
                except Exception as e:
                    logger.debug(
                        "[StateHandler] Failed to expand %s: %s",
                        path,
                        e,
                        extra={"dev_only": True},
                    )

        # Schedule next batch
        from oncutf.utils.shared.timer_manager import TimerType, get_timer_manager

        get_timer_manager().schedule(
            self._process_next_restore_batch,
            delay=20,
            timer_type=TimerType.UI_UPDATE,
            timer_id="tree_incremental_restore",
            consolidate=False,
        )

    def save_to_config(self) -> None:
        """Save current expanded state to window config."""
        parent = self._view.parent()
        while parent is not None:
            if hasattr(parent, "window_config_manager"):
                parent.window_config_manager.save_window_config()
                logger.debug(
                    "[StateHandler] Expanded state saved to config",
                    extra={"dev_only": True},
                )
                return
            parent = parent.parent() if hasattr(parent, "parent") else None

        logger.debug(
            "[StateHandler] No window_config_manager found, state not saved",
            extra={"dev_only": True},
        )
