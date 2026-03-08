# Workflow Comparison: pip vs uv

Quick reference for `tests.yml` vs `tests-uv.yml`

## Side-by-Side

| Aspect | tests.yml (pip) | tests-uv.yml (uv) |
| -------- | ---------------- | ------------------- |
| **Status** | Production | Experimental |
| **Dependency Manager** | pip | uv (pip-compatible) |
| **Caching** | setup-python built-in | astral-sh/setup-uv |
| **Install Command** | `pip install -e ".[test,dev]"` | `uv pip install --system -e ".[test,dev]"` |
| **Expected Speed** | Baseline | 30-50% faster |
| **Stability** | Proven | Monitor |
| **Matrix** | Smart (same) | Smart (same) |

## Key Differences

### Version A (pip)

```yaml
- name: Set up Python
  uses: actions/setup-python@v5
  with:
    python-version: "3.12"
    cache: "pip"
    cache-dependency-path: pyproject.toml

- name: Install dependencies
  run: |
    python -m pip install --upgrade pip
    pip install -e ".[test,dev]"
```

#### Pros

- Standard Python tooling
- Predictable resolution
- Well-understood behavior

#### Cons

- Slower dependency resolution
- Less efficient caching in some scenarios

---

### Version B (uv)

```yaml
- name: Set up Python
  uses: actions/setup-python@v5
  with:
    python-version: "3.12"

- name: Install uv
  uses: astral-sh/setup-uv@v4
  with:
    enable-cache: true

- name: Install dependencies
  run: |
    uv pip install --system -e ".[test,dev]"
```

#### Pros

- Faster dependency resolution (Rust-based)
- Modern caching
- pip-compatible interface

**Cons:**

- Slightly different resolver logic
- Less battle-tested in production
- Need to verify PyQt5/rawpy/native deps

---

## Performance Expectations

### Typical CI Timings (estimates)

## Pull Request (full matrix: 3 OS × 2 Python = 6 jobs)

| Stage | pip | uv | Δ |
| --- | --- | --- | --- |
| Checkout | ~5s | ~5s | — |
| Setup Python | ~10s | ~10s | — |
| Install deps | ~60s | ~35s | **-40%** |
| Run tests | ~180s | ~180s | — |
| **Total per job** | ~255s | ~230s | **-10%** |
| **Total PR (parallel)** | ~4-5 min | ~3.5-4 min | **-15%** |

## Push (light matrix: 2 jobs)

| Stage | pip | uv | Δ |
| --- | --- | --- | --- |
| Total per job | ~255s | ~230s | -10% |
| **Total push (parallel)** | ~4-5 min | ~3.5-4 min | **-15%** |

*Note: Actual times vary based on cache hits, runner load, network.*

---

## Testing Strategy

### Phase 1: Parallel Runs (Current)

- Keep both workflows active
- Run on same branches/commits
- Compare:
  - Total runtime
  - Cache behavior
  - Dependency versions installed
  - Test results (must match exactly)

### Phase 2: Evaluation (2-3 weeks)

- Monitor for:
  - Resolution differences
  - Edge cases with PyQt5/rawpy
  - Cache stability
  - Any test flakiness

### Phase 3: Decision

- **If uv proves stable:**
  - Promote `tests-uv.yml` to `tests.yml`
  - Archive old workflow
- **If issues found:**
  - Keep experimenting
  - Report upstream to astral-sh/uv
  - Stick with pip for now

---

## What to Watch For

### Green Flags ✓

- Same test results across both workflows
- Faster CI runs with uv
- No dependency resolution surprises
- Cache hits consistent

### Red Flags ✗

- Different versions resolved
- Tests pass on pip, fail on uv (or vice versa)
- Mysterious cache misses
- Platform-specific failures with uv

---

## Quick Commands

### Compare installed packages

```bash
# In workflow logs, compare:
pip list --format=freeze > pip-freeze.txt
uv pip list --format=freeze > uv-freeze.txt
diff pip-freeze.txt uv-freeze.txt
```

### Check cache sizes

```bash
# Look in workflow logs for:
# pip: "Cache restored from key: ..."
# uv: "Cache restored from key: ..."
```

### Force no cache (testing)

```yaml
# In workflow, temporarily:
cache: false  # for pip
enable-cache: false  # for uv
```

---

## Migration Checklist

When ready to fully switch to uv:

- [ ] Run both workflows for 2+ weeks
- [ ] Compare 10+ CI runs
- [ ] Verify cross-platform consistency
- [ ] Check native deps (PyQt5, rawpy) install correctly
- [ ] Confirm no resolution differences
- [ ] Test locally with uv on all target platforms
- [ ] Update developer docs to mention uv option
- [ ] Rename `tests-uv.yml` → `tests.yml`
- [ ] Archive old `tests.yml` → `tests-pip-legacy.yml`
- [ ] Update README badges (if any)

---

## Benchmarking Template

Use this to track actual performance data. Copy this table and fill in results from workflow runs.

### PR Run Comparison

**Run Date:** `[YYYY-MM-DD]`

