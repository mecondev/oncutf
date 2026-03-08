# Benchmarking: pip vs uv Detailed Comparison

Systematic guide for comparing `tests.yml` (pip) and `tests-uv.yml` (uv) workflows.

---

## Overview

This document helps you:

- Run controlled comparisons
- Collect meaningful data
- Make informed decision on uv adoption
- Document findings

**Target:** 20+ data points over 4 weeks

---

## Step 1: Initial Setup

### Prerequisites

- Both workflows enabled
- Access to GitHub Actions tab
- Spreadsheet or editor for notes
- ~4 weeks of CI runs (minimum 2 per week)

### What to Monitor

1. Total workflow runtime
2. Dependency installation time
3. Cache behavior
4. Test results consistency
5. Dependency versions

---

## Step 2: Data Collection

### Collection Method

#### Option A: Manual (From UI)

1. Go to **Actions** tab
2. Click on workflow run
3. Expand each job
4. Note timings from logs

#### Option B: Automated (Future)

```bash
# Use GitHub API to fetch timing data
gh run list --json durationMinutes,status,name
```

### Per-Run Checklist

For each run, fill in:

```plaintext
Date: [YYYY-MM-DD HH:MM]
Event: [push / pull_request]
Branch: [branch-name]
Commit: [short-sha]

=== tests.yml (pip) ===
[ ] Workflow started
[ ] Lint completed: [total time]
[ ] Typecheck completed: [total time]
[ ] Tests completed: [total time]
[ ] All passed: Y/N
[ ] Cache hit: Y/N
[ ] Notable issues: [none / list]

=== tests-uv.yml (uv) ===
[ ] Workflow started
[ ] Lint completed: [total time]
[ ] Typecheck completed: [total time]
[ ] Tests completed: [total time]
[ ] All passed: Y/N
[ ] Cache hit: Y/N
[ ] Notable issues: [none / list]

=== Comparison ===
Faster: [pip / uv] by [X%]
Results match: Y/N
```

---

## Step 3: Performance Baseline

### Run 1-5: Establish Baseline (Week 1)

Fill in actual times from your first 5 runs:

### PR Baseline (Pull Request)

| Run | Date | pip (s) | uv (s) | Δ | Cache | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `__-__` | `___` | `___` | `-__%` | ?/? | |
| 2 | `__-__` | `___` | `___` | `-__%` | ?/? | |
| 3 | `__-__` | `___` | `___` | `-__%` | ?/? | |
| 4 | `__-__` | `___` | `___` | `-__%` | ?/? | |
| 5 | `__-__` | `___` | `___` | `-__%` | ?/? | |
| **Avg** | | `___` | `___` | **-__%** | | **Baseline** |

### Push Baseline (Feature Branch)

| Run | Date | pip (s) | uv (s) | Δ | Cache | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `__-__` | `___` | `___` | `-__%` | ?/? | |
| 2 | `__-__` | `___` | `___` | `-__%` | ?/? | |
| 3 | `__-__` | `___` | `___` | `-__%` | ?/? | |
| 4 | `__-__` | `___` | `___` | `-__%` | ?/? | |
| 5 | `__-__` | `___` | `___` | `-_-%` | ?/? | |
| **Avg** | | `___` | `___` | **-__%** | | **Baseline** |

#### Assessment

- [ ] uv is faster (target: 10%+)
- [ ] uv is slower (unexpected)
- [ ] About the same (caching effect)

---

## Step 4: Stability Testing (Weeks 2-3)

### Run 6-15: Monitor for Issues

Collect 10 more runs watching for:

#### Test Consistency Check

| Run | Date | pip tests | uv tests | Match | Issues |
| --- | --- | --- | --- | --- | --- |
| 6 | `__-__` | ✓ / ✗ | ✓ / ✗ | ✓/✗ | |
| 7 | `__-__` | ✓ / ✗ | ✓ / ✗ | ✓/✗ | |
| 8 | `__-__` | ✓ / ✗ | ✓ / ✗ | ✓/✗ | |
| 9 | `__-__` | ✓ / ✗ | ✓ / ✗ | ✓/✗ | |
| 10 | `__-__` | ✓ / ✗ | ✓ / ✗ | ✓/✗ | |
| ... | | | | | |
| 15 | `__-__` | ✓ / ✗ | ✓ / ✗ | ✓/✗ | |

#### Green flags

- [ ] 100% match between pip and uv tests
- [ ] No flaky failures
- [ ] No platform-specific differences

