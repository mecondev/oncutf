#!/usr/bin/env python3
"""
Icon Migration Script: Feather Icons → Material Design Icons

Author: Michael Economou
Date: 2026-02-02

This script maps Feather icon names to Material Design icon names
and can perform search & replace across the codebase.
"""

import re
from pathlib import Path
from typing import Dict

# FEATHER → MATERIAL DESIGN MAPPING
# Based on docs/icon_migration_mapping.md
ICON_MAPPING: Dict[str, str] = {
    # NAVIGATION (6)
    "keyboard_arrow_up": "keyboard_arrow_up",
    "keyboard_arrow_down": "keyboard_arrow_down",
    "keyboard_arrow_right": "keyboard_arrow_right",
    "close": "close",
    "menu": "menu",
    "search": "search",

    # EDITING & CLIPBOARD (6)
    "content_cut": "content_cut",
    "content_paste": "content_paste",
    "content_copy": "content_copy",
    "edit": "edit",
    "undo": "undo",
    "redo": "redo",

    # FILE OPERATIONS (7)
    "folder": "folder",
    "create_new_folder": "create_new_folder",
    "draft": "draft",
    "note_add": "note_add",
    "save": "save",
    "download": "download",
    "refresh": "refresh",
    "refresh": "refresh",  # Same as refresh-cw

    # SELECTION & CHECKBOXES (2)
    "check_box": "check_box",
    "check_box_outline_blank": "check_box_outline_blank",

    # TOGGLES & BUTTONS (4)
    "add": "add",
    "remove": "remove",
    "toggle_off": "toggle_off",
    "toggle_on": "toggle_on",

    # UTILITIES & INFO (8)
    "info": "info",
    "list": "list",
    "schedule": "schedule",
    "tag": "tag",
    "palette": "palette",
    "view_column": "view_column",
    "stacks": "stacks",  # NEW: Using stacks instead of layers
    "more_vert": "more_vert",

    # METADATA/HASH ICONS (8 - used in svg_icon_generator.py)
    "circle": "circle",
    "check_circle": "check_circle",
    "edit_note": "edit_note",
    "error": "error",
    "warning": "warning",
    "tag": "tag",  # Hash metadata

    # FILE TYPE ICONS (for CustomFileSystemModel)
    "image": "image",  # Images (jpg, png, etc.)
    "movie": "movie",  # Videos (mp4, mov, etc.)
    "audio_file": "audio_file",  # Audio files (mp3, wav, etc.)
    "description": "description",  # Text/documents (txt, pdf, etc.)
    "folder_zip": "folder_zip",  # Archives (zip, rar, etc.)
    "code": "code",  # Code files (py, js, etc.)

    # NEW REQUIRED ICONS
    "rotate_left": "rotate_left",  # Rotation controls
    "rotate_right": "rotate_right",
    "zoom_in": "zoom_in",  # Zoom controls
    "zoom_out": "zoom_out",
    "filter_alt": "filter_alt",  # Empty thumbnails filter
    "grid_view": "grid_view",  # Grid view toggle
    "history": "history",  # History/undo
}

# FOLDER MAPPING (for path updates)
FOLDER_MAPPING: Dict[str, str] = {
    # Category → new folder
    "keyboard_arrow_up": "navigation",
    "keyboard_arrow_down": "navigation",
    "keyboard_arrow_right": "navigation",
    "close": "navigation",
    "menu": "navigation",
    "search": "navigation",

    "content_cut": "editing",
    "content_paste": "editing",
    "content_copy": "editing",
    "edit": "editing",
    "undo": "editing",
    "redo": "editing",
    "rotate_left": "editing",  # NEW
    "rotate_right": "editing",  # NEW

    "folder": "files",
    "create_new_folder": "files",
    "draft": "files",
    "note_add": "files",
    "save": "files",
    "download": "files",
    "refresh": "files",
    "folder_zip": "files",  # NEW: archives

    "check_box": "selection",
    "check_box_outline_blank": "selection",

    "add": "toggles",
    "remove": "toggles",
    "toggle_off": "toggles",
    "toggle_on": "toggles",

    "info": "utilities",
    "list": "utilities",
    "schedule": "utilities",
    "tag": "utilities",
    "palette": "utilities",
    "view_column": "utilities",
    "stacks": "utilities",  # NEW: replaces layers
    "more_vert": "utilities",
    "zoom_in": "utilities",  # NEW
    "zoom_out": "utilities",  # NEW
    "filter_alt": "utilities",  # NEW
    "grid_view": "utilities",  # NEW
    "history": "utilities",  # NEW
    "flip_camera_ios": "utilities",  # NEW
    "progress_activity": "utilities",  # NEW

    "circle": "metadata",
    "check_circle": "metadata",
    "edit_note": "metadata",
    "error": "metadata",
    "warning": "metadata",

    # File type icons
    "image": "filetypes",  # NEW category
    "photo": "filetypes",
    "movie": "filetypes",
    "audio_file": "filetypes",
    "description": "filetypes",
    "code": "filetypes",
}


