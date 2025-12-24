#!/usr/bin/env python3
"""Script to fix module docstring dates to match actual file creation/modification dates.

This script scans Python files and ensures the Date field in module docstrings
matches the actual file creation date. It looks for patterns like:
    Author: Michael Economou
    Date: YYYY-MM-DD

Usage:
    python fix_module_dates.py -p /path/to/project          # Dry-run mode
    python fix_module_dates.py -p /path/to/project -f       # Apply changes
"""

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Hardcoded exclusions - files/folders that should not be modified
EXCLUDED_PATHS = {
    "scripts/",  # Entire scripts folder (recently added to git)
    "main.py",  # Written 2025-05-01 but added to git 2025-05-06
    "main_window.py",  # Written 2025-05-01 but added to git 2025-05-06
    "config.py",  # Written 2025-05-01 but added to git 2025-05-06
}

# Minimum date threshold - all dates before this become 2025-05-01
PROJECT_START = datetime(2025, 5, 1)


def is_excluded(filepath: Path, project_path: Path) -> bool:
    """Check if file is in excluded list.
    """
    relative_path = filepath.relative_to(project_path)
    filepath_str = str(relative_path)

    # Check exact filename matches
    if filepath_str in EXCLUDED_PATHS:
        return True

    # Check if in excluded folder
    for excluded in EXCLUDED_PATHS:
        if excluded.endswith("/"):
            folder = excluded.rstrip("/")
            if filepath_str.startswith(folder + "/"):
                return True

    return False


def get_file_creation_date(filepath: Path) -> str:
    """Get file creation date using git history where available.

    Strategy:
    1. Try git log to find first commit (most reliable)
    2. Fall back to filesystem stat (least reliable)

    Returns date in YYYY-MM-DD format, clamped to project start (2025-05-01).
    """
    file_date = None

    # Try git first (most reliable for tracked files)
    try:
        result = subprocess.run(
            ["git", "log", "--follow", "--diff-filter=A", "--format=%aI", "--", str(filepath)],
            capture_output=True,
            text=True,
            check=False,
            cwd=filepath.parent,
        )

        if result.returncode == 0 and result.stdout.strip():
            # Parse ISO date: "2025-05-06T19:24:35+03:00"
            git_dates = result.stdout.strip().split("\n")
            # Get the LAST date (oldest commit)
            oldest_date_str = git_dates[-1].split("T")[0]
            file_date = datetime.strptime(oldest_date_str, "%Y-%m-%d")
    except Exception:
        pass

    # Fallback to filesystem date
    if file_date is None:
        try:
            stat = filepath.stat()
            timestamp = min(stat.st_ctime, stat.st_mtime)
            file_date = datetime.fromtimestamp(timestamp)
        except Exception:
            # Last resort: use project start date
            file_date = datetime(2025, 5, 1)

    # Clamp to project start date (2025-05-01)
    project_start = datetime(2025, 5, 1)
    file_date = max(file_date, project_start)

    # Don't allow future dates
    today = datetime.now()
    file_date = min(file_date, today)

    return file_date.strftime("%Y-%m-%d")


def extract_module_docstring(content: str) -> tuple[str | None, int, int]:
    """Extract module docstring from file content.

    Returns (docstring_text, start_pos, end_pos) or (None, 0, 0) if not found.
    """
    lines = content.split("\n")

    # Skip shebang and encoding declarations
    start_line = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#") or stripped == "":
            continue
        start_line = i
        break

    # Check if starts with docstring
    if start_line >= len(lines):
        return None, 0, 0

    first_line = lines[start_line].strip()
    if not (first_line.startswith(('"""', "'''"))):
        return None, 0, 0

    delimiter = '"""' if first_line.startswith('"""') else "'''"

    # Find docstring end
    if first_line.count(delimiter) >= 2:
        # Single-line docstring
        docstring = lines[start_line]
        start_pos = content.find(docstring)
        end_pos = start_pos + len(docstring)
        return docstring, start_pos, end_pos

    # Multi-line docstring
    end_line = start_line + 1
    for i in range(start_line + 1, len(lines)):
        if delimiter in lines[i]:
            end_line = i
            break

    docstring_lines = lines[start_line : end_line + 1]
    docstring = "\n".join(docstring_lines)
    start_pos = content.find(docstring)
    end_pos = start_pos + len(docstring)

    return docstring, start_pos, end_pos