#### Red flags

- [ ] Tests fail on uv but pass on pip (or vice versa)
- [ ] Intermittent failures with uv only
- [ ] Different failures between workflows

---

## Step 5: Dependency Comparison

### Check What Gets Installed

From workflow logs, extract package versions:

```bash
# Log into workflow, copy output of:
pip list --format=freeze | sort
# vs
uv pip list --format=freeze | sort
```

#### Create comparison

| Package | pip version | uv version | Match | Notes |
| --- | --- | --- | --- | --- |
| PyQt5 | `____` | `____` | ✓/✗ | Critical |
| pytest | `____` | `____` | ✓/✗ | Critical |
| ruff | `____` | `____` | ✓/✗ | Critical |
| mypy | `____` | `____` | ✓/✗ | Critical |
| rawpy | `____` | `____` | ✓/✗ | Critical |
| Pillow | `____` | `____` | ✓/✗ | Important |
| watchdog | `____` | `____` | ✓/✗ | Important |
| exiftool | — | — | ✓/✗ | System |

#### Critical packages that MUST match

```plaintext
PyQt5
pytest
ruff
mypy
rawpy
```

**Acceptable differences:**

- Patch version (1.2.3 vs 1.2.4)
- Optional deps
- Build backend differences

**Not acceptable:**

- Major/minor version differences in core deps
- Different Python version requirements
- Missing packages on one side

---

## Step 6: Cross-Platform Validation (Weeks 3-4)

### Test on All Platforms

Matrix to fill in (at least 2 runs per platform):

#### Linux (Ubuntu, Python 3.12 + 3.13)

| Date | Python | pip (s) | uv (s) | Δ | Tests | Issues |
| --- | --- | --- | --- | --- | --- | --- |
| `__-__` | 3.12 | `__` | `__` | | ✓/✗ | |
| `__-__` | 3.12 | `__` | `__` | | ✓/✗ | |
| `__-__` | 3.13 | `__` | `__` | | ✓/✗ | |
| `__-__` | 3.13 | `__` | `__` | | ✓/✗ | |

#### Windows (Python 3.12 + 3.13)

| Date | Python | pip (s) | uv (s) | Δ | Tests | Issues |
| --- | --- | --- | --- | --- | --- | --- |
| `__-__` | 3.12 | `__` | `__` | | ✓/✗ | |
| `__-__` | 3.12 | `__` | `__` | | ✓/✗ | |
| `__-__` | 3.13 | `__` | `__` | | ✓/✗ | |
| `__-__` | 3.13 | `__` | `__` | | ✓/✗ | |

#### macOS (Python 3.12 + 3.13)

| Date | Python | pip (s) | uv (s) | Δ | Tests | Issues |
| --- | --- | --- | --- | --- | --- | --- |
| `__-__` | 3.12 | `__` | `__` | | ✓/✗ | |
| `__-__` | 3.12 | `__` | `__` | | ✓/✗ | |
| `__-__` | 3.13 | `__` | `__` | | ✓/✗ | |
| `__-__` | 3.13 | `__` | `__` | | ✓/✗ | |

#### Must verify

- [ ] All Python versions work equally
- [ ] All platforms have comparable speed
- [ ] No platform-specific failures

---

## Step 7: Final Assessment

### Success Metrics Scorecard

```plaintext
PERFORMANCE
  Speed improvement 10%+          [ ] Pass / [ ] Fail
  Consistent across runs          [ ] Pass / [ ] Fail
  Consistent across platforms     [ ] Pass / [ ] Fail

STABILITY
  All tests pass (pip)            [ ] Pass / [ ] Fail
  All tests pass (uv)             [ ] Pass / [ ] Fail
  Results identical               [ ] Pass / [ ] Fail
  No platform-specific issues     [ ] Pass / [ ] Fail

DEPENDENCIES
  Critical packages match         [ ] Pass / [ ] Fail
  PyQt5 installs OK              [ ] Pass / [ ] Fail
  rawpy installs OK              [ ] Pass / [ ] Fail
  No unexpected differences       [ ] Pass / [ ] Fail

CACHE & BEHAVIOR
  Cache hits consistent           [ ] Pass / [ ] Fail
  No cache thrashing             [ ] Pass / [ ] Fail
  Predictable performance        [ ] Pass / [ ] Fail
```

### Decision Matrix

