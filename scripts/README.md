# Scripts Directory

This directory contains utility scripts for repository maintenance, testing, and analysis.

## Translation & Localization

### translate_greek_to_english.py

Automatically translates Greek text to English across the entire codebase using OpenAI's GPT-4o-mini API.

**Features:**
- Detects Greek text in multiple contexts:
  - Python: comments, docstrings, logger messages, string literals
  - Markdown: headings, paragraphs, list items
  - JSON: string values
  - Plain text: all content
- Respects `.gitignore` exclusions (except `examples/` folder)
- Progress reporting with file-by-file change details
- API usage tracking with cost estimation
- Two modes: dry-run (default) and apply mode

**Requirements:**
```bash
pip install openai python-dotenv
```

**Setup:**
1. Create a `.env` file in the parent directory of the repo (one level up)
2. Add your OpenAI API key:
   ```
   OPENAI_API_KEY=sk-...
   ```

**Usage:**

**Dry-run mode** (shows what would change, no modifications):
```bash
python scripts/translate_greek_to_english.py
```

**Apply mode** (actually modifies files):
```bash
python scripts/translate_greek_to_english.py -f
```

**Scan specific directory:**
```bash
python scripts/translate_greek_to_english.py --root path/to/dir
```

**Sample output:**
```
Scanning repository: /mnt/data_1/edu/Python/oncutf
Mode: DRY-RUN (no changes will be made)
Extensions: .py, .txt, .md, .json
--------------------------------------------------------------------------------

File: scripts/test_html_icon.py
  Line 16 (comment):
```
    OLD: # Create rich text with inline indicators
```
    NEW: # Creating rich text with inline indicators

================================================================================
Summary:
  Files scanned: 145
  Files changed: 23
  Total translations: 187

API Usage Summary:
  Input tokens:  12,450
  Output tokens: 9,320
  
Estimated cost:
  Input:  $0.001868
  Output: $0.005592
  Total:  $0.007460 USD
```

**Important notes:**
- **Always run in dry-run mode first** to review changes before applying
- The script does **not** create backups - make sure your work is committed to git
- The script does **not** automatically commit changes - review and commit manually
- API costs are typically very low (few cents for entire codebase)
- Translation quality is optimized for technical/developer content

---

## Analysis & Documentation

### analyze_metadata_fields.py
Analyzes metadata field usage across files in the project.

### generate_project_report.py
**Unified project analysis tool** that generates comprehensive reports in two modes:

**Structure mode** - Full tree visualization with analysis:
```bash
python scripts/generate_project_report.py --mode structure
```
- Directory tree with indentation
- Module docstrings (inline snippets)
- Classes & functions listing per file
- Line counts per file
- Docstring coverage statistics
- Missing docstrings report

**Content mode** - AI-friendly context:
```bash
python scripts/generate_project_report.py --mode content
```
- Grouped by top-level directory
- Module docstrings (first line)
- Classes & functions listing
- Line counts & totals
- Optimized for AI assistants (Copilot, etc.)

**Options:**
```bash
# Custom output path
python scripts/generate_project_report.py --mode structure -o custom_report.md

# Exclude directories (repeatable)
python scripts/generate_project_report.py --mode structure --exclude tests --exclude scripts

# Non-recursive (root only)
python scripts/generate_project_report.py --mode structure --no-recursive

# Custom docstring length (default: 300)
python scripts/generate_project_report.py --mode content --max-doc-length 500
```

This script replaces the older `extract_docstrings.py`, `extract_full_structure.py`, and `generate_project_context.py` scripts.

### logger_analyzer.py
Analyzes logging patterns, coverage, and usage.

### metadata_comparison_analysis.py
Compares different metadata extraction methods and their results.

---

## Testing Scripts

### run_all_tests.py
Test runner with detailed reporting and coverage options.

### test_hash_dialog_shortcuts.py
Tests keyboard shortcuts functionality in hash dialogs.

### test_html_icon.py
Tests HTML rendering in UI components.

### test_parallel_hash.py
Performance tests for parallel hash computation.

### test_preview_debounce.py
Tests debouncing behavior in preview features.

### test_qss.py
Tests Qt stylesheet application and validation.

### test_results_dialog.py
Tests results dialog functionality and behavior.

### test_shortcuts_behavior.py
Tests keyboard shortcut behavior across the application.

---

## Maintenance Scripts

### add_module_docstrings.py
Adds or updates module-level docstrings in Python files.

### benchmark_parallel_loading.py
Performance benchmarking for parallel loading operations.

---

## General Usage

Most scripts can be run directly:
```bash
python scripts/<script_name>.py
```

Some scripts may require additional dependencies. Check the script header for requirements.

For questions or issues, refer to the main project documentation or individual script docstrings.
