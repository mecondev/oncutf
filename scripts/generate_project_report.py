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
import contextlib
import datetime as dt
import sys
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
    "structure-full": "reports/project_structure_full.md",
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


def get_full_docstring_coverage(path: Path) -> dict:
    """Parse a Python file and extract ALL docstrings (module, class, function).

    Returns:
        dict with:
            - line_count: number of lines
            - module_doc: bool (has module docstring)
            - classes: list of {name, has_doc, line, methods: [{name, has_doc, line}]}
            - functions: list of {name, has_doc, line}
            - syntax_error: bool
            - stats: {total, documented} counts
    """
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return {
            "line_count": 0,
            "module_doc": False,
            "classes": [],
            "functions": [],
            "syntax_error": True,
            "stats": {"total": 0, "documented": 0},
        }

    line_count = text.count("\n") + 1

    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError:
        return {
            "line_count": line_count,
            "module_doc": False,
            "classes": [],
            "functions": [],
            "syntax_error": True,
            "stats": {"total": 0, "documented": 0},
        }

    total = 0
    documented = 0

    # Module docstring
    total += 1
    module_has_doc = ast.get_docstring(tree) is not None
    if module_has_doc:
        documented += 1

    classes = []
    functions = []

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            total += 1
            class_has_doc = ast.get_docstring(node) is not None
            if class_has_doc:
                documented += 1

            methods = []
            for item in node.body:
                if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                    total += 1
                    method_has_doc = ast.get_docstring(item) is not None
                    if method_has_doc:
                        documented += 1
                    methods.append({
                        "name": item.name,
                        "has_doc": method_has_doc,
                        "line": item.lineno,
                    })

            classes.append({
                "name": node.name,
                "has_doc": class_has_doc,
                "line": node.lineno,
                "methods": methods,
            })

        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            total += 1
            func_has_doc = ast.get_docstring(node) is not None
            if func_has_doc:
                documented += 1
            functions.append({
                "name": node.name,
                "has_doc": func_has_doc,
                "line": node.lineno,
            })

    return {
        "line_count": line_count,
        "module_doc": module_has_doc,
        "classes": classes,
        "functions": functions,
        "syntax_error": False,
        "stats": {"total": total, "documented": documented},
    }


def get_full_docstring_texts(path: Path) -> dict:
    """Parse a Python file and return full docstring texts for module, classes and functions.

    Returns a dict with keys:
        - module_doc: str|None
        - classes: list of {name, line, doc: str|None, methods: [{name,line,doc}]}
        - functions: list of {name,line,doc}
        - syntax_error: bool
        - line_count: int
    """
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
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

    classes = []
    functions = []

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            cls_doc = ast.get_docstring(node)
            methods = []
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.append({
                        "name": item.name,
                        "line": item.lineno,
                        "doc": ast.get_docstring(item),
                    })

            classes.append({
                "name": node.name,
                "line": node.lineno,
                "doc": cls_doc,
                "methods": methods,
            })

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append({
                "name": node.name,
                "line": node.lineno,
                "doc": ast.get_docstring(node),
            })

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


