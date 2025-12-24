"""
Module: .cache/extract_docstrings.py

Author: Michael Economou
Date: 2025-06-14

This module provides functionality for the OnCutF batch file renaming application.
"""

import ast
import os


def extract_docstrings_from_file(filepath):
    with open(filepath, encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read())
            docstring = ast.get_docstring(tree)
            return docstring
        except Exception as e:
            return f"[Error parsing file: {e}]"


def scan_project(root_dir):
    result = []
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith(".py"):
                full_path = os.path.join(dirpath, filename)
                relative_path = os.path.relpath(full_path, root_dir)
                docstring = extract_docstrings_from_file(full_path)
                result.append((relative_path, docstring))
    return result


def save_results(results, output_file):
    with open(output_file, "w", encoding="utf-8") as f:
        for path, doc in results:
            f.write(f"{path}\n{'-' * len(path)}\n")
            f.write(f"{doc if doc else '[No docstring found]'}\n\n")


if __name__ == "__main__":
    project_dir = "."  # Or put the project path here
    output_path = "reports/docstrings_report.txt"
    docstrings = scan_project(project_dir)
    save_results(docstrings, output_path)
    print(f" Docstrings saved to {output_path}")
