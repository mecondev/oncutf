# Project Context – oncutf-main

_Generated automatically on 2025-11-17 15:30_

This file provides a high-level overview of the Python codebase:
- per top-level directory
- listing modules, line counts, brief docstrings, and main classes/functions.
Use it as context for AI assistants (VS Code Copilot, etc.).

## Overview

- **Total Python files**: 188
- **Approximate total lines**: 327848
- **Root directory**: `D:\edu\python\oncutf-main`

---

## `(root)/`

### `config.py` 
- Lines: **755**
- Docstring: _"Module: config.py Author: Michael Economou Date: 2025-05-01 This module defines global configuration constants and settings used throughout the oncutf [...]"_

### `main.py` 
- Lines: **236**
- Docstring: _"Module: main.py Author: Michael Economou Date: 2025-05-01 This module serves as the entry point for the oncutf application. It sets up logging, [...]"_
- Functions: get_user_config_dir, cleanup_on_exit, signal_handler, main

### `main_window.py` 
- Lines: **1531**
- Docstring: _"main_window.py Author: Michael Economou Date: 2025-05-01 This module defines the MainWindow class, which implements the primary user interface for the [...]"_
- Classes: MainWindow

---

## `core/`

### `core/__init__.py` 
- Lines: **10**
- Docstring: _"Module: __init__.py Author: Michael Economou Date: 2025-05-31"_

### `core/advanced_cache_manager.py` 
- Lines: **262**
- Docstring: _"Module: advanced_cache_manager.py Author: Michael Economou Date: 2025-01-27 Advanced Cache Manager - Simple but effective caching for speed and reliability."_
- Classes: LRUCache, DiskCache, AdvancedCacheManager

### `core/application_context.py` 
- Lines: **306**
- Docstring: _"Application Context - Centralized state management. This module provides centralized access to application state, eliminating the need for complex parent- [...]"_
- Classes: ApplicationContext
- Functions: get_app_context

### `core/application_service.py` 
- Lines: **749**
- Docstring: _"Application Service Layer with unified interface to all operations. This module provides a unified interface to all application operations, reducing the [...]"_
- Classes: ApplicationService
- Functions: get_application_service, initialize_application_service, cleanup_application_service

### `core/async_operations_manager.py` 
- Lines: **618**
- Docstring: _"Module: async_operations_manager.py Author: Michael Economou Date: 2025-06-25 Async Operations Manager Module This module provides asynchronous operations [...]"_
- Classes: AsyncTask, AsyncFileOperations, AsyncTaskManager, AsyncOperationsManager
- Functions: get_async_operations_manager, initialize_async_operations

### `core/backup_manager.py` 
- Lines: **307**
- Docstring: _"Module: backup_manager.py Author: Michael Economou Date: 2025-06-10 This module provides database backup functionality for the oncutf application. It [...]"_
- Classes: BackupManager
- Functions: get_backup_manager, cleanup_backup_manager

### `core/batch_operations_manager.py` 
- Lines: **635**
- Docstring: _"Module: batch_operations_manager.py Author: Michael Economou Date: 2025-06-20 batch_operations_manager.py This module provides batch operations [...]"_
- Classes: BatchOperation, BatchStats, BatchOperationsManager
- Functions: get_batch_manager, cleanup_batch_manager

### `core/batch_processor.py` 
- Lines: **221**
- Docstring: _"Module: batch_processor.py Author: Michael Economou Date: 2025-01-27 Batch Processor - Simple but effective batch processing for speed and reliability."_
- Classes: BatchProcessor, SmartBatchProcessor, BatchProcessorFactory

### `core/column_manager.py` 
- Lines: **779**
- Docstring: _"Module: column_manager.py Author: Michael Economou Date: 2025-06-10 Column Management System for OnCutF Application This module provides centralized [...]"_
- Classes: ColumnType, ColumnConfig, ColumnState, ColumnManager

### `core/config_imports.py` 
- Lines: **80**
- Docstring: _"Module: config_imports.py Author: Michael Economou Date: 2025-05-31 config_imports.py Centralized config imports to reduce clutter in main files. Re- [...]"_

### `core/conflict_resolver.py` 
- Lines: **300**
- Docstring: _"Module: conflict_resolver.py Author: Michael Economou Date: 2025-01-27 Conflict Resolver - Simple but reliable conflict resolution for rename operations."_
- Classes: ConflictOperation, ConflictResolution, UndoStack, ConflictResolver

### `core/database_manager.py` 
- Lines: **1296**
- Docstring: _"Module: database_manager.py Author: Michael Economou Date: 2025-06-10 database_manager.py Enhanced database management with improved architecture. [...]"_
- Classes: DatabaseManager
- Functions: get_database_manager, initialize_database

### `core/dialog_manager.py` 
- Lines: **184**
- Docstring: _"Module: dialog_manager.py Author: Michael Economou Date: 2025-05-31 dialog_manager.py Manages all dialog and validation operations for the application. [...]"_
- Classes: DialogManager

### `core/direct_metadata_loader.py` 
- Lines: **601**
- Docstring: _"Module: direct_metadata_loader.py Author: Michael Economou Date: 2025-07-06 Direct metadata loader for on-demand metadata/hash loading. Provides simple, [...]"_
- Classes: DirectMetadataLoader
- Functions: get_direct_metadata_loader, cleanup_direct_metadata_loader

### `core/drag_cleanup_manager.py` 
- Lines: **213**
- Docstring: _"Module: drag_cleanup_manager.py Author: Michael Economou Date: 2025-05-31 DragCleanupManager - Handles drag and drop cleanup operations This manager [...]"_
- Classes: DragCleanupManager

### `core/drag_manager.py` 
- Lines: **319**
- Docstring: _"Centralized drag & drop state manager. Solves the sticky cursor issue by providing unified cleanup and state tracking across all widgets. Author: Michael [...]"_
- Classes: DragManager
- Functions: start_drag, end_drag, force_cleanup_drag, is_dragging

### `core/drag_visual_manager.py` 
- Lines: **544**
- Docstring: _"Drag Visual Manager - Visual feedback for drag & drop operations. This module provides visual feedback for drag & drop operations including: - [...]"_
- Classes: DragType, DropZoneState, ModifierState, DragVisualManager
- Functions: start_drag_visual, end_drag_visual, update_drop_zone_state, update_modifier_state, is_valid_drop_target, update_drag_feedback_for_widget

### `core/event_handler_manager.py` 
- Lines: **2624**
- Docstring: _"Module: event_handler_manager.py Author: Michael Economou Date: 2025-05-31 Manages all event handling operations for the main window. Handles browse, [...]"_
- Classes: EventHandlerManager

### `core/file_load_manager.py` 
- Lines: **504**
- Docstring: _"Module: file_load_manager.py Author: Michael Economou Date: 2025-06-15 file_load_manager.py Unified file loading manager with fully optimized policy: - [...]"_
- Classes: FileLoadManager

### `core/file_operations_manager.py` 
- Lines: **168**
- Docstring: _"Module: file_operations_manager.py Author: Michael Economou Date: 2025-06-15 file_operations_manager.py Manages file operations like rename, validation, [...]"_
- Classes: FileOperationsManager