| Metric | tests.yml (pip) | tests-uv.yml (uv) | Δ | Notes |
| ------ | --------------- | ----------------- | - | ----- |
| **Lint (Ubuntu 3.12)** | | | | |
| — Clock time | `__m __s` | `__m __s` | — | From workflow logs |
| — Cache hit | Y/N | Y/N | — | Check logs |
| **Typecheck (Ubuntu 3.12)** | | | | |
| — Clock time | `__m __s` | `__m __s` | — | From workflow logs |
| — Cache hit | Y/N | Y/N | — | Check logs |
| **Tests (Ubuntu 3.12)** | | | | |
| — Clock time | `__m __s` | `__m __s` | — | From workflow logs |
| — Tests passed | Y/N | Y/N | ✓/✗ | Must match |
| **Tests (Windows 3.12)** | | | | |
| — Clock time | `__m __s` | `__m __s` | — | From workflow logs |
| — Tests passed | Y/N | Y/N | ✓/✗ | Must match |
| **Tests (macOS 3.13)** | | | | |
| — Clock time | `__m __s` | `__m __s` | — | From workflow logs |
| — Tests passed | Y/N | Y/N | ✓/✗ | Must match |
| **Total PR (6 jobs parallel)** | `_m _s` | `_m _s` | **%** | Overall result |

### Push Run Comparison

**Run Date:** `[YYYY-MM-DD]`

| Metric | tests.yml (pip) | tests-uv.yml (uv) | Δ | Notes |
| ------ | --------------- | ----------------- | - | ----- |
| **Lint (Ubuntu 3.12)** | | | | |
| — Clock time | `__m __s` | `__m __s` | — | Lightweight |
| **Typecheck (Ubuntu 3.12)** | | | | |
| — Clock time | `__m __s` | `__m __s` | — | Lightweight |
| **Tests (Ubuntu 3.12)** | | | | |
| — Clock time | `__m __s` | `__m __s` | — | Fast feedback |
| — Tests passed | Y/N | Y/N | ✓/✗ | Must match |
| **Tests (Windows 3.12)** | | | | |
| — Clock time | `__m __s` | `__m __s` | — | Platform coverage |
| — Tests passed | Y/N | Y/N | ✓/✗ | Must match |
| **Total push (2 jobs parallel)** | `_m _s` | `_m _s` | **%** | Overall result |

### Dependency Resolution Check

**Run Date:** `[YYYY-MM-DD]`

#### Installed Packages (pip)

```bash
pip list --format=freeze | head -10
```

#### Installed Packages (uv)

```bash
uv pip list --format=freeze | head -10
```

#### Differences

```bash
diff <(pip list --format=freeze | sort) \
     <(uv pip list --format=freeze | sort)
```

**Result:** ✓ Identical / ⚠️ Minor differences / ✗ Major differences

**If differences found:**

- [ ] All versions match (or differences are expected)
- [ ] Critical deps same (PyQt5, pytest, ruff, mypy)
- [ ] Native deps OK (rawpy, Pillow, etc.)

### Observations & Issues

**Test Stability:**

- [ ] All tests pass consistently with pip
- [ ] All tests pass consistently with uv
- [ ] No flaky tests on either
- [ ] No platform-specific failures

**Cache Behavior:**

- [ ] Pip cache hit rate: `__%`
- [ ] uv cache hit rate: `__%`
- [ ] Cache sizes comparable
- [ ] No mysterious misses

**Speed Improvement:**

- [ ] PR time improved: `_%` ✓
- [ ] Push time improved: `_%` ✓
- [ ] Dependency install faster: `_%` ✓
- [ ] Overall speedup: `_%` (target: 10-15%)

**Edge Cases Found:**

- [ ] PyQt5 install: OK / Issues: `____`
- [ ] rawpy install: OK / Issues: `____`
- [ ] Pillow install: OK / Issues: `____`
- [ ] exiftool: OK / Issues: `____`
- [ ] Qt plugins: OK / Issues: `____`

**Recommendation After This Run:**

- [ ] Continue testing (more data needed)
- [ ] Try again with different OS/Python
- [ ] Investigate issues found
- [ ] Ready for migration (if all green)

---

## How to Use Benchmarking Template

1. **Run both workflows** on same commits (multiple times)
2. **Collect timing data** from Actions tab (3-5 runs each)
3. **Average the numbers** (ignore outliers)
4. **Check dependencies** with `pip list` vs `uv pip list`
5. **Document observations** in "Edge Cases Found"
6. **Share results** in project documentation

## Target: 10 data points per scenario before decision

---

## FAQ

**Q: Can I use both workflows at once?**
A: Yes, they run independently. Useful for comparison.

**Q: Which should I trust for production?**
A: Currently `tests.yml` (pip). Wait for uv stability proof.

**Q: What if uv installs different versions?**
A: Check `uv pip list` vs `pip list`. Report if unexpected. May need to pin versions.

**Q: Can I use uv locally?**
A: Yes. `pip install uv`, then `uv pip install -e ".[dev]"`. Not required.

**Q: Is uv replacing pip?**
A: Not officially. It's pip-compatible but not a drop-in. Python packaging landscape evolving.

**Q: What about Poetry/PDM/Hatch?**
A: Out of scope. oncutf uses setuptools + pyproject.toml. uv is compatible with this.

---

## Recommendation

**For now:**

- Use `tests.yml` as primary
- Enable `tests-uv.yml` on experiment branches
- Monitor both if time permits

**Goal:**

- Validate uv stability
- Gain CI speed benefits if safe
- No rush — correctness > speed
