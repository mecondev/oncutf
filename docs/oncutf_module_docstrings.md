# oncutf Module Docstrings

**Author:** Michael Economou
**Date:** 2025-05-06

This document contains the module-level docstrings for the main Python files
in the oncutf project. It serves as internal documentation and quick reference
for developers working on the application's architecture and modular design.

Each entry includes:
- The module name and file path
- Author and creation date
- A description of the module's purpose and scope

## `modules/counter_module.py`
Module: counter_module.py

Author: Michael Economou
Date: 2025-05-02

This module defines a rename module that inserts an incrementing counter
into filenames. It is used within the oncutf application to generate
sequential file names based on configurable start value, step, and padding.

## `modules/metadata_module.py`
Module: metadata_module.py

Author: Michael Economou
Date: 2025-05-04

This module provides a widget-based rename module that allows selecting
a metadata field (such as creation date, modification date, or EXIF tag)
to include in the renamed filename.

It is used in the oncutf tool to dynamically extract and apply file
metadata during batch renaming.

## `modules/specified_text_module.py`
Module: specified_text_module.py

Author: Michael Economou
Date: 2025-05-02

This module defines a rename module that inserts user-specified text
into filenames. It allows users to prepend, append, or inject static
text at a defined position within the filename.

Used in the oncutf application as one of the modular renaming components.

## `utils/file_loader.py`
Module: file_loader.py

Author: Michael Economou
Date: 2025-05-01

This utility module handles the logic for selecting and loading files
from one or more folders into the application's data model.

It supports recursive directory scanning, file type filtering, and
preparation of file data for use in the oncutf renaming system.

## `utils/filename_validator.py`
Module: filename_validator.py

Author: Michael Economou
Date: 2025-05-01

This utility module provides logic for validating filenames across
different operating systems. It checks for invalid characters, reserved
names, and other constraints to ensure safe and portable file naming.

Used by oncutf to prevent errors during batch renaming.

## `widgets/metadata_worker.py`
Module: metadata_worker.py

Author: Michael Economou
Date: 2025-05-01

This module defines a background worker located in the `widgets` package
responsible for retrieving metadata from files asynchronously. Running
in its own thread decouples metadata extraction from the UI thread and
keeps the application responsive.

Typically used in the oncutf application to run exiftool or similar
metadata extractors in the background and emit signals when data is ready.

## `main.py`
Module: main.py

Author: Michael Economou
Date: 2025-05-01

This module serves as the entry point for the oncutf application.
It sets up logging, initializes the Qt application with a stylesheet, creates
and displays the main window, and starts the application's main event loop.

## `main_window.py`
Module: main_window.py

Author: Michael Economou
Date: 2025-05-01

This module defines the MainWindow class, which implements the primary user interface
for the oncutf application. It includes logic for loading files from folders, launching
metadata extraction in the background, and managing user interaction such as rename previews.

## `models/file_item.py`
Module: file_item.py

Author: Michael Economou
Date: 2025-05-01

This module defines the FileItem class which represents an individual file
in the application. It stores file properties including path, name, metadata,
and status information, serving as the core data structure for file handling
throughout the oncutf application.

## `models/file_table_model.py`
Module: file_table_model.py

Author: Michael Economou
Date: 2025-05-01

This module implements a custom table model (FileTableModel) that manages
the presentation and interaction of file data in the main file table view.
It handles sorting, filtering, and display of file attributes, as well as
interacting with the underlying collection of FileItem objects.

## `widgets/custom_table_view.py`
Module: custom_table_view.py

Author: Michael Economou
Date: 2025-05-02

This module provides a customized QTableView implementation with enhanced
features such as drag-and-drop support, custom selection behavior, and
visual indicators. It serves as the primary UI component for displaying
and interacting with files in the oncutf application.

## `widgets/metadata_widget.py`
Module: metadata_widget.py

Author: Michael Economou
Date: 2025-05-03

This module implements a widget for displaying file metadata in a
user-friendly format. It supports multiple view modes, collapsible
sections, and filtering capabilities to help users easily navigate
complex metadata structures extracted from files.

## `widgets/rename_module_widget.py`
Module: rename_module_widget.py

Author: Michael Economou
Date: 2025-05-02

This module defines the base class for all rename module widgets in the
oncutf application. It provides the common interface and functionality
that all specific rename modules inherit from, including configuration
UI, validation, and preview generation capabilities.

## `utils/json_config_manager.py`
Module: json_config_manager.py

Author: Michael Economou
Date: 2025-06-20

This module provides a comprehensive JSON-based configuration manager for any application.
It handles JSON serialization, deserialization, and management with support for
multiple configuration categories, automatic backups, and thread-safe operations.

The module includes ConfigCategory base class for type-safe configuration handling,
WindowConfig, FileHashConfig, and AppConfig classes for specific application needs,
and JSONConfigManager as the main configuration management class.

## `utils/path_utils.py`
Module: path_utils.py

Author: Michael Economou
Date: 2025-06-20

This utility module provides cross-platform path normalization and comparison functions.
It addresses path separator inconsistencies between different operating systems and
ensures reliable path-based operations throughout the application.

Key functions include normalize_path(), paths_equal(), and find_file_by_path()
for consistent path handling across Windows and Unix-like systems.

## Related Documentation

- **Database System**: [Database Quick Start](database_quick_start.md) | [Database System](database_system.md)
- **Safe Operations**: [Safe Rename Workflow](safe_rename_workflow.md)
- **Case-Sensitive Renaming**: [Case-Sensitive Rename Guide](case_sensitive_rename_guide.md)
- **Progress Tracking**: [Progress Manager System](progress_manager_system.md)
- **Configuration**: [JSON Config System](json_config_system.md)