### `core/file_store.py` 
- Lines: **249**
- Docstring: _"Module: file_store.py Author: Michael Economou Date: 2025-05-31 File Store - Centralized file management This module handles all file-related operations, [...]"_
- Classes: FileStore

### `core/file_validation_manager.py` 
- Lines: **543**
- Docstring: _"Module: file_validation_manager.py Author: Michael Economou Date: 2025-06-15 file_validation_manager.py Advanced file validation manager with content- [...]"_
- Classes: ValidationAccuracy, OperationType, FileSignature, ValidationResult, ValidationThresholds, FileValidationManager
- Functions: get_file_validation_manager

### `core/hash_manager.py` 
- Lines: **409**
- Docstring: _"Module: hash_manager.py Author: Michael Economou Date: 2025-06-10 hash_manager.py Manages file hashing operations, duplicate detection, and file integrity [...]"_
- Classes: HashManager
- Functions: calculate_crc32, compare_folders

### `core/hash_worker.py` 
- Lines: **596**
- Docstring: _"Module: hash_worker.py Author: Michael Economou Date: 2025-06-10 hash_worker.py QThread worker for background hash calculation operations. This module [...]"_
- Classes: HashWorker

### `core/initialization_manager.py` 
- Lines: **145**
- Docstring: _"Module: initialization_manager.py Author: Michael Economou Date: 2025-05-31 InitializationManager - Handles initialization and setup operations This [...]"_
- Classes: InitializationManager

### `core/memory_manager.py` 
- Lines: **424**
- Docstring: _"Memory Manager Module. This module provides comprehensive memory management for the oncutf application. It handles automatic cleanup of unused cache [...]"_
- Classes: CacheEntry, MemoryStats, LRUCache, MemoryManager
- Functions: get_memory_manager, initialize_memory_manager

### `core/metadata_command_manager.py` 
- Lines: **366**
- Docstring: _"Module: metadata_command_manager.py Author: Michael Economou Date: 2025-07-08 Command manager for metadata operations with undo/redo functionality. [...]"_
- Classes: MetadataCommandManager
- Functions: get_metadata_command_manager, cleanup_metadata_command_manager

### `core/metadata_commands.py` 
- Lines: **512**
- Docstring: _"Module: metadata_commands.py Author: Michael Economou Date: 2025-07-08 Command pattern implementation for metadata operations. Provides undo/redo [...]"_
- Classes: MetadataCommand, EditMetadataFieldCommand, ResetMetadataFieldCommand, SaveMetadataCommand, BatchMetadataCommand

### `core/metadata_manager.py` 
- Lines: **980**
- Docstring: _"Module: metadata_manager.py Author: Michael Economou Date: 2025-05-31 metadata_manager.py Centralized metadata management operations extracted from [...]"_
- Classes: MetadataManager

### `core/modifier_handler.py` 
- Lines: **117**
- Docstring: _"Module: modifier_handler.py Author: Michael Economou Date: 2025-05-31 modifier_handler.py Centralized handling of keyboard modifier combinations for file [...]"_
- Classes: ModifierAction
- Functions: decode_modifiers, get_action_flags, decode_modifiers_to_flags, get_action_description, is_merge_mode, is_recursive_mode

### `core/optimized_database_manager.py` 
- Lines: **674**
- Docstring: _"Optimized Database Manager Module. This module provides an enhanced database management system with: - Prepared statements for better performance - [...]"_
- Classes: QueryStats, ConnectionPool, PreparedStatementCache, OptimizedDatabaseManager
- Functions: get_optimized_database_manager, initialize_optimized_database

### `core/performance_monitor.py` 
- Lines: **231**
- Docstring: _"Module: performance_monitor.py Author: Michael Economou Date: 2025-01-27 Performance Monitor for UnifiedRenameEngine Provides metrics and monitoring for [...]"_
- Classes: PerformanceMetric, PerformanceStats, PerformanceMonitor, PerformanceDecorator
- Functions: get_performance_monitor, monitor_performance

### `core/persistent_hash_cache.py` 
- Lines: **221**
- Docstring: _"Module: persistent_hash_cache.py Author: Michael Economou Date: 2025-06-15 persistent_hash_cache.py Enhanced persistent hash cache using the improved [...]"_
- Classes: PersistentHashCache
- Functions: get_persistent_hash_cache

### `core/persistent_metadata_cache.py` 
- Lines: **389**
- Docstring: _"Module: persistent_metadata_cache.py Author: Michael Economou Date: 2025-06-15 persistent_metadata_cache.py Enhanced persistent metadata cache using the [...]"_
- Classes: MetadataEntry, PersistentMetadataCache, DummyMetadataCache
- Functions: get_persistent_metadata_cache

### `core/preview_manager.py` 
- Lines: **302**
- Docstring: _"Module: preview_manager.py Author: Michael Economou Date: 2025-05-31 preview_manager.py Manages preview name generation for rename operations. Extracted [...]"_
- Classes: PreviewManager

### `core/pyqt_imports.py` 
- Lines: **239**
- Docstring: _"Module: qt_imports.py Author: Michael Economou Date: 2025-05-31 qt_imports.py Centralized PyQt5 imports to reduce import clutter in main files. Groups [...]"_

### `core/rename_history_manager.py` 
- Lines: **386**
- Docstring: _"Module: rename_history_manager.py Author: Michael Economou Date: 2025-06-10 rename_history_manager.py Rename history management system for undo/redo [...]"_
- Classes: RenameOperation, RenameBatch, RenameHistoryManager
- Functions: get_rename_history_manager

### `core/rename_manager.py` 
- Lines: **445**
- Docstring: _"Module: rename_manager.py Author: Michael Economou Date: 2025-05-31 RenameManager - Handles rename operations and workflow This manager centralizes rename [...]"_
- Classes: RenameManager

### `core/selection_manager.py` 
- Lines: **394**
- Docstring: _"Module: selection_manager.py Author: Michael Economou Date: 2025-05-31 selection_manager.py Centralized selection management operations extracted from [...]"_
- Classes: SelectionManager

### `core/selection_store.py` 
- Lines: **464**
- Docstring: _"Module: selection_store.py Author: Michael Economou Date: 2025-05-31 Selection Store - Centralized selection state management This module provides [...]"_
- Classes: SelectionStore

### `core/shortcut_manager.py` 
- Lines: **247**
- Docstring: _"Module: shortcut_manager.py Author: Michael Economou Date: 2025-01-15 ShortcutManager - Handles keyboard shortcuts This manager centralizes keyboard [...]"_
- Classes: ShortcutManager

### `core/splitter_manager.py` 
- Lines: **259**
- Docstring: _"Module: splitter_manager.py Author: Michael Economou Date: 2025-06-10 splitter_manager.py This module defines the SplitterManager class, which handles all [...]"_
- Classes: SplitterManager

### `core/status_manager.py` 
- Lines: **696**
- Docstring: _"Module: status_manager.py Author: Michael Economou Date: 2025-05-31 status_manager.py Enhanced Status Manager for OnCutF Application Manages status bar [...]"_
- Classes: StatusPriority, StatusCategory, StatusEntry, StatusManager

### `core/structured_metadata_manager.py` 
- Lines: **413**
- Docstring: _"Structured Metadata Manager This module handles the conversion of raw metadata from ExifTool to structured metadata that can be stored in the database [...]"_
- Classes: StructuredMetadataManager
- Functions: get_structured_metadata_manager, initialize_structured_metadata_manager

