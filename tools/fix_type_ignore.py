#!/usr/bin/env python3
"""Script to add specific error codes to generic 'type: ignore' comments.

Author: Michael Economou
Date: 2026-01-09
"""

import re
import sys
from pathlib import Path

# Patterns to match and their suggested error codes
# NOTE: replacement must include "# type: ignore" prefix!
PATTERNS = [
    # Qt attribute access
    (r"Qt\.WA_\w+.*# type: ignore$", "# type: ignore[attr-defined]  # Qt widget attribute"),
    (
        r"Qt\.(AlignCenter|AlignLeft|AlignRight|AlignTop|AlignBottom|AlignVCenter|AlignHCenter).*# type: ignore$",
        "# type: ignore[arg-type]  # Qt alignment flag",
    ),
    (
        r"Qt\.(LeftButton|RightButton|MiddleButton).*# type: ignore$",
        "# type: ignore[comparison-overlap]  # Qt mouse button",
    ),
    (
        r"Qt\.(PointingHandCursor|WaitCursor|ArrowCursor).*# type: ignore$",
        "# type: ignore[attr-defined]  # Qt cursor",
    ),
    (
        r"Qt\.(FramelessWindowHint|WindowStaysOnTopHint|ToolTip|Dialog).*# type: ignore$",
        "# type: ignore[attr-defined]  # Qt window flags",
    ),
    (
        r"Qt\.(ScrollBarAlways|ScrollBarAsNeeded|ScrollBarAlwaysOff).*# type: ignore$",
        "# type: ignore[attr-defined]  # Qt scrollbar policy",
    ),
    (r"Qt\.(transparent|white|black).*# type: ignore$", "# type: ignore[attr-defined]  # Qt color"),
    (
        r"Qt\.(UserRole|DisplayRole|DecorationRole).*# type: ignore$",
        "# type: ignore[attr-defined]  # Qt item role",
    ),
    (r"Qt\.(ItemIsEnabled).*# type: ignore$", "# type: ignore[attr-defined]  # Qt item flags"),
    (
        r"Qt\.(StrongFocus|NoFocus).*# type: ignore$",
        "# type: ignore[attr-defined]  # Qt focus policy",
    ),
    (
        r"Qt\.(NoModifier|AscendingOrder|DescendingOrder).*# type: ignore$",
        "# type: ignore[attr-defined]  # Qt enum",
    ),
    (r"Qt\.(Key_\w+).*# type: ignore$", "# type: ignore[attr-defined]  # Qt key constants"),
    (r"QEvent\.\w+.*# type: ignore$", "# type: ignore[attr-defined]  # QEvent type"),
    # app.primaryScreen(), app.screens()
    (
        r"app\.(primaryScreen|screens|overrideCursor)\(\).*# type: ignore$",
        "# type: ignore[attr-defined]  # QApplication method",
    ),
    # sys._MEIPASS
    (r"sys\._MEIPASS.*# type: ignore$", "# type: ignore[attr-defined]  # PyInstaller attribute"),
    # logger patching
    (r"logger\._patched_.*# type: ignore$", "# type: ignore[attr-defined]  # Dynamic attribute"),
    # Widget methods that take Qt flags
    (r"\.setAlignment\(.*# type: ignore$", "# type: ignore[arg-type]  # Qt alignment argument"),
    (
        r"\.addWidget\(.*Qt\.Align.*# type: ignore$",
        "# type: ignore[arg-type]  # Qt alignment argument",
    ),
    (r"\.setWindowFlags\(.*# type: ignore$", "# type: ignore[attr-defined]  # Qt window flags"),
    (r"\.setAttribute\(.*# type: ignore$", "# type: ignore[attr-defined]  # Qt widget attribute"),
    (r"\.setCursor\(.*# type: ignore$", "# type: ignore[attr-defined]  # Qt cursor"),
    (r"\.setFocusPolicy\(.*# type: ignore$", "# type: ignore[attr-defined]  # Qt focus policy"),
    (
        r"\.setVerticalScrollBarPolicy\(.*# type: ignore$",
        "# type: ignore[attr-defined]  # Qt scrollbar policy",
    ),
    (
        r"\.setHorizontalScrollBarPolicy\(.*# type: ignore$",
        "# type: ignore[attr-defined]  # Qt scrollbar policy",
    ),
    (r"\.fill\(Qt\..*# type: ignore$", "# type: ignore[attr-defined]  # Qt color"),
    (r"\.setData\(.*Qt\.UserRole.*# type: ignore$", "# type: ignore[attr-defined]  # Qt item role"),
    (r"\.setFlags\(.*Qt\..*# type: ignore$", "# type: ignore[attr-defined]  # Qt item flags"),
    (r"\.setForeground\(.*# type: ignore$", "# type: ignore[arg-type]  # QColor argument"),
    # Event handling
    (
        r"event\.button\(\) ==.*# type: ignore$",
        "# type: ignore[comparison-overlap]  # Qt button comparison",
    ),
    (r"event\.buttons\(\) &.*# type: ignore$", "# type: ignore[operator]  # Qt button bitwise op"),
    (r"event\.key\(\).*# type: ignore$", "# type: ignore[attr-defined]  # Qt key constant"),
    # Other patterns
    (r"overrideCursor\(\).*# type: ignore$", "# type: ignore[attr-defined]  # QApplication method"),
    (r"is_effective_data\(.*# type: ignore$", "# type: ignore[attr-defined]  # Dynamic attribute"),
]


