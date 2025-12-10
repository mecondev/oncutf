#!/usr/bin/env python3
"""
Generate a high-level project context file for AI assistants (e.g. VS Code Copilot).

It scans the repository, finds Python files, extracts:
- line counts
- module docstring (if any)
- top-level classes
- top-level functions

and writes a Markdown file with a structured overview.

You can paste parts of that Markdown into AI chat to give it
a "project-wide view" similar to Cursor's project index.
"""

from __future__ import annotations

import ast
import datetime as dt
import os
from pathlib import Path
from textwrap import shorten

# --- Configuration ---------------------------------------------------------

# Directories to ignore while walking
IGNORED_DIRS = {
    ".git",
    ".idea",
    ".vscode",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "backups",
    "temp",
    "venv",
    ".venv",
    ".cursor",
    ".ai",
}

# File extensions to include
INCLUDE_EXTENSIONS = {".py"}

# Output file (relative to project root). Default to `reports/` per project convention.
OUTPUT_PATH = Path("reports") / "project_context.md"


# --- Helpers ---------------------------------------------------------------

def is_ignored_dir(path: Path) -> bool:
    """Return True if this directory should be skipped."""
    return path.name in IGNORED_DIRS


def get_module_summary(path: Path, max_doc_len: int = 160) -> dict:
    """
    Parse a Python file and return a small summary:
    - line_count
    - module_doc (first line only)
    - classes (top-level)
    - functions (top-level)
    """
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Fallback if a file has weird encoding
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        print(f"Warning: Could not read {path}: {e}")
        return {
            "line_count": 0,
            "module_doc": None,
            "classes": [],
            "functions": [],
            "syntax_error": True,
        }

    line_count = text.count("\n") + 1

    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError:
        return {
            "line_count": line_count,
            "module_doc": None,
            "classes": [],
            "functions": [],
            "syntax_error": True,
        }

    module_doc = ast.get_docstring(tree)
    if module_doc:
        # Keep only the first line or a short snippet (ASCII-safe length)
        module_doc = shorten(module_doc.strip().replace("\n", " "), width=max_doc_len)

    classes = []
    functions = []

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, ast.FunctionDef):
            functions.append(node.name)

    return {
        "line_count": line_count,
        "module_doc": module_doc,
        "classes": classes,
        "functions": functions,
        "syntax_error": False,
    }


def group_by_top_level_dir(root: Path, files: list[Path]) -> dict[str, list[Path]]:
    """
    Group files by their top-level directory.

    Example:
      core/metadata_manager.py -> group 'core'
      widgets/file_table_view.py -> group 'widgets'
      main.py -> group '(root)'
    """
    groups: dict[str, list[Path]] = {}

    for f in files:
        try:
            rel = f.relative_to(root)
            key = "(root)" if len(rel.parts) == 1 else rel.parts[0]

            groups.setdefault(key, []).append(f)
        except ValueError:
            # File is not relative to root
            continue

    # Sort files inside each group
    for key in groups:
        groups[key] = sorted(groups[key], key=lambda p: str(p))

    return dict(sorted(groups.items(), key=lambda kv: kv[0]))


# --- Main logic ------------------------------------------------------------

def find_python_files(root: Path, recursive: bool = True, extra_ignored: set[str] | None = None) -> list[Path]:
    """Find Python files under root.

    Args:
        root: project root
        recursive: if True walk recursively, otherwise only top-level directory
        extra_ignored: optional set of additional directory names to ignore
    """
    result: list[Path] = []

    ignored = set(IGNORED_DIRS)
    if extra_ignored:
        ignored.update(extra_ignored)

    if recursive:
        for dirpath, dirnames, filenames in os.walk(root):
            dirpath_path = Path(dirpath)
            dirnames[:] = [d for d in dirnames if (dirpath_path / d).name not in ignored]

            for name in filenames:
                p = dirpath_path / name
                if p.suffix in INCLUDE_EXTENSIONS:
                    result.append(p)
    else:
        # Non-recursive: only list files in the project root
        for entry in root.iterdir():
            if entry.is_file() and entry.suffix in INCLUDE_EXTENSIONS:
                result.append(entry)

    return sorted(result, key=lambda p: str(p))