### `core/table_manager.py` 
- Lines: **247**
- Docstring: _"Module: table_manager.py Author: Michael Economou Date: 2025-05-31 table_manager.py Manager for handling file table operations in the MainWindow. [...]"_
- Classes: TableManager

### `core/thread_pool_manager.py` 
- Lines: **577**
- Docstring: _"Module: thread_pool_manager.py Author: Michael Economou Date: 2025-06-25 Thread Pool Manager Module This module provides an optimized thread pool [...]"_
- Classes: TaskPriority, WorkerTask, ThreadPoolStats, PriorityQueue, SmartWorkerThread, ThreadPoolManager
- Functions: get_thread_pool_manager, initialize_thread_pool, submit_task, get_pool_stats

### `core/ui_manager.py` 
- Lines: **843**
- Docstring: _"Module: ui_manager.py Author: Michael Economou Date: 2025-05-31 Manages UI setup and layout configuration for the main window. Handles widget [...]"_
- Classes: UIManager

### `core/unified_column_service.py` 
- Lines: **372**
- Docstring: _"Module: unified_column_service.py Author: Michael Economou Date: 2025-08-24 Unified Column Service for OnCutF Application This module provides a [...]"_
- Classes: ColumnAlignment, ColumnConfig, UnifiedColumnService
- Functions: get_column_service, invalidate_column_service

### `core/unified_metadata_manager.py` 
- Lines: **1440**
- Docstring: _"Module: unified_metadata_manager.py Author: Michael Economou Date: 2025-07-06 Unified metadata management system combining MetadataManager and [...]"_
- Classes: UnifiedMetadataManager
- Functions: get_unified_metadata_manager, cleanup_unified_metadata_manager

### `core/unified_rename_engine.py` 
- Lines: **813**
- Docstring: _"Module: unified_rename_engine.py Author: Michael Economou Date: 2025-01-27 UnifiedRenameEngine - Central engine for all rename operations. Integrates [...]"_
- Classes: PreviewResult, ValidationItem, ValidationResult, ExecutionItem, ExecutionResult, RenameState, BatchQueryManager, SmartCacheManager, UnifiedPreviewManager, UnifiedValidationManager, UnifiedExecutionManager, RenameStateManager, UnifiedRenameEngine

### `core/utility_manager.py` 
- Lines: **368**
- Docstring: _"Module: utility_manager.py Author: Michael Economou Date: 2025-05-31 UtilityManager - Handles utility functions and miscellaneous operations This manager [...]"_
- Classes: UtilityManager

### `core/window_config_manager.py` 
- Lines: **399**
- Docstring: _"Module: window_config_manager.py Author: Michael Economou Date: 2025-06-10 window_config_manager.py Manages window configuration including geometry, [...]"_
- Classes: WindowConfigManager

---

## `models/`

### `models/__init__.py` 
- Lines: **1**

### `models/file_item.py` 
- Lines: **115**
- Docstring: _"file_item.py Author: Michael Economou Date: 2025-05-01 This module defines the FileItem class, which represents a single file entry with attributes such [...]"_
- Classes: FileItem

### `models/file_table_model.py` 
- Lines: **887**
- Docstring: _"file_table_model.py Author: Michael Economou Date: 2025-05-01 This module defines the FileTableModel class, which is a custom QAbstractTableModel for [...]"_
- Classes: FileTableModel

---

## `modules/`

### `modules/__init__.py` 
- Lines: **1**

### `modules/base_module.py` 
- Lines: **79**
- Docstring: _"Module: base_module.py Author: Michael Economou Date: 2025-05-31 Base module for all rename modules."_
- Classes: BaseRenameModule

### `modules/counter_module.py` 
- Lines: **213**
- Docstring: _"Module: counter_module.py Author: Michael Economou Date: 2025-05-31 This module defines a rename module that inserts an incrementing counter into [...]"_
- Classes: CounterModule

### `modules/metadata_module.py` 
- Lines: **404**
- Docstring: _"Module: metadata_module.py Author: Michael Economou Date: 2025-05-31 This module provides logic for extracting metadata fields (such as creation date, [...]"_
- Classes: MetadataModule

### `modules/metadata_module_bak.py` 
- Lines: **404**
- Docstring: _"Module: metadata_module.py Author: Michael Economou Date: 2025-05-31 This module provides logic for extracting metadata fields (such as creation date, [...]"_
- Classes: MetadataModule

### `modules/name_transform_module.py` 
- Lines: **72**
- Docstring: _"Module: name_transform_module.py Author: Michael Economou Date: 2025-05-31 modules/name_transform_module.py Applies case and separator transformations to [...]"_
- Classes: NameTransformModule

### `modules/original_name_module.py` 
- Lines: **65**
- Docstring: _"Module: original_name_module.py Author: Michael Economou Date: 2025-05-31 original_name_module.py Module for applying original name transformations."_
- Classes: OriginalNameModule

### `modules/specified_text_module.py` 
- Lines: **327**
- Docstring: _"Module: specified_text_module.py Author: Michael Economou Date: 2025-05-31 This module defines a rename module that inserts user-specified text into [...]"_
- Classes: SpecifiedTextModule

### `modules/text_removal_module.py` 
- Lines: **248**
- Docstring: _"Module: text_removal_module.py Author: Michael Economou Date: 2025-01-07 This module provides functionality to remove specific text patterns from [...]"_
- Classes: TextRemovalModule

---

## `scripts/`

### `scripts/generate_project_context.py` 
- Lines: **261**
- Docstring: _"Generate a high-level project context file for AI assistants (e.g. VS Code Copilot). It scans the repository, finds Python files, extracts: - line counts [...]"_
- Functions: is_ignored_dir, get_module_summary, group_by_top_level_dir, find_python_files, main

---

## `tests/`

### `tests/__init__.py` 
- Lines: **1**

### `tests/conftest.py` 
- Lines: **92**
- Docstring: _"Module: conftest.py Author: Michael Economou Date: 2025-05-31 Global pytest configuration and fixtures for the oncutf test suite. Includes CI-friendly [...]"_
- Functions: pytest_configure, pytest_collection_modifyitems, ci_environment, pyqt5_available, mock_theme_colors, sample_metadata

### `tests/mocks.py` 
- Lines: **18**
- Docstring: _"Module: mocks.py Author: Michael Economou Date: 2025-05-31"_
- Classes: MockFileItem

### `tests/test_backup_simple.py` 
- Lines: **96**
- Docstring: _"Module: test_backup_simple.py Author: Michael Economou Date: 2025-05-31 Simple backup manager tests for development verification. Tests basic [...]"_
- Classes: TestBackupSimple

### `tests/test_counter.py` 
- Lines: **29**
- Docstring: _"Module: test_counter.py Author: Michael Economou Date: 2025-05-31 This module provides functionality for the OnCutF batch file renaming application."_
- Functions: test_counter_default, test_counter_step_padding

### `tests/test_counter_module.py` 
- Lines: **91**
- Docstring: _"Module: test_counter_module.py Author: Michael Economou Date: 2025-05-31 This module provides functionality for the OnCutF batch file renaming application."_
- Functions: test_counter_module_default, test_counter_module_custom_start, test_counter_module_custom_padding, test_counter_module_step_and_index, test_counter_module_zero_padding, test_counter_module_negative_start, test_counter_module_negative_index, test_counter_module_zero_step, test_counter_module_invalid_input, test_counter_module_negative_step

