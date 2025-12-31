#!/usr/bin/env python3
"""Generate comprehensive project reports for structure analysis or AI context.

This unified script replaces:
- extract_docstrings.py (legacy)
- extract_full_structure.py (tree visualization)
- generate_project_context.py (AI context)

Two modes:
1. structure: Full tree visualization with docstrings, classes, functions, stats
2. content: AI-friendly context grouped by directory

Author: Michael Economou
Date: 2026-01-01
"""

from __future__ import annotations

import argparse
import ast
import datetime as dt
from pathlib import Path
from textwrap import shorten

# --- Configuration ---------------------------------------------------------

# Directories to exclude (based on .gitignore)
IGNORED_DIRS = {
    ".git",
    ".idea",
    ".vscode",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".cursor",
    ".ai",
    "backups",
    "temp",
    "venv",
    ".venv",
    "env",
    "build",
    "dist",
    "*.egg-info",
    ".eggs",
    "htmlcov",
    "logs",
    "tests",
    "scripts",
    "reports",
    "node_modules",
}

# File extensions to include
INCLUDE_EXTENSIONS = {".py"}

# Default output paths
DEFAULT_OUTPUT = {
    "structure": "reports/project_structure.md",
    "content": "reports/project_context.md",
}


# --- AST Analysis ----------------------------------------------------------


def get_module_summary(path: Path, max_doc_len: int = 300) -> dict:
    """Parse a Python file and extract comprehensive summary.

    Returns:
        dict with:
            - line_count: number of lines
            - module_doc: module docstring (shortened)
            - classes: list of top-level class names
            - functions: list of top-level function names
            - syntax_error: bool indicating parse failure
    """
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
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
        # Shorten to max length (ASCII-safe)
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


# --- File Discovery --------------------------------------------------------


def find_python_files(
    root: Path, recursive: bool = True, extra_ignored: set[str] | None = None
) -> list[Path]:
    """Find Python files under root, respecting ignore rules."""
    result: list[Path] = []
    ignored = set(IGNORED_DIRS)
    if extra_ignored:
        ignored.update(extra_ignored)

    if recursive:
        for dirpath, dirnames, filenames in root.walk():
            # Filter out ignored directories
            dirnames[:] = [d for d in dirnames if d not in ignored]

            for name in filenames:
                p = dirpath / name
                if p.suffix in INCLUDE_EXTENSIONS:
                    result.append(p)
    else:
        # Non-recursive: only root directory
        for entry in root.iterdir():
            if entry.is_file() and entry.suffix in INCLUDE_EXTENSIONS:
                result.append(entry)

    return sorted(result, key=lambda p: str(p))


# --- Structure Mode (Tree) -------------------------------------------------


def build_structure_tree(
    path: Path, prefix: str = "", stats: dict | None = None, missing: list | None = None
) -> list[str]:
    """Build tree visualization with docstrings, classes, functions, line counts.

    Args:
        path: Directory to scan
        prefix: Indentation prefix
        stats: Dict tracking {total, documented} file counts
        missing: List to collect files without docstrings

    Returns:
        List of formatted lines
    """
    if stats is None:
        stats = {"total": 0, "documented": 0}
    if missing is None:
        missing = []

    lines = []
    items = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name))

    for item in items:
        if item.name.startswith(".") or item.name in IGNORED_DIRS:
            continue

        if item.is_dir():
            lines.append(f"{prefix}[DIR] {item.name}/")
            lines.extend(build_structure_tree(item, prefix + "    ", stats, missing))
        elif item.suffix == ".py":
            stats["total"] += 1
            summary = get_module_summary(item)

            # File header with line count
            file_line = f"{prefix}[PY] {item.name} ({summary['line_count']} lines)"

            # Docstring
            if summary["module_doc"]:
                stats["documented"] += 1
                file_line += f"\n{prefix}     {summary['module_doc']}"
            else:
                missing.append(str(item))

            # Classes
            if summary["classes"]:
                classes_str = ", ".join(summary["classes"])
                file_line += f"\n{prefix}     Classes: {classes_str}"

            # Functions
            if summary["functions"]:
                funcs_str = ", ".join(summary["functions"])
                file_line += f"\n{prefix}     Functions: {funcs_str}"

            lines.append(file_line)
        else:
            lines.append(f"{prefix}[FILE] {item.name}")

    return lines


def generate_structure_report(
    project_root: Path, output_path: Path, recursive: bool = True, extra_ignored: set | None = None
) -> None:
    """Generate structure mode report: tree with full analysis."""
    py_files = find_python_files(project_root, recursive, extra_ignored)
    if not py_files:
        print("No Python files found.")
        return

    stats = {"total": 0, "documented": 0}
    missing: list[str] = []

    tree_lines = build_structure_tree(project_root, stats=stats, missing=missing)

    coverage_percent = (stats["documented"] / stats["total"] * 100) if stats["total"] else 0
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        f.write(f"# Project Structure – {project_root.name}\n\n")
        f.write(f"_Generated on {now}_\n\n")
        f.write(
            f"**Docstring Coverage:** {stats['documented']} / {stats['total']} files documented ({coverage_percent:.1f}%)\n\n"
        )
        f.write("---\n\n")
        f.write("\n".join(tree_lines))

        if missing:
            f.write("\n\n---\n\n")
            f.write("## [WARNING] Files Missing Module-Level Docstrings\n\n")
            for m in missing:
                f.write(f"- {m}\n")

    print(f"[OK] Structure report written to: {output_path}")
    print(
        f"[STATS] Docstring Coverage: {stats['documented']} / {stats['total']} files ({coverage_percent:.1f}%)"
    )
    if missing:
        print(f"[WARNING] {len(missing)} files missing docstrings")


