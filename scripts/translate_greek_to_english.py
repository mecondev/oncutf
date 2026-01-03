#!/usr/bin/env python3
"""Script to translate Greek text to English in Python codebase.

This script scans Python, Markdown, JSON, and text files for Greek characters
in comments, docstrings, logger messages, and string literals, then translates
them to English using OpenAI's GPT-4o-mini API.

Default mode: Dry-run (shows what would be changed)
Use -f/--fix flag to apply changes in-place.

Usage:
    python translate_greek_to_english.py           # Dry-run mode
    python translate_greek_to_english.py -f        # Apply changes
    python translate_greek_to_english.py --help    # Show help
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

try:
    from openai import OpenAI  # type: ignore
except ImportError:
    print("ERROR: openai package not installed. Install with: pip install openai")
    sys.exit(1)

try:
    from dotenv import load_dotenv  # type: ignore
except ImportError:
    print("ERROR: python-dotenv not installed. Install with: pip install python-dotenv")
    sys.exit(1)

try:
    from tqdm import tqdm  # type: ignore
except ImportError:
    print("ERROR: tqdm not installed. Install with: pip install tqdm")
    sys.exit(1)


# ============================================================================
# Configuration
# ============================================================================

# File extensions to scan
EXTENSIONS = {".py", ".txt", ".md", ".json"}

# Directories to exclude (from .gitignore + repo structure)
EXCLUDED_DIRS = {
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "build",
    "dist",
    ".eggs",
    "backups",
    "htmlcov",
    "logs",
    "temp",
    ".git",
    ".vscode",
    ".idea",
    ".cursor",
    "node_modules",
    "tests",
    "scripts",
    "reports",
}

# Files to always exclude (functional data, not documentation)
EXCLUDED_FILES = {
    "oncutf/utils/naming/transform_utils.py",  # Greek-to-Latin transliteration dictionary
    "tests/test_transform_utils.py",  # Test data with Greek characters
}

# Directories with archived/legacy documentation (excluded by default)
ARCHIVE_DIRS = {
    "docs/archive",
}

# Greek character detection regex
GREEK_PATTERN = re.compile(r"[\u0370-\u03FF\u1F00-\u1FFF]+")

# Token pricing for gpt-4o-mini (as of Dec 2024)
COST_PER_1K_INPUT_TOKENS = 0.00015  # $0.15 per 1M tokens
COST_PER_1K_OUTPUT_TOKENS = 0.0006  # $0.60 per 1M tokens


# ============================================================================
# Greek Text Detection
# ============================================================================


def contains_greek(text: str) -> bool:
    """Check if text contains Greek characters."""
    return bool(GREEK_PATTERN.search(text))


def extract_greek_strings_from_python(content: str) -> list[tuple[int, str, str]]:
    """Extract Greek strings from Python file (comments, docstrings, logger messages).

    Returns list of (line_number, context_type, greek_text).
    """
    results = []
    lines = content.split("\n")

    in_docstring = False
    docstring_delimiter = None
    docstring_start = 0
    docstring_lines = []

    for i, line in enumerate(lines, 1):
        # Check for docstring start/end
        if '"""' in line or "'''" in line:
            if not in_docstring:
                # Starting docstring
                docstring_delimiter = '"""' if '"""' in line else "'''"

                in_docstring = True
                docstring_start = i
                docstring_lines = [line]

                # Check if it's a single-line docstring
                if line.count(docstring_delimiter) >= 2:
                    in_docstring = False
                    full_docstring = line
                    if contains_greek(full_docstring):
                        results.append((i, "docstring", full_docstring))
                    docstring_lines = []
            else:
                # Ending docstring
                docstring_lines.append(line)
                full_docstring = "\n".join(docstring_lines)
                if contains_greek(full_docstring):
                    results.append((docstring_start, "docstring", full_docstring))
                in_docstring = False
                docstring_lines = []
        elif in_docstring:
            docstring_lines.append(line)
        else:
            # Check for inline comments
            if "#" in line:
                comment_match = re.search(r"#\s*(.+)$", line)
                if comment_match:
                    comment_text = comment_match.group(0)
                    if contains_greek(comment_text):
                        results.append((i, "comment", comment_text))

            # Check for logger messages
            logger_match = re.search(r'logger\.\w+\(["\'](.+?)["\']\)', line)
            if logger_match:
                log_text = logger_match.group(0)
                if contains_greek(log_text):
                    results.append((i, "logger", log_text))

            # Check for string literals (simple heuristic)
            string_matches = re.finditer(r'["\']([^"\']+)["\']', line)
            for match in string_matches:
                if contains_greek(match.group(0)):
                    # Avoid duplicates (already caught by logger check)
                    if "logger" not in line:
                        results.append((i, "string", match.group(0)))

    return results


