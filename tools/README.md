# Developer Tools

This directory contains utility scripts for development, maintenance, and analysis of the codebase. These tools are **not** part of the runtime application and are intended for use by developers only.

## Categories

### Audit & Analysis
- `audit_boundaries.py`: Enforce architectural boundaries.
- `audit_dead_code.py` (if applicable): Detect unused code.
- `logger_analyzer.py`: Analyze logging usage and performance.
- `metadata_comparison_analysis.py`: Compare metadata extraction results.
- `analyze_metadata_fields.py`: Analyze metadata field usage.
- `vulture_whitelist.py`: Whitelist for Vulture dead code analysis.

### Maintenance
- `add_module_docstrings.py`: Bulk add docstrings to modules.
- `fix_module_dates.py`: Update or fix file header dates.
- `fix_type_ignore.py`: Manage type: ignore comments.
- `translate_greek_to_english.py`: Helper to translate legacy variable names.

### Profiling & Benchmarking
- `performance_profiler.py`: General performance profiling tool.
- `benchmark_parallel_loading.py`: Benchmark parallel loading performance.
- `profile_*.py`: Specialized profiling scripts (startup, memory, etc.).

### Manual Tests
- `test_*.py`: Standalone scripts for testing specific components or behaviors manually.
