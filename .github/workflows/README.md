# GitHub Actions Workflows

## Overview

This directory contains two test workflow variants for oncutf:

### Version A: `tests.yml` (Production - pip-based)

**Status:** Active, production-ready

**Features:**

- Traditional pip-based dependency installation
- Built-in setup-python@v5 pip caching
- Smart matrix strategy:
  - **Pull requests:** Full matrix (3 OS × 2 Python versions = 6 jobs)
  - **Pushes:** Lighter matrix (ubuntu + windows, Python 3.12 only = 2 jobs)
- Concurrency control (cancels stale runs)
- Explicit permissions (contents: read)
- Cross-platform exiftool installation with fallback

**When to use:**

- Default for all main/develop branches
- Maximum stability and predictability
- Known dependency resolution behavior

**Runtime typical:**

- PR: ~15-20 minutes (full matrix)
- Push: ~5-8 minutes (lighter matrix)

---

### Version B: `tests-uv.yml` (Experiment - uv-based)

**Status:** Experimental, safe to test

**Features:**

- Uses `astral-sh/setup-uv@v4` for faster dependency resolution
- **pip-compatible mode** (not full project-mode migration)
- Same smart matrix strategy as Version A
- Same robustness features (concurrency, permissions, etc.)
- Uses `uv pip install --system` for compatibility

**When to use:**

- Testing faster CI runs
- Experimenting with uv dependency resolution
- Comparing performance vs pip

**Expected benefits:**

- 30-50% faster dependency installation
- Better cache behavior
- Modern resolver

**Known considerations:**

- Slightly different resolution logic than pip
- Not yet the default; monitor for edge cases
- PyQt5/rawpy/native deps need verification

**How to test:**

1. Push to `experiment/uv` branch
2. Compare timing with Version A on same commits
3. Verify test results match exactly
4. Watch for dependency resolution differences

---

## Matrix Strategy

Both workflows use smart matrix to balance coverage vs speed:

### Pull Requests (Full Coverage)

```yaml
OS: [ubuntu, windows, macos]
Python: [3.12, 3.13]
Total jobs: 3 × 2 = 6
```

**Why:** Maximum confidence before merge.

### Pushes (Fast Feedback)

```yaml
OS: [ubuntu, windows]
Python: [3.12]
Total jobs: 2
```

**Why:** Most failures caught on ubuntu; Windows covers platform-specific issues. macOS deferred to PR.

---

## Testing & Comparison

### How to Compare pip vs uv

If you want to test uv and compare with pip:

1. **Both workflows run in parallel** on develop/main
2. **Go to Actions tab** and compare timings
3. **Use [BENCHMARKING.md](./BENCHMARKING.md)** for systematic comparison
4. **Track data for 4 weeks** before deciding

**Important:** See [BENCHMARKING.md](./BENCHMARKING.md) for detailed templates, data collection guide, and success criteria.

### Documentation Files

| File | Purpose |
|------|---------|
| **[README.md](./README.md)** | This file — Overview & quick reference |
| **[COMPARISON.md](./COMPARISON.md)** | Detailed pip vs uv feature & performance comparison |
| **[BENCHMARKING.md](./BENCHMARKING.md)** | **Start here** — Data collection, templates, testing guide |
| **[MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md)** | Step-by-step migration plan (when ready) |
| **[CHANGELOG.md](./CHANGELOG.md)** | Version history & changes |

---

## Migration Path

### Current State

- `tests.yml` is the primary workflow
- `tests-uv.yml` is experimental

### Next Steps

1. **Run both workflows in parallel** on develop/main
2. **Benchmark both** using [BENCHMARKING.md](./BENCHMARKING.md):
   - Collect 20+ data points over 4 weeks
   - Track runtime, cache, test consistency
   - Compare dependency resolution
3. **Make decision:**
   - If uv stable & 10%+ faster → migrate (4-phase plan in MIGRATION_GUIDE.md)
   - If issues found → stay on pip
   - If uncertain → continue testing
4. If migrating:
   - Rename `tests-uv.yml` → `tests.yml`
   - Archive old `tests.yml` as `tests-pip-legacy.yml`

### Not Recommended Yet

- Full `uv sync` / lockfile workflow
- Removing pip entirely
- Mixing uv and pip in same workflow

**Why:** PyQt5 + cross-platform + native deps = proceed carefully.

---

## Workflow Quality Gates

All workflows run (in order):

1. **Lint (Ruff)** — Code style, imports, basic checks
2. **Typecheck (mypy)** — Static type analysis (3-tier strict config)
3. **Tests (pytest)** — Full test suite with Qt + exiftool

**Failure policy:** `fail-fast: false` — all matrix jobs run even if one fails.

---

## Adding New Workflows

When adding new workflows:

- Use same `permissions`, `concurrency` patterns
- Follow smart matrix strategy if applicable
- Document purpose in this README
- Keep in sync with project quality gates (ruff, mypy, pytest)

---

## Performance Tuning

Current optimizations:

- ✓ Built-in pip caching (Version A)
- ✓ uv caching (Version B)
- ✓ Concurrency cancellation
- ✓ Smart matrix
- ✓ Minimal dependency installs per job

Future considerations:

- Separate `lint` / `typecheck` / `test` extras in pyproject.toml
- Matrix excludes for known-good combinations
- Conditional Windows/macOS runs based on changed files

---

## Troubleshooting

### Slow dependency installation

- Check cache hit rates in workflow logs
- Consider Version B (uv) for faster resolution

### Cross-platform failures

- Check exiftool installation logs
- Verify Qt platform plugin setup (QT_QPA_PLATFORM)
- Test locally with same OS/Python combination

### Matrix confusion

- PR → full matrix (6 jobs)
- Push → light matrix (2 jobs)
- Both visible in Actions tab

### uv-specific issues

- Ensure `--system` flag used (no venv conflicts)
- Check for resolution differences vs pip
- Compare installed versions: `uv pip list` vs `pip list`

---

## References

- [actions/setup-python](https://github.com/actions/setup-python)
- [astral-sh/setup-uv](https://github.com/astral-sh/setup-uv)
- [uv documentation](https://docs.astral.sh/uv/)
- [GitHub Actions concurrency](https://docs.github.com/en/actions/using-jobs/using-concurrency)