# --- Content Mode (AI Context) ---------------------------------------------


def group_by_directory(root: Path, files: list[Path]) -> dict[str, list[Path]]:
    """Group files by their top-level directory."""
    groups: dict[str, list[Path]] = {}

    for f in files:
        try:
            rel = f.relative_to(root)
            key = "(root)" if len(rel.parts) == 1 else rel.parts[0]
            groups.setdefault(key, []).append(f)
        except ValueError:
            continue

    # Sort files inside each group
    for key in groups:
        groups[key] = sorted(groups[key], key=lambda p: str(p))

    return dict(sorted(groups.items()))


def generate_content_report(
    project_root: Path,
    output_path: Path,
    recursive: bool = True,
    extra_ignored: set | None = None,
    max_doc_len: int = 300,
) -> None:
    """Generate content mode report: AI-friendly context grouped by directory."""
    py_files = find_python_files(project_root, recursive, extra_ignored)
    if not py_files:
        print("No Python files found.")
        return

    groups = group_by_directory(project_root, py_files)

    total_lines = 0
    total_files = len(py_files)
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    # Calculate total lines
    for p in py_files:
        try:
            text = p.read_text(encoding="utf-8")
            total_lines += text.count("\n") + 1
        except Exception:
            continue

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        f.write(f"# Project Context – {project_root.name}\n\n")
        f.write(f"_Generated on {now}_\n\n")
        f.write("This file provides AI-friendly context:\n")
        f.write("- Grouped by top-level directory\n")
        f.write("- Module docstrings, line counts, classes, functions\n\n")

        # Overview
        f.write("## Overview\n\n")
        f.write(f"- **Total Python files**: {total_files}\n")
        f.write(f"- **Total lines**: {total_lines:,}\n")
        f.write(f"- **Root directory**: `{project_root}`\n\n")

        # Per group
        for group_name, files in groups.items():
            f.write("---\n\n")
            f.write(f"## `{group_name}/`\n\n")

            for path in files:
                try:
                    rel = path.relative_to(project_root)
                    rel_str = str(rel).replace("\\", "/")
                except ValueError:
                    rel_str = str(path)

                summary = get_module_summary(path, max_doc_len)

                f.write(f"### `{rel_str}`\n\n")
                f.write(f"- **Lines:** {summary['line_count']}\n")

                if summary["syntax_error"]:
                    f.write("- [WARNING] Syntax error (skipped AST details)\n")

                if summary["module_doc"]:
                    f.write(f"- **Docstring:** _{summary['module_doc']}_\n")

                if summary["classes"]:
                    f.write(f"- **Classes:** {', '.join(summary['classes'])}\n")

                if summary["functions"]:
                    f.write(f"- **Functions:** {', '.join(summary['functions'])}\n")

                f.write("\n")

    print(f"[OK] Content report written to: {output_path}")
    print(f"[STATS] Total: {total_files} files, {total_lines:,} lines")


# --- Main ------------------------------------------------------------------


def main() -> None:
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Generate project structure or AI context reports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --mode structure           # Tree with docstrings, classes, stats
  %(prog)s --mode content             # AI context grouped by directory
  %(prog)s --mode structure -o custom.md --exclude tests scripts
        """,
    )

    parser.add_argument(
        "--mode",
        choices=["structure", "content"],
        required=True,
        help="Report type: 'structure' (tree + analysis) or 'content' (AI context)",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Output file path (default: reports/project_structure.md or reports/project_context.md)",
    )

    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Additional directories to exclude (repeatable)",
    )

    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Scan only root directory (no subdirectories)",
    )

    parser.add_argument(
        "--max-doc-length",
        type=int,
        default=300,
        help="Max characters for docstring snippets (default: 300)",
    )

    args = parser.parse_args()

    # Determine project root
    script_dir = Path(__file__).parent.resolve()
    project_root = script_dir.parent

    if not (project_root / "main.py").exists():
        project_root = Path.cwd()

    print(f"[INFO] Scanning project at: {project_root}")

    # Determine output path
    if args.output:
        output_path = Path(args.output)
        if not output_path.is_absolute():
            output_path = project_root / output_path
    else:
        output_path = project_root / DEFAULT_OUTPUT[args.mode]

    # Generate report
    recursive = not args.no_recursive
    extra_ignored = set(args.exclude) if args.exclude else None

    if args.mode == "structure":
        generate_structure_report(project_root, output_path, recursive, extra_ignored)
    else:  # content
        generate_content_report(
            project_root, output_path, recursive, extra_ignored, args.max_doc_length
        )


if __name__ == "__main__":
    main()