def main() -> None:
    # Get script directory and project root
    script_dir = Path(__file__).parent.resolve()
    project_root = script_dir.parent  # Assume script is in scripts/ folder

    # If running from project root directly, use cwd
    if not (project_root / "main.py").exists():
        project_root = Path.cwd()

    print(f"[generate_project_context] Scanning project at: {project_root}")

    # Use recursion by default; can be overridden by CLI
    py_files = find_python_files(project_root, recursive=True)
    if not py_files:
        print("No Python files found. Are you in the correct project root?")
        return

    groups = group_by_top_level_dir(project_root, py_files)

    # Prepare output path
    output_path = project_root / OUTPUT_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)

    total_lines = 0
    total_files = len(py_files)
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    try:
        with output_path.open("w", encoding="utf-8") as f:
            f.write(f"# Project Context – {project_root.name}\n\n")
            f.write(f"_Generated automatically on {now}_\n\n")
            f.write("This file provides a high-level overview of the Python codebase:\n")
            f.write("- per top-level directory\n")
            f.write("- listing modules, line counts, brief docstrings, and main classes/functions.\n")
            f.write("Use it as context for AI assistants (VS Code Copilot, etc.).\n\n")

            # Overview
            for p in py_files:
                try:
                    text = p.read_text(encoding="utf-8")
                    total_lines += text.count("\n") + 1
                except Exception:
                    # Skip files we can't read
                    continue

            f.write("## Overview\n\n")
            f.write(f"- **Total Python files**: {total_files}\n")
            f.write(f"- **Approximate total lines**: {total_lines}\n")
            f.write(f"- **Root directory**: `{project_root}`\n\n")

            # Per group
            for group_name, files in groups.items():
                f.write("---\n\n")
                f.write(f"## `{group_name}/`\n\n")

                for path in files:
                    try:
                        rel = path.relative_to(project_root)
                        # Use forward slashes for consistency across platforms
                        rel_str = str(rel).replace("\\", "/")
                    except ValueError:
                        rel_str = str(path)

                    summary = get_module_summary(path)

                    line_count = summary["line_count"]
                    module_doc = summary["module_doc"]
                    classes = summary["classes"]
                    functions = summary["functions"]
                    syntax_error = summary["syntax_error"]

                    f.write(f"### `{rel_str}` \n")
                    f.write(f"- Lines: **{line_count}**\n")

                    if syntax_error:
                        f.write("- [WARNING] Syntax error while parsing (skipped AST details)\n")

                    if module_doc:
                        f.write(f"- Docstring: _\"{module_doc}\"_\n")

                    if classes:
                        f.write(f"- Classes: {', '.join(classes)}\n")
                    if functions:
                        f.write(f"- Functions: {', '.join(functions)}\n")

                    f.write("\n")

        print(f"[generate_project_context] Successfully wrote context file to: {output_path}")

    except Exception as e:
        print(f"[generate_project_context] Error writing output file: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate a project context Markdown file for AI assistants."
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=str(OUTPUT_PATH),
        help="Output Markdown path (default: reports/project_context.md)",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Recurse into subdirectories (default: enabled)",
    )
    parser.add_argument(
        "-e",
        "--exclude",
        action="append",
        default=[],
        help="Additional top-level directory names to ignore (repeatable)",
    )
    parser.add_argument(
        "-m",
        "--max-doc-length",
        type=int,
        default=160,
        help="Maximum characters for module docstring summarization (default: 160)",
    )

    args = parser.parse_args()

    # Override output path and other options
    OUTPUT_PATH = Path(args.output)

    # Run main logic with selected options
    # We reimplement a small portion to pass flags through
    script_dir = Path(__file__).parent.resolve()
    project_root = script_dir.parent
    if not (project_root / "main.py").exists():
        project_root = Path.cwd()

    print(f"[generate_project_context] Scanning project at: {project_root}")

    py_files = find_python_files(project_root, recursive=args.recursive, extra_ignored=set(args.exclude))
    if not py_files:
        print("No Python files found. Are you in the correct project root?")
        sys.exit(0)

    groups = group_by_top_level_dir(project_root, py_files)

    output_path = project_root / OUTPUT_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)

    total_lines = 0
    total_files = len(py_files)
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    try:
        with output_path.open("w", encoding="utf-8") as f:
            f.write(f"# Project Context – {project_root.name}\n\n")
            f.write(f"_Generated automatically on {now}_\n\n")
            f.write("This file provides a high-level overview of the Python codebase:\n")
            f.write("- per top-level directory\n")
            f.write("- listing modules, line counts, brief docstrings, and main classes/functions.\n")
            f.write("Use it as context for AI assistants (VS Code Copilot, etc.).\n\n")

            for p in py_files:
                try:
                    text = p.read_text(encoding="utf-8")
                    total_lines += text.count("\n") + 1
                except Exception:
                    continue

            f.write("## Overview\n\n")
            f.write(f"- **Total Python files**: {total_files}\n")
            f.write(f"- **Approximate total lines**: {total_lines}\n")
            f.write(f"- **Root directory**: `{project_root}`\n\n")

            for group_name, files in groups.items():
                f.write("---\n\n")
                f.write(f"## `{group_name}/`\n\n")

                for path in files:
                    try:
                        rel = path.relative_to(project_root)
                        rel_str = str(rel).replace("\\", "/")
                    except ValueError:
                        rel_str = str(path)

                    summary = get_module_summary(path, max_doc_len=args.max_doc_length)

                    line_count = summary["line_count"]
                    module_doc = summary["module_doc"]
                    classes = summary["classes"]
                    functions = summary["functions"]
                    syntax_error = summary["syntax_error"]

                    f.write(f"### `{rel_str}` \n")
                    f.write(f"- Lines: **{line_count}**\n")

                    if syntax_error:
                        f.write("- [WARNING] Syntax error while parsing (skipped AST details)\n")

                    if module_doc:
                        f.write(f"- Docstring: _\"{module_doc}\"_\n")

                    if classes:
                        f.write(f"- Classes: {', '.join(classes)}\n")
                    if functions:
                        f.write(f"- Functions: {', '.join(functions)}\n")

                    f.write("\n")

        print(f"[generate_project_context] Successfully wrote context file to: {output_path}")

    except Exception as e:
        print(f"[generate_project_context] Error writing output file: {e}")
        import traceback
        traceback.print_exc()