def print_mapping_table():
    """Print the icon mapping table for reference."""
    print("=" * 80)
    print("ICON MIGRATION MAPPING: Feather → Material Design")
    print("=" * 80)
    print(f"{'Feather Icon':<25} → {'Material Design Icon':<30} Category")
    print("-" * 80)

    for feather, material in sorted(ICON_MAPPING.items()):
        category = FOLDER_MAPPING.get(material, "unknown")
        print(f"{feather:<25} → {material:<30} {category}")

    print("-" * 80)
    print(f"Total mappings: {len(ICON_MAPPING)}")
    print("=" * 80)


def find_icon_usages(root_dir: Path, dry_run: bool = True):
    """
    Find all icon usages in Python files.

    Args:
        root_dir: Root directory to search
        dry_run: If True, only report findings without making changes
    """
    # Exclude .venv, __pycache__, .git, etc.
    python_files = [
        f for f in root_dir.rglob("*.py")
        if not any(part.startswith('.') for part in f.parts)
        and '__pycache__' not in f.parts
        and '.venv' not in f.parts
        and 'htmlcov' not in f.parts
    ]

    # Patterns to search for
    patterns = [
        r'get_menu_icon\(["\']([^"\']+)["\']\)',  # get_menu_icon("icon-name")
        r'\.svg\(["\']([^"\']+)["\']\)',          # .svg("icon-name")
        r'feather_icons/([^"\']+)\.svg',          # feather_icons/icon-name.svg
    ]

    findings = []

    for py_file in python_files:
        try:
            content = py_file.read_text(encoding='utf-8')

            for pattern in patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    icon_name = match.group(1)
                    if icon_name in ICON_MAPPING:
                        findings.append({
                            'draft': py_file,
                            'icon': icon_name,
                            'new_icon': ICON_MAPPING[icon_name],
                            'pattern': pattern,
                            'match': match.group(0)
                        })
        except Exception as e:
            print(f"Error reading {py_file}: {e}")

    # Report findings
    print(f"\nFound {len(findings)} icon usages to migrate:")
    print("-" * 80)

    files_with_changes = {}
    for finding in findings:
        file_path = finding['draft']
        if file_path not in files_with_changes:
            files_with_changes[file_path] = []
        files_with_changes[file_path].append(finding)

    for file_path, file_findings in sorted(files_with_changes.items()):
        rel_path = file_path.relative_to(root_dir)
        print(f"\n{rel_path} ({len(file_findings)} changes):")
        for f in file_findings:
            print(f"  {f['icon']:25} → {f['new_icon']}")

    return findings


def migrate_icon_names(root_dir: Path, dry_run: bool = True):
    """
    Migrate icon names in Python files.

    Args:
        root_dir: Root directory to search
        dry_run: If True, only report what would change without making changes
    """
    # Exclude .venv, __pycache__, .git, etc.
    python_files = [
        f for f in root_dir.rglob("*.py")
        if not any(part.startswith('.') for part in f.parts)
        and '__pycache__' not in f.parts
        and '.venv' not in f.parts
        and 'htmlcov' not in f.parts
    ]
    total_replacements = 0

    for py_file in python_files:
        try:
            content = py_file.read_text(encoding='utf-8')
            original_content = content

            # Replace icon names in various contexts
            for feather, material in ICON_MAPPING.items():
                # Pattern 1: get_menu_icon("icon-name")
                content = re.sub(
                    rf'(get_menu_icon\(["\']){feather}(["\'])',
                    rf'\1{material}\2',
                    content
                )

                # Pattern 2: feather_icons/icon-name.svg paths
                content = re.sub(
                    rf'feather_icons/{feather}\.svg',
                    f'{FOLDER_MAPPING.get(material, "icons")}/{material}.svg',
                    content
                )

                # Pattern 3: ICON_MAPPINGS dictionary values
                content = re.sub(
                    rf'(["\']){feather}(["\'])',
                    rf'\1{material}\2',
                    content
                )

            if content != original_content:
                total_replacements += 1
                rel_path = py_file.relative_to(root_dir)

                if dry_run:
                    print(f"Would update: {rel_path}")
                else:
                    py_file.write_text(content, encoding='utf-8')
                    print(f"Updated: {rel_path}")

        except Exception as e:
            print(f"Error processing {py_file}: {e}")

    print(f"\n{'Would update' if dry_run else 'Updated'} {total_replacements} files")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Migrate Feather icons to Material Design icons'
    )
    parser.add_argument(
        '--show-mapping',
        action='store_true',
        help='Show the icon mapping table'
    )
    parser.add_argument(
        '--find',
        action='store_true',
        help='Find all icon usages in the codebase'
    )
    parser.add_argument(
        '--migrate',
        action='store_true',
        help='Migrate icon names (use --no-dry-run to apply changes)'
    )
    parser.add_argument(
        '--no-dry-run',
        action='store_true',
        help='Actually apply changes (default is dry-run)'
    )
    parser.add_argument(
        '--root',
        type=Path,
        default=Path(__file__).parent.parent,
        help='Root directory of the project'
    )

    args = parser.parse_args()

    if args.show_mapping:
        print_mapping_table()

    if args.find:
        find_icon_usages(args.root, dry_run=True)

    if args.migrate:
        dry_run = not args.no_dry_run
        if dry_run:
            print("\n*** DRY RUN MODE - No changes will be made ***\n")
        migrate_icon_names(args.root, dry_run=dry_run)

    if not (args.show_mapping or args.find or args.migrate):
        parser.print_help()


if __name__ == '__main__':
    main()