def process_file(filepath: Path, dry_run: bool = False) -> tuple[int, int]:
    """Process a single file and add specific error codes.

    Returns:
        Tuple of (lines_changed, lines_unchanged)
    """
    with open(filepath) as f:
        content = f.read()

    original_content = content
    lines_changed = 0
    lines_unchanged = 0

    for pattern, replacement in PATTERNS:
        matches = re.findall(pattern, content, re.MULTILINE)
        if matches:
            # Replace pattern - use simple string replacement to avoid regex escape issues
            lines = content.split("\n")
            new_lines = []
            for line in lines:
                if re.search(pattern, line):
                    # Replace the trailing "# type: ignore" with the specific version
                    new_line = re.sub(r"# type: ignore$", replacement, line)
                    new_lines.append(new_line)
                    lines_changed += 1
                else:
                    new_lines.append(line)
            content = "\n".join(new_lines)

    # Count remaining generic type:ignore
    remaining = len(re.findall(r"# type: ignore$", content, re.MULTILINE))
    lines_unchanged = remaining

    if not dry_run and content != original_content:
        with open(filepath, "w") as f:
            f.write(content)
        print(f"Fixed {filepath}: {lines_changed} type:ignore comments")
    elif dry_run and lines_changed > 0:
        print(f"[DRY-RUN] {filepath}: {lines_changed} would be fixed, {lines_unchanged} remaining")

    return lines_changed, lines_unchanged


def main():
    """Main function to process all Python files."""
    dry_run = "--dry-run" in sys.argv

    oncutf_dir = Path("oncutf")
    if not oncutf_dir.exists():
        print("Error: oncutf/ directory not found. Run from project root.")
        sys.exit(1)

    total_changed = 0
    total_unchanged = 0
    files_processed = 0

    # Process all Python files
    for pyfile in oncutf_dir.rglob("*.py"):
        # Skip __pycache__
        if "__pycache__" in str(pyfile):
            continue

        changed, unchanged = process_file(pyfile, dry_run=dry_run)
        if changed > 0 or unchanged > 0:
            files_processed += 1
            total_changed += changed
            total_unchanged += unchanged

    print(f"\n{'[DRY-RUN] ' if dry_run else ''}Summary:")
    print(f"Files processed: {files_processed}")
    print(f"Type:ignore comments fixed: {total_changed}")
    print(f"Generic type:ignore remaining: {total_unchanged}")

    if dry_run:
        print("\nRun without --dry-run to apply changes.")


if __name__ == "__main__":
    main()