### `tests/test_custom_msgdialog.py` 
- Lines: **157**
- Docstring: _"Module: test_custom_msgdialog.py Author: Michael Economou Date: 2025-05-31 This module contains unit tests for the CustomMessageDialog class used in the [...]"_
- Functions: test_esc_key_triggers_cancel, test_progress_updates_correctly, test_dialog_question_response_yes, test_dialog_question_response_no, test_information_dialog_sets_message, test_conflict_dialog_selection_skip, test_conflict_dialog_selection_overwrite, test_waiting_dialog_is_application_modal, test_escape_triggers_callback_and_close

### `tests/test_file_size_formatter.py` 
- Lines: **214**
- Docstring: _"Module: test_file_size_formatter.py Author: Michael Economou Date: 2025-05-31 test_file_size_formatter.py Test cases for the FileSizeFormatter utility. [...]"_
- Classes: TestFileSizeFormatter, TestIntegrationWithFileItem
- Functions: run_comparison_test

### `tests/test_filename_validator.py` 
- Lines: **197**
- Docstring: _"Module: test_filename_validator.py Author: Michael Economou Date: 2025-05-31 Tests for filename validation utilities"_
- Classes: TestFilenameValidator

### `tests/test_filesize.py` 
- Lines: **142**
- Docstring: _"Module: test_filesize.py Author: Michael Economou Date: 2025-05-31 test_filesize.py Test script to compare file size calculations between our application [...]"_
- Classes: TestFileSizeComparison
- Functions: run_manual_test

### `tests/test_hash_manager.py` 
- Lines: **485**
- Docstring: _"Module: test_hash_manager.py Author: Michael Economou Date: 2025-05-31 test_hash_manager.py Test module for hash calculation functionality."_
- Classes: TestHashManager, TestConvenienceFunctions, TestEventHandlerIntegration, TestErrorHandling, TestPerformance

### `tests/test_hash_worker_progress.py` 
- Lines: **272**
- Docstring: _"Module: test_hash_worker_progress.py Author: Michael Economou Date: 2025-05-31 test_hash_worker_progress.py Tests for HashWorker cumulative progress [...]"_
- Classes: TestHashWorkerProgress

### `tests/test_hierarchical_combo_box.py` 
- Lines: **347**
- Docstring: _"Module: test_hierarchical_combo_box.py Author: Michael Economou Date: 2025-01-11 Tests for HierarchicalComboBox widget Tests dropdown behavior, chevron [...]"_
- Classes: TestHierarchicalComboBox, TestHierarchicalComboBoxLogic

### `tests/test_human_readable.py` 
- Lines: **126**
- Docstring: _"Module: test_human_readable.py Author: Michael Economou Date: 2025-05-31 test_human_readable.py Test script to compare human-readable file size formatting [...]"_
- Functions: get_system_human_sizes, test_different_size_ranges, format_size_our_way, test_actual_files, test_edge_cases, format_size_decimal

### `tests/test_loading_dialog.py` 
- Lines: **133**
- Docstring: _"Module: test_loading_dialog.py Author: Michael Economou Date: 2025-05-31 This module contains tests for the loading dialog behavior used in the oncutf [...]"_
- Classes: FakeWorker
- Functions: parent_widget, dialog, test_progress_and_range, test_signal_integration

### `tests/test_logging.py` 
- Lines: **58**
- Docstring: _"Module: test_logging.py Author: Michael Economou Date: 2025-05-31 test_logging.py Tests the logging system setup to verify: - General logs (info/debug) go [...]"_
- Functions: clean_logs, run_tests

### `tests/test_metadata.py` 
- Lines: **36**
- Docstring: _"Module: test_metadata.py Author: Michael Economou Date: 2025-05-31 This module provides functionality for the OnCutF batch file renaming application."_
- Functions: test_metadata_from_date_attr, test_metadata_from_metadata_field

### `tests/test_metadata_commands.py` 
- Lines: **649**
- Docstring: _"Module: test_metadata_commands.py Author: Michael Economou Date: 2025-07-08 Test module for metadata command system. This module tests the undo/redo [...]"_
- Classes: TestEditMetadataFieldCommand, TestResetMetadataFieldCommand, TestSaveMetadataCommand, TestBatchMetadataCommand, TestMetadataCommandManager, TestIntegration

### `tests/test_metadata_module.py` 
- Lines: **109**
- Docstring: _"Module: test_metadata_module.py Author: Michael Economou Date: 2025-05-31 This module provides functionality for the OnCutF batch file renaming application."_
- Functions: setup_function, test_metadata_module_basic, test_metadata_module_missing_field, test_metadata_module_metadata_dict, test_metadata_module_exif_style_date, test_metadata_module_invalid_date_format, test_metadata_module_date_with_timezone, test_metadata_module_unknown_field_type, test_metadata_module_with_cache_priority, test_metadata_module_cache_fallback_to_file_metadata

### `tests/test_metadata_tree_view.py` 
- Lines: **282**
- Docstring: _"Module: test_metadata_tree_view.py Author: Michael Economou Date: 2025-01-11 Tests for MetadataTreeView widget Tests tree expansion, hover behavior, [...]"_
- Classes: TestMetadataTreeView, TestMetadataTreeViewLogic

### `tests/test_metadata_validation_system.py` 
- Lines: **470**
- Docstring: _"Module: test_metadata_validation_system.py Author: Michael Economou Date: 2025-05-31 Tests for metadata validation system Comprehensive pytest tests for [...]"_
- Classes: TestMetadataFieldValidator, TestMetadataValidatedWidgets, TestValidationIntegration

### `tests/test_metadata_worker.py` 
- Lines: **84**
- Docstring: _"Module: test_metadata_worker.py Author: Michael Economou Date: 2025-05-31 This module provides functionality for the OnCutF batch file renaming application."_
- Functions: fake_reader, fake_cache, test_metadata_worker_cancel_stops_early, test_metadata_worker_runs_to_completion

### `tests/test_progress_manager.py` 
- Lines: **125**
- Docstring: _"Module: test_progress_manager.py Author: Michael Economou Date: 2025-05-31 test_progress_manager.py Tests for the new unified ProgressManager."_
- Classes: TestProgressManager

### `tests/test_rename_integration.py` 
- Lines: **196**
- Docstring: _"Module: test_rename_integration.py Author: Michael Economou Date: 2025-05-31 Integration tests for the enhanced rename workflow with validation"_
- Classes: TestRenameIntegration

### `tests/test_rename_logic.py` 
- Lines: **103**
- Docstring: _"Module: test_rename_logic.py Author: Michael Economou Date: 2025-05-31 This module provides functionality for the OnCutF batch file renaming application."_
- Classes: MockFile
- Functions: temp_dir, test_build_plan_no_conflicts, test_build_plan_with_conflict, test_execute_rename_plan, test_execute_rename_skips_invalid_action

### `tests/test_safe_rename_workflow.py` 
- Lines: **264**
- Docstring: _"Test module for safe rename workflow functionality. This module tests the enhanced rename workflow that prevents Qt object lifecycle crashes while [...]"_
- Classes: TestSafeRenameWorkflow