| Criterion | Target | Actual | Status |
| --- | --- | --- | --- |
| Speed improvement | 10%+ | `___%` | ✓/✗ |
| Stability matches | 100% | `___%` | ✓/✗ |
| Test consistency | 100% | `___%` | ✓/✗ |
| Platform coverage | 3 OS | `_` | ✓/✗ |
| Data points | 20+ | `_` | ✓/✗ |

### Final Recommendation

```plaintext
Date: [YYYY-MM-DD]
Reviewed by: [Your name]

RECOMMENDATION: [ ] Adopt uv  / [ ] Stay on pip / [ ] More testing needed

CONFIDENCE LEVEL: [ ] High (70%+) / [ ] Medium (50-70%) / [ ] Low (<50%)

SUMMARY:
________________________________________________________________________
________________________________________________________________________
________________________________________________________________________

NEXT STEPS:
- [ ] Migration to full uv (if adopt)
- [ ] More testing (if uncertain)
- [ ] Archive this data (always)
```

---

## Example Data (Filled In)

### Sample Run (Realistic)

```plaintext
=== PR Baseline (After 5 runs, Week 1) ===

pip average: 280s
uv average: 245s
Improvement: -12.5% ✓

Tests: 5/5 match ✓
Cache: 4/5 hit for both ✓
Issues: None ✓

=== Stability (After 10 runs, Week 2-3) ===

Test match rate: 10/10 (100%) ✓
Platform issues: None ✓
Dependency match: 100% critical packages ✓

=== Cross-Platform (Week 3-4) ===

Linux 3.12: pip=240s, uv=210s (-12.5%) ✓
Windows 3.12: pip=260s, uv=230s (-11.5%) ✓
macOS 3.13: pip=270s, uv=235s (-13%) ✓

=== Final ===

Date: 2026-04-22
RECOMMENDATION: Adopt uv
CONFIDENCE: High (78%)

Reasons:
- Consistent 12% speed improvement across all platforms
- 100% test result consistency
- No dependency resolution surprises
- PyQt5/rawpy/Pillow all work correctly
- Team ready for change

Action: Migrate to uv (Phase 3)
```

---

## Tips & Tricks

### Extract Timings Fast

```bash
# Copy from workflow log and parse:
grep "Completed" workflow.log | awk '{print $NF}'
```

### Compare Dependency Lists

```bash
# Create diffs automatically
pip list --format=freeze > pip.txt
uv pip list --format=freeze > uv.txt
diff pip.txt uv.txt
```

### Automate Data Collection

```bash
# Eventually: use GitHub API
gh run list --json durationMinutes,name,status \
  --jq '.[] | select(.name | contains("Tests")) | "\(.name): \(.durationMinutes)m (\(.status))"'
```

### Track Over Time

```csv
Date,Event,Pipeline,Runtime_seconds,Cache_hit,Tests_passed
2026-03-15,push,pip,280,true,100
2026-03-15,push,uv,245,true,100
2026-03-16,pr,pip,285,true,100
2026-03-16,pr,uv,248,true,100
```

---

## Common Issues During Benchmarking

### Issue: Wildly Different Timings

**Cause:** GitHub runner variance
**Solution:** Average multiple runs (5+), ignore outliers

### Issue: uv Slower Than pip

**Cause:** First-time setup overhead, cache cold
**Solution:** Run 3-4 times per workflow to warm cache

### Issue: Different Test Results

**Cause:** Dependency resolution difference
**Solution:** Compare `pip list` outputs, investigate differences

### Issue: Cache Never Hits

**Cause:** Key mismatch or new runner
**Solution:** Check cache key in workflow, verify paths

---

## Success Criteria Summary

✓ **Must have all of these to adopt uv:**

1. 10%+ consistent speed improvement
2. 100% test result consistency
3. No dependency resolution surprises
4. All platforms stable
5. 20+ data points over 4 weeks

❌ **Any of these = stay on pip:**

1. Speed improvement <5%
2. Test failures on uv only
3. Dependency differences in critical packages
4. Platform-specific failures
5. Team concerns about tooling

---

## Document This Work

Store results in:

- **Short-term:** Notes in this file
- **Medium-term:** GitHub Discussion or Wiki
- **Long-term:** Archive in `docs/ci-migration/`

---

## References

- [COMPARISON.md](./COMPARISON.md) — Quick pip vs uv overview
- [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md) — Step-by-step migration (after decision)
- [tests.yml](./tests.yml) — Production workflow (pip)
- [tests-uv.yml](./tests-uv.yml) — Experiment workflow (uv)
