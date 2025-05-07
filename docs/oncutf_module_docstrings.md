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

## `workers/metadata_worker.py`
Module: metadata_worker.py

Author: Michael Economou
Date: 2025-05-01

This module defines a worker thread or task responsible for retrieving
metadata from files asynchronously. It decouples metadata extraction
from the UI thread to keep the application responsive.

Typically used in the oncutf application to run exiftool or similar
metadata extractors in the background and emit signals when data is ready.