### `tests/test_simple_hash_integration.py` 
- Lines: **143**
- Docstring: _"Module: test_simple_hash_integration.py Author: Michael Economou Date: 2025-05-31 test_simple_hash_integration.py Simple integration test for hash [...]"_
- Functions: test_hash_manager_basic_functionality, test_hash_manager_with_progress_callback, test_cumulative_size_calculation

### `tests/test_specified_text.py` 
- Lines: **31**
- Docstring: _"Module: test_specified_text.py Author: Michael Economou Date: 2025-05-31 This module provides functionality for the OnCutF batch file renaming application."_
- Functions: test_specified_text_simple, test_specified_text_invalid

### `tests/test_specified_text_module.py` 
- Lines: **48**
- Docstring: _"Module: test_specified_text_module.py Author: Michael Economou Date: 2025-05-31"_
- Functions: test_specified_text_valid, test_specified_text_trims_whitespace, test_specified_text_invalid_characters, test_specified_text_empty

### `tests/test_text_helpers.py` 
- Lines: **174**
- Docstring: _"Module: test_text_helpers.py Author: Michael Economou Date: 2025-05-31 test_text_helpers.py Tests for text helper functions in utils/text_helpers.py"_
- Classes: TestElideText, TestTruncateFilenameMiddle, TestFormatFileSizeStable, TestIntegration

### `tests/test_text_removal_module.py` 
- Lines: **133**
- Docstring: _"Test module for TextRemovalModule. Author: Michael Economou Date: 2025-01-24"_
- Classes: TestTextRemovalModule

### `tests/test_theme_integration.py` 
- Lines: **238**
- Docstring: _"Module: test_theme_integration.py Author: Michael Economou Date: 2025-01-11 Tests for theme integration across UI components Tests color consistency, QSS [...]"_
- Classes: TestThemeIntegration, TestThemeLogic

### `tests/test_timer_manager.py` 
- Lines: **70**
- Docstring: _"Module: test_timer_manager.py Author: Michael Economou Date: 2025-05-31 test_timer_manager.py Basic tests for the centralized timer management system."_
- Classes: TestTimerBasics

### `tests/test_tooltip_helper.py` 
- Lines: **174**
- Docstring: _"Module: test_tooltip_helper.py Author: Michael Economou Date: 2025-05-31 Tests for tooltip helper system"_
- Classes: TestTooltipHelper

### `tests/test_transform_utils.py` 
- Lines: **55**
- Docstring: _"Module: test_transform_utils.py Author: Michael Economou Date: 2025-05-31 This module provides functionality for the OnCutF batch file renaming application."_
- Functions: test_apply_transform_basic, test_apply_transform_greeklish, test_apply_transform_greeklish_passthrough

### `tests/test_validated_line_edit.py` 
- Lines: **126**
- Docstring: _"Module: test_validated_line_edit.py Author: Michael Economou Date: 2025-05-31 Tests for ValidatedLineEdit widget"_
- Classes: TestValidatedLineEdit

---

## `utils/`

### `utils/__init__.py` 
- Lines: **22**
- Docstring: _"Module: __init__.py Author: Michael Economou Date: 2025-05-31"_

### `utils/build_metadata_tree_model.py` 
- Lines: **572**
- Docstring: _"Module: build_metadata_tree_model.py Author: Michael Economou Date: 2025-05-31 utils/build_metadata_tree_model.py Provides a utility function for [...]"_
- Functions: format_key, classify_key, create_item, get_hidden_fields_for_level, build_metadata_tree_model

### `utils/cursor_helper.py` 
- Lines: **147**
- Docstring: _"Module: cursor_helper.py Author: Michael Economou Date: 2025-05-31 cursor_helper.py Utility functions for cursor management across the application. [...]"_
- Functions: wait_cursor, emergency_cursor_cleanup, force_restore_cursor, get_current_cursor_info, is_drag_cursor_active

### `utils/dialog_utils.py` 
- Lines: **105**
- Docstring: _"Module: dialog_utils.py Author: Michael Economou Date: 2025-05-31 dialog_utils.py Utility functions for dialog and widget positioning and management. [...]"_
- Functions: center_widget_on_parent, setup_dialog_size_and_center, show_dialog_smooth, show_info_message, show_error_message, show_question_message

### `utils/dpi_helper.py` 
- Lines: **225**
- Docstring: _"Module: dpi_helper.py Author: Michael Economou Date: 2025-06-10 dpi_helper.py DPI adaptation utilities for cross-platform font and UI scaling. Handles [...]"_
- Classes: DPIHelper
- Functions: get_dpi_helper, scale_font_size, scale_ui_size, get_font_sizes, log_dpi_info

### `utils/drag_visual_manager.py` 
- Lines: **1**

### `utils/drag_zone_validator.py` 
- Lines: **168**
- Docstring: _"Module: drag_zone_validator.py Author: Michael Economou Date: 2025-06-10 Drag Zone Validator - Common logic for drag & drop zone validation This module [...]"_
- Classes: DragZoneValidator

### `utils/exiftool_wrapper.py` 
- Lines: **501**
- Docstring: _"Module: exiftool_wrapper.py Author: Michael Economou Date: 2025-05-31 exiftool_wrapper.py This module provides a lightweight ExifTool wrapper using a [...]"_
- Classes: ExifToolWrapper

### `utils/file_drop_helper.py` 
- Lines: **122**
- Docstring: _"Module: file_drop_helper.py Author: Michael Economou Date: 2025-05-31 file_drop_helper.py This module provides modular logic for drag & drop handling in [...]"_
- Functions: analyze_drop, filter_allowed_files, ask_recursive_dialog, show_rejected_dialog, extract_file_paths

### `utils/file_size_calculator.py` 
- Lines: **187**
- Docstring: _"Module: file_size_calculator.py Author: Michael Economou Date: 2025-06-10 file_size_calculator.py Utility functions for calculating file and folder sizes [...]"_
- Functions: calculate_files_total_size, calculate_processed_size, calculate_folder_size, estimate_operation_time

### `utils/file_size_formatter.py` 
- Lines: **218**
- Docstring: _"Module: file_size_formatter.py Author: Michael Economou Date: 2025-06-10 file_size_formatter.py Cross-platform file size formatting utility. Supports both [...]"_
- Classes: FileSizeFormatter
- Functions: _ensure_locale_setup, get_default_formatter, format_file_size, format_file_size_system_compatible

### `utils/file_status_helpers.py` 
- Lines: **96**
- Docstring: _"file_status_helpers.py Central helpers for file metadata and hash status. All lookups use path normalization for cross-platform compatibility."_
- Functions: get_metadata_for_file, has_metadata, get_hash_for_file, has_hash, batch_metadata_status, batch_hash_status

### `utils/filename_validator.py` 
- Lines: **265**
- Docstring: _"Module: filename_validator.py Author: Michael Economou Date: 2025-05-31 This module provides functions for validating and cleaning filenames according to [...]"_
- Functions: is_valid_filename_char, clean_filename_text, clean_trailing_chars, validate_filename_part, should_allow_character_input, get_validation_error_message, is_validation_error_marker, clean_and_validate, prepare_final_filename

