"""
Module: extract_full_structure.py
Extract full project structure with docstring snippets and coverage statistics.

This script generates a comprehensive project structure report including:
- Directory tree visualization with emoji icons
- Python file docstring extraction and display
- Documentation coverage statistics
- List of files missing module-level docstrings

Author: Michael Economou
Date: 2025-01-17
"""

import argparse
from pathlib import Path


def get_docstring_snippet(file_path):
    try:
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()
        in_doc = False
        doc_lines = []
        for line in lines:
            line = line.strip()
            if line.startswith(('"""', "'''")):
                if in_doc:
                    doc_lines.append(line)
                    break
                else:
                    in_doc = True
                    doc_lines.append(line)
            elif in_doc:
                doc_lines.append(line)
        return " ".join(doc_lines).replace('"""', '').replace("'''", '').strip()
    except Exception:
        return ""

def build_structure(path, prefix="", docstats=None, missing=None):
    lines = []
    for item in sorted(path.iterdir()):
        if item.name.startswith(".") or item.name in {"__pycache__", "venv"}:
            continue
        if item.is_dir():
            lines.append(f"{prefix} {item.name}/")
            lines.extend(build_structure(item, prefix + "    ", docstats, missing))
        elif item.suffix == ".py":
            docstats["total"] += 1
            snippet = get_docstring_snippet(item)
            if snippet:
                docstats["documented"] += 1
                lines.append(f"{prefix} {item.name} — *{snippet}*")
            else:
                lines.append(f"{prefix} {item.name}")
                missing.append(str(item.relative_to(path)))
        else:
            lines.append(f"{prefix} {item.name}")
    return lines

def main():
    parser = argparse.ArgumentParser(description="Extract full project structure with docstring snippets.")
    parser.add_argument("-p", "--path", type=str, default=".", help="Project root path")
    parser.add_argument("-o", "--output", type=str, default="reports/project_structure.md", help="Output Markdown file")
    parser.add_argument("--markdown", action="store_true", help="Enable Markdown output (default: on)")
    args = parser.parse_args()

    project_path = Path(args.path).resolve()
    output_path = Path(args.output).resolve()

    output_path.parent.mkdir(parents=True, exist_ok=True)

    docstats = {"total": 0, "documented": 0}
    missing = []
    structure = build_structure(project_path, docstats=docstats, missing=missing)

    coverage_percent = (docstats["documented"] / docstats["total"] * 100) if docstats["total"] else 0

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# Project Structure with Docstring Snippets\n\n")
        f.write(f"**Docstring Coverage:** {docstats['documented']} / {docstats['total']} files documented ({coverage_percent:.1f}%)\n\n")
        f.write("\n".join(structure))
        if missing:
            f.write("\n\n---\n\n")
            f.write("## ️ Files Missing Module-Level Docstrings\n\n")
            for m in missing:
                f.write(f"- {m}\n")

    print(f"\n Structure written to: {output_path}")
    print(f" Docstring Coverage: {docstats['documented']} / {docstats['total']} files ({coverage_percent:.1f}%)")
    if missing:
        print("\n️ Missing docstrings:")
        for m in missing:
            print(f" - {m}")

if __name__ == "__main__":
    main()
