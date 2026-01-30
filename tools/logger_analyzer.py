"""Module: scripts/logger_analyzer.py

Author: Michael Economou
Date: 2025-12-07

This module provides functionality for analyzing logger calls in the oncutf application.
It detects legacy %-formatting in logger calls and suggests f-string equivalents,
using AST for robust parsing and respecting project structure.
"""

import argparse
import ast
import csv
import os
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

# Directories to exclude from analysis
EXCLUDED_DIRS = {
    ".venv",
    ".git",
    ".idea",
    ".vscode",
    "__pycache__",
    "htmlcov",
    "build",
    "dist",
    "temp",
}

# Common emoji / pictograph ranges (keeps maintenance-light, not exhaustive but covers most emoji)
EMOJI_RANGES = [
    (0x1F600, 0x1F64F),  # Emoticons
    (0x1F300, 0x1F5FF),  # Misc Symbols and Pictographs
    (0x1F680, 0x1F6FF),  # Transport & Map
    (0x2600, 0x26FF),  # Misc symbols
    (0x2700, 0x27BF),  # Dingbats
    (0x1F900, 0x1F9FF),  # Supplemental Symbols and Pictographs
    (0x1FA70, 0x1FAFF),  # Symbols & Pictographs Extended-A
    (0x1F1E6, 0x1F1FF),  # Regional indicator symbols (flags)
]


def is_emoji_codepoint(code: int) -> bool:
    return any(a <= code <= b for a, b in EMOJI_RANGES)


class LoggerVisitor(ast.NodeVisitor):
    def __init__(self, source_lines: list[str]):
        self.source_lines = source_lines
        self.suggestions: list[dict[str, Any]] = []
        self.current_function = "global"

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        old_func = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_func

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        old_func = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_func

    def visit_Call(self, node: ast.Call) -> None:
        # Check if it looks like logger.method(...)
        if not isinstance(node.func, ast.Attribute):
            return

        # Check for 'logger' variable or 'self.logger' attribute
        is_logger_call = False
        if (isinstance(node.func.value, ast.Name) and node.func.value.id == "logger") or (
            isinstance(node.func.value, ast.Attribute)
            and isinstance(node.func.value.value, ast.Name)
            and node.func.value.value.id == "self"
            and node.func.value.attr == "logger"
        ):
            is_logger_call = True

        if not is_logger_call:
            return

        method_name = node.func.attr
        if method_name not in {"debug", "info", "warning", "error", "critical", "exception"}:
            return

        # Check arguments: must have at least (msg, arg1) for %-formatting
        if len(node.args) < 2:
            return

        # First arg must be a string literal
        msg_node = node.args[0]
        if not (isinstance(msg_node, ast.Constant) and isinstance(msg_node.value, str)):
            return

        msg_str = msg_node.value

        # Check if it contains % format specifiers
        if "%" not in msg_str:
            return

        # Arguments to be formatted
        fmt_args = node.args[1:]

        # Get source representation of args
        arg_sources = []
        for arg in fmt_args:
            try:
                arg_sources.append(ast.unparse(arg))
            except AttributeError:
                # Fallback for older python (pre-3.9) or complex nodes
                # We can try to extract from source lines if unparse fails
                arg_sources.append("ARG")

        # Attempt to replace %s, %d, etc. with {arg}
        f_string_content = msg_str
        valid_replacement = True

        # Regex for printf style specifiers
        # Matches %s, %d, %.2f, %r, etc.
        specifier_pattern = re.compile(r"%[-+ 0#]*[0-9]*\.?[0-9]*[hlL]?[diouxXeEfFgGcrs]")

        for arg_src in arg_sources:
            match = specifier_pattern.search(f_string_content)
            if match:
                spec = match.group(0)
                # Handle %r specifically if needed, but {arg} is usually sufficient for logging
                # unless explicit repr() is desired.
                replacement = f"{{{arg_src}}}"
                f_string_content = f_string_content.replace(spec, replacement, 1)
            else:
                # More args than specifiers?
                valid_replacement = False
                break

        # If we still have % specifiers left, it might be a mismatch or literal %
        if specifier_pattern.search(f_string_content):
            # Check if they are escaped %% (which we should have handled? No, simple replace doesn't)
            # For safety, if unhandled % remains, we might skip or flag
            pass

        if not valid_replacement:
            return

        # Reconstruct keywords (extra, exc_info, stack_info)
        kwargs_str = ""
        for kw in node.keywords:
            val = ast.unparse(kw.value)
            kwargs_str += f", {kw.arg}={val}"

        # Construct new call
        if isinstance(node.func, ast.Attribute):
            caller = f"{ast.unparse(node.func.value)}.{node.func.attr}"
        else:
            caller = "logger.unknown"

        suggested_call = f'{caller}(f"{f_string_content}"{kwargs_str})'

        # Get original text
        start_line = node.lineno - 1
        end_line = node.end_lineno - 1
        original_text = "\n".join(self.source_lines[start_line : end_line + 1]).strip()

        self.suggestions.append(
            {
                "Line": node.lineno,
                "Function": self.current_function,
                "Original": original_text,
                "Suggested": suggested_call,
            }
        )


