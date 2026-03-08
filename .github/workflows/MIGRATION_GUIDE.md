# uv Migration Guide for oncutf

Practical guide for migrating from pip to uv in CI/CD (when ready).

---

## Current Status: Phase 0 (Setup)

✓ Both workflows exist (`tests.yml` and `tests-uv.yml`)
✓ Can run in parallel for comparison
⏳ Waiting for stability validation

---

## Phase 1: Validation (2-4 weeks)

### Goals

- Prove uv stability in CI
- Compare performance
- Identify edge cases

### Actions

1. **Enable both workflows**

   ```bash
   git checkout develop
   # Both tests.yml and tests-uv.yml will run
   ```

2. **Monitor workflow runs**
   - Go to Actions tab
   - Compare runtime between pip and uv variants
   - Check for failures

3. **Compare dependency resolution**

   ```bash
   # In workflow logs, check installed packages
   # Look for differences in versions
   ```

4. **Track metrics**

   | Metric | tests.yml | tests-uv.yml | Notes |
   | ------ | --------- | ------------ | ----- |
   | Avg runtime (PR) | ? | ? | Target: 15-20% faster |
   | Avg runtime (push) | ? | ? | Target: 15-20% faster |
   | Failure rate | ? | ? | Must be equal |
   | Cache hit rate | ? | ? | Should be similar |

### Success Criteria

- [ ] 20+ successful uv workflow runs
- [ ] No test result differences between pip and uv
- [ ] No dependency resolution surprises
- [ ] 10%+ speed improvement
- [ ] Cross-platform stability (Linux/macOS/Windows)

---

## Phase 2: Gradual Adoption (1-2 weeks)

### Goals

- Use uv as primary on feature branches
- Keep pip as fallback

### Actions

1. **Make tests-uv.yml the default for feature branches**

   ```yaml
   # In tests-uv.yml, change triggers:
   on:
     push:
       branches: [ main, develop, 'feature/**' ]
     pull_request:
       branches: [ main, develop ]
   ```

2. **Keep tests.yml for main/develop only**

   ```yaml
   # In tests.yml, restrict triggers:
   on:
     push:
       branches: [ main, develop ]
     pull_request:
       branches: [ main ]
   ```

3. **Monitor for issues**
   - Watch for feature branch failures
   - Compare with main/develop (still using pip)

### Success Criteria

- [ ] Feature branches run smoothly with uv
- [ ] No regression in stability
- [ ] Developer feedback positive

---

## Phase 3: Full Migration (1 week)

### Goals

- Make uv the primary CI tool
- Archive pip workflow as legacy

### Actions

1. **Rename workflows**

   ```bash
   cd .github/workflows
   mv tests.yml tests-pip-legacy.yml
   mv tests-uv.yml tests.yml
   git add .
   git commit -m "Migrate CI to uv as primary dependency manager"
   ```

2. **Update workflow trigger**

   ```yaml
   # In tests.yml (formerly tests-uv.yml):
   on:
     push:
       branches: [ main, develop ]
     pull_request:
       branches: [ main, develop ]
   ```

3. **Disable legacy workflow**

   ```yaml
   # In tests-pip-legacy.yml, add comment at top:
   # LEGACY: Kept for reference. Use tests.yml (uv-based) instead.
   # To manually trigger this workflow, use workflow_dispatch.
   ```

4. **Update documentation**
   - Update README.md to mention uv
   - Update DEVELOPMENT.md if exists
   - Update copilot-instructions.md

### Success Criteria

- [ ] New main workflow is uv-based
- [ ] All team members notified
- [ ] Documentation updated
- [ ] Legacy workflow archived (not deleted)

---

## Phase 4: Optimization (Ongoing)

### Goals

- Fine-tune uv for maximum benefit
- Explore advanced features

### Potential Optimizations

#### 1. Use uv extras more efficiently

```yaml
# Split pyproject.toml extras:
[project.optional-dependencies]
lint = ["ruff"]
typecheck = ["mypy", "PyQt5-stubs"]
test = ["pytest", "pytest-qt", "pytest-mock"]
dev = ["ruff", "mypy", "pytest", "pytest-qt", "pytest-mock", "vulture"]

# Then in workflows:
- name: Install lint dependencies
  run: uv pip install --system -e ".[lint]"

- name: Install typecheck dependencies
  run: uv pip install --system -e ".[typecheck]"
```

#### 2. Consider lockfile (advanced)

```bash
# Generate lockfile (optional, for maximum reproducibility)
uv pip compile pyproject.toml -o requirements.lock

# In workflow:
uv pip install --system -r requirements.lock
```

**⚠️ Warning:** Lockfiles add maintenance overhead. Only if needed.

