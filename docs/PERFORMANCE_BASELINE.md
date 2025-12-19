# Performance Baseline Documentation

> **Date**: December 19, 2025  
> **Environment**: Linux, Python 3.13, PyQt5  
> **Author**: Michael Economou

---

## Overview

This document captures baseline performance metrics for the oncutf application
before Phase 7 optimization work. These metrics serve as reference points to
measure improvement.

---

## 1. Startup Time Metrics

### Import Times

| Module | Time (ms) | Notes |
|--------|-----------|-------|
| PyQt5 | 6.6 | Qt bindings init |
| PyQt5.QtWidgets | 111.0 | Main widget library |
| oncutf | 0.5 | Package init |
| oncutf.config | 3.4 | Configuration loading |
| oncutf.core | 2.1 | Core package |
| oncutf.core.application_context | 30.6 | App context setup |
| oncutf.core.application_service | 40.9 | Service layer |
| oncutf.core.unified_rename_engine | 48.0 | Rename engine |
| oncutf.core.unified_metadata_manager | 153.8 | **Slowest - metadata management** |
| oncutf.ui.main_window | 4.1 | UI (already imported deps) |
| oncutf.services | 6.8 | Service protocols |
| oncutf.controllers | 7.2 | Controllers |

**Total Import Time**: 415.0 ms

### Window Creation

| Phase | Time (ms) | Notes |
|-------|-----------|-------|
| MainWindow.__init__ | 928.6 | **Main bottleneck** |
| MainWindow.show() | 82.6 | First paint |

**Total Startup Time**: ~1.43 seconds

### Top 5 Slowest Imports

1. `oncutf.core.unified_metadata_manager`: 153.8ms
2. `PyQt5.QtWidgets`: 111.0ms  
3. `oncutf.core.unified_rename_engine`: 48.0ms
4. `oncutf.core.application_service`: 40.9ms
5. `oncutf.core.application_context`: 30.6ms

---

## 2. Memory Usage Metrics

### Memory by Phase

| Phase | Memory | Notes |
|-------|--------|-------|
| After PyQt5 import | 3.6 MB | Qt initialization |
| After oncutf import | 5.1 MB | +1.5 MB for app modules |
| After QApplication | 5.1 MB | No significant change |
| After MainWindow | 13.9 MB | +8.8 MB for UI |

**Peak Memory**: 13.9 MB

### Top Memory Consumers (Python tracemalloc)

| Location | Size | Count | Notes |
|----------|------|-------|-------|
| importlib (frozen) | 5.4 MB | 44,752 | Python import machinery |
| bootstrap (frozen) | 3.0 MB | 19,086 | Module loading |
| pathlib | 939.3 KB | 13 | Path operations |
| linecache | 403.4 KB | 4,017 | Source line reading |
| typing.py | 258.6 KB | 1,915 | Type annotations |
| main_window.py | 159.7 KB | 2,313 | Main UI |
| logger_helper.py | 99.4 KB | 1,590 | Logging setup |

### Top Files by Memory

| File | Total | Notes |
|------|-------|-------|
| importlib (frozen) | 5.5 MB | Import system |
| bootstrap (frozen) | 3.1 MB | Module bootstrap |
| pathlib | 941.0 KB | Path handling |
| typing.py | 422.4 KB | Type hints |
| main_window.py | 199.7 KB | Main window |
| logger_helper.py | 147.8 KB | Logging |
| ui_manager.py | 145.6 KB | UI management |
| file_tree_view.py | 138.4 KB | Tree widget |

---

## 3. Identified Optimization Opportunities

### High Priority

1. **MainWindow.__init__ (928.6ms)**
   - This is the main bottleneck
   - Consider lazy initialization of managers
   - Defer non-essential widget creation

2. **unified_metadata_manager (153.8ms)**
   - Heaviest import
   - Consider lazy loading of ExifTool
   - Defer initialization until first use

### Medium Priority

3. **logger_helper.py**
   - Uses 147.8 KB memory
   - Many partial function objects (1,590)
   - Consider optimization of safe_log wrapper

4. **unified_rename_engine (48.0ms)**
   - Heavy initialization
   - Consider lazy module loading

### Low Priority

5. **PyQt5.QtWidgets (111.0ms)**
   - External dependency, limited optimization potential
   - Could use selective imports but impact may be minimal

---

## 4. Optimization Targets

Based on baseline metrics, reasonable targets for Phase 7:

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| Total Startup | 1.43s | <1.0s | 30% |
| Import Time | 415ms | 300ms | 28% |
| Window Creation | 928ms | 600ms | 35% |
| Peak Memory | 13.9 MB | 12 MB | 14% |

---

## 5. Test Environment Details

```
OS: Linux (Ubuntu/Debian variant)
Python: 3.13.0
PyQt5: 5.15.x
Test files: None (empty startup)
ExifTool: Not spawned (no files loaded)
```

---

## 6. Notes

- Memory measurements use Python's tracemalloc
- Startup times measured with time.perf_counter()
- Metrics captured on development machine
- Production performance may vary based on:
  - Hardware specs
  - Installed Python packages
  - Qt themes and plugins
  - Available system memory

---

*This baseline document will be updated after each optimization phase to track progress.*