### `utils/fonts.py` 
- Lines: **293**
- Docstring: _"Module: fonts.py Author: Michael Economou Date: 2025-05-31 Font utilities for Inter fonts Manages loading and providing access to the Inter font family"_
- Classes: InterFonts
- Functions: _get_inter_fonts, get_inter_font, get_inter_css_weight, get_inter_family

### `utils/fonts_rc.py` 
- Lines: **104156**
- Docstring: _"Module: fonts_rc.py Author: Michael Economou Date: 2025-06-20"_
- Functions: qInitResources, qCleanupResources

### `utils/fonts_rc_temp_backup.py` 
- Lines: **156328**
- Docstring: _"Module: fonts_rc_temp_backup.py Author: Michael Economou Date: 2025-06-20"_
- Functions: qInitResources, qCleanupResources

### `utils/icon_cache.py` 
- Lines: **90**
- Docstring: _"Module: icon_cache.py Author: Michael Economou Date: 2025-05-31 This utility module provides functions for caching QIcons or other visual assets to avoid [...]"_
- Functions: prepare_status_icons, load_preview_status_icons

### `utils/icon_utilities.py` 
- Lines: **69**
- Docstring: _"Module: icons.py Author: Michael Economou Date: 2025-05-31 This utility module provides functions for creating and preparing icons, typically using QIcon [...]"_
- Functions: create_colored_icon

### `utils/icons_loader.py` 
- Lines: **239**
- Docstring: _"Module: icons_loader.py Author: Michael Economou Date: 2025-05-31 This module provides unified icon loading functionality for the application. It handles [...]"_
- Classes: ThemeIconLoader
- Functions: load_metadata_icons, get_menu_icon, get_menu_icon_path, get_app_icon

### `utils/init_logging.py` 
- Lines: **37**
- Docstring: _"Module: init_logging.py Author: Michael Economou Date: 2025-05-31 init_logging.py Provides a single entry point to initialize the logging system for the [...]"_
- Functions: init_logging

### `utils/json_config_manager.py` 
- Lines: **338**
- Docstring: _"Module: json_config_manager.py Author: Michael Economou Date: 2025-06-10 json_config_manager.py A comprehensive JSON-based configuration manager for any [...]"_
- Classes: ConfigCategory, WindowConfig, FileHashConfig, AppConfig, JSONConfigManager
- Functions: create_app_config_manager, get_app_config_manager, load_config, save_config

### `utils/logger_factory.py` 
- Lines: **121**
- Docstring: _"Module: logger_factory.py Author: Michael Economou Date: 2025-05-31 logger_factory.py Optimized logger factory with caching for improved performance. [...]"_
- Classes: LoggerFactory
- Functions: get_cached_logger

### `utils/logger_file_helper.py` 
- Lines: **59**
- Docstring: _"Module: logger_file_helper.py Author: Michael Economou Date: 2025-05-31 logger_file_helper.py Provides utility functions to attach file handlers to a [...]"_
- Functions: add_file_handler

### `utils/logger_helper.py` 
- Lines: **138**
- Docstring: _"Module: logger_helper.py Author: Michael Economou Date: 2025-05-31 logger_helper.py Provides utility functions for working with loggers in a safe and [...]"_
- Classes: DevOnlyFilter
- Functions: safe_text, safe_log, patch_logger_safe_methods, get_logger

### `utils/logger_setup.py` 
- Lines: **116**
- Docstring: _"Module: logger_setup.py Author: Michael Economou Date: 2025-05-31 logger_setup.py This module provides the ConfigureLogger class for setting up logging in [...]"_
- Classes: ConfigureLogger
- Functions: safe_text, safe_log

### `utils/metadata_cache_helper.py` 
- Lines: **368**
- Docstring: _"Module: metadata_cache_helper.py Author: Michael Economou Date: 2025-06-20 utils/metadata_cache_helper.py Unified metadata cache access helper to [...]"_
- Classes: MetadataCacheHelper
- Functions: get_metadata_cache_helper

### `utils/metadata_exporter.py` 
- Lines: **425**
- Docstring: _"Module: metadata_exporter.py Author: Michael Economou Date: 2025-06-10 utils/metadata_exporter.py Metadata export utility supporting multiple human- [...]"_
- Classes: MetadataExporter

### `utils/metadata_field_mapper.py` 
- Lines: **450**
- Docstring: _"Module: metadata_field_mapper.py Author: Michael Economou Date: 2025-01-09 Centralized metadata field mapping and value formatting for file table columns [...]"_
- Classes: MetadataFieldMapper

### `utils/metadata_field_validators.py` 
- Lines: **351**
- Docstring: _"Module: metadata_field_validators.py Author: Michael Economou Date: 2025-06-20 metadata_field_validators.py Validation system for metadata field editing. [...]"_
- Classes: MetadataFieldValidator

### `utils/metadata_loader.py` 
- Lines: **192**
- Docstring: _"Module: metadata_loader.py Author: Michael Economou Date: 2025-05-31 Updated: 2025-05-23 This module defines the MetadataLoader class, responsible for [...]"_
- Classes: MetadataLoader

### `utils/metadata_validators.py` 
- Lines: **84**
- Docstring: _"Module: metadata_validators.py Author: Michael Economou Date: 2025-06-10 metadata_validators.py This module provides validation functions for metadata [...]"_
- Functions: validate_rotation, get_validator_for_key

### `utils/multiscreen_helper.py` 
- Lines: **300**
- Docstring: _"Module: multiscreen_helper.py Author: Michael Economou Date: 2025-01-21 Utility functions for handling window positioning in multiscreen desktop [...]"_
- Functions: get_screen_for_widget, center_dialog_on_parent_screen, center_dialog_on_screen, position_dialog_relative_to_parent, ensure_dialog_on_parent_screen, get_existing_directory_on_parent_screen, get_open_file_name_on_parent_screen, get_save_file_name_on_parent_screen

### `utils/path_normalizer.py` 
- Lines: **61**
- Docstring: _"path_normalizer.py Central path normalization function for the entire application. This module provides a single, consistent way to normalize file paths [...]"_
- Functions: normalize_path

### `utils/path_utils.py` 
- Lines: **258**
- Docstring: _"Module: path_utils.py Author: Michael Economou Date: 2025-06-10 path_utils.py Utility functions for robust path operations across different operating [...]"_
- Functions: get_project_root, get_resources_dir, get_assets_dir, get_style_dir, get_fonts_dir, get_icons_dir, get_images_dir, get_theme_dir, get_resource_path, resource_exists, normalize_path, paths_equal, find_file_by_path, find_parent_with_attribute

### `utils/placeholder_helper.py` 
- Lines: **211**
- Docstring: _"Module: placeholder_helper.py Author: Michael Economou Date: 2025-01-15 Unified placeholder management system for all widgets. Provides consistent [...]"_
- Classes: PlaceholderHelper
- Functions: create_placeholder_helper

### `utils/preview_engine.py` 
- Lines: **165**
- Docstring: _"Module: preview_engine.py Author: Michael Economou Date: 2025-06-01 preview_engine.py This module provides the core logic for applying rename rules [...]"_
- Functions: apply_rename_modules, _generate_module_cache_key, clear_module_cache

### `utils/preview_generator.py` 
- Lines: **159**
- Docstring: _"Preview name generation functions for file renaming. This module provides functions to generate preview names for file renaming based on user-defined [...]"_
- Functions: generate_preview_names