def extract_greek_from_markdown(content: str) -> list[tuple[int, str, str]]:
    """Extract Greek text from Markdown files."""
    results = []
    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        if contains_greek(line):
            # Determine context
            if line.strip().startswith("#"):
                context = "heading"
            elif line.strip().startswith("- ") or line.strip().startswith("* "):
                context = "list_item"
            else:
                context = "paragraph"
            results.append((i, context, line))

    return results


def extract_greek_from_json(content: str) -> list[tuple[str, str]]:
    """Extract Greek values from JSON files."""
    results = []

    try:
        data = json.loads(content)

        def traverse(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_path = f"{path}.{key}" if path else key
                    traverse(value, new_path)
            elif isinstance(obj, list):
                for idx, item in enumerate(obj):
                    traverse(item, f"{path}[{idx}]")
            elif isinstance(obj, str):
                if contains_greek(obj):
                    results.append((path, obj))

        traverse(data)
    except json.JSONDecodeError:
        pass  # Skip malformed JSON

    return results


def extract_greek_from_text(content: str) -> list[tuple[int, str]]:
    """Extract Greek lines from plain text files."""
    results = []
    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        if contains_greek(line):
            results.append((i, line))

    return results


# ============================================================================
# Translation via OpenAI
# ============================================================================


class TranslationClient:
    """OpenAI client for translating Greek to English."""

    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    def translate(self, greek_text: str) -> str:
        """Translate Greek text to English using GPT-4o-mini."""
        prompt = f"""You are a technical translator. Translate the following Greek text to English.
Preserve technical terms, code syntax, and formatting.
Make the translation concise and developer-friendly.
Only return the translated text, no explanations.

Original Greek text:
\"\"\"
{greek_text}
\"\"\"
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a technical translator specializing in developer documentation.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=1000,
            )

            # Track token usage
            if hasattr(response, "usage"):
                self.total_input_tokens += response.usage.prompt_tokens
                self.total_output_tokens += response.usage.completion_tokens

            translated = response.choices[0].message.content.strip()

            # Remove surrounding quotes if present
            if translated.startswith('"""') and translated.endswith('"""'):
                translated = translated[3:-3].strip()
            elif translated.startswith('"') and translated.endswith('"'):
                translated = translated[1:-1]

            return translated

        except Exception as e:
            print(f"    ERROR during translation: {e}")
            return greek_text  # Return original on error

    def get_cost_report(self) -> str:
        """Generate cost report for API usage."""
        input_cost = (self.total_input_tokens / 1000) * COST_PER_1K_INPUT_TOKENS
        output_cost = (self.total_output_tokens / 1000) * COST_PER_1K_OUTPUT_TOKENS
        total_cost = input_cost + output_cost

        return f"""
API Usage Summary:
  Input tokens:  {self.total_input_tokens:,}
  Output tokens: {self.total_output_tokens:,}

Estimated cost:
  Input:  ${input_cost:.6f}
  Output: ${output_cost:.6f}
  Total:  ${total_cost:.6f} USD
"""


# ============================================================================
# File Processing
# ============================================================================


def should_process_file(
    filepath: Path, root: Path, include_archives: bool = False, custom_excludes: list[str] = None
) -> bool:
    """Check if file should be processed based on exclusions."""
    # Check extension
    if filepath.suffix not in EXTENSIONS:
        return False

    relative_path = filepath.relative_to(root)
    relative_str = str(relative_path)

    # Check if in excluded files list
    if relative_str in EXCLUDED_FILES:
        return False

    # Check custom excludes
    if custom_excludes:
        for exclude_pattern in custom_excludes:
            if exclude_pattern in relative_str:
                return False

    # Check if in excluded directory
    for part in relative_path.parts:
        if part in EXCLUDED_DIRS or part.startswith("."):
            return False

    # Check if in archive directory (unless explicitly included)
    if not include_archives:
        for archive_dir in ARCHIVE_DIRS:
            if relative_str.startswith(archive_dir):
                return False

    return True


def process_python_file(filepath: Path, translator: TranslationClient, dry_run: bool) -> dict:
    """Process a Python file for Greek text."""
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    greek_items = extract_greek_strings_from_python(content)

    if not greek_items:
        return {"changed": False, "changes": []}

    changes = []
    new_content = content

    for line_num, context, greek_text in greek_items:
        # For docstrings, preserve the delimiters and only translate content
        if context == "docstring":
            # Detect delimiter type
            delimiter = '"""' if '"""' in greek_text else "'''"

            # Extract just the text content (without delimiters)
            # Handle both single-line: """text""" and multi-line: """\ntext\n"""
            if greek_text.startswith(delimiter) and greek_text.endswith(delimiter):
                # Extract content between delimiters
                content_only = greek_text[len(delimiter) : -len(delimiter)]

                # Translate only the content
                translated_content = translator.translate(content_only)

                # Reconstruct with delimiters
                english_text = delimiter + translated_content + delimiter
            else:
                # Fallback: translate entire string (shouldn't happen with proper extraction)
                english_text = translator.translate(greek_text)
        else:
            # For comments, strings, and logger messages, translate as-is
            english_text = translator.translate(greek_text)

        # Store change info
        changes.append(
            {"line": line_num, "context": context, "old": greek_text, "new": english_text}
        )

        # Apply replacement
        if not dry_run:
            new_content = new_content.replace(greek_text, english_text, 1)

    # Write back if not dry-run
    if not dry_run and changes:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)

    return {"changed": len(changes) > 0, "changes": changes}


def process_markdown_file(filepath: Path, translator: TranslationClient, dry_run: bool) -> dict:
    """Process a Markdown file for Greek text."""
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    greek_items = extract_greek_from_markdown(content)

    if not greek_items:
        return {"changed": False, "changes": []}

    changes = []
    lines = content.split("\n")

    for line_num, context, greek_line in greek_items:
        english_line = translator.translate(greek_line)

        changes.append(
            {"line": line_num, "context": context, "old": greek_line, "new": english_line}
        )

        if not dry_run:
            lines[line_num - 1] = english_line

    if not dry_run and changes:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    return {"changed": len(changes) > 0, "changes": changes}


def process_json_file(filepath: Path, translator: TranslationClient, dry_run: bool) -> dict:
    """Process a JSON file for Greek values."""
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    greek_items = extract_greek_from_json(content)

    if not greek_items:
        return {"changed": False, "changes": []}

    changes = []
    new_content = content

    for path, greek_value in greek_items:
        english_value = translator.translate(greek_value)

        changes.append({"path": path, "old": greek_value, "new": english_value})

        if not dry_run:
            # Simple string replacement (works for most cases)
            new_content = new_content.replace(f'"{greek_value}"', f'"{english_value}"', 1)

    if not dry_run and changes:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)

    return {"changed": len(changes) > 0, "changes": changes}


def process_text_file(filepath: Path, translator: TranslationClient, dry_run: bool) -> dict:
    """Process a plain text file for Greek content."""
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    greek_items = extract_greek_from_text(content)

    if not greek_items:
        return {"changed": False, "changes": []}

    changes = []
    lines = content.split("\n")

    for line_num, greek_line in greek_items:
        english_line = translator.translate(greek_line)

        changes.append({"line": line_num, "old": greek_line, "new": english_line})

        if not dry_run:
            lines[line_num - 1] = english_line

    if not dry_run and changes:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    return {"changed": len(changes) > 0, "changes": changes}


# ============================================================================
# Main Scanner
# ============================================================================


def scan_repository(
    root: Path,
    translator: TranslationClient,
    dry_run: bool,
    include_archives: bool = False,
    custom_excludes: list[str] = None,
):
    """Scan repository for Greek text and translate to English."""
    print(f"Scanning repository: {root}")
    print(
        f"Mode: {'DRY-RUN (no changes will be made)' if dry_run else 'FIX MODE (applying changes)'}"
    )
    print(f"Extensions: {', '.join(EXTENSIONS)}")

    # Show exclusions
    print("\nExcluding:")
    print(f"  - Files: {', '.join(EXCLUDED_FILES)}")
    print(
        "  - Directories: reports/, docs/archive/" + (" (overridden)" if include_archives else "")
    )
    if custom_excludes:
        print(f"  - Custom: {', '.join(custom_excludes)}")

    print("-" * 80)

    # First pass: collect all files to process
    files_to_process = []
    for filepath in root.rglob("*"):
        if filepath.is_file() and should_process_file(
            filepath, root, include_archives, custom_excludes
        ):
            files_to_process.append(filepath)

    print(f"Found {len(files_to_process)} files to scan\n")

    files_scanned = 0
    files_changed = 0
    total_changes = 0

    # Process files with progress bar
    for filepath in tqdm(files_to_process, desc="Processing files", unit="file"):

        files_scanned += 1
        relative_path = filepath.relative_to(root)

        # Process based on extension
        try:
            if filepath.suffix == ".py":
                result = process_python_file(filepath, translator, dry_run)
            elif filepath.suffix == ".md":
                result = process_markdown_file(filepath, translator, dry_run)
            elif filepath.suffix == ".json":
                result = process_json_file(filepath, translator, dry_run)
            elif filepath.suffix == ".txt":
                result = process_text_file(filepath, translator, dry_run)
            else:
                continue

            if result["changed"]:
                files_changed += 1
                total_changes += len(result["changes"])

                # Use tqdm.write to avoid interfering with progress bar
                tqdm.write(f"\nFile: {relative_path}")
                for change in result["changes"]:
                    if "line" in change:
                        tqdm.write(f"  Line {change['line']} ({change.get('context', 'text')}):")
                    elif "path" in change:
                        tqdm.write(f"  JSON path: {change['path']}")

                    # Truncate long strings for display
                    old_display = (
                        change["old"][:100] + "..." if len(change["old"]) > 100 else change["old"]
                    )
                    new_display = (
                        change["new"][:100] + "..." if len(change["new"]) > 100 else change["new"]
                    )

                    tqdm.write(f"    OLD: {old_display}")
                    tqdm.write(f"    NEW: {new_display}")

        except Exception as e:
            tqdm.write(f"\nERROR processing {relative_path}: {e}")

    # Summary
    print("\n" + "=" * 80)
    print("Summary:")
    print(f"  Files scanned: {files_scanned}")
    print(f"  Files changed: {files_changed}")
    print(f"  Total translations: {total_changes}")

    # Cost report
    print(translator.get_cost_report())


# ============================================================================
# Main Entry Point
# ============================================================================


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Translate Greek text to English in Python codebase",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s              # Dry-run mode (default)
  %(prog)s -f           # Apply changes to files
  %(prog)s --root ../   # Scan different directory
        """,
    )

    parser.add_argument(
        "-f", "--fix", action="store_true", help="Apply changes to files (default: dry-run mode)"
    )

    parser.add_argument(
        "--root", type=str, default=".", help="Root directory to scan (default: current directory)"
    )

    parser.add_argument(
        "--include-archives",
        action="store_true",
        help="Include docs/archive/ directory (excluded by default)",
    )

    parser.add_argument(
        "--exclude",
        type=str,
        action="append",
        help="Additional file patterns to exclude (can be used multiple times)",
    )

    args = parser.parse_args()

    # Load API key from .env file one level up
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        print(f"WARNING: .env file not found at {env_path}")
        print("Trying to load from current directory...")
        load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found in environment")
        print(f"Expected location: {env_path}")
        sys.exit(1)

    # Initialize translator
    translator = TranslationClient(api_key)

    # Scan repository
    root_path = Path(args.root).resolve()
    if not root_path.exists():
        print(f"ERROR: Directory not found: {root_path}")
        sys.exit(1)

    scan_repository(
        root_path,
        translator,
        dry_run=not args.fix,
        include_archives=args.include_archives,
        custom_excludes=args.exclude,
    )


if __name__ == "__main__":
    main()
