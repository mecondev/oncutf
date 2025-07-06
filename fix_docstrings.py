#!/usr/bin/env python3
"""
Script to fix all Python files by adding proper module docstrings with Author and Date fields.
"""

import os
import re
from pathlib import Path
from datetime import datetime

def get_proper_date(file_path):
    """Get the proper date for a file based on its creation/modification time."""
    try:
        # Get file modification time
        mtime = os.path.getmtime(file_path)
        file_date = datetime.fromtimestamp(mtime)

        # If file is older than 2025-05-31, use 2025-05-31
        # If file is newer, use 2025-07-06 (today)
        cutoff_date = datetime(2025, 5, 31)
        today = datetime(2025, 7, 6)

        if file_date < cutoff_date:
            return "2025-05-31"
        else:
            return "2025-07-06"
    except:
        return "2025-07-06"

def fix_docstring(file_path):
    """Fix the docstring in a Python file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Skip if file is empty
        if not content.strip():
            return False

        # Get the module name from file path
        module_name = Path(file_path).name

        # Get the proper date
        proper_date = get_proper_date(file_path)

        # Check if file already has proper docstring with Author and Date
        if 'Author: Michael Economou' in content and 'Date: 202' in content:
            print(f"✅ Already correct: {file_path}")
            return False

        # Pattern to match existing docstring
        docstring_pattern = r'^(#!/usr/bin/env python3\s*\n)?"""([^"]*)"""'

        # Check if file starts with shebang
        has_shebang = content.startswith('#!/usr/bin/env python3')

        # Create the new docstring
        new_docstring = f'''"""
Module: {module_name}

Author: Michael Economou
Date: {proper_date}

'''

        # Try to find existing docstring
        match = re.search(docstring_pattern, content, re.MULTILINE | re.DOTALL)

        if match:
            # Extract existing description
            existing_desc = match.group(2).strip()

            # Skip Author/Date lines if they exist
            desc_lines = []
            for line in existing_desc.split('\n'):
                line = line.strip()
                if line and not line.startswith('Author:') and not line.startswith('Date:') and not line.startswith('Module:'):
                    desc_lines.append(line)

            if desc_lines:
                # Add existing description
                new_docstring += '\n'.join(desc_lines) + '\n'

            new_docstring += '"""'

            # Replace the existing docstring
            if has_shebang:
                shebang_line = "#!/usr/bin/env python3\n"
                rest_content = content[len(shebang_line):]
                new_content = shebang_line + new_docstring + '\n' + re.sub(docstring_pattern, '', rest_content, count=1).lstrip()
            else:
                new_content = new_docstring + '\n' + re.sub(docstring_pattern, '', content, count=1).lstrip()
        else:
            # No existing docstring, add one
            new_docstring += '"""'

            if has_shebang:
                shebang_line = "#!/usr/bin/env python3\n"
                rest_content = content[len(shebang_line):]
                new_content = shebang_line + new_docstring + '\n' + rest_content
            else:
                new_content = new_docstring + '\n' + content

        # Write the fixed content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        print(f"✅ Fixed: {file_path}")
        return True

    except Exception as e:
        print(f"❌ Error fixing {file_path}: {e}")
        return False

def main():
    """Main function to fix all Python files."""
    project_root = Path(".")

    # Find all Python files
    python_files = []
    for pattern in ["**/*.py"]:
        python_files.extend(project_root.glob(pattern))

    # Filter out __pycache__ and other unwanted directories
    python_files = [f for f in python_files if '__pycache__' not in str(f) and '.git' not in str(f)]

    print(f"Found {len(python_files)} Python files to process")

    fixed_count = 0
    for file_path in sorted(python_files):
        if fix_docstring(file_path):
            fixed_count += 1

    print(f"\n✅ Fixed {fixed_count} files")
    print(f"✅ Processed {len(python_files)} files total")

if __name__ == "__main__":
    main()
