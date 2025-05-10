"""
utils/build_metadata_tree_model.py

Author: Michael Economou
Date: 2025-05-09

Provides a utility function for converting nested metadata
(dicts/lists) into a QStandardItemModel suitable for display in a QTreeView.
"""

from PyQt5.QtGui import QStandardItemModel, QStandardItem

def build_metadata_tree_model(metadata: dict) -> QStandardItemModel:
    """
    Recursively builds a QStandardItemModel from nested metadata (dicts, lists, primitives).

    Args:
        metadata (dict): The metadata dictionary to visualize.

    Returns:
        QStandardItemModel: A hierarchical model suitable for QTreeView.
    """
    model = QStandardItemModel()
    model.setHorizontalHeaderLabels(["Key", "Value"])

    def add_items(parent, data):
        if isinstance(data, dict):
            for key, value in data.items():
                key_item = QStandardItem(str(key))
                if isinstance(value, (dict, list)):
                    value_item = QStandardItem("")
                    key_item.setEditable(False)
                    value_item.setEditable(False)
                    add_items(key_item, value)
                else:
                    value_item = QStandardItem(str(value))
                parent.appendRow([key_item, value_item])
        elif isinstance(data, list):
            for index, value in enumerate(data):
                key_item = QStandardItem(f"[{index}]")
                if isinstance(value, (dict, list)):
                    value_item = QStandardItem("")
                    add_items(key_item, value)
                else:
                    value_item = QStandardItem(str(value))
                parent.appendRow([key_item, value_item])
        else:
            parent.appendRow([QStandardItem("value"), QStandardItem(str(data))])

    add_items(model.invisibleRootItem(), metadata)
    return model


