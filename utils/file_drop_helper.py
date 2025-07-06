"""
Module: file_drop_helper.py

Author: Michael Economou
Date: 2025-05-31

file_drop_helper.py
This module provides modular logic for drag & drop handling in the oncutf file table.
It detects the drop type (folder, files, mixed), checks allowed file types,
triggers custom dialogs (recursive, rejected files), and returns results for the UI.
"""
import os
from typing import Dict, List, Literal, Tuple

from core.qt_imports import QMimeData

from config import ALLOWED_EXTENSIONS

# Custom dialogs will be imported when connected
# from widgets.custommsg_dialog import show_recursive_dialog, show_rejected_dialog


DropType = Literal["single_folder", "multiple_folders", "files", "mixed", "unknown"]


def analyze_drop(paths: List[str]) -> Dict:
    """
    Analyze the given paths from drag & drop and return information about the drop type.
    Returns a dict with keys: type, folders, files, rejected.
    """
    folders = [p for p in paths if os.path.isdir(p)]
    files = [p for p in paths if os.path.isfile(p)]
    rejected = [p for p in paths if not os.path.exists(p)]

    if len(folders) == 1 and not files:
        drop_type = "single_folder"
    elif len(folders) > 1 and not files:
        drop_type = "multiple_folders"
    elif files and not folders:
        drop_type = "files"
    elif files and folders:
        drop_type = "mixed"
    else:
        drop_type = "unknown"

    return {
        "type": drop_type,
        "folders": folders,
        "files": files,
        "rejected": rejected
    }


def filter_allowed_files(files: List[str]) -> Tuple[List[str], List[str]]:
    """
    Returns two lists: allowed files (by ALLOWED_EXTENSIONS) and rejected files.
    """
    allowed = []
    rejected = []
    for f in files:
        ext = os.path.splitext(f)[1].lower().lstrip(".")
        if ext in ALLOWED_EXTENSIONS:
            allowed.append(f)
        else:
            rejected.append(f)
    return allowed, rejected


def ask_recursive_dialog(folder_path: str, parent=None) -> bool:
    """
    Show a custom dialog asking if the user wants a recursive scan for the folder.
    Returns True if the user selects Yes.
    """
    from widgets.custom_msgdialog import CustomMessageDialog
    folder_name = os.path.basename(folder_path)
    message = f"Do you want to import files from all subfolders of '{folder_name}' as well?"
    return CustomMessageDialog.question(parent, "Recursive Import", message, yes_text="Yes (recursive)", no_text="No (top folder only)")


def show_rejected_dialog(rejected: list[str], imported_count: int = 0, parent=None) -> None:
    """
    Show a custom dialog listing the rejected files/folders, with a summary message above a scrollable area.
    """
    from widgets.custom_msgdialog import CustomMessageDialog
    skipped_count = len(rejected)
    if skipped_count == 0:
        return
    summary = f"{imported_count} files imported, {skipped_count} skipped."
    if skipped_count <= 5:
        # Show as simple message
        message = summary + "\n\n" + "\n".join(rejected)
        CustomMessageDialog.information(parent, "Some files were skipped", message)
    else:
        # Show summary and scrollable list
        from core.qt_imports import QDialog, QLabel, QPushButton, QTextEdit, QVBoxLayout
        dialog = QDialog(parent)
        dialog.setWindowTitle("Some files were skipped")
        layout = QVBoxLayout(dialog)
        summary_label = QLabel(summary)
        layout.addWidget(summary_label)
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setMinimumHeight(180)
        text_edit.setText("\n".join(rejected))
        layout.addWidget(text_edit)
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(dialog.accept)
        layout.addWidget(ok_btn)
        dialog.exec_()

def extract_file_paths(mime_data: QMimeData) -> List[str]:
    """
    Extracts local file paths from a QMimeData object.
    Only includes local files, ignores other types like text.
    """
    return [url.toLocalFile() for url in mime_data.urls() if url.isLocalFile()]