def analyze_file(
    file_path: Path, *, strip_emojis: bool = True, aggressive: bool = False, quiet: bool = False
) -> tuple[list[dict[str, Any]], int, dict[str, int]]:
    try:
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Fallback: decode with replacement characters so we can sanitize them later
            raw = file_path.read_bytes()
            content = raw.decode("utf-8", errors="replace")

        # Sanitize content: remove control/surrogate/non-character code points
        def sanitize_content(text: str) -> tuple[str, int, dict[str, int]]:
            removed = 0
            parts: list[str] = []
            removed_map: dict[str, int] = {}
            for ch in text:
                code = ord(ch)

                # Remove surrogate code points
                if 0xD800 <= code <= 0xDFFF:
                    removed += 1
                    label = f"U+{code:04X} (SURROGATE)"
                    removed_map[label] = removed_map.get(label, 0) + 1
                    continue

                # Remove Unicode non-characters (U+FFFE, U+FFFF and similar per plane)
                if (code & 0xFFFE) == 0xFFFE and code >= 0xFFFE:
                    removed += 1
                    label = f"U+{code:04X} (NONCHAR)"
                    removed_map[label] = removed_map.get(label, 0) + 1
                    continue

                # Remove control characters except common whitespace (tab/newline/carriage)
                if unicodedata.category(ch) == "Cc" and ch not in "\r\n\t":
                    removed += 1
                    try:
                        name = unicodedata.name(ch)
                    except ValueError:
                        name = "CONTROL"
                    label = f"U+{code:04X} ({name})"
                    removed_map[label] = removed_map.get(label, 0) + 1
                    continue

                # Replacement char (from decoding errors)
                if ch == "\ufffd":
                    removed += 1
                    label = f"U+{code:04X} (REPLACEMENT)"
                    removed_map[label] = removed_map.get(label, 0) + 1
                    continue

                # Strip emoji if requested
                if strip_emojis and is_emoji_codepoint(code):
                    removed += 1
                    try:
                        name = unicodedata.name(ch)
                    except ValueError:
                        name = "EMOJI"
                    label = f"U+{code:04X} ({name})"
                    removed_map[label] = removed_map.get(label, 0) + 1
                    continue

                # Aggressive mode: allow only letters, numbers, punctuation and space separators
                if aggressive:
                    cat = unicodedata.category(ch)
                    if not (
                        cat.startswith(("L", "N", "P"))  # Letter/Number/Punctuation
                        or cat == "Zs"
                        or ch in "\t\r\n"
                    ):
                        removed += 1
                        try:
                            name = unicodedata.name(ch)
                        except ValueError:
                            name = "OTHER"
                        label = f"U+{code:04X} ({name})"
                        removed_map[label] = removed_map.get(label, 0) + 1
                        continue

                parts.append(ch)
            return "".join(parts), removed, removed_map

        cleaned, removed_count, removed_map = sanitize_content(content)
        if removed_count > 0:
            try:
                file_path.write_text(cleaned, encoding="utf-8")
                if not quiet:
                    # Print detailed list of removed character labels and counts
                    removed_items = ", ".join(f"{k}: {v}" for k, v in removed_map.items())
                    print(
                        f"[CLEANUP] Removed {removed_count} characters from {file_path}: {removed_items}"
                    )
                else:
                    print(f"[CLEANUP] Removed {removed_count} characters from {file_path}")
            except Exception as write_err:
                print(
                    f"[CLEANUP][ERROR] Failed writing cleaned content to {file_path}: {write_err}"
                )

        # Use cleaned content for parsing. For non-.py files we only sanitize, no AST analysis.
        content = cleaned
        suggestions: list[dict[str, Any]] = []
        if file_path.suffix == ".py":
            try:
                lines = content.splitlines()
                tree = ast.parse(content)
                visitor = LoggerVisitor(lines)
                visitor.visit(tree)

                for s in visitor.suggestions:
                    s["File"] = str(file_path)
                suggestions = visitor.suggestions
            except Exception as parse_err:
                # If parsing fails, report and continue (we already sanitized)
                print(f"[ERROR] AST parse failed for {file_path}: {parse_err}")

        return suggestions, removed_count, removed_map
    except Exception as e:
        print(f"[ERROR] Parsing {file_path}: {e}")
        return [], 0, {}