### `utils/progress_dialog.py` 
- Lines: **381**
- Docstring: _"Module: progress_dialog.py Author: Michael Economou Date: 2025-06-01 progress_dialog.py Unified progress dialog for all background operations in the [...]"_
- Classes: ProgressDialog

### `utils/rename_logic.py` 
- Lines: **248**
- Docstring: _"Module: rename_logic.py Author: Michael Economou Date: 2025-06-01 rename_logic.py This module provides the core logic for building, resolving, and [...]"_
- Functions: is_case_only_change, safe_case_rename, build_rename_plan, resolve_rename_conflicts, execute_rename_plan, get_preview_pairs

### `utils/renamer.py` 
- Lines: **253**
- Docstring: _"Module: renamer.py Author: Michael Economou Date: 2025-06-01 Initializes the Renamer with required inputs for batch renaming. Parameters: files [...]"_
- Classes: RenameResult, Renamer
- Functions: filter_metadata_safe

### `utils/smart_icon_cache.py` 
- Lines: **447**
- Docstring: _"Smart Icon Cache Module. This module provides an advanced icon caching system with LRU eviction, memory optimization, and intelligent loading patterns. [...]"_
- Classes: IconCacheEntry, SmartIconCache
- Functions: get_smart_icon_cache, initialize_smart_icon_cache, get_cached_icon, preload_icons, set_icon_theme

### `utils/svg_icon_generator.py` 
- Lines: **263**
- Docstring: _"Module: svg_icon_generator.py Author: Michael Economou Date: 2025-06-20 svg_icon_generator.py SVG Icon Generator for OnCutF metadata status icons. Creates [...]"_
- Classes: SVGIconGenerator
- Functions: generate_metadata_icons, generate_hash_icon

### `utils/text_helpers.py` 
- Lines: **135**
- Docstring: _"Module: text_helpers.py Author: Michael Economou Date: 2025-05-31 text_helpers.py Utility functions for text manipulation and formatting. Provides helper [...]"_
- Functions: elide_text, truncate_filename_middle, format_file_size_stable

### `utils/theme.py` 
- Lines: **45**
- Docstring: _"Module: theme.py Author: Michael Economou Date: 2025-05-31 theme.py Theme management system using the new ThemeEngine. Provides color access and theme [...]"_
- Functions: _get_theme_engine, get_theme_color, get_current_theme_colors, get_qcolor

### `utils/theme_engine.py` 
- Lines: **1549**
- Docstring: _"Module: theme_engine.py Author: Michael Economou Date: 2025-06-20 Simplified theme engine for OnCutF application. Applies all styling globally to handle [...]"_
- Classes: ThemeEngine

### `utils/theme_font_generator.py` 
- Lines: **208**
- Docstring: _"Module: theme_font_generator.py Author: Michael Economou Date: 2025-06-20 theme_font_generator.py Generates CSS font styles with DPI-aware sizing for [...]"_
- Functions: generate_dpi_aware_css, get_tree_font_size, get_table_font_size, get_ui_font_sizes

### `utils/time_formatter.py` 
- Lines: **254**
- Docstring: _"Module: time_formatter.py Author: Michael Economou Date: 2025-06-10 time_formatter.py Time formatting utilities for progress dialogs. Formats elapsed and [...]"_
- Classes: TimeTracker, ProgressEstimator
- Functions: format_duration, format_time_range

### `utils/timer_manager.py` 
- Lines: **384**
- Docstring: _"Module: timer_manager.py Author: Michael Economou Date: 2025-05-31 timer_manager.py Centralized timer management system for improved performance and [...]"_
- Classes: TimerPriority, TimerType, TimerManager
- Functions: get_timer_manager, schedule_ui_update, schedule_drag_cleanup, schedule_selection_update, schedule_metadata_load, schedule_scroll_adjust, schedule_resize_adjust, schedule_dialog_close, cancel_timer, cancel_timers_by_type, cleanup_all_timers

### `utils/tooltip_helper.py` 
- Lines: **451**
- Docstring: _"Module: tooltip_helper.py Author: Michael Economou Date: 2025-05-31 This module provides centralized tooltip management with custom styling and behavior. [...]"_
- Classes: TooltipType, CustomTooltip, TooltipHelper
- Functions: show_tooltip, show_error_tooltip, show_warning_tooltip, show_info_tooltip, show_success_tooltip, setup_tooltip

### `utils/transform_utils.py` 
- Lines: **232**
- Docstring: _"Module: transform_utils.py Author: Michael Economou Date: 2025-05-31 transform_utils.py Utility functions for applying text transformations to filenames, [...]"_
- Functions: strip_accents, safe_upper, to_greeklish, apply_transform

### `utils/validate_filename_text.py` 
- Lines: **31**
- Docstring: _"Module: validate_filename_text.py Author: Michael Economou Date: 2025-06-10 This module defines a utility function for validating user-supplied text [...]"_
- Functions: is_valid_filename_text

---

## `widgets/`

### `widgets/__init__.py` 
- Lines: **63**
- Docstring: _"Module: __init__.py Author: Michael Economou Date: 2025-06-01 widgets package initialization This package contains all custom widgets used in the OnCutF [...]"_

### `widgets/base_validated_input.py` 
- Lines: **330**
- Docstring: _"Module: base_validated_input.py Author: Michael Economou Date: 2025-06-01 Base class for validated input widgets providing common validation [...]"_
- Classes: BaseValidatedInput

### `widgets/bulk_rotation_dialog.py` 
- Lines: **365**
- Docstring: _"Module: bulk_rotation_dialog.py Author: Michael Economou Date: 2025-06-01 bulk_rotation_dialog.py Dialog for bulk rotation operations."_
- Classes: BulkRotationDialog

### `widgets/custom_file_system_model.py` 
- Lines: **197**
- Docstring: _"Module: custom_file_system_model.py Author: Michael Economou Date: 2025-05-31 custom_file_system_model.py Custom QFileSystemModel that uses feather icons [...]"_
- Classes: CustomFileSystemModel

### `widgets/custom_message_dialog.py` 
- Lines: **436**
- Docstring: _"Module: custom_msgdialog.py Author: Michael Economou Date: 2025-05-31 custom_msgdialog.py This module defines the CustomMessageDialog class, a flexible [...]"_
- Classes: CustomMessageDialog

### `widgets/custom_splash_screen.py` 
- Lines: **386**
- Docstring: _"Module: custom_splash_screen.py Author: Michael Economou Date: 2025-06-25 custom_splash_screen.py Custom splash screen widget for the oncutf application. [...]"_
- Classes: CustomSplashScreen

### `widgets/file_table_view.py` 
- Lines: **2680**
- Docstring: _"Module: file_table_view.py Author: Michael Economou Date: 2025-05-31 Custom QTableView with Windows Explorer-like behavior: - Full-row selection with [...]"_
- Classes: FileTableView

### `widgets/file_tree_view.py` 
- Lines: **784**
- Docstring: _"Module: file_tree_view.py Author: Michael Economou Date: 2025-05-31 file_tree_view.py Implements a custom tree view with clean single-item drag [...]"_
- Classes: FileTreeView, DragCancelFilter

### `widgets/final_transform_container.py` 
- Lines: **304**
- Docstring: _"Module: final_transform_container.py Author: Michael Economou Date: 2025-06-25 final_transform_container.py Container widget for the final transformation [...]"_
- Classes: FinalTransformContainer, GreeklishToggle