#### 3. Explore uv sync (project mode)

```yaml
# Full uv project mode (most advanced)
- name: Sync project with uv
  run: uv sync

- name: Run tests
  run: uv run pytest tests/
```

**⚠️ Warning:** This is a bigger migration. Requires full uv project setup.

---

## Rollback Plan

If issues arise, rollback is simple:

```bash
cd .github/workflows
mv tests.yml tests-uv-experimental.yml
mv tests-pip-legacy.yml tests.yml
git add .
git commit -m "Rollback to pip-based CI due to [REASON]"
git push
```

---

## Decision Points

### When to stay on pip

- uv causes dependency resolution issues
- Team not comfortable with new tooling
- PyQt5/rawpy compatibility problems
- No clear performance benefit

### When to adopt uv

- 15%+ CI speedup confirmed
- No stability issues over 4+ weeks
- Team comfortable with tooling
- Dependency resolution matches pip

### When to consider full uv project mode

- Want lockfile-based reproducibility
- Need faster local development installs
- Ready for full Python toolchain migration
- Have time to refactor dev workflow

---

## Local Development Impact

Developers can choose:

### Option 1: Stay on pip (default)

```bash
pip install -e ".[dev]"
```

### Option 2: Use uv

```bash
pip install uv
uv pip install -e ".[dev]"
```

### Option 3: Full uv (advanced)

```bash
pip install uv
uv sync
```

#### Recommendation

Keep pip as default for devs. uv is optional.

---

## Troubleshooting

### uv installs different versions

```bash
# Check what changed:
pip list --format=freeze > pip-versions.txt
uv pip list --format=freeze > uv-versions.txt
diff pip-versions.txt uv-versions.txt

# If critical differences found:
# 1. Pin versions in pyproject.toml
# 2. Report to astral-sh/uv if unexpected
```

### Tests fail only with uv

```bash
# Debug locally:
python -m venv test-uv
source test-uv/bin/activate
pip install uv
uv pip install -e ".[test,dev]"
pytest tests/ -v

# Compare with pip:
python -m venv test-pip
source test-pip/bin/activate
pip install -e ".[test,dev]"
pytest tests/ -v
```

### Cache issues

```yaml
# Try disabling cache temporarily:
- name: Install uv
  uses: astral-sh/setup-uv@v4
  with:
    enable-cache: false  # Disable to test
```

### Platform-specific failures

```bash
# Check which OS fails:
# - Linux: likely system deps
# - Windows: likely path issues
# - macOS: likely brew deps

# Verify exiftool installation in logs
```

---

## Communication Plan

### Before Migration

- [ ] Notify team of testing phase
- [ ] Share this guide
- [ ] Explain benefits and risks
- [ ] Set timeline expectations

### During Migration

- [ ] Regular updates on progress
- [ ] Share metrics (speed, stability)
- [ ] Address concerns promptly
- [ ] Keep rollback plan visible

### After Migration

- [ ] Announce completion
- [ ] Share before/after metrics
- [ ] Update all documentation
- [ ] Celebrate faster CI 🎉 (without emoji in actual workflow)

---

## Timeline Example

| Week | Phase | Activity |
| --- | --- | --- |
| 1-2 | Phase 0 | Setup both workflows |
| 3-5 | Phase 1 | Validate uv stability |
| 6 | Phase 2 | Gradual adoption |
| 7 | Phase 3 | Full migration |
| 8+ | Phase 4 | Optimize |

**Total: ~2 months** from start to full adoption.

---

## Success Metrics

At the end, measure:

- [ ] CI runtime reduced by 15%+
- [ ] No increase in failure rate
- [ ] Developer satisfaction maintained or improved
- [ ] Documentation updated
- [ ] Team confident in new tooling

---

## Not Recommended

- ❌ Switching to uv without validation period
- ❌ Deleting pip workflow immediately
- ❌ Forcing devs to use uv locally
- ❌ Adopting full uv project mode without team buy-in
- ❌ Ignoring resolution differences

---

## Resources

- [uv documentation](https://docs.astral.sh/uv/)
- [setup-uv action](https://github.com/astral-sh/setup-uv)
- [uv GitHub discussions](https://github.com/astral-sh/uv/discussions)
- [oncutf PROJECT_RULES.md](../../PROJECT_RULES.md)

---

## Questions?

For oncutf-specific questions, check:

- `.github/workflows/README.md` — Overview
- `.github/workflows/COMPARISON.md` — pip vs uv comparison
- This file — Migration guide

For uv questions, check:

- [uv docs](https://docs.astral.sh/uv/)
- [GitHub issues](https://github.com/astral-sh/uv/issues)
