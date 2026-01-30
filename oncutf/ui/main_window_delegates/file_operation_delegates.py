"""File operation delegates for MainWindow.

Author: Michael Economou
Date: 2026-01-10
"""


class FileOperationDelegates:
    """Delegate class for file loading and browsing operations.

    All methods delegate to file_load_controller or file_load_manager.
    """

    def load_files_from_folder(self, folder_path: str, force: bool = False) -> None:
        """Load files from folder via Application Service."""
        self.app_service.load_files_from_folder(folder_path, force)

    def load_files_from_paths(self, file_paths: list[str], *, clear: bool = True) -> None:
        """Load files from paths via FileLoadController."""
        from oncutf.utils.logging.logger_factory import get_cached_logger

        logger = get_cached_logger(__name__)

        result = self.file_load_controller.load_files(file_paths, clear=clear)
        logger.debug(
            "[FileLoadController] load_files result: %s",
            result,
            extra={"dev_only": True},
        )

    def load_files_from_dropped_items(self, paths: list[str], modifiers=None) -> None:
        """Load files from dropped items via FileLoadController."""
        import time

        from PyQt5.QtCore import Qt

        from oncutf.utils.logging.logger_factory import get_cached_logger

        logger = get_cached_logger(__name__)

        if modifiers is None:
            modifiers = Qt.NoModifier

        t0 = time.time()
        logger.debug(
            "[DROP-MAIN] load_files_from_dropped_items START with %d paths",
            len(paths),
            extra={"dev_only": True},
        )

        result = self.file_load_controller.handle_drop(paths, modifiers)

        logger.debug(
            "[DROP-MAIN] handle_drop returned at +%.3fms, success=%s",
            (time.time() - t0) * 1000,
            result.get("success"),
            extra={"dev_only": True},
        )
        logger.debug(
            "[FileLoadController] handle_drop result: %s",
            result,
            extra={"dev_only": True},
        )

    def load_single_item_from_drop(self, path: str, modifiers=None) -> None:
        """Load single item from drop via FileLoadController."""
        import time

        from PyQt5.QtCore import Qt

        from oncutf.utils.cursor_helper import wait_cursor
        from oncutf.utils.logging.logger_factory import get_cached_logger

        logger = get_cached_logger(__name__)

        if modifiers is None:
            modifiers = Qt.NoModifier

        t0 = time.time()
        logger.debug(
            "[DROP-SINGLE] load_single_item_from_drop START: %s",
            path,
            extra={"dev_only": True},
        )

        # Set wait cursor IMMEDIATELY before any processing.
        from PyQt5.QtWidgets import QApplication

        t1 = time.time()
        logger.debug(
            "[DROP-SINGLE] Attempting wait cursor at +%.3fms",
            (t1 - t0) * 1000,
            extra={"dev_only": True},
        )
        with wait_cursor(restore_after=False):
            QApplication.processEvents()
            t2 = time.time()
            logger.debug(
                "[DROP-SINGLE] After processEvents at +%.3fms",
                (t2 - t0) * 1000,
                extra={"dev_only": True},
            )
            self.file_load_controller.handle_drop([path], modifiers)

        logger.debug(
            "[DROP-SINGLE] Completed at +%.3fms",
            (time.time() - t0) * 1000,
            extra={"dev_only": True},
        )

    def prepare_folder_load(self, folder_path: str, *, clear: bool = True) -> list[str]:
        """Prepare folder load via FileLoadManager."""
        return self.file_load_manager.prepare_folder_load(folder_path, clear=clear)

    def should_skip_folder_reload(self, folder_path: str, force: bool = False) -> bool:
        """Check if folder reload should be skipped."""
        return folder_path == self.context.get_current_folder() and not force

    def get_file_items_from_folder(self, folder_path: str) -> list:
        """Get file items from folder via FileLoadManager."""
        return self.file_load_manager.get_file_items_from_folder(folder_path)

    def reload_current_folder(self) -> None:
        """Reload current folder via FileLoadManager."""
        self.file_load_manager.reload_current_folder()

    def handle_browse(self) -> None:
        """Handle browse via EventCoordinator."""
        self.event_handler_manager.handle_browse()

    def handle_folder_import(self) -> None:
        """Handle folder import via EventCoordinator."""
        self.event_handler_manager.handle_folder_import()

    def clear_file_table(self, message: str = "No folder selected") -> None:
        """Clear file table via FileLoadController."""
        from oncutf.utils.logging.logger_factory import get_cached_logger

        logger = get_cached_logger(__name__)

        success = self.file_load_controller.clear_files()
        logger.debug(
            "[FileLoadController] clear_files result: %s",
            success,
            extra={"dev_only": True},
        )

    def clear_file_table_shortcut(self) -> None:
        """Clear file table via Application Service."""
        return self.shortcut_handler.clear_file_table_shortcut()

    def find_fileitem_by_path(self, path: str) -> list:
        """Find FileItem by path via FileOperationsManager."""
        return self.file_operations_manager.find_fileitem_by_path(self.file_model.files, path)

    def shortcut_calculate_hash_selected(self) -> None:
        """Calculate hash for selected files via Application Service."""
        return self.shortcut_handler.shortcut_calculate_hash_selected()

    def rename_files(self) -> None:
        """Execute batch rename via Application Service."""
        return self.shortcut_handler.rename_files()

    def force_reload(self) -> None:
        """Force reload via UtilityManager."""
        self.utility_manager.force_reload()

    def auto_color_by_folder(self) -> None:
        """Auto-color files by their parent folder (Ctrl+Shift+C).

        Groups all files by folder and assigns unique random colors to each folder's files.
        Skips files that already have colors assigned (preserves user choices).
        Only works when 2+ folders are present.
        """
        return self.shortcut_handler.auto_color_by_folder()
