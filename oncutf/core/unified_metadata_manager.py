"""Module: unified_metadata_manager.py

Author: Michael Economou
Date: 2025-07-06
Refactored: 2025-12-21

Unified metadata management system - FACADE PATTERN.

This module now serves as a thin facade that delegates to specialized handlers:
- MetadataShortcutHandler: Keyboard shortcuts for metadata operations
- MetadataLoader: Loading orchestration (single/batch/streaming)
- MetadataProgressHandler: Progress dialog management
- MetadataCacheService: Cache operations
- CompanionMetadataHandler: Companion file metadata
- MetadataWriter: Save operations (ExifTool write)

The facade maintains backward compatibility while internal implementation
is now cleanly separated into focused modules.
"""

import contextlib
import os
from datetime import datetime

from PyQt5.QtCore import QObject, pyqtSignal

from oncutf.core.pyqt_imports import QApplication, Qt
from oncutf.models.file_item import FileItem
from oncutf.utils.cursor_helper import wait_cursor
from oncutf.utils.logger_factory import get_cached_logger
from oncutf.utils.metadata_cache_helper import MetadataCacheHelper
from oncutf.utils.path_utils import paths_equal

logger = get_cached_logger(__name__)


class UnifiedMetadataManager(QObject):
    """Unified metadata management system - Facade.

    This class delegates to specialized handlers while maintaining
    a unified API for all metadata operations.

    Delegates to:
    - MetadataShortcutHandler: Keyboard shortcuts
    - MetadataLoader: Loading orchestration
    - MetadataProgressHandler: Progress dialogs
    - MetadataCacheService: Cache operations
    - CompanionMetadataHandler: Companion files
    - MetadataWriter: Save operations
    """

    # Signals
    metadata_loaded = pyqtSignal(str, dict)  # file_path, metadata
    loading_started = pyqtSignal(str)  # file_path
    loading_finished = pyqtSignal()

    def __init__(self, parent_window=None):
        """Initialize UnifiedMetadataManager with parent window reference."""
        super().__init__(parent_window)
        self.parent_window = parent_window
        self._cache_helper: MetadataCacheHelper | None = None
        self._currently_loading: set[str] = set()

        # State tracking
        self.force_extended_metadata = False
        self._metadata_cancelled = False
        self._save_cancelled = False

        # Structured metadata system (lazy-initialized)
        self._structured_manager = None

        # ExifTool wrapper (lazy-initialized)
        self._exiftool_wrapper = None

        # Parallel loader (lazy-initialized)
        self._parallel_loader = None

        # Workers (for cleanup)
        self._metadata_worker = None
        self._metadata_thread = None
        self._hash_worker = None

        # Initialize extracted modules for delegation
        from oncutf.core.metadata import (
            CompanionMetadataHandler,
            MetadataCacheService,
            MetadataLoader,
            MetadataProgressHandler,
            MetadataShortcutHandler,
            MetadataWriter,
        )

        self._cache_service = MetadataCacheService(parent_window)
        self._companion_handler = CompanionMetadataHandler()
        self._writer = MetadataWriter(parent_window)
        self._shortcut_handler = MetadataShortcutHandler(self, parent_window)
        self._progress_handler = MetadataProgressHandler(parent_window)
        self._loader = MetadataLoader(
            parent_window=parent_window,
            exiftool_getter=lambda: self.exiftool_wrapper,
            companion_handler=self._companion_handler,
            progress_handler=self._progress_handler,
        )

        logger.info("[UnifiedMetadataManager] Initialized with delegated modules")

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def exiftool_wrapper(self):
        """Lazy-initialized ExifTool wrapper."""
        if self._exiftool_wrapper is None:
            from oncutf.utils.exiftool_wrapper import ExifToolWrapper

            self._exiftool_wrapper = ExifToolWrapper()
            logger.debug(
                "[UnifiedMetadataManager] ExifToolWrapper initialized",
                extra={"dev_only": True},
            )
        return self._exiftool_wrapper

    def initialize_cache_helper(self) -> None:
        """Initialize the cache helper if parent window is available."""
        self._cache_service.initialize_cache_helper()
        if self.parent_window and hasattr(self.parent_window, "metadata_cache"):
            self._cache_helper = MetadataCacheHelper(
                self.parent_window.metadata_cache, self.parent_window
            )

    @property
    def structured(self):
        """Lazy-initialized structured metadata manager."""
        if self._structured_manager is None:
            from oncutf.core.structured_metadata_manager import StructuredMetadataManager

            self._structured_manager = StructuredMetadataManager()
        return self._structured_manager

    @property
    def parallel_loader(self):
        """Lazy-initialized parallel metadata loader."""
        if self._parallel_loader is None:
            from oncutf.core.parallel_metadata_loader import ParallelMetadataLoader

            self._parallel_loader = ParallelMetadataLoader()
        return self._parallel_loader

    # =========================================================================
    # Cache Methods - Delegate to MetadataCacheService
    # =========================================================================

    def check_cached_metadata(self, file_item: FileItem) -> dict | None:
        """Delegate to cache_service."""
        return self._cache_service.check_cached_metadata(file_item)

    def check_cached_hash(self, file_item: FileItem) -> str | None:
        """Delegate to cache_service."""
        return self._cache_service.check_cached_hash(file_item)

    def has_cached_metadata(self, file_item: FileItem) -> bool:
        """Delegate to cache_service."""
        return self._cache_service.has_cached_metadata(file_item.full_path)

    def has_cached_hash(self, file_item: FileItem) -> bool:
        """Delegate to cache_service."""
        return self._cache_service.has_cached_hash(file_item.full_path)

    # =========================================================================
    # Enhanced Metadata - Delegate to CompanionMetadataHandler
    # =========================================================================

    def get_enhanced_metadata(
        self, file_item: FileItem, folder_files: list[str] = None
    ) -> dict | None:
        """Delegate to companion_handler."""
        base_metadata = self.check_cached_metadata(file_item)
        return self._companion_handler.get_enhanced_metadata(file_item, base_metadata, folder_files)

    def _enhance_metadata_with_companions(
        self, file_item: FileItem, base_metadata: dict, all_files: list[FileItem]
    ) -> dict:
        """Delegate to companion_handler."""
        return self._companion_handler.enhance_metadata_with_companions(
            file_item, base_metadata, all_files
        )

    # =========================================================================
    # Loading State Management
    # =========================================================================

    def is_running_metadata_task(self) -> bool:
        """Check if there's currently a metadata task running."""
        return len(self._currently_loading) > 0

    def is_loading(self) -> bool:
        """Check if any files are currently being loaded."""
        return len(self._currently_loading) > 0

    def reset_cancellation_flag(self) -> None:
        """Reset the metadata cancellation flag."""
        self._metadata_cancelled = False
        self._loader.reset_cancellation_flag()

    # =========================================================================
    # Mode Determination - Delegate to MetadataShortcutHandler
    # =========================================================================

    def determine_loading_mode(self, file_count: int, _use_extended: bool = False) -> str:
        """Delegate to loader."""
        return self._loader.determine_loading_mode(file_count)

    def determine_metadata_mode(self, modifier_state=None) -> tuple[bool, bool]:
        """Delegate to shortcut_handler."""
        return self._shortcut_handler.determine_metadata_mode(modifier_state)

    def should_use_extended_metadata(self, modifier_state=None) -> bool:
        """Delegate to shortcut_handler."""
        return self._shortcut_handler.should_use_extended_metadata(modifier_state)

    # =========================================================================
    # Shortcut Methods - Delegate to MetadataShortcutHandler
    # =========================================================================

    def shortcut_load_metadata(self) -> None:
        """Delegate to shortcut_handler."""
        self._shortcut_handler.shortcut_load_metadata()

    def shortcut_load_extended_metadata(self) -> None:
        """Delegate to shortcut_handler."""
        self._shortcut_handler.shortcut_load_extended_metadata()

    def shortcut_load_metadata_all(self) -> None:
        """Delegate to shortcut_handler."""
        self._shortcut_handler.shortcut_load_metadata_all()

    def shortcut_load_extended_metadata_all(self) -> None:
        """Delegate to shortcut_handler."""
        self._shortcut_handler.shortcut_load_extended_metadata_all()

    # =========================================================================
    # Main Loading Methods - Delegate to MetadataLoader
    # =========================================================================

    def load_metadata_streaming(self, items: list[FileItem], use_extended: bool = False):
        """Delegate to loader."""
        return self._loader.load_metadata_streaming(items, use_extended)

    def load_metadata_for_items(
        self, items: list[FileItem], use_extended: bool = False, source: str = "unknown"
    ) -> None:
        """Delegate to loader with signal emission."""

        def on_finished():
            self.loading_finished.emit()

        self._loader.load_metadata_for_items(items, use_extended, source, on_finished=on_finished)

    # =========================================================================
    # Hash Loading
    # =========================================================================

    def load_hashes_for_files(self, files: list[FileItem], source: str = "user_request") -> None:
        """Load hashes for files that don't have them cached."""
        if not files:
            return

        # Filter files that need loading
        files_to_load = []
        for file_item in files:
            if file_item.full_path not in self._currently_loading:
                cached = self.check_cached_hash(file_item)
                if not cached:
                    files_to_load.append(file_item)
                    self._currently_loading.add(file_item.full_path)

        if not files_to_load:
            logger.info(
                "[UnifiedMetadataManager] All %d files already have cached hashes",
                len(files),
            )
            return

        logger.info(
            "[UnifiedMetadataManager] Loading hashes for %d files (%s)",
            len(files_to_load),
            source,
        )

        # Show progress dialog for multiple files
        if len(files_to_load) > 1:
            self._show_hash_progress_dialog(files_to_load, source)
        else:
            self._start_hash_loading(files_to_load, source)

    def _show_hash_progress_dialog(self, files: list[FileItem], source: str) -> None:
        """Show progress dialog for hash loading."""
        try:

            def cancel_hash_loading():
                self._cancel_current_loading()

            from oncutf.utils.progress_dialog import ProgressDialog

            self._hash_progress_dialog = ProgressDialog.create_hash_dialog(
                self.parent_window, cancel_callback=cancel_hash_loading
            )

            if self._hash_worker:
                self._hash_worker.progress_updated.connect(
                    lambda current, total, _: self._hash_progress_dialog.update_progress(
                        current, total
                    )
                )
                self._hash_worker.size_progress.connect(
                    lambda processed, total: self._hash_progress_dialog.update_size_progress(
                        processed, total
                    )
                )

            self._hash_progress_dialog.show()
            self._start_hash_loading(files, source)

        except Exception:
            logger.exception("[UnifiedMetadataManager] Error showing hash progress dialog")
            if hasattr(self, "_hash_progress_dialog") and self._hash_progress_dialog:
                self._hash_progress_dialog.close()
                self._hash_progress_dialog = None
            self._start_hash_loading(files, source)

    def _start_hash_loading(self, files: list[FileItem], _source: str) -> None:
        """Start hash loading using parallel hash worker."""
        if not files:
            return

        from oncutf.core.hash.parallel_hash_worker import ParallelHashWorker

        file_paths = [f.full_path for f in files]
        self._hash_worker = ParallelHashWorker(parent=self.parent_window)
        self._hash_worker.setup_checksum_calculation(file_paths)

        self._hash_worker.file_hash_calculated.connect(
            self._on_file_hash_calculated, Qt.QueuedConnection
        )
        self._hash_worker.finished_processing.connect(
            lambda _: self._on_hash_finished(), Qt.QueuedConnection
        )
        self._hash_worker.progress_updated.connect(
            lambda current, total, _: self._on_hash_progress(current, total),
            Qt.QueuedConnection,
        )

        self._hash_worker.start()

    def _on_hash_progress(self, current: int, total: int) -> None:
        """Handle hash loading progress updates."""
        # Progress handler manages this via connected signals

    def _on_file_hash_calculated(self, file_path: str, hash_value: str = "") -> None:
        """Handle individual file hash calculated."""
        self._currently_loading.discard(file_path)

        if hash_value:
            try:
                from oncutf.core.hash.hash_manager import HashManager

                hm = HashManager()
                hm.store_hash(file_path, hash_value)
            except Exception:
                logger.warning(
                    "[UnifiedMetadataManager] Failed to store hash for %s",
                    file_path,
                    exc_info=True,
                )

        # Progressive UI update
        if self.parent_window and hasattr(self.parent_window, "file_model"):
            if hasattr(self.parent_window.file_model, "refresh_icon_for_file"):
                self.parent_window.file_model.refresh_icon_for_file(file_path)
            else:
                try:
                    for i, file in enumerate(self.parent_window.file_model.files):
                        if paths_equal(file.full_path, file_path):
                            top_left = self.parent_window.file_model.index(i, 0)
                            bottom_right = self.parent_window.file_model.index(
                                i, self.parent_window.file_model.columnCount() - 1
                            )
                            self.parent_window.file_model.dataChanged.emit(
                                top_left, bottom_right, [Qt.DecorationRole, Qt.ToolTipRole]
                            )
                            break
                except Exception:
                    pass

    def _on_hash_finished(self) -> None:
        """Handle hash loading completion."""
        self._cleanup_hash_worker_and_thread()
        self.loading_finished.emit()

        if self.parent_window:
            if hasattr(self.parent_window, "file_model"):
                self.parent_window.file_model.refresh_icons()
            if (
                hasattr(self.parent_window, "preview_manager")
                and self.parent_window.preview_manager
            ):
                self.parent_window.preview_manager.on_hash_calculation_completed()

        logger.info("[UnifiedMetadataManager] Hash loading completed")

    # =========================================================================
    # Cancellation
    # =========================================================================

    def _cancel_current_loading(self) -> None:
        """Cancel current loading operation."""
        self._metadata_cancelled = True
        self._loader.request_cancellation()

        if hasattr(self, "_metadata_worker") and self._metadata_worker:
            self._metadata_worker.cancel()

        if hasattr(self, "_hash_worker") and self._hash_worker:
            self._hash_worker.cancel()

        logger.info("[UnifiedMetadataManager] Loading operation cancelled")

    def request_save_cancel(self) -> None:
        """Delegate to writer and sync flag."""
        self._save_cancelled = True
        return self._writer.request_save_cancel()

    # =========================================================================
    # Metadata Saving - Delegate to MetadataWriter
    # =========================================================================

    def set_metadata_value(self, file_path: str, key_path: str, new_value: str) -> bool:
        """Delegate to writer."""
        return self._writer.set_metadata_value(file_path, key_path, new_value)

    def save_metadata_for_selected(self) -> None:
        """Delegate to writer."""
        return self._writer.save_metadata_for_selected()

    def save_all_modified_metadata(self, is_exit_save: bool = False) -> None:
        """Delegate to writer."""
        return self._writer.save_all_modified_metadata(is_exit_save)

    def _save_metadata_files(
        self, files_to_save: list, all_modifications: dict, is_exit_save: bool = False
    ) -> None:
        """Save metadata files using ExifTool."""
        if not files_to_save:
            return

        success_count = 0
        failed_files = []
        _loading_dialog = None

        file_count = len(files_to_save)
        save_mode = "single_file_wait_cursor" if file_count == 1 else "multiple_files_dialog"

        logger.info(
            "[UnifiedMetadataManager] Saving metadata for %d file(s) using mode: %s",
            file_count,
            save_mode,
        )

        try:
            if save_mode == "multiple_files_dialog":
                from oncutf.utils.progress_dialog import ProgressDialog

                cancel_callback = self.request_save_cancel if not is_exit_save else None
                _loading_dialog = ProgressDialog(
                    parent=self.parent_window,
                    operation_type="metadata_save",
                    cancel_callback=cancel_callback,
                    show_enhanced_info=False,
                    is_exit_save=is_exit_save,
                )
                _loading_dialog.set_status("Saving metadata...")
                _loading_dialog.show()
                QApplication.processEvents()

            cursor_context = (
                wait_cursor()
                if save_mode == "single_file_wait_cursor"
                else contextlib.nullcontext()
            )

            with cursor_context:
                current_file_index = 0
                for file_item in files_to_save:
                    if self._save_cancelled:
                        logger.info(
                            "[UnifiedMetadataManager] Save cancelled after %d/%d files",
                            success_count,
                            file_count,
                        )
                        break

                    current_file_index += 1

                    if _loading_dialog:
                        _loading_dialog.set_filename(file_item.filename)
                        _loading_dialog.set_count(current_file_index, file_count)
                        _loading_dialog.set_progress(current_file_index, file_count)
                        QApplication.processEvents()

                    file_path = file_item.full_path
                    modifications = self._get_modified_metadata_for_file(
                        file_path, all_modifications
                    )

                    if not modifications:
                        continue

                    try:
                        success = self.exiftool_wrapper.write_metadata(file_path, modifications)

                        if success:
                            success_count += 1
                            self._update_file_after_save(file_item, modifications)
                        else:
                            failed_files.append(file_item.filename)

                    except Exception:
                        failed_files.append(file_item.filename)
                        logger.exception(
                            "[UnifiedMetadataManager] Error saving metadata for %s",
                            file_item.filename,
                        )

        except Exception:
            logger.exception("[UnifiedMetadataManager] Error in metadata saving process")
        finally:
            if _loading_dialog:
                _loading_dialog.close()

        was_cancelled = self._save_cancelled
        self._show_save_results(success_count, failed_files, files_to_save, was_cancelled)

        # Record save command
        if success_count > 0:
            self._record_save_command(files_to_save, failed_files, all_modifications)

    def _get_modified_metadata_for_file(self, file_path: str, all_modified_metadata: dict) -> dict:
        """Get modified metadata for a specific file."""
        if file_path in all_modified_metadata:
            return all_modified_metadata[file_path]

        from oncutf.utils.path_normalizer import normalize_path

        normalized = normalize_path(file_path)
        for key, value in all_modified_metadata.items():
            if normalize_path(key) == normalized:
                return value
        return {}

    def _update_file_after_save(self, file_item, saved_metadata: dict = None):
        """Update file item after successful metadata save."""
        # Clear staged changes
        try:
            staging_manager = self.parent_window.context.get_manager("metadata_staging")
            staging_manager.clear_staged_changes(file_item.full_path)
        except KeyError:
            pass

        # Update caches
        if saved_metadata:
            self._update_caches_after_save(file_item, saved_metadata)

        # Clear modifications in tree view
        if hasattr(self.parent_window, "metadata_tree_view"):
            self.parent_window.metadata_tree_view.clear_modifications_for_file(file_item.full_path)

        # Update modification time
        with contextlib.suppress(Exception):
            file_item.date_modified = datetime.fromtimestamp(os.path.getmtime(file_item.full_path))

        # Refresh display if this file is shown
        self._refresh_display_if_current(file_item)

    def _update_caches_after_save(self, file_item, saved_metadata: dict):
        """Update UI and persistent caches after save."""
        # Update UI cache
        if hasattr(self.parent_window, "metadata_cache"):
            cache = self.parent_window.metadata_cache
            entry = cache.get_entry(file_item.full_path)
            if entry and hasattr(entry, "data"):
                for key_path, new_value in saved_metadata.items():
                    self._update_nested_metadata(entry.data, key_path, new_value)
                entry.modified = False

        # Update persistent cache
        try:
            from oncutf.core.cache.persistent_metadata_cache import get_persistent_metadata_cache

            persistent_cache = get_persistent_metadata_cache()
            if persistent_cache:
                current = persistent_cache.get(file_item.full_path)
                if current:
                    updated = dict(current)
                    for key_path, new_value in saved_metadata.items():
                        self._update_nested_metadata(updated, key_path, new_value)
                    persistent_cache.set(file_item.full_path, updated, is_extended=False)
        except Exception:
            logger.warning(
                "[UnifiedMetadataManager] Failed to update persistent cache", exc_info=True
            )

    def _update_nested_metadata(self, data: dict, key_path: str, value: str):
        """Update nested metadata structure."""
        if "/" in key_path or ":" in key_path:
            sep = "/" if "/" in key_path else ":"
            parts = key_path.split(sep, 1)
            if len(parts) == 2:
                group, key = parts
                if group not in data:
                    data[group] = {}
                if isinstance(data[group], dict):
                    data[group][key] = value
                else:
                    data[group] = {key: value}
            else:
                data[key_path] = value
        else:
            data[key_path] = value

    def _refresh_display_if_current(self, file_item):
        """Refresh metadata display if file is currently shown."""
        if not hasattr(self.parent_window, "metadata_tree_view"):
            return
        tree = self.parent_window.metadata_tree_view
        if hasattr(tree, "_current_file_path") and tree._current_file_path == file_item.full_path:
            if hasattr(self.parent_window, "metadata_cache"):
                entry = self.parent_window.metadata_cache.get_entry(file_item.full_path)
                if entry and hasattr(entry, "data"):
                    display_data = dict(entry.data)
                    display_data["FileName"] = file_item.filename
                    tree.display_metadata(display_data, context="after_save")

    def _show_save_results(self, success_count, failed_files, files_to_save, was_cancelled=False):
        """Show results of metadata save operation."""
        total_files = len(files_to_save)

        if was_cancelled:
            skipped_count = total_files - success_count - len(failed_files)
            message = (
                f"Save cancelled after {success_count}/{total_files} files"
                if success_count
                else "Save cancelled"
            )
            logger.info("[UnifiedMetadataManager] %s", message)

            if self.parent_window and hasattr(self.parent_window, "status_bar"):
                self.parent_window.status_bar.showMessage(message, 5000 if success_count else 3000)

            if self.parent_window:
                from oncutf.ui.widgets.custom_message_dialog import CustomMessageDialog

                msg_parts = ["Save operation cancelled by user."]
                if success_count > 0:
                    msg_parts.append(f"\nSuccessfully saved: {success_count} files")
                if failed_files:
                    msg_parts.append(f"Failed: {len(failed_files)} files")
                if skipped_count > 0:
                    msg_parts.append(f"Skipped: {skipped_count} files")

                CustomMessageDialog.information(
                    self.parent_window, "Save Cancelled", "\n".join(msg_parts)
                )
            return

        if success_count > 0:
            logger.info("[UnifiedMetadataManager] Saved metadata for %d files", success_count)
            if self.parent_window and hasattr(self.parent_window, "status_bar"):
                self.parent_window.status_bar.showMessage(
                    f"Metadata saved for {success_count} files", 3000
                )

        if failed_files:
            logger.warning("[UnifiedMetadataManager] Failed to save %d files", len(failed_files))
            if self.parent_window:
                from oncutf.core.pyqt_imports import QMessageBox

                QMessageBox.warning(
                    self.parent_window,
                    "Metadata Save Error",
                    f"Failed to save metadata for {len(failed_files)} files.\n\n"
                    f"Files: {', '.join(failed_files[:5])}{'...' if len(failed_files) > 5 else ''}",
                )

    def _record_save_command(self, files_to_save, failed_files, all_modifications):
        """Record save command for undo/redo."""
        try:
            from oncutf.core.metadata_command_manager import get_metadata_command_manager
            from oncutf.core.metadata_commands import SaveMetadataCommand

            command_manager = get_metadata_command_manager()
            if command_manager and SaveMetadataCommand:
                successful_files = []
                successful_metadata = {}

                for file_item in files_to_save:
                    if file_item.filename not in failed_files:
                        successful_files.append(file_item.full_path)
                        mods = self._get_modified_metadata_for_file(
                            file_item.full_path, all_modifications
                        )
                        if mods:
                            successful_metadata[file_item.full_path] = mods

                if successful_files:
                    save_command = SaveMetadataCommand(
                        file_paths=successful_files, saved_metadata=successful_metadata
                    )
                    command_manager.execute_command(save_command)
        except Exception:
            logger.warning("[UnifiedMetadataManager] Error recording save command", exc_info=True)

    # =========================================================================
    # Structured Metadata Integration - Delegate to StructuredMetadataManager
    # =========================================================================

    def get_structured_metadata(self, file_path: str) -> dict:
        """Delegate to structured manager."""
        return self.structured.get_structured_metadata(file_path)

    def process_and_store_metadata(self, file_path: str, raw_metadata: dict) -> bool:
        """Delegate to structured manager."""
        return self.structured.process_and_store_metadata(file_path, raw_metadata)

    def get_field_value(self, file_path: str, field_key: str) -> str | None:
        """Delegate to structured manager."""
        return self.structured.get_field_value(file_path, field_key)

    def update_field_value(self, file_path: str, field_key: str, field_value: str) -> bool:
        """Delegate to structured manager."""
        return self.structured.update_field_value(file_path, field_key, field_value)

    def add_custom_field(self, field_key: str, field_name: str, category: str, **kwargs) -> bool:
        """Delegate to structured manager."""
        return self.structured.add_custom_field(field_key, field_name, category, **kwargs)

    def get_available_categories(self) -> list[dict]:
        """Delegate to structured manager."""
        return self.structured.get_available_categories()

    def get_available_fields(self, category: str | None = None) -> list[dict]:
        """Delegate to structured manager."""
        return self.structured.get_available_fields(category)

    def search_files_by_metadata(self, field_key: str, field_value: str) -> list[str]:
        """Delegate to structured manager."""
        return self.structured.search_files_by_metadata(field_key, field_value)

    def refresh_structured_caches(self) -> None:
        """Delegate to structured manager."""
        self.structured.refresh_caches()

    # =========================================================================
    # Cleanup
    # =========================================================================

    def _cleanup_metadata_worker_and_thread(self) -> None:
        """Clean up metadata worker and thread."""
        if hasattr(self, "_metadata_worker") and self._metadata_worker:
            self._metadata_worker.deleteLater()
            self._metadata_worker = None

        if hasattr(self, "_metadata_thread") and self._metadata_thread:
            self._metadata_thread.quit()
            if not self._metadata_thread.wait(3000):
                self._metadata_thread.terminate()
                self._metadata_thread.wait(1000)
            self._metadata_thread.deleteLater()
            self._metadata_thread = None

    def _cleanup_hash_worker_and_thread(self) -> None:
        """Clean up hash worker."""
        if hasattr(self, "_hash_worker") and self._hash_worker:
            if self._hash_worker.isRunning():
                if not self._hash_worker.wait(3000):
                    self._hash_worker.terminate()
                    self._hash_worker.wait(1000)
            self._hash_worker.deleteLater()
            self._hash_worker = None

    def cleanup(self) -> None:
        """Clean up resources."""
        self._cancel_current_loading()
        self._cleanup_metadata_worker_and_thread()
        self._cleanup_hash_worker_and_thread()
        self._progress_handler.cleanup()

        if hasattr(self, "_exiftool_wrapper") and self._exiftool_wrapper:
            self._exiftool_wrapper.close()

        if self._structured_manager is not None:
            self._structured_manager = None

        self._currently_loading.clear()
        logger.info("[UnifiedMetadataManager] Cleanup completed")


# =========================================================================
# Factory Functions
# =========================================================================

_unified_metadata_manager = None


def get_unified_metadata_manager(parent_window=None) -> UnifiedMetadataManager:
    """Get or create the unified metadata manager instance."""
    global _unified_metadata_manager
    if _unified_metadata_manager is None:
        _unified_metadata_manager = UnifiedMetadataManager(parent_window)
    return _unified_metadata_manager


def cleanup_unified_metadata_manager() -> None:
    """Clean up the unified metadata manager instance."""
    global _unified_metadata_manager
    if _unified_metadata_manager:
        _unified_metadata_manager.cleanup()
        _unified_metadata_manager = None