def generate_structure_full_report(
    project_root: Path,
    output_path: Path,
    recursive: bool = True,
    extra_ignored: set | None = None,
    missing_items_out: list[str] | None = None,
    include_docstrings: bool = False,
) -> None:
    """Generate structure-full report: complete docstring coverage for modules, classes, functions."""
    py_files = find_python_files(project_root, recursive, extra_ignored)
    if not py_files:
        print("No Python files found.")
        return

    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    total_all = 0
    documented_all = 0
    missing_items: list[str] = []

    with output_path.open("w", encoding="utf-8") as f:
        f.write(f"# Full Docstring Coverage Report – {project_root.name}\n\n")
        f.write(f"_Generated on {now}_\n\n")
        f.write("This report checks docstrings for:\n")
        f.write("- Module-level docstrings\n")
        f.write("- Class docstrings\n")
        f.write("- Function/method docstrings\n\n")
        if include_docstrings:
            f.write("---\n\n")
            f.write("**NOTE:** This run includes the full text of module/class/function docstrings below each item.\n\n")
        f.write("---\n\n")

        for py_file in py_files:
            try:
                rel_path = py_file.relative_to(project_root)
            except ValueError:
                rel_path = py_file

            coverage = get_full_docstring_coverage(py_file)
            texts = get_full_docstring_texts(py_file) if include_docstrings else None
            total_all += coverage["stats"]["total"]
            documented_all += coverage["stats"]["documented"]

            file_pct = (
                (coverage["stats"]["documented"] / coverage["stats"]["total"] * 100)
                if coverage["stats"]["total"]
                else 100
            )

            # File header - status mapping (ordered worst -> best)
            # FAIL  : < 50%
            # WARNIG: 50% - 79%
            # PARTIAL: 80% - 99%
            # OK    : 100%
            if file_pct == 100:
                status = "[OK]"
            elif file_pct >= 80:
                status = "[PARTIAL]"
            elif file_pct >= 50:
                status = "[WARNIG]"
            else:
                status = "[FAIL]"
            f.write(f"## {status} `{rel_path}` ({coverage['line_count']} lines)\n\n")
            f.write(
                f"**Coverage:** {coverage['stats']['documented']}/{coverage['stats']['total']} "
                f"({file_pct:.0f}%)\n\n"
            )

            if coverage["syntax_error"]:
                f.write("[!] _Syntax error - could not parse_\n\n")
                continue

            # Module docstring
            if not coverage["module_doc"]:
                f.write("- [X] Module docstring missing\n")
                missing_items.append(f"{rel_path}:1 module")
            else:
                if include_docstrings and texts is not None:
                    mod_doc = texts.get("module_doc")
                    if mod_doc:
                        f.write("\n**Module docstring:**\n\n")
                        f.write("```\n")
                        f.write(mod_doc.strip() + "\n")
                        f.write("```\n\n")

            # Classes
            for cls in coverage["classes"]:
                cls_status = "[+]" if cls["has_doc"] else "[X]"
                f.write(f"- {cls_status} Class `{cls['name']}` (line {cls['line']})\n")
                if not cls["has_doc"]:
                    missing_items.append(f"{rel_path}:{cls['line']} class {cls['name']}")

                for method in cls["methods"]:
                    m_status = "[+]" if method["has_doc"] else "[X]"
                    f.write(f"  - {m_status} `{method['name']}()` (line {method['line']})\n")
                    if not method["has_doc"]:
                        missing_items.append(
                            f"{rel_path}:{method['line']} method {cls['name']}.{method['name']}"
                        )

                # If requested, include full docstrings for this class and its methods
                if include_docstrings:
                    texts = get_full_docstring_texts(py_file)
                    # find matching class
                    for tcls in texts.get("classes", []):
                        if tcls["name"] == cls["name"]:
                            if tcls.get("doc"):
                                f.write("\n    **Class docstring:**\n\n")
                                f.write("    ```\n")
                                # indent class docstring lines for readability
                                for line in tcls["doc"].splitlines():
                                    f.write("    " + line + "\n")
                                f.write("    ```\n\n")
                            # methods
                            for method in tcls.get("methods", []):
                                if method.get("doc"):
                                    f.write(f"    **Method `{method['name']}()` docstring:** (line {method['line']})\n\n")
                                    f.write("    ```\n")
                                    for line in method["doc"].splitlines():
                                        f.write("    " + line + "\n")
                                    f.write("    ```\n\n")

            # Top-level functions
            for func in coverage["functions"]:
                f_status = "[+]" if func["has_doc"] else "[X]"
                f.write(f"- {f_status} Function `{func['name']}()` (line {func['line']})\n")
                if not func["has_doc"]:
                    missing_items.append(f"{rel_path}:{func['line']} function {func['name']}")
                else:
                    # If requested, include full docstring for this top-level function
                    if include_docstrings and texts is not None:
                        for tfunc in texts.get("functions", []):
                            if tfunc.get("name") == func["name"] and tfunc.get("doc"):
                                f.write("\n    **Function docstring:**\n\n")
                                f.write("    ```\n")
                                for line in tfunc["doc"].splitlines():
                                    f.write("    " + line + "\n")
                                f.write("    ```\n\n")
                                break

            f.write("\n")
        # Summary section
        overall_pct = (documented_all / total_all * 100) if total_all else 0
        f.write("---\n\n")
        f.write("## Summary\n\n")
        f.write(f"**Total docstrings:** {documented_all} / {total_all} ({overall_pct:.1f}%)\n\n")

        if missing_items:
            f.write(f"### Missing Docstrings ({len(missing_items)} items)\n\n")
            for item in missing_items:
                f.write(f"- `{item}`\n")

    print(f"[OK] Structure-full report written to: {output_path}")
    print(f"[STATS] Full Docstring Coverage: {documented_all} / {total_all} ({overall_pct:.1f}%)")
    if missing_items:
        print(f"[WARNING] {len(missing_items)} missing docstrings")

    if missing_items_out is not None:
        missing_items_out.clear()
        missing_items_out.extend(missing_items)


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
        description="""Generate comprehensive project reports for analysis and documentation.

Three report types:
  structure      - Tree visualization with module docstrings, classes, functions
                   Shows hierarchy, module coverage, missing module docstrings
  structure-full - Complete docstring coverage (module + class + function/method)
                   Detailed report of ALL missing docstrings
  content        - AI-friendly context report grouped by directory
                   Useful for providing project context to language models""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:

  # Generate structure report with tree and module analysis
  %(prog)s --mode structure

  # Generate FULL docstring coverage report (modules, classes, functions)
  %(prog)s --mode structure-full

  # Generate AI context for the entire project
  %(prog)s --mode content

  # Generate report with datetime stamp at START of filename (for sorting)
  %(prog)s --mode structure -d
  # Output: reports/20260101_2130_project_structure.md

  # Custom output location with excluded directories
  %(prog)s --mode structure -o analysis/project.md --exclude tests scripts

  # Scan only top-level files (no recursion)
  %(prog)s --mode content --no-recursive

  # Full docstring check excluding tests
  %(prog)s --mode structure-full --exclude tests

Output Defaults:
  structure:      reports/project_structure.md
  structure-full: reports/project_structure_full.md
  content:        reports/project_context.md

Mode details:
  structure:      Module-level docstrings only (fast overview)
  structure-full: ALL docstrings - modules, classes, methods, functions
  content:        Summary by directory (good for LLM context windows)
        """,
    )

    parser.add_argument(
        "--mode",
        choices=["structure", "structure-full", "content"],
        required=True,
        help="Report type: 'structure', 'structure-full', or 'content'",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=str,
        metavar="PATH",
        help="Output file path (default: reports/project_<mode>.md)",
    )

    parser.add_argument(
        "-d",
        "--date",
        action="store_true",
        help="Add datetime stamp at START of filename for sorting (e.g., 20260101_2130_project_structure.md)",
    )

    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="DIR",
        help="Additional directories to exclude (repeatable, e.g., --exclude tests --exclude build)",
    )

    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Scan only top-level Python files (skip subdirectories)",
    )

    parser.add_argument(
        "--max-doc-length",
        type=int,
        default=300,
        metavar="N",
        help="Max characters for docstring previews (default: 300)",
    )

    parser.add_argument(
        "--include-docstrings",
        action="store_true",
        help="Include full module/class/function docstrings in the report and export to docs/reports with timestamp prefix",
    )

    parser.add_argument(
        "-m",
        "--missing",
        action="store_true",
        help=(
            "Print missing docstring items to stdout (structure-full only). "
            "Format: path:line kind name"
        ),
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

    # If include_docstrings requested and no custom output, export to docs/reports
    if args.include_docstrings and not args.output:
        output_path = project_root / "docs" / "reports" / output_path.name
        # Ensure timestamp prefix for sorting when including docstrings
        args.date = True

    # Add datetime stamp if requested (at START of filename for sorting)
    if args.date:
        timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M")
        stem = output_path.stem
        suffix = output_path.suffix
        output_path = output_path.with_name(f"{timestamp}_{stem}{suffix}")

    # Generate report
    recursive = not args.no_recursive
    extra_ignored = set(args.exclude) if args.exclude else None

    if args.mode == "structure":
        generate_structure_report(project_root, output_path, recursive, extra_ignored)
    elif args.mode == "structure-full":
        missing_items: list[str] | None = [] if args.missing else None
        generate_structure_full_report(
            project_root,
            output_path,
            recursive,
            extra_ignored,
            missing_items_out=missing_items,
            include_docstrings=args.include_docstrings,
        )
        if missing_items:
            try:
                for item in missing_items:
                    print(item)
            except BrokenPipeError:
                with contextlib.suppress(Exception):
                    sys.stdout.close()
                return
    else:  # content
        generate_content_report(
            project_root, output_path, recursive, extra_ignored, args.max_doc_length
        )


if __name__ == "__main__":
    main()
