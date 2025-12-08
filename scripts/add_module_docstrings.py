
"""
Module: .cache/add_module_docstrings.py

Author: Michael Economou
Date: 2025-06-14

This module provides functionality for the OnCutF batch file renaming application.
"""

import ast
import os

PLACEHOLDER = '"""TODO: Add module-level docstring."""\n\n'

def has_module_docstring(filepath):
    with open(filepath, encoding='utf-8') as f:
        try:
            tree = ast.parse(f.read())
            return ast.get_docstring(tree) is not None
        except Exception:
            return False  # If it's not readable, we leave it out

def add_placeholder_docstring(filepath):
    with open(filepath, encoding='utf-8') as f:
        lines = f.readlines()

    insert_at = 0
    # Skipping initial blank lines or comments
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "" or stripped.startswith("#"):
            continue
        insert_at = i
        break

    lines.insert(insert_at, PLACEHOLDER)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(lines)

def process_project(project_path):
    count_modified = 0
    for root, _, files in os.walk(project_path):
        for file in files:
            if file.endswith(".py"):
                full_path = os.path.join(root, file)
                if not has_module_docstring(full_path):
                    add_placeholder_docstring(full_path)
                    count_modified += 1
    return count_modified

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Add placeholder module-level docstrings to .py files.")
    parser.add_argument("-p", "--project", required=True, help="Path to project folder")

    args = parser.parse_args()

    if not os.path.isdir(args.project):
        print("Error: Invalid path.")
        exit(1)

    modified = process_project(args.project)
    print(f"Done. Added placeholder docstrings to {modified} file(s).")
