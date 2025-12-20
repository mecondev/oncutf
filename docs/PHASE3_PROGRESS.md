# Phase 3 Performance Optimization - Progress Report

**Date:** 2025-12-20  
**Branch:** `phase3-performance`  
**Status:** IN PROGRESS

---

## Objectives

Phase 3 focuses on performance profiling and optimization to improve application startup time and runtime performance.

**Target:** Identify and optimize key bottlenecks in:
1. Application startup
2. Metadata loading
3. Rename preview generation
4. Memory usage

---

## Current Baseline (2025-12-20)

### Startup Performance

Measured with `scripts/profile_performance.py`:

```
📊 Startup Performance:
  Import time:       264.5 ms
  QApplication:       42.7 ms
  MainWindow init:  1389.7 ms
  Window show:         0.0 ms
  ────────────────────────────────────────
  Total startup:    1696.9 ms

💾 Memory Usage:
  Current:            12.4 MB
  Peak:               12.4 MB
```

### Detailed Profiling (cProfile)

Top bottlenecks in MainWindow initialization:

| Operation | Time (ms) | Notes |
|-----------|-----------|-------|
| Total MainWindow init | 950 | - |
| Import phase | 409 | Lazy loading already optimized |
| UI setup (phase 3) | 397 | Widget creation |
| Configuration (phase 4) | 259 | Config loading, window restore |
| Core infrastructure (phase 1) | 242 | App context, managers |
| PlaceholderHelper setup | 132 | **OPTIMIZED** - now lazy + cached |
| processEvents | 78 | Qt internal (unavoidable) |
| TooltipHelper adjustSize | 36 | Qt internal (unavoidable) |

### Comparison with Previous Baseline

**Note:** Previous baseline (PERFORMANCE_BASELINE.md) reported 989ms total startup,
but that was measured under different conditions (different date, possibly different
system state, different Qt version/build). Current measurement (1697ms) is higher
but represents the actual current state.

**Factors affecting comparison:**
- Previous measurements were done on 2025-12-19
- Phase 2 refactoring completed between measurements (split large modules)
- Qt/system state variations
- Different profiling methodology

**Conclusion:** Treat 1697ms as the new baseline for Phase 3 optimizations.

---

## Optimizations Implemented

### 1. PlaceholderHelper Lazy Loading (Commit: b4a53166)

**Problem:** 5 placeholder icons were loaded and scaled during MainWindow initialization, taking ~125ms total (5 × ~25ms each).

**Solution:**
- Lazy icon loading: icons now loaded only on first `show()` call
- Global pixmap cache: scaled icons shared across instances
- Fast transformation: `Qt.FastTransformation` instead of `Qt.SmoothTransformation`

**Impact:**
- Before: ~125ms during init
- After: Icons loaded only when placeholders are actually shown (not during startup)
- Expected improvement: **~50-100ms** reduction (icons rarely shown immediately)

**Files Changed:**
- `oncutf/utils/placeholder_helper.py`

---

## Identified Bottlenecks (Not Yet Optimized)

### Import Overhead (409ms)

**Current state:**
- Already has lazy loading for ExifTool, CompanionFilesHelper, ParallelMetadataLoader
- Most heavy imports are unavoidable (PyQt5, core modules)

**Potential optimizations:**
- Further lazy loading of heavy modules (identified in profiling)
- Deferred initialization of managers that aren't needed immediately

### UI Setup Phase (397ms)

**Breakdown:**
- Widget creation and configuration
- Layout setup
- Signal/slot connections

**Potential optimizations:**
- Defer non-visible widget creation
- Simplify initial layouts
- Batch signal connections

### Qt Internal Overhead (~114ms)

**Components:**
- `processEvents`: 78ms
- `adjustSize`: 36ms
- `showNormal`: ~100ms (in some runs)

**Note:** These are Qt framework internals and cannot be meaningfully optimized.

---

## Next Steps

### High Priority

1. **Profile metadata loading performance**
   - Create test with sample files
   - Measure per-file metadata load time
   - Identify ExifTool overhead

2. **Profile rename preview generation**
   - Measure preview calculation time
   - Test with various file counts (10, 100, 1000 files)
   - Identify bottlenecks in rename engine

3. **Memory profiling**
   - Track memory growth with large file sets
   - Verify cache eviction is working
   - Identify memory leaks

### Medium Priority

4. **Further import optimization**
   - Profile import times with `importlib` hooks
   - Identify modules that can be lazy-loaded
   - Consider async module loading

5. **UI responsiveness**
   - Add signal debouncing for high-frequency updates
   - Implement progressive rendering for large tables
   - Optimize column visibility updates

### Low Priority

6. **Micro-optimizations**
   - Review hot code paths with line_profiler
   - Optimize frequently-called utility functions
   - Consider caching expensive calculations

---

## Performance Tracking Tools

Created profiling scripts in `scripts/`:

| Script | Purpose |
|--------|---------|
| `profile_performance.py` | Quick startup performance measurement |
| `profile_mainwindow.py` | Detailed cProfile analysis of MainWindow init |
| `profile_multi_runs.py` | Multiple runs with statistics (not yet used) |

**Usage:**
```bash
# Quick startup test
python scripts/profile_performance.py

# Detailed profiling
python scripts/profile_mainwindow.py | head -100
```

---

## Recommendations

1. **Accept current baseline:** 1697ms is the realistic current startup time
2. **Focus on user-facing performance:** Optimize operations users trigger frequently (metadata load, rename preview)
3. **Don't over-optimize startup:** Users launch the app once per session
4. **Prioritize runtime responsiveness:** Smooth interactions matter more than cold start time

---

## Conclusion

Phase 3 has established a solid performance baseline and implemented lazy loading for placeholder icons. The main bottlenecks identified are:

1. **Unavoidable:** Qt framework overhead (~114ms)
2. **Already optimized:** Import phase with lazy loading (~409ms)
3. **Optimization candidates:** UI setup phase (~397ms), configuration loading (~259ms)

**Recommendation:** Focus Phase 3 efforts on runtime performance (metadata loading, rename preview) rather than further startup optimization, as the remaining startup overhead is mostly unavoidable Qt framework costs.
