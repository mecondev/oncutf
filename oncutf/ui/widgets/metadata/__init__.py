"""Module: metadata package

Author: Michael Economou
Date: 2025-12-24

Package for MetadataWidget components - field formatters and handlers.
"""

from oncutf.ui.widgets.metadata.category_manager import CategoryManager
from oncutf.ui.widgets.metadata.field_formatter import FieldFormatter
from oncutf.ui.widgets.metadata.hash_handler import HashHandler
from oncutf.ui.widgets.metadata.metadata_keys_handler import MetadataKeysHandler

__all__ = ["CategoryManager", "FieldFormatter", "HashHandler", "MetadataKeysHandler"]