### `widgets/hierarchical_combo_box.py` 
- Lines: **357**
- Docstring: _"Hierarchical QComboBox widget with tree-like structure support. This module provides a hierarchical QComboBox widget that displays items in a tree-like [...]"_
- Classes: _AliasHeaderTreeView, HierarchicalComboBox

### `widgets/interactive_header.py` 
- Lines: **250**
- Docstring: _"Module: interactive_header.py Author: Michael Economou Date: 2025-05-31 interactive_header.py This module defines InteractiveHeader, a subclass of [...]"_
- Classes: InteractiveHeader

### `widgets/metadata_edit_dialog.py` 
- Lines: **507**
- Docstring: _"Module: metadata_edit_dialog.py Author: Michael Economou Date: 2025-06-01 metadata_edit_dialog.py Generic dialog for editing metadata fields. Based on [...]"_
- Classes: MetadataEditDialog

### `widgets/metadata_history_dialog.py` 
- Lines: **480**
- Docstring: _"Module: metadata_history_dialog.py Author: Michael Economou Date: 2025-01-15 Dialog for viewing and managing metadata command history. Provides interface [...]"_
- Classes: MetadataHistoryDialog
- Functions: show_metadata_history_dialog

### `widgets/metadata_tree_view.py` 
- Lines: **3264**
- Docstring: _"Custom QTreeView widget with drag-and-drop metadata loading support. This module defines a custom QTreeView widget that supports drag-and-drop [...]"_
- Classes: MetadataProxyModel, MetadataTreeView

### `widgets/metadata_validated_input.py` 
- Lines: **388**
- Docstring: _"Module: metadata_validated_input.py Author: Michael Economou Date: 2025-06-01 Validated input widgets specifically designed for metadata field editing. [...]"_
- Classes: MetadataValidatedLineEdit, MetadataValidatedTextEdit, MetadataRotationComboBox
- Functions: create_metadata_input_widget

### `widgets/metadata_waiting_dialog.py` 
- Lines: **113**
- Docstring: _"Module: metadata_waiting_dialog.py Author: Michael Economou Date: 2025-06-01 operation_dialog.py Frameless waiting dialog for background operations [...]"_
- Classes: OperationDialog

### `widgets/metadata_widget.py` 
- Lines: **1364**
- Docstring: _"Module: metadata_widget.py Author: Michael Economou Date: 2025-05-31 Widget for metadata selection (file dates or EXIF), with optimized signal emission system."_
- Classes: MetadataWidget

### `widgets/metadata_widget_bak.py` 
- Lines: **1364**
- Docstring: _"Module: metadata_widget.py Author: Michael Economou Date: 2025-05-31 Widget for metadata selection (file dates or EXIF), with optimized signal emission system."_
- Classes: MetadataWidget

### `widgets/metadata_worker.py` 
- Lines: **352**
- Docstring: _"Module: metadata_worker.py Author: Michael Economou Date: 2025-05-31 Updated: 2025-01-31 This module defines a background worker that loads metadata from [...]"_
- Classes: MetadataWorker

### `widgets/name_transform_widget.py` 
- Lines: **122**
- Docstring: _"Module: name_transform_widget.py Author: Michael Economou Date: 2025-06-15 name_transform_widget.py UI widget for configuring NameTransformModule. [...]"_
- Classes: NameTransformWidget

### `widgets/original_name_widget.py` 
- Lines: **70**
- Docstring: _"Module: original_name_widget.py Author: Michael Economou Date: 2025-06-15 Rename module that reuses original filename."_
- Classes: OriginalNameWidget

### `widgets/performance_widget.py` 
- Lines: **183**
- Docstring: _"Module: performance_widget.py Author: Michael Economou Date: 2025-01-27 Performance Widget for displaying UnifiedRenameEngine performance metrics."_
- Classes: PerformanceWidget

### `widgets/preview_tables_view.py` 
- Lines: **574**
- Docstring: _"Module: preview_tables_view.py Author: Michael Economou Date: 2025-06-15 preview_tables_view.py Implements a view that manages the preview tables for [...]"_
- Classes: PreviewTableWidget, PreviewTablesView

### `widgets/progress_manager.py` 
- Lines: **223**
- Docstring: _"Module: progress_manager.py Author: Michael Economou Date: 2025-06-25 Unified Progress Manager for all file operations. This module provides a [...]"_
- Classes: ProgressManager
- Functions: create_hash_progress_manager, create_metadata_progress_manager, create_copy_progress_manager

### `widgets/progress_widget.py` 
- Lines: **766**
- Docstring: _"Module: progress_widget.py Author: Michael Economou Date: 2025-06-01 Unified progress widget supporting both basic and enhanced progress tracking. [...]"_
- Classes: ProgressWidget
- Functions: create_basic_progress_widget, create_size_based_progress_widget

### `widgets/realtime_validation_widget.py` 
- Lines: **200**
- Docstring: _"Module: realtime_validation_widget.py Author: Michael Economou Date: 2025-01-27 Real-time Validation Widget for immediate validation feedback."_
- Classes: RealTimeValidationWidget

### `widgets/rename_conflict_resolver.py` 
- Lines: **162**
- Docstring: _"Module: rename_conflict_resolver.py Author: Michael Economou Date: 2025-06-15 This module provides a conflict resolution system for file rename [...]"_
- Classes: ConflictResolutionStrategy, RenameConflictResolver

### `widgets/rename_history_dialog.py` 
- Lines: **372**
- Docstring: _"Module: rename_history_dialog.py Author: Michael Economou Date: 2025-06-01 rename_history_dialog.py Dialog for viewing and managing rename history with [...]"_
- Classes: RenameHistoryDialog
- Functions: show_rename_history_dialog

### `widgets/rename_module_widget.py` 
- Lines: **481**
- Docstring: _"Module: rename_module_widget.py Author: Michael Economou Date: 2025-06-15 This module defines a custom widget for managing rename modules within the [...]"_
- Classes: RenameModuleWidget

### `widgets/rename_modules_area.py` 
- Lines: **505**
- Docstring: _"Module: rename_modules_area.py Author: Michael Economou Date: 2025-06-15 rename_modules_area.py Container widget that holds multiple RenameModuleWidget [...]"_
- Classes: RenameModulesArea

### `widgets/ui_delegates.py` 
- Lines: **496**
- Docstring: _"Custom QStyledItemDelegate classes for enhanced UI components. This module provides custom delegates for enhanced UI components: - FileTableHoverDelegate: [...]"_
- Classes: ComboBoxItemDelegate, FileTableHoverDelegate, TreeViewItemDelegate, MetadataTreeItemDelegate

### `widgets/validated_line_edit.py` 
- Lines: **111**
- Docstring: _"Module: validated_line_edit.py Author: Michael Economou Date: 2025-05-31 This module provides a custom QLineEdit widget with built-in filename validation, [...]"_
- Classes: ValidatedLineEdit

### `widgets/view_helpers.py` 
- Lines: **34**
- Docstring: _"Module: view_helpers.py Author: Michael Economou Date: 2025-05-31 view_helpers.py This module provides view-level helper functions for UI updates in the [...]"_
- Functions: update_info_icon