def check_and_fix_docstring_date(filepath: Path, project_path: Path, dry_run: bool = True) -> dict:
    """Check if module docstring date matches file creation date and fix if needed.
    Also ensures Author is 'Michael Economou'.

    Logic:
    - If file is excluded: skip it
    - Compare docstring date vs git date
    - If docstring date > git date: change to git date
    - If docstring date < 2025-05-01: change to 2025-05-01
    - If docstring date <= git date: leave as is (already correct)

    Returns dict with keys: changed, old_date, new_date, message
    """
    # Check if file is excluded
    if is_excluded(filepath, project_path):
        return {"changed": False, "message": "File is excluded from date fixing"}

    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return {"changed": False, "error": f"Could not read file: {e}"}

    # Get actual file date from git
    git_date_str = get_file_creation_date(filepath)
    git_date = datetime.strptime(git_date_str, "%Y-%m-%d")

    # Extract docstring
    docstring, start_pos, end_pos = extract_module_docstring(content)

    if not docstring:
        return {"changed": False, "message": "No module docstring found"}

    # Check for Author and Date patterns
    author_pattern = r"Author:\s*(.+?)(?:\n|$)"
    date_pattern = r"Date:\s*(\d{4}-\d{2}-\d{2})"

    author_match = re.search(author_pattern, docstring)
    date_match = re.search(date_pattern, docstring)

    if not author_match or not date_match:
        return {"changed": False, "message": "Missing Author or Date field in docstring"}

    current_author = author_match.group(1).strip()
    current_date_str = date_match.group(1)
    current_date = datetime.strptime(current_date_str, "%Y-%m-%d")

    # Check Author
    needs_author_fix = current_author != "Michael Economou"

    # Check Date: only change if docstring date is NEWER than git date
    # OR if docstring date is before project start
    needs_date_fix = False
    new_date = current_date

    if current_date < PROJECT_START:
        # If before project start, use project start date
        needs_date_fix = True
        new_date = PROJECT_START
    elif current_date > git_date:
        # If docstring date is newer than git date, use git date
        needs_date_fix = True
        new_date = git_date

    if not needs_author_fix and not needs_date_fix:
        return {
            "changed": False,
            "message": f"Already correct: Author={current_author}, Date={current_date_str}",
        }

    # Need to fix author and/or date
    new_docstring = docstring
    changes = []

    if needs_author_fix:
        new_docstring = re.sub(author_pattern, "Author: Michael Economou\n", new_docstring)
        changes.append(f"Author: {current_author} -> Michael Economou")

    if needs_date_fix:
        new_date_str = new_date.strftime("%Y-%m-%d")
        new_docstring = re.sub(date_pattern, f"Date: {new_date_str}", new_docstring)
        changes.append(f"Date: {current_date_str} -> {new_date_str}")

    change_msg = ", ".join(changes)

    if dry_run:
        new_date_str = new_date.strftime("%Y-%m-%d") if needs_date_fix else current_date_str
        return {
            "changed": True,
            "dry_run": True,
            "old_author": current_author if needs_author_fix else None,
            "old_date": current_date_str if needs_date_fix else None,
            "new_date": new_date_str if needs_date_fix else None,
            "message": change_msg,
        }

    # Apply the fix
    new_content = content[:start_pos] + new_docstring + content[end_pos:]

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)

        new_date_str = new_date.strftime("%Y-%m-%d")
        return {
            "changed": True,
            "dry_run": False,
            "old_date": current_date_str,
            "new_date": new_date_str,
            "message": f"Updated: {current_date_str} -> {new_date_str}",
        }
    except Exception as e:
        return {"changed": False, "error": f"Could not write file: {e}"}


def process_project(
    project_path: Path,
    dry_run: bool = True,
    verbose: bool = False,
    exclude_files: list[str] | None = None,
):
    """Process all Python files in the project."""
    if exclude_files is None:
        exclude_files = []

    print(f"Scanning: {project_path}")
    if exclude_files:
        print(f"Excluding: {', '.join(exclude_files)}")
    print(f"Mode: {'DRY-RUN (no changes)' if dry_run else 'FIX MODE (applying changes)'}")
    print("-" * 80)

    files_scanned = 0
    files_changed = 0
    files_skipped = 0
    files_errors = 0

    changes = []

    for root, _, files in os.walk(project_path):
        for filename in files:
            if not filename.endswith(".py"):
                continue

            filepath = Path(root) / filename
            relative_path = filepath.relative_to(project_path)

            # Check if file is excluded
            if filename in exclude_files or str(relative_path) in exclude_files:
                continue

            files_scanned += 1

            result = check_and_fix_docstring_date(filepath, project_path, dry_run)

            if result.get("error"):
                files_errors += 1
                if verbose:
                    print(f"ERROR: {relative_path}")
                    print(f"  {result['error']}")
            elif result.get("changed"):
                files_changed += 1
                changes.append(
                    {
                        "path": relative_path,
                        "old_date": result.get("old_date"),
                        "new_date": result.get("new_date"),
                    }
                )
                print(f"{'WOULD CHANGE' if dry_run else 'CHANGED'}: {relative_path}")
                print(f"  {result['message']}")
            else:
                files_skipped += 1
                if verbose:
                    print(f"SKIPPED: {relative_path}")
                    print(f"  {result['message']}")

    # Summary
    print("\n" + "=" * 80)
    print("Summary:")
    print(f"  Files scanned: {files_scanned}")
    print(f"  Files changed: {files_changed}")
    print(f"  Files skipped: {files_skipped}")
    print(f"  Errors: {files_errors}")

    if changes:
        print(f"\n{'Changes that would be made' if dry_run else 'Changes made'}:")
        for change in changes:
            print(f"  {change['path']}: {change['old_date']} -> {change['new_date']}")

    if dry_run and files_changed > 0:
        print(f"\nRun with -f flag to apply {files_changed} changes.")


def main():
    parser = argparse.ArgumentParser(
        description="Fix module docstring dates to match file creation dates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -p .                    # Dry-run on current directory
  %(prog)s -p /path/to/project -f  # Apply changes
  %(prog)s -p . -f -v              # Apply with verbose output
        """,
    )

    parser.add_argument(
        "-p", "--project", type=str, required=True, help="Path to project directory"
    )

    parser.add_argument(
        "-f", "--fix", action="store_true", help="Apply changes (default: dry-run mode)"
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show all files including skipped ones"
    )

    parser.add_argument(
        "--exclude",
        type=str,
        action="append",
        default=[],
        help="Exclude specific files (can be used multiple times)",
    )

    args = parser.parse_args()

    project_path = Path(args.project).resolve()

    if not project_path.exists():
        print(f"ERROR: Path does not exist: {project_path}")
        return 1

    if not project_path.is_dir():
        print(f"ERROR: Path is not a directory: {project_path}")
        return 1

    process_project(
        project_path, dry_run=not args.fix, verbose=args.verbose, exclude_files=args.exclude
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