def scan_directory(
    root_path: Path,
    *,
    strip_emojis: bool = True,
    aggressive: bool = False,
    recursive: bool = True,
    include_hidden: bool = False,
    quiet: bool = False,
    extensions: set[str] | None = None,
) -> tuple[list[dict[str, Any]], int, int, int]:
    """Scan directory for .py files and analyze them.

    Returns: (suggestions, files_scanned, files_modified, total_removed_chars)
    """
    all_suggestions: list[dict[str, Any]] = []
    files_scanned = 0
    files_modified = 0
    total_removed = 0

    if extensions is None:
        extensions = {".py"}

    if recursive:
        for root, dirs, files in os.walk(root_path):
            # Modify dirs in-place to skip excluded directories
            if include_hidden:
                dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
            else:
                dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".")]

            for file in files:
                file_path = Path(root) / file
                if file_path.suffix not in extensions:
                    continue
                files_scanned += 1
                suggestions, removed_count, _removed_map = analyze_file(
                    file_path, strip_emojis=strip_emojis, aggressive=aggressive, quiet=quiet
                )
                all_suggestions.extend(suggestions)
                if removed_count > 0:
                    files_modified += 1
                    total_removed += removed_count
    else:
        # Non-recursive: only top-level
        for entry in root_path.iterdir():
            if entry.is_file() and entry.suffix in extensions:
                files_scanned += 1
                suggestions, removed_count, _removed_map = analyze_file(
                    entry, strip_emojis=strip_emojis, aggressive=aggressive, quiet=quiet
                )
                all_suggestions.extend(suggestions)
                if removed_count > 0:
                    files_modified += 1
                    total_removed += removed_count

    return all_suggestions, files_scanned, files_modified, total_removed


def write_markdown(results: list[dict[str, Any]], out_path: Path):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with out_path.open("w", encoding="utf-8") as f:
        f.write("# Logger Format-Style to f-string Suggestions\n\n")
        f.write(f"Generated on {now}\n")
        f.write(f"Total suggestions: {len(results)}\n\n")

        for entry in results:
            f.write(f"### {entry['File']} — Line {entry['Line']}\n")
            f.write(f"**Function:** `{entry['Function']}`\n\n")
            f.write("```python\n")
            f.write(f"# OLD:\n{entry['Original']}\n")
            f.write(f"# NEW:\n{entry['Suggested']}\n")
            f.write("```\n\n")


def write_csv(results: list[dict[str, Any]], out_path: Path):
    if not results:
        return
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert format-style logger calls to f-strings using AST."
    )
    parser.add_argument("--file", type=str, help="Optional: single file to analyze")
    parser.add_argument(
        "--ext",
        nargs="+",
        default=[".py"],
        help="File extensions to scan (space separated), e.g. .py .log (default: .py)",
    )
    default_out = ".cache/logger_suggestions.md"
    parser.add_argument("--out", type=str, default=default_out, help="Output file (.md or .csv)")
    parser.add_argument(
        "--no-strip-emojis",
        dest="strip_emojis",
        action="store_false",
        help="Do not strip emojis from files (default: strip)",
    )
    parser.set_defaults(strip_emojis=True)
    parser.add_argument(
        "--aggressive",
        action="store_true",
        help="Aggressively remove non-letter/number/punctuation characters",
    )
    parser.add_argument(
        "--no-recursive",
        dest="no_recursive",
        action="store_true",
        help="Do not recurse into subdirectories (only top-level)",
    )
    parser.add_argument(
        "--include-hidden",
        dest="include_hidden",
        action="store_true",
        help="Include hidden directories (starting with .) when scanning",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        dest="quiet",
        action="store_true",
        help="Suppress verbose per-file cleanup output",
    )
    args = parser.parse_args()

    base_dir = Path(".")

    # Add timestamp to output filename
    out_path_orig = Path(args.out)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_stem = f"{out_path_orig.stem}_{timestamp}"
    out_path = out_path_orig.with_name(f"{new_stem}{out_path_orig.suffix}")

    print("[INFO] Scanning for logger statements (AST-based)...")
    ext_set = {e if e.startswith(".") else f".{e}" for e in args.ext}
    print(
        f"[INFO] Sanitization: strip_emojis={args.strip_emojis}, aggressive={args.aggressive}, extensions={sorted(ext_set)}"
    )

    results: list[dict[str, Any]] = []
    files_scanned = files_modified = total_removed = 0

    if args.file:
        suggestions, removed, removed_map = analyze_file(
            Path(args.file),
            strip_emojis=args.strip_emojis,
            aggressive=args.aggressive,
            quiet=args.quiet,
        )
        results = suggestions
        files_scanned = 1
        files_modified = 1 if removed > 0 else 0
        total_removed = removed
    else:
        suggestions, files_scanned, files_modified, total_removed = scan_directory(
            base_dir,
            strip_emojis=args.strip_emojis,
            aggressive=args.aggressive,
            recursive=not getattr(args, "no_recursive", False),
            include_hidden=getattr(args, "include_hidden", False),
            quiet=args.quiet,
            extensions=ext_set,
        )
        results = suggestions

    # Always print summary
    print(
        f"[SUMMARY] Files scanned: {files_scanned}, Files modified: {files_modified}, Total removed chars: {total_removed}"
    )

    if not results:
        print("[INFO] No format-style loggers found.")
    else:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if out_path.suffix == ".csv":
            write_csv(results, out_path)
        else:
            write_markdown(results, out_path)
        print(f"[OK] Report saved to: {out_path}")
        print(f"[OK] Suggestions: {len(results)}")
